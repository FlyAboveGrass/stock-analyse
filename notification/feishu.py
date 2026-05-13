import os
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Iterable, Any
from datetime import datetime, timedelta, date

from config.monitor_list import load_monitor_list

logger = logging.getLogger(__name__)

EASTMONEY_BATCH_QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
EASTMONEY_GLOBAL_INDEX_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_BATCH_FIELDS = "f12,f14,f2,f3"
EASTMONEY_BATCH_UT = "f057cbcbce2a86e2866ab8877db1d059"
REQUEST_TIMEOUT = 5


MONITOR_LIST = load_monitor_list()


def get_stock_data(code: str, stock_type: str):
    """根据股票类型获取历史数据"""
    import akshare as ak
    
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
    cutoff_date_str = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    cutoff_date = date.today() - timedelta(days=60)
    
    if stock_type == "etf":
        hist = None

        try:
            hist = ak.fund_etf_hist_em(
                symbol=code,
                period='daily',
                start_date=start_date,
                end_date=end_date
            )
            if hist is None or len(hist) == 0:
                hist = ak.fund_etf_hist_em(symbol=code, period='daily')

            if hist is not None and len(hist) > 0:
                if '日期' in hist.columns:
                    hist = hist[hist['日期'] >= cutoff_date_str]
                return hist, '收盘'
        except Exception:
            pass

        try:
            market_code = f"{'sh' if code.startswith('5') else 'sz'}{code}"
            hist = ak.fund_etf_hist_sina(symbol=market_code)

            if hist is not None and len(hist) > 0:
                hist = hist.rename(columns={'date': '日期', 'close': '收盘'})
                if '日期' in hist.columns:
                    hist = hist[hist['日期'] >= cutoff_date]
                return hist, '收盘'
        except Exception:
            pass

        return None, None
    
    elif stock_type == "index":
        try:
            if code == "HSI":
                try:
                    hist = ak.stock_hk_index_daily_em(symbol="HSI")
                    if hist is not None and len(hist) > 0:
                        hist = hist.rename(columns={"date": "日期", "latest": "收盘"})
                        if "日期" in hist.columns:
                            hist["日期"] = hist["日期"].astype(str)
                            hist = hist[hist["日期"] >= cutoff_date_str]
                        return hist, "收盘"
                except Exception:
                    pass

                hist = ak.stock_hk_index_daily_sina(symbol="HSI")
                if hist is not None and len(hist) > 0:
                    hist = hist.rename(columns={"date": "日期", "close": "收盘"})
                    if "日期" in hist.columns:
                        hist["日期"] = hist["日期"].astype(str)
                        hist = hist[hist["日期"] >= cutoff_date_str]
                    return hist, "收盘"
                return None, None

            index_code = code.replace(".", "").replace("SH", "").replace("sz", "")
            hist = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            
            if hist is not None and len(hist) > 0:
                if 'date' in hist.columns:
                    hist = hist[hist['date'] >= cutoff_date]
                    hist = hist.rename(columns={'date': '日期', 'close': '收盘'})
                elif '日期' in hist.columns:
                    hist = hist[hist['日期'] >= cutoff_date]
            return hist, '收盘'
        except Exception as e:
            return None, None
    
    elif stock_type == "hk":
        try:
            hk_code = code.replace(".HK", "").replace(".hk", "")
            hist = ak.stock_hk_daily(symbol=hk_code, adjust="qfq")

            if hist is not None and len(hist) > 0:
                hist = hist.rename(columns={"date": "日期", "close": "收盘"})
                if "日期" in hist.columns:
                    hist["日期"] = hist["日期"].astype(str)
                    hist = hist[hist["日期"] >= cutoff_date_str]
                return hist, "收盘"

            return None, None
        except Exception:
            return None, None

    else:
        try:
            if code.startswith('6'):
                market_code = f"sh{code}"
            else:
                market_code = f"sz{code}"
            
            try:
                hist = ak.stock_zh_a_hist_tx(symbol=market_code)
                if hist is not None and len(hist) > 0:
                    hist = hist.rename(columns={
                        'date': '日期',
                        'close': '收盘',
                        'open': '开盘',
                        'high': '最高',
                        'low': '最低',
                        'amount': '成交额'
                    })
                    if '日期' in hist.columns:
                        cutoff = date.today() - timedelta(days=60)
                        hist = hist[hist['日期'] >= cutoff]
                    return hist, '收盘'
            except:
                pass
            
            try:
                hist = ak.stock_zh_a_hist(
                    symbol=market_code,
                    period="daily",
                    adjust="qfq"
                )
                
                if hist is not None and len(hist) > 0:
                    if '日期' in hist.columns:
                        cutoff = date.today() - timedelta(days=60)
                        hist = hist[hist['日期'] >= cutoff]
                    return hist, '收盘'
            except:
                pass
            
            return None, None
        except Exception as e:
            return None, None


