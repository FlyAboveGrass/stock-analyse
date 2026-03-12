from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Signal:
    """交易信号"""
    symbol: str
    direction: Literal["breakout", "breakdown"]  # 上穿(突破) / 下穿(跌破)
    price: float
    ma20: float
    timestamp: str
    position_type: str  # 多头/空头
    
    def __str__(self) -> str:
        emoji = "🚀" if self.direction == "breakout" else "🔻"
        direction_text = "突破" if self.direction == "breakout" else "跌破"
        
        return f"""
{emoji} *{self.symbol}* {direction_text} 20日均线

• 现价: `{self.price:.2f}`
• MA20: `{self.ma20:.2f}`
• 位置: {'🌙 多头' if self.position_type == 'above' else '⭐ 空头'}
• 时间: {self.timestamp}
"""


class SignalDetector:
    """均线穿越信号检测器"""
    
    def __init__(self, ma_period: int = 20):
        """
        初始化检测器
        
        Args:
            ma_period: 均线周期，默认20日
        """
        self.ma_period = ma_period
    
    def detect(
        self, 
        symbol: str, 
        current_price: float, 
        ma20: float, 
        previous_position: Optional[str] = None
    ) -> Optional[Signal]:
        """
        检测是否有新信号
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            ma20: 20日均线值
            previous_position: 上一次的位置 ("above" 或 "below")
            
        Returns:
            Signal对象（如果有新信号），否则返回None
        """
        # 判断当前位置
        current_position = "above" if current_price > ma20 else "below"
        
        # 无历史状态，跳过（首次运行）
        if previous_position is None:
            return None
        
        # 状态未变化，无信号
        if current_position == previous_position:
            return None
        
        # 检测到穿越
        direction = "breakout" if current_position == "above" else "breakdown"
        
        return Signal(
            symbol=symbol,
            direction=direction,
            price=current_price,
            ma20=ma20,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            position_type=current_position
        )
    
    @staticmethod
    def get_position_name(position: str) -> str:
        """获取位置名称"""
        return "多头" if position == "above" else "空头"
