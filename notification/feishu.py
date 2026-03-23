import os
import logging
import requests
from typing import Optional, List, Dict
from datetime import datetime, timedelta, date

logger = logging.getLogger(__name__)


MONITOR_LIST = [
    {"code": "516020", "name": "化工ETF", "type": "etf"},
    {"code": "560590", "name": "A500红利", "type": "etf"},
    {"code": "512800", "name": "银行ETF", "type": "etf"},
    {"code": "518880", "name": "黄金ETF", "type": "etf"},
    {"code": "513180", "name": "恒生科技ETF", "type": "etf"},
    {"code": "512400", "name": "有色金属ETF", "type": "etf"},
    {"code": "516010", "name": "游戏ETF", "type": "etf"},
    {"code": "512930", "name": "AI智能", "type": "etf"},
    {"code": "515790", "name": "光伏ETF", "type": "etf"},
    {"code": "159995", "name": "芯片ETF", "type": "etf"},
    {"code": "516780", "name": "稀土ETF", "type": "etf"},
    {"code": "562500", "name": "机器人ETF", "type": "etf"},
    {"code": "513520", "name": "日经ETF", "type": "etf"},
    {"code": "000001.SH", "name": "上证指数", "type": "index"},
    {"code": "000905.SH", "name": "中证500", "type": "index"},
    {"code": "000688.SH", "name": "科创50", "type": "index"},
    {"code": "HSI", "name": "恒生指数", "type": "index"},
    {"code": "002050", "name": "三花智控", "type": "stock"},
    {"code": "600519", "name": "贵州茅台", "type": "stock"},
    {"code": "300750", "name": "宁德时代", "type": "stock"},
    {"code": "688981", "name": "中芯国际", "type": "stock"},
    {"code": "600111", "name": "北方稀土", "type": "stock"},
    {"code": "000592", "name": "平潭发展", "type": "stock"},
]


def get_stock_data(code: str, stock_type: str):
    """根据股票类型获取历史数据"""
    import akshare as ak
    
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
    cutoff_date_str = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    cutoff_date = date.today() - timedelta(days=60)
    
    if stock_type == "etf":
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
    
    elif stock_type == "index":
        try:
            index_code = code.replace(".", "").replace("SH", "").replace("sz", "")
            if index_code == "HSI":
                hist = ak.stock_zh_index_daily(symbol="sh000001")
            else:
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


class FeishuNotifier:
    """飞书机器人通知器"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('FEISHU_WEBHOOK_URL')
        
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
        
        report = {
            "dates": [],
            "stocks": []
        }
        
        dates = []
        hist_test = None
        
        try:
            import akshare as ak
            hist_test = ak.fund_etf_hist_em(
                symbol="512400", 
                period="daily",
                start_date=(datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d')
            )
            hist_test = hist_test.sort_values('日期').reset_index(drop=True)
            dates = hist_test.tail(days)['日期'].tolist()
        except:
            pass
        
        report["dates"] = dates
        
        for stock in MONITOR_LIST:
            stock_data = {
                "name": stock["name"],
                "code": stock["code"],
                "statuses": []
            }
            
            try:
                hist, price_col = get_stock_data(stock["code"], stock["type"])
                
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
                recent_n = hist_sorted.tail(days + 20).copy().reset_index(drop=True)
                
                if len(recent_n) < days:
                    stock_data["statuses"] = [f"❌ 数据不足"] * days
                    report["stocks"].append(stock_data)
                    continue
                
                for i in range(len(recent_n)):
                    if i >= days:
                        break
                    
                    row = recent_n.iloc[i]
                    close_price = row[price_col]
                    
                    if i > 0:
                        prev_price = recent_n.iloc[i-1][price_col]
                        change_pct = (close_price - prev_price) / prev_price * 100
                        change_str = f"{change_pct:+.2f}%"
                    else:
                        change_str = "—"
                    
                    target_date = row['日期']
                    full_idx_list = hist_sorted[hist_sorted['日期'] == target_date].index.tolist()
                    
                    ma20 = None
                    if full_idx_list:
                        full_idx = full_idx_list[0]
                        if full_idx >= 19:
                            ma20_data = hist_sorted.iloc[full_idx-19:full_idx+1][price_col]
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
        
        header = f"## A股/ETF MA20均线监控\n\n| 股票名称 | " + " | ".join(str(d) for d in dates) + " |"
        separator = "| --- | " + " | ".join(["---"] * days) + " |"
        
        rows = []
        for stock in report["stocks"]:
            row = f"| {stock['name']}（{stock['code']}） | " + " | ".join(stock["statuses"]) + " |"
            rows.append(row)
        
        message = f"""{header}
{separator}
{chr(10).join(rows)}

---
*数据来源: AkShare (东方财富)*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""
        
        return message
    
    def test(self) -> bool:
        return self.send("✅ 飞书机器人连接测试成功")
