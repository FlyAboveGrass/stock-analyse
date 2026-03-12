import os
import logging
import requests
from typing import Optional, Union

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram通知器"""
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        初始化Telegram通知器
        
        Args:
            token: Telegram Bot Token
            chat_id: Chat ID
        """
        self.token = token or os.getenv('TELEGRAM_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.token or not self.chat_id:
            raise ValueError("TELEGRAM_TOKEN 和 TELEGRAM_CHAT_ID 必须设置")
        
        self.api_url = f"https://api.telegram.org/bot{self.token}"
    
    def send(self, message: str, parse_mode: Union[str, None] = "Markdown") -> bool:
        """
        发送消息
        
        Args:
            message: 消息内容
            parse_mode: 解析模式 (Markdown 或 HTML)
            
        Returns:
            是否发送成功
        """
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Telegram消息发送成功: {message[:50]}...")
                return True
            else:
                logger.error(f"Telegram发送失败: {result.get('description')}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Telegram请求异常: {e}")
            return False
    
    def send_signal(self, signal) -> bool:
        """
        发送交易信号
        
        Args:
            signal: Signal对象
            
        Returns:
            是否发送成功
        """
        message = str(signal)
        return self.send(message)
    
    def send_text(self, text: str) -> bool:
        """
        发送纯文本消息
        
        Args:
            text: 文本内容
            
        Returns:
            是否发送成功
        """
        return self.send(text, parse_mode=None)
    
    def test(self) -> bool:
        """
        测试连接
        
        Returns:
            是否连接成功
        """
        url = f"{self.api_url}/getMe"
        try:
            response = requests.get(url, timeout=10)
            result = response.json()
            return result.get('ok', False)
        except requests.RequestException:
            return False