def calculate_ma(prices, period: int = 20) -> float:
    """计算MA"""
    import pandas as pd
    if len(prices) < period:
        return None
    ma = prices.rolling(window=period).mean().iloc[-1]
    return float(ma)


def _quote_lookup_key(code: str, stock_type: str) -> str:
    """将监控项代码映射成实时行情返回中的查找键。"""
    if stock_type == "index" and code != "HSI":
        return code.split(".")[0]
    if stock_type == "hk":
        return code.split(".")[0]
    return code


def _quote_secid(code: str, stock_type: str) -> str:
    """将监控项代码映射成东财行情接口的 secid。"""
    if stock_type == "index":
        if code == "HSI":
            return "100.HSI"
        base_code, market = code.split(".")
        return f"{1 if market.upper() == 'SH' else 0}.{base_code}"

    if code.startswith(("5", "6")):
        return f"1.{code}"
    return f"0.{code}"


def _iter_quote_items(diff: Any) -> Iterable[Dict[str, Any]]:
    """兼容东财 diff 既可能是 list 也可能是 dict 的返回。"""
    if isinstance(diff, dict):
        return diff.values()
    if isinstance(diff, list):
        return diff
    return []


def _coerce_quote_value(value: Any, scale: float = 1.0) -> Optional[float]:
    """将行情接口字段转换为 float，无法转换时返回 None。"""
    if value in (None, "", "-"):
        return None

    try:
        result = float(value) / scale
    except (TypeError, ValueError):
        return None

    if result != result:
        return None
    return result


def _normalize_display_name(value: Any) -> Optional[str]:
    """标准化展示名称，空值返回 None。"""
    if value is None:
        return None

    name = str(value).strip()
    return name or None


def _build_quote(
    price_value: Any,
    change_pct_value: Any,
    scale: float = 1.0,
    name_value: Any = None,
) -> Optional[Dict[str, float]]:
    """将东财返回构造成统一的实时行情结构。"""
    price = _coerce_quote_value(price_value, scale=scale)
    change_pct = _coerce_quote_value(change_pct_value, scale=scale)

    if price is None:
        return None

    quote = {
        "price": price,
        "change_pct": change_pct if change_pct is not None else 0.0,
    }
    display_name = _normalize_display_name(name_value)
    if display_name:
        quote["name"] = display_name

    return quote


def _resolve_report_stock_name(stock: Dict[str, str], realtime_quote: Optional[Dict[str, float]]) -> str:
    """日报优先展示实时行情中的正式名称，其次回退到监控列表名称。"""
    if realtime_quote:
        realtime_name = _normalize_display_name(realtime_quote.get("name"))
        if realtime_name:
            return realtime_name

    stock_name = _normalize_display_name(stock.get("name"))
    return stock_name or stock["code"]


