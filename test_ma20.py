#!/usr/bin/env python3
"""
测试脚本：生成近5日MA20均线状态表格
支持批量处理监控列表中的所有股票
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta, date

sys.path.insert(0, str(Path(__file__).parent))

import akshare as ak
from core.indicator import TechnicalIndicator


# 监控列表
MONITOR_LIST = [
    # A股ETF
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
    
    # A股指数
    {"code": "000001.SH", "name": "上证指数", "type": "index"},
    {"code": "000905.SH", "name": "中证500", "type": "index"},
    {"code": "000688.SH", "name": "科创50", "type": "index"},
    {"code": "HSI", "name": "恒生指数", "type": "index"},
    
    # A股股票
    {"code": "002050", "name": "三花智控", "type": "stock"},
    {"code": "600519", "name": "贵州茅台", "type": "stock"},
    {"code": "300750", "name": "宁德时代", "type": "stock"},
    {"code": "688981", "name": "中芯国际", "type": "stock"},
    {"code": "600111", "name": "北方稀土", "type": "stock"},
    {"code": "000592", "name": "平潭发展", "type": "stock"},
    
    # 港股
    {"code": "02020.HK", "name": "安踏体育", "type": "hk"},
    {"code": "01810.HK", "name": "小米集团-W", "type": "hk"},
    {"code": "00285.HK", "name": "比亚迪电子", "type": "hk"},
    {"code": "83690.HK", "name": "美团-WR", "type": "hk"},
    {"code": "09988.HK", "name": "阿里巴巴-W", "type": "hk"},
    {"code": "09880.HK", "name": "优必选", "type": "hk"},
]


def get_stock_data(code: str, stock_type: str):
    """根据股票类型获取历史数据"""
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
    cutoff_date_str = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    cutoff_date = date.today() - timedelta(days=60)
    
    if stock_type == "etf":
        # ETF - 使用 fund_etf_hist_em
        hist = ak.fund_etf_hist_em(
            symbol=code,
            period='daily',
            start_date=start_date,
            end_date=end_date
        )
        if hist is None or len(hist) == 0:
            # 尝试不带日期参数
            hist = ak.fund_etf_hist_em(symbol=code, period='daily')
        
        if hist is not None and len(hist) > 0:
            # ETF日期是字符串类型
            if '日期' in hist.columns:
                hist = hist[hist['日期'] >= cutoff_date_str]
        
        return hist, '收盘'
    
    elif stock_type == "index":
        # 指数 - 使用 stock_zh_index_daily
        try:
            index_code = code.replace(".", "").replace("SH", "").replace("sz", "")
            if index_code == "HSI":
                # 恒生指数
                hist = ak.stock_zh_index_daily(symbol="sh000001")
            else:
                hist = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            
            if hist is not None and len(hist) > 0:
                # 日期列是 datetime.date 类型
                if 'date' in hist.columns:
                    hist = hist[hist['date'] >= cutoff_date]
                    hist = hist.rename(columns={'date': '日期', 'close': '收盘'})
                elif '日期' in hist.columns:
                    hist = hist[hist['日期'] >= cutoff_date]
            return hist, '收盘'
        except Exception as e:
            print(f"   ⚠️ 指数获取失败: {e}")
            return None, None
    
    elif stock_type == "hk":
        # 港股 - 尝试多种接口
        try:
            hk_code = code.replace(".HK", "").replace("0", "")
            # 方法1: stock_hk_hist
            try:
                hist = ak.stock_hk_hist(
                    symbol=hk_code,
                    start_date=start_date,
                    end_date=end_date
                )
                if hist is not None and len(hist) > 0:
                    hist = hist.rename(columns={'date': '日期', 'close': '收盘'})
                    return hist, '收盘'
            except:
                pass
            
            # 方法2: 使用港股实时数据接口
            try:
                spot = ak.stock_hk_spot_em()
                stock_info = spot[spot['代码'] == hk_code]
                if len(stock_info) > 0:
                    # 实时数据只有一个点，需要其他方式获取历史
                    pass
            except:
                pass
                
            return None, None
        except Exception as e:
            print(f"   ⚠️ 港股 {code} 获取失败: {e}")
            return None, None
    
    else:
        # A股股票 - 尝试多种接口
        try:
            if code.startswith('6'):
                market_code = f"sh{code}"
            else:
                market_code = f"sz{code}"
            
            # 方法1: stock_zh_a_hist_tx (腾讯接口，更稳定)
            try:
                hist = ak.stock_zh_a_hist_tx(symbol=market_code)
                if hist is not None and len(hist) > 0:
                    # 统一列名为中文
                    hist = hist.rename(columns={
                        'date': '日期',
                        'close': '收盘',
                        'open': '开盘',
                        'high': '最高',
                        'low': '最低',
                        'amount': '成交额'
                    })
                    if '日期' in hist.columns:
                        # 日期列可能是 datetime.date 类型，需要转换
                        cutoff = date.today() - timedelta(days=60)
                        hist = hist[hist['日期'] >= cutoff]
                    return hist, '收盘'
            except Exception as e:
                pass
            
            # 方法2: stock_zh_a_hist (不带日期参数)
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
            print(f"   ⚠️ A股 {code} 获取失败: {e}")
            return None, None


def generate_ma20_row(code: str, name: str, stock_type: str, indicator: TechnicalIndicator):
    """生成单个股票的MA20状态行"""
    
    try:
        hist, price_col = get_stock_data(code, stock_type)
        
        if hist is None or len(hist) == 0:
            return f"| {name}（{code}） | " + " | ".join(["❌ 数据获取失败"] * 5) + " |"
        
    except Exception as e:
        print(f"   ⚠️ {code} 获取数据失败: {e}")
        return f"| {name}（{code}） | " + " | ".join(["❌"] * 5) + " |"
    
    try:
        # 统一列名 - 处理 date/日期
        if 'date' in hist.columns and '日期' not in hist.columns:
            hist = hist.rename(columns={'date': '日期'})
        
        # 检查是否有日期列
        if '日期' not in hist.columns:
            return f"| {name}（{code}） | " + " | ".join(["❌ 格式错误"] * 5) + " |"
            
        # 转换为正序
        hist_sorted = hist.sort_values('日期').reset_index(drop=True)
        
        # 取最后5行
        recent_5 = hist_sorted.tail(5).copy().reset_index(drop=True)
        
        if len(recent_5) < 5:
            return f"| {name}（{code}） | " + " | ".join(["❌ 数据不足"] * 5) + " |"
        
        dates = recent_5['日期'].tolist()
        statuses = []
        
        for i in range(len(recent_5)):
            row = recent_5.iloc[i]
            close_price = row[price_col]
            
            # 计算涨跌幅（与前一天相比）
            if i > 0:
                prev_price = recent_5.iloc[i-1][price_col]
                change_pct = (close_price - prev_price) / prev_price * 100
                change_str = f"{change_pct:+.2f}%"
            else:
                change_str = "—"
            
            # 计算MA20
            if i >= 19:
                ma20_data = recent_5.iloc[i-19:i+1][price_col]
                ma20 = indicator.calculate_ma(ma20_data, period=20)
            else:
                # 从完整历史中获取
                target_date = row['日期']
                full_idx_list = hist_sorted[hist_sorted['日期'] == target_date].index.tolist()
                if not full_idx_list:
                    ma20 = None
                else:
                    full_idx = full_idx_list[0]
                    if full_idx >= 19:
                        ma20_data = hist_sorted.iloc[full_idx-19:full_idx+1][price_col]
                        ma20 = indicator.calculate_ma(ma20_data, period=20)
                    else:
                        ma20 = None
            
            if ma20:
                is_above = close_price > ma20
                # ✅ 表示在MA20之上，⬇️ 表示在MA20之下
                status = f"{'✅' if is_above else '⬇️'} {change_str}"
                statuses.append(status)
            else:
                statuses.append("❌")
        
        return f"| {name}（{code}） | " + " | ".join(statuses) + " |"
        
    except Exception as e:
        print(f"   ⚠️ {code} 处理失败: {e}")
        return f"| {name}（{code}） | " + " | ".join(["❌"] * 5) + " |"


def test_all_stocks():
    """生成所有股票的MA20监控表格"""
    indicator = TechnicalIndicator()
    
    print(f"📊 开始生成 {len(MONITOR_LIST)} 只股票的MA20监控报告...")
    print()
    
    # 获取最新的5个交易日日期
    try:
        # 用一只股票获取日期
        test_hist = ak.fund_etf_hist_em(symbol="512400", period="daily",
                                         start_date=(datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                                         end_date=datetime.now().strftime('%Y%m%d'))
        test_hist_sorted = test_hist.sort_values('日期').reset_index(drop=True)
        dates = test_hist_sorted.tail(5)['日期'].tolist()
    except:
        dates = []
    
    print(f"📅 最近5个交易日: {dates}")
    print()
    
    # 生成表格
    header = "| 股票名称 | " + " | ".join(dates) + " |"
    separator = "| --- | " + " | ".join(["---"] * len(dates)) + " |"
    
    rows = []
    for i, stock in enumerate(MONITOR_LIST):
        print(f"[{i+1}/{len(MONITOR_LIST)}] 处理 {stock['name']} ({stock['code']})...")
        row = generate_ma20_row(stock['code'], stock['name'], stock['type'], indicator)
        rows.append(row)
    
    # 构建Markdown
    markdown = f"""## A股/ETF MA20均线监控

{header}
{separator}
{chr(10).join(rows)}

---
*数据来源: AkShare (东方财富)*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    print("\n" + "="*60)
    print("📈 监控报告生成完成")
    print("="*60)
    
    # 保存到文件
    timestamp = datetime.now().strftime('%Y.%m.%d-%H:%M')
    output_file = Path(f"data/{timestamp}_ma20监控报告.md")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"\n💾 报告已保存到: {output_file}")
    
    # 打印预览
    print("\n" + "="*60)
    print("报告预览:")
    print("="*60)
    print(markdown)
    
    return markdown


if __name__ == "__main__":
    test_all_stocks()