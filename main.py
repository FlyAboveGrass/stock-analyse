#!/usr/bin/env python3
"""
A股股票及ETF均线监控主程序

功能：
- 每隔10分钟自动获取A股股票和ETF的实时价格
- 计算20日移动平均线(MA20)
- 检测价格上穿/下穿MA20的信号
- 通过Telegram发送通知
"""

import os
import sys
import logging
import schedule
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.loader import ConfigLoader
from core.fetcher import StockFetcher
from core.indicator import TechnicalIndicator
from core.detector import SignalDetector
from notification.telegram import TelegramNotifier
from notification.feishu import FeishuNotifier
from storage.state import StateStorage


class StockMonitor:
    """股票均线监控主类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化监控器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = ConfigLoader.load(config_path)
        
        # 初始化组件
        self.fetcher = StockFetcher()
        self.indicator = TechnicalIndicator()
        self.detector = SignalDetector(ma_period=self.config.get('ma', {}).get('period', 20))
        self.storage = StateStorage()
        
        # 通知器
        notif_type = self.config.get('notification', {}).get('type', 'telegram')
        notif_cfg = self.config.get('notification', {})
        
        if notif_type == 'feishu':
            feishu_cfg = notif_cfg.get('feishu', {})
            self.notifier = FeishuNotifier(
                webhook_url=os.getenv('FEISHU_WEBHOOK_URL', feishu_cfg.get('webhook_url', ''))
            )
        else:
            telegram_cfg = notif_cfg.get('telegram', {})
            self.notifier = TelegramNotifier(
                token=os.getenv('TELEGRAM_TOKEN', telegram_cfg.get('token', '')),
                chat_id=os.getenv('TELEGRAM_CHAT_ID', telegram_cfg.get('chat_id', ''))
            )
        
        # 监控配置
        self.interval = self.config['monitor']['interval']
        self.stocks = self.config.get('stocks', [])
        self.etfs = self.config.get('etfs', [])
        self.watchlist = self.stocks + self.etfs
        
        # 统计
        self.run_count = 0
        self.error_count = 0
        
        logger.info(f"✅ 监控服务初始化完成")
        logger.info(f"   监控标的: {len(self.watchlist)} 只")
        logger.info(f"   监控间隔: {self.interval} 秒")
    
    def check_one(self, symbol: str) -> Optional[dict]:
        """
        检查单只股票
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含价格和MA20的字典，失败返回None
        """
        try:
            # 获取实时价格
            price = self.fetcher.get_realtime_price(symbol)
            
            # 获取历史数据计算MA20
            hist = self.fetcher.get_historical_prices(symbol)
            ma20 = self.indicator.calculate_ma(hist['收盘'], period=20)
            
            return {
                'success': True,
                'price': price,
                'ma20': ma20
            }
        except Exception as e:
            logger.warning(f"   ⚠️ {symbol} 获取数据失败: {e}")
            self.error_count += 1
            return None
    
    def run(self):
        """执行一次监控检查"""
        self.run_count += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"\n[{timestamp}] 第{self.run_count}轮监控开始...")
        
        # 加载历史状态
        states = self.storage.load()
        
        # 记录本次状态变化
        signals_sent = 0
        
        for symbol in self.watchlist:
            # 获取数据
            result = self.check_one(symbol)
            if not result:
                continue
            
            price = result['price']
            ma20 = result['ma20']
            
            # 获取历史状态
            previous_state = states.get(symbol)
            previous_position = previous_state.get('position') if previous_state else None
            
            # 检测信号
            signal = self.detector.detect(
                symbol=symbol,
                current_price=price,
                ma20=ma20,
                previous_position=previous_position
            )
            
            # 发送通知
            if signal:
                logger.info(f"   🔔 信号: {signal.direction} - {symbol}")
                try:
                    self.notifier.send_signal(signal)
                    signals_sent += 1
                except Exception as e:
                    logger.error(f"   ❌ 通知发送失败: {e}")
            else:
                logger.debug(f"   ✓ {symbol}: 价格={price:.2f}, MA20={ma20:.2f}")
            
            # 更新状态
            current_position = "above" if price > ma20 else "below"
            self.storage.update(symbol, current_position, price, ma20)
        
        logger.info(f"   ✅ 本轮检查完成 (信号: {signals_sent})")
    
    def start(self):
        """启动定时监控"""
        # 立即执行一次
        self.run()
        
        # 发送启动通知
        try:
            self.notifier.send(
                f"✅ *监控服务已启动*\n\n"
                f"• 监控标的: {len(self.watchlist)} 只\n"
                f"• 股票: {len(self.stocks)} 只\n"
                f"• ETF: {len(self.etfs)} 只\n"
                f"• 间隔: {self.interval}秒\n"
                f"• 模式: MA20均线监控"
            )
        except Exception as e:
            logger.warning(f"启动通知发送失败: {e}")
        
        # 设置定时任务
        schedule.every(self.interval).seconds.do(self.run)
        
        logger.info(f"\n🚀 监控服务已启动，每 {self.interval} 秒执行一次")
        logger.info("按 Ctrl+C 停止监控\n")
        
        while True:
            schedule.run_pending()
            time.sleep(1)


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='A股均线监控系统')
    parser.add_argument('--once', '-o', action='store_true', help='仅运行一次，不持续监控')
    parser.add_argument('--report', '-r', action='store_true', help='发送每日MA20报告（最近3天）并退出')
    parser.add_argument('--config', '-c', default='config.yaml', help='配置文件路径')
    args = parser.parse_args()
    
    config_path = args.config
    
    if not Path(config_path).exists():
        if not Path("config.yaml").exists():
            logger.error("配置文件不存在: config.yaml")
            logger.info("请在项目目录下运行，或指定配置文件路径")
            sys.exit(1)
        config_path = "config.yaml"
    
    try:
        monitor = StockMonitor(config_path)
        
        if args.report:
            logger.info("发送每日MA20报告模式...")
            if hasattr(monitor.notifier, 'send_daily_report'):
                success = monitor.notifier.send_daily_report(days=3)
                if success:
                    logger.info("✅ 报告发送成功")
                else:
                    logger.error("❌ 报告发送失败")
                    sys.exit(1)
            else:
                logger.warning("当前通知器不支持报告模式，使用普通运行模式")
                monitor.run()
        elif args.once:
            logger.info("单次运行模式...")
            monitor.run()
        else:
            # 持续监控模式
            monitor.start()
            
    except KeyboardInterrupt:
        logger.info("\n\n👋 监控服务已停止")
        sys.exit(0)
    except Exception as e:
        logger.error(f"监控服务异常退出: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
