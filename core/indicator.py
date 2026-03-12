import pandas as pd
from typing import Optional


class TechnicalIndicator:
    """技术指标计算"""
    
    @staticmethod
    def calculate_ma(prices: pd.Series, period: int = 20) -> float:
        """
        计算移动平均线
        
        Args:
            prices: 收盘价序列
            period: 均线周期
            
        Returns:
            MA值
        """
        if len(prices) < period:
            raise ValueError(f"数据不足: 需要{period}个数据点，当前{len(prices)}个")
        
        ma = prices.rolling(window=period).mean().iloc[-1]
        return float(ma)
    
    @staticmethod
    def calculate_ma_series(prices: pd.Series, period: int = 20) -> pd.Series:
        """
        计算MA序列（用于画图）
        
        Args:
            prices: 收盘价序列
            period: 均线周期
            
        Returns:
            MA序列
        """
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int = 20) -> float:
        """
        计算指数移动平均线
        
        Args:
            prices: 收盘价序列
            period: 均线周期
            
        Returns:
            EMA值
        """
        if len(prices) < period:
            raise ValueError(f"数据不足: 需要{period}个数据点，当前{len(prices)}个")
        
        ema = prices.ewm(span=period, adjust=False).mean().iloc[-1]
        return float(ema)
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series, 
        period: int = 20, 
        std_dev: float = 2.0
    ) -> tuple[float, float, float]:
        """
        计算布林带
        
        Args:
            prices: 收盘价序列
            period: 均线周期
            std_dev: 标准差倍数
            
        Returns:
            (中轨, 上轨, 下轨)
        """
        if len(prices) < period:
            raise ValueError(f"数据不足")
        
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return (
            float(middle.iloc[-1]),
            float(upper.iloc[-1]),
            float(lower.iloc[-1])
        )
