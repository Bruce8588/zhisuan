#!/usr/bin/env python3.11
"""
智算2.0 - 主监控程序
整合六大模块：数据获取 → 趋势判断 → 记录功能 → 信号追踪 → 推送 → 交易
"""
import os
import sys
import time
import schedule
from datetime import datetime

# 添加项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS
from core.fetcher import DataFetcher
from core.trend import TrendAnalyzer
from core.signal import SignalTracker
from core.trade import TradeRecorder
from services.recorder import Recorder
from services.notify import Notifier


class QuantMonitor:
    """量化监控主程序"""
    
    def __init__(self):
        print("=" * 50)
        print("智算2.0 启动")
        print("=" * 50)
        
        # 初始化各模块
        self.fetcher = DataFetcher()
        self.trend_analyzer = TrendAnalyzer()
        self.signal_tracker = SignalTracker()
        self.trade_recorder = TradeRecorder()
        self.recorder = Recorder()
        self.notifier = Notifier()
        
        # 股票池
        self.all_stocks = ALL_STOCKS
    
    def run_data_fetcher(self):
        """数据获取"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 数据获取...")
        self.fetcher.update_all(self.all_stocks)
        print("  数据获取完成")
    
    def run_trend_analyzer(self):
        """趋势分析"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 趋势分析...")
        self.trend_analyzer.analyze_all(self.all_stocks)
        print("  趋势分析完成")
    
    def run_recorder(self):
        """记录功能"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 生成记录...")
        self.recorder.generate_all(self.all_stocks)
        print("  记录生成完成")
    
    def run_signal_check(self):
        """信号检测"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 检测信号...")
        
        # 检测所有股票信号
        signals = self.signal_tracker.check_all_signals(self.all_stocks)
        
        if signals["BUY"]:
            print(f"  买入信号: {len(signals['BUY'])} 个")
            for s in signals["BUY"]:
                print(f"    - {s['stock']}: {s['reason']}")
        
        if signals["SELL"]:
            print(f"  卖出信号: {len(signals['SELL'])} 个")
            for s in signals["SELL"]:
                print(f"    - {s['stock']}: {s['reason']}")
        
        # 发送通知
        self.notifier.send_signal(signals)
        
        return signals
    
    def run_trade(self):
        """交易处理"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 交易处理...")
        
        # 更新持仓盈亏
        for symbol, info in self.all_stocks.items():
            price = self.signal_tracker.get_latest_price(symbol, info["code"])
            if price:
                self.trade_recorder.update_profit(symbol, price["close"], "pool_a")
        
        print("  交易处理完成")
    
    def run_all(self):
        """运行完整流程"""
        print(f"\n{'='*50}")
        print(f"开始执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        self.run_data_fetcher()
        self.run_trend_analyzer()
        self.run_recorder()
        self.run_signal_check()
        self.run_trade()
        
        print(f"\n{'='*50}")
        print("执行完成")
        print("=" * 50)
    
    def start_schedule(self, interval=5):
        """定时运行
        
        Args:
            interval: 运行间隔（分钟），默认5分钟
        """
        # 设置运行间隔
        schedule.every(interval).minutes.do(self.run_all)
        
        print(f"\n定时任务已启动")
        print(f"运行间隔: 每{interval}分钟")
        print("交易时段: 9:30-11:30, 13:00-15:00")
        print("按Ctrl+C停止\n")
        
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智算2.0")
    parser.add_argument("--mode", choices=["all", "data", "trend", "signal", "schedule"], 
                        default="all", help="运行模式")
    parser.add_argument("--pool", choices=["pool_a", "watchlist", "all"], 
                        default="all", help="股票池")
    parser.add_argument("--interval", type=int, default=5, 
                        help="定时模式运行间隔（分钟），默认5分钟")
    
    args = parser.parse_args()
    
    monitor = QuantMonitor()
    
    if args.mode == "all":
        monitor.run_all()
    elif args.mode == "data":
        monitor.run_data_fetcher()
    elif args.mode == "trend":
        monitor.run_trend_analyzer()
    elif args.mode == "signal":
        monitor.run_signal_check()
    elif args.mode == "schedule":
        monitor.start_schedule(interval=args.interval)
