#!/usr/bin/env python3
"""
信号追踪模块
功能：基于趋势判断文件，捕捉买入/卖出信号
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.rules import *


class SignalTracker:
    """信号追踪器"""
    
    def __init__(self, db_dir=None, trend_dir=None):
        self.db_dir = db_dir or os.path.join(BASE_DIR, "data")
        self.trend_dir = trend_dir or os.path.join(BASE_DIR, "output", "趋势判断")
    
    def get_latest_trend(self, symbol, code):
        """获取最新趋势"""
        trend_file = os.path.join(self.trend_dir, f"{symbol}_趋势判断.csv")
        
        if not os.path.exists(trend_file):
            return None
        
        df = pd.read_csv(trend_file)
        if len(df) == 0:
            return None
        
        return df.iloc[-1]
    
    def get_latest_price(self, symbol, code):
        """获取最新价格"""
        db_file = os.path.join(self.db_dir, f"{symbol}_{code}_min1.csv")
        
        if not os.path.exists(db_file):
            return None
        
        df = pd.read_csv(db_file)
        if len(df) == 0:
            return None
        
        latest = df.iloc[-1]
        return {
            "time": latest["day"],
            "open": float(latest["open"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
        }
    
    def check_buy_signal(self, symbol, info):
        """检查买入信号"""
        code = info["code"]
        
        # 获取最新趋势和价格
        trend_data = self.get_latest_trend(symbol, code)
        price_data = self.get_latest_price(symbol, code)
        
        if trend_data is None or price_data is None:
            return None
        
        trend = trend_data["趋势代码"]
        current_price = price_data["close"]
        
        signals = []
        
        # 买入信号1：趋势转为上升（从下跌转为回升）
        if trend in ["up", "up_rally", "up_natural"]:
            # 检查之前是否是下跌趋势
            prev_trend = trend_data.get("趋势代码")  # 需要获取前一个趋势
            # 简化：直接判断当前趋势是上升
            signals.append({
                "type": "BUY",
                "reason": f"趋势转为{TREND_NAMES.get(trend, trend)}",
                "price": current_price,
                "time": price_data["time"],
            })
        
        # 买入信号2：自然回升突破
        if trend == "down_natural":
            n_high = trend_data.get("n_high")
            if n_high and current_price > n_high * 1.03:
                signals.append({
                    "type": "BUY",
                    "reason": "自然回升突破",
                    "price": current_price,
                    "time": price_data["time"],
                })
        
        return signals if signals else None
    
    def check_sell_signal(self, symbol, info):
        """检查卖出信号"""
        code = info["code"]
        
        trend_data = self.get_latest_trend(symbol, code)
        price_data = self.get_latest_price(symbol, code)
        
        if trend_data is None or price_data is None:
            return None
        
        trend = trend_data["趋势代码"]
        current_price = price_data["close"]
        
        signals = []
        
        # 卖出信号1：趋势转为下跌
        if trend in ["down", "down_natural", "down_rally"]:
            signals.append({
                "type": "SELL",
                "reason": f"趋势转为{TREND_NAMES.get(trend, trend)}",
                "price": current_price,
                "time": price_data["time"],
            })
        
        return signals if signals else None
    
    def check_all_signals(self, stocks):
        """检查所有股票信号"""
        results = {"BUY": [], "SELL": []}
        
        for symbol, info in stocks.items():
            # 买入信号
            buy_signals = self.check_buy_signal(symbol, info)
            if buy_signals:
                for signal in buy_signals:
                    signal["stock"] = symbol
                    results["BUY"].append(signal)
            
            # 卖出信号
            sell_signals = self.check_sell_signal(symbol, info)
            if sell_signals:
                for signal in sell_signals:
                    signal["stock"] = symbol
                    results["SELL"].append(signal)
        
        return results


if __name__ == "__main__":
    from config.stocks import POOL_A
    
    tracker = SignalTracker()
    
    print("=== 检查信号 ===")
    signals = tracker.check_all_signals(POOL_A)
    
    if signals["BUY"]:
        print("\n买入信号:")
        for s in signals["BUY"]:
            print(f"  {s['stock']}: {s['reason']} @ {s['price']}")
    
    if signals["SELL"]:
        print("\n卖出信号:")
        for s in signals["SELL"]:
            print(f"  {s['stock']}: {s['reason']} @ {s['price']}")
    
    if not signals["BUY"] and not signals["SELL"]:
        print("暂无信号")
