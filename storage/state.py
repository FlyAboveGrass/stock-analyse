import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StateStorage:
    """状态持久化存储"""
    
    def __init__(self, file_path: str = "data/state.json"):
        """
        初始化状态存储
        
        Args:
            file_path: 状态文件路径
        """
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> Dict[str, Any]:
        """
        加载状态
        
        Returns:
            状态字典
        """
        if not self.file_path.exists():
            return {}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"状态文件读取失败: {e}，将重新初始化")
            return {}
    
    def save(self, states: Dict[str, Any]):
        """
        保存状态
        
        Args:
            states: 状态字典
        """
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(states, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"状态文件保存失败: {e}")
    
    def update(
        self, 
        symbol: str, 
        position: str, 
        price: float, 
        ma20: float
    ):
        """
        更新单个标的状态
        
        Args:
            symbol: 股票代码
            position: 位置 ("above" 或 "below")
            price: 当前价格
            ma20: 20日均线值
        """
        states = self.load()
        states[symbol] = {
            "position": position,
            "price": price,
            "ma20": ma20,
            "updated_at": datetime.now().isoformat()
        }
        self.save(states)
    
    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取单个标的状态
        
        Args:
            symbol: 股票代码
            
        Returns:
            状态字典，如果不存在则返回None
        """
        states = self.load()
        return states.get(symbol)
    
    def remove(self, symbol: str):
        """
        删除单个标的状态
        
        Args:
            symbol: 股票代码
        """
        states = self.load()
        if symbol in states:
            del states[symbol]
            self.save(states)
    
    def clear(self):
        """清空所有状态"""
        self.save({})
    
    def get_all_symbols(self) -> list[str]:
        """
        获取所有已监控的股票代码
        
        Returns:
            股票代码列表
        """
        states = self.load()
        return list(states.keys())