def get_target_realtime_quotes(
    monitor_list: Optional[Iterable[Dict[str, str]]] = None,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """按监控列表批量获取实时行情，避免全市场拉表。"""
    monitor_list = list(monitor_list or MONITOR_LIST)

    quotes = {
        "etf": {},
        "stock": {},
        "index": {},
        "hk": {},
    }

    mainland_monitors = []
    mainland_code_to_type: Dict[str, str] = {}
    has_hsi = False
    hk_codes = set()

    for stock in monitor_list:
        if stock["type"] == "hk":
            hk_codes.add(_quote_lookup_key(stock["code"], stock["type"]))
            continue

        secid = _quote_secid(stock["code"], stock["type"])
        if secid == "100.HSI":
            has_hsi = True
            continue

        mainland_monitors.append(secid)
        mainland_code_to_type[_quote_lookup_key(stock["code"], stock["type"])] = stock["type"]

    if mainland_monitors:
        params = {
            "ut": EASTMONEY_BATCH_UT,
            "fltt": "2",
            "invt": "2",
            "fields": EASTMONEY_BATCH_FIELDS,
            "secids": ",".join(mainland_monitors) + ",?v=08926209912590994",
        }
        try:
            response = requests.get(
                EASTMONEY_BATCH_QUOTE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            data_json = response.json()
            for item in _iter_quote_items(data_json.get("data", {}).get("diff")):
                code = str(item.get("f12", ""))
                stock_type = mainland_code_to_type.get(code)
                if not stock_type:
                    continue

                quote = _build_quote(item.get("f2"), item.get("f3"), name_value=item.get("f14"))
                if quote is not None:
                    quotes[stock_type][code] = quote
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.warning("批量获取沪深实时行情失败: %s", exc)

    if has_hsi:
        params = {
            "np": "2",
            "fltt": "1",
            "invt": "2",
            "fs": "i:100.HSI",
            "fields": "f12,f14,f2,f3",
            "fid": "f3",
            "pn": "1",
            "pz": "10",
            "po": "1",
            "dect": "1",
            "wbp2u": "|0|0|0|web",
        }
        try:
            response = requests.get(
                EASTMONEY_GLOBAL_INDEX_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            data_json = response.json()
            for item in _iter_quote_items(data_json.get("data", {}).get("diff")):
                if str(item.get("f12", "")) != "HSI":
                    continue

                quote = _build_quote(item.get("f2"), item.get("f3"), scale=100, name_value=item.get("f14"))
                if quote is not None:
                    quotes["index"]["HSI"] = quote
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.warning("获取恒生指数实时行情失败: %s", exc)

    if hk_codes:
        try:
            import akshare as ak

            hk_spot = ak.stock_hk_spot_em()
            for _, item in hk_spot.iterrows():
                code = str(item.get("代码", "")).zfill(5)
                if code not in hk_codes:
                    continue

                quote = _build_quote(item.get("最新价"), item.get("涨跌幅"), name_value=item.get("名称"))
                if quote is not None:
                    quotes["hk"][code] = quote
        except Exception as exc:
            logger.warning("获取港股实时行情失败: %s", exc)

    return quotes


def get_realtime_quotes(
    monitor_list: Optional[Iterable[Dict[str, str]]] = None,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """兼容旧调用，实际只拉取监控列表中的实时行情。"""
    return get_target_realtime_quotes(monitor_list or MONITOR_LIST)


def get_realtime_quote(
    realtime_quotes: Dict[str, Dict[str, Dict[str, float]]], code: str, stock_type: str
) -> Optional[Dict[str, float]]:
    """从快照映射中获取单个标的的实时行情"""
    return realtime_quotes.get(stock_type, {}).get(_quote_lookup_key(code, stock_type))


def _display_date_str(value: Any) -> str:
    """将 DataFrame 中的日期统一格式化成 YYYY-MM-DD。"""
    return str(value)[:10]


def _build_report_points(hist_sorted, price_col: str, days: int, report_date: date, realtime_quote):
    """构建日报展示窗口，必要时补入当天实时价。"""
    if hist_sorted.empty:
        return []

    last_hist_date = _display_date_str(hist_sorted.iloc[-1]["日期"])
    report_date_str = report_date.isoformat()
    use_live_quote = realtime_quote is not None and report_date.weekday() < 5

    if use_live_quote and last_hist_date < report_date_str:
        start_idx = max(len(hist_sorted) - (days - 1), 0)
        points = [
            {
                "display_date": _display_date_str(hist_sorted.iloc[idx]["日期"]),
                "hist_idx": idx,
                "close_price": hist_sorted.iloc[idx][price_col],
                "realtime_quote": None,
            }
            for idx in range(start_idx, len(hist_sorted))
        ]
        points.append(
            {
                "display_date": report_date_str,
                "hist_idx": len(hist_sorted),
                "close_price": realtime_quote["price"],
                "realtime_quote": realtime_quote,
            }
        )
        return points

    start_idx = max(len(hist_sorted) - days, 0)
    points = []
    for idx in range(start_idx, len(hist_sorted)):
        point_quote = None
        close_price = hist_sorted.iloc[idx][price_col]
        if use_live_quote and idx == len(hist_sorted) - 1 and last_hist_date == report_date_str:
            close_price = realtime_quote["price"]
            point_quote = realtime_quote

        points.append(
            {
                "display_date": _display_date_str(hist_sorted.iloc[idx]["日期"]),
                "hist_idx": idx,
                "close_price": close_price,
                "realtime_quote": point_quote,
            }
        )

    return points


def _fetch_report_stock_data(stock: Dict[str, str]):
    """获取单个监控项的历史数据，供线程池并发使用。"""
    hist, price_col = get_stock_data(stock["code"], stock["type"])
    return stock, hist, price_col


class FeishuNotifier:
    """飞书机器人通知器"""
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        monitor_list: Optional[Iterable[Dict[str, str]]] = None,
    ):
        self.webhook_url = webhook_url or os.getenv('FEISHU_WEBHOOK_URL')
        self.monitor_list = list(monitor_list) if monitor_list is not None else None
        
        if not self.webhook_url:
            raise ValueError("FEISHU_WEBHOOK_URL 必须设置")
    
    def send(self, message: str, msg_type: str = "text") -> bool:
        payload = {
            "msg_type": msg_type,
            "content": {}
        }
        
        if msg_type == "text":
            payload["content"] = {"text": message}
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=30)
            result = response.json()
            
            if result.get('code') is None or result.get('code') == 0:
                logger.info(f"飞书消息发送成功")
                return True
            else:
                logger.error(f"飞书发送失败: {result.get('msg')}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"飞书请求异常: {e}")
            return False
    
    def send_signal(self, signal) -> bool:
        emoji = "🚀" if signal.direction == "breakout" else "🔻"
        direction_text = "突破" if signal.direction == "breakout" else "跌破"
        
        message = f"""{emoji} *{signal.symbol}* {direction_text} 20日均线

• 现价: {signal.price:.2f}
• MA20: {signal.ma20:.2f}
• 位置: {"多头" if signal.position_type == "above" else "空头"}
• 时间: {signal.timestamp}"""
        
        return self.send(message)
    
    def send_text(self, text: str) -> bool:
        return self.send(text, msg_type="text")
    
    def send_daily_report(self, days: int = 3) -> bool:
        """发送每日MA20监控报告"""
        
        report_data = self._generate_report(days)
        
        if not report_data:
            return self.send("⚠️ 未能获取到任何股票数据")
        
        message = self._build_report_message(report_data, days)
        return self.send(message)
    
    def _generate_report(self, days: int) -> Dict:
        """生成报告数据"""
        import pandas as pd

        monitor_list = self.monitor_list if self.monitor_list is not None else MONITOR_LIST
        
        report = {
            "dates": [],
            "stocks": []
        }
        report_date = date.today()
        realtime_quotes = get_target_realtime_quotes(monitor_list)

        max_workers = min(8, max(1, len(monitor_list)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            stock_results = list(executor.map(_fetch_report_stock_data, monitor_list))

        for stock, hist, price_col in stock_results:
            realtime_quote = get_realtime_quote(
                realtime_quotes, stock["code"], stock["type"]
            )
            stock_data = {
                "name": _resolve_report_stock_name(stock, realtime_quote),
                "code": stock["code"],
                "statuses": []
            }
            
            try:
                if hist is None or len(hist) == 0:
                    stock_data["statuses"] = [f"❌ 数据获取失败"] * days
                    report["stocks"].append(stock_data)
                    continue
                
                if 'date' in hist.columns and '日期' not in hist.columns:
                    hist = hist.rename(columns={'date': '日期'})
                
                if '日期' not in hist.columns:
                    stock_data["statuses"] = [f"❌ 格式错误"] * days
                    report["stocks"].append(stock_data)
                    continue
                
                hist_sorted = hist.sort_values('日期').reset_index(drop=True)
                report_points = _build_report_points(
                    hist_sorted,
                    price_col,
                    days,
                    report_date,
                    realtime_quote,
                )

                if not report["dates"] and len(report_points) >= days:
                    report["dates"] = [point["display_date"] for point in report_points[-days:]]

                if len(report_points) < days:
                    stock_data["statuses"] = [f"❌ 数据不足"] * days
                    report["stocks"].append(stock_data)
                    continue
                
                for point in report_points:
                    full_idx = point["hist_idx"]
                    close_price = point["close_price"]
                    point_quote = point["realtime_quote"]

                    if point_quote and point_quote.get("change_pct") is not None:
                        change_str = f"{point_quote['change_pct']:+.2f}%"
                    elif full_idx > 0:
                        prev_price = hist_sorted.iloc[full_idx - 1][price_col]
                        change_pct = (close_price - prev_price) / prev_price * 100
                        change_str = f"{change_pct:+.2f}%"
                    else:
                        change_str = "—"
                    
                    ma20 = None
                    if full_idx >= 19:
                        if point_quote:
                            prior_prices = hist_sorted.iloc[full_idx - 19 : full_idx][price_col].tolist()
                            ma20_data = pd.Series(prior_prices + [close_price])
                        else:
                            ma20_data = hist_sorted.iloc[full_idx - 19 : full_idx + 1][price_col]
                        ma20 = calculate_ma(ma20_data, period=20)
                    
                    if ma20:
                        is_above = close_price > ma20
                        status = f"{'✅' if is_above else '⬇️'} {change_str}"
                        stock_data["statuses"].append(status)
                    else:
                        stock_data["statuses"].append("❌")
                
                while len(stock_data["statuses"]) < days:
                    stock_data["statuses"].append("❌")
                    
            except Exception as e:
                stock_data["statuses"] = [f"❌ 错误"] * days
            
            report["stocks"].append(stock_data)
        
        return report
    
    def _build_report_message(self, report: Dict, days: int) -> str:
        """构建报告消息"""
        dates = report.get("dates", [])

        date_line = " | ".join(str(d) for d in dates) if dates else f"最近 {days} 个交易日"

        rows = []
        for stock in report["stocks"]:
            statuses = " | ".join(stock["statuses"])
            row = f"{stock['name']}: {statuses}"
            rows.append(row)

        body = "\n".join(rows) if rows else "暂无监控数据"

        message = (
            "A股/港股/ETF MA20均线监控\n"
            f"日期: {date_line}\n\n"
            f"{body}\n\n"
            "数据来源: AkShare (东方财富)\n"
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return message
    
    def test(self) -> bool:
        return self.send("✅ 飞书机器人连接测试成功")
