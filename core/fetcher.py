import akshare as ak
import pandas as pd
from typing import Optional


class StockFetcher:
    """A股股票数据获取器"""
    
    @staticmethod
    def get_realtime_price(symbol: str) -> float:
        """
        获取实时价格
        
        Args:
            symbol: 股票代码，如 "600519"
            
        Returns:
            当前价格
        """
        # 获取实时行情列表
        df = ak.stock_zh_a_spot_em()
        
        # 匹配股票代码
        stock = df[df['代码'] == symbol]
        
        if stock.empty:
            raise ValueError(f"未找到股票: {symbol}")
        
        # 获取最新价
        price = stock.iloc[0]['最新价']
        
        # 如果是NaN（停牌等），返回昨收价
        if pd.isna(price):
            price = stock.iloc[0]['昨收']
        
        return float(price)
    
    @staticmethod
    def get_realtime_prices_batch(symbols: list[str]) -> dict[str, float]:
        """
        批量获取实时价格
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            股票代码到价格的字典
        """
        # 获取所有实时行情
        df = ak.stock_zh_a_spot_em()
        
        prices = {}
        for symbol in symbols:
            stock = df[df['代码'] == symbol]
            if stock.empty:
                prices[symbol] = None
                continue
            
            price = stock.iloc[0]['最新价']
            if pd.isna(price):
                price = stock.iloc[0]['昨收']
            prices[symbol] = float(price) if not pd.isna(price) else None
        
        return prices
    
    @staticmethod
    def get_historical_prices(symbol: str, period: int = 25) -> pd.DataFrame:
        """
        获取历史K线数据
        
        Args:
            symbol: 股票代码，如 "600519" 或 "sh600519"
            period: 获取天数（默认25天，确保有足够数据计算MA20）
            
        Returns:
            包含日期、收盘价的DataFrame
        """
        # 格式转换：需要添加市场前缀
        if symbol.startswith('6'):
            market_code = f"sh{symbol}"
        else:
            market_code = f"sz{symbol}"
        
        # 计算日期范围
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=period * 2)).strftime("%Y%m%d")
        
        df = ak.stock_zh_a_hist(
            symbol=market_code,
            period="daily",
            adjust="qfq",
            start_date=start_date,
            end_date=end_date
        )
        
        # 确保有足够数据
        if len(df) < period:
            raise ValueError(f"股票 {symbol} 历史数据不足: 需要{period}天，实际{len(df)}天")
        
        return df.tail(period)
    
    @staticmethod
    def is_trading_day() -> bool:
        """
        判断当前是否为交易日
        
        Returns:
            是否为交易日
        """
        from datetime import datetime, timedelta
        
        # 简单判断：周六日不是交易日
        now = datetime.now()
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        return True
