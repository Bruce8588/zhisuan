#!/usr/bin/env python3
"""
交易记录模块
功能：记录信号，模拟交易，计算盈亏，保存持仓
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class TradeRecorder:
    """交易记录器"""
    
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(BASE_DIR, "output")
        self.trades_dir = os.path.join(self.output_dir, "交易记录")
        os.makedirs(self.trades_dir, exist_ok=True)
        
        self.pool_a_file = os.path.join(self.trades_dir, "pool_a_trades.json")
        self.watchlist_file = os.path.join(self.trades_dir, "watchlist_trades.json")
        
        # 初始化文件
        for f in [self.pool_a_file, self.watchlist_file]:
            if not os.path.exists(f):
                with open(f, "w") as fp:
                    json.dump([], fp)
    
    def load_trades(self, filename):
        """加载交易记录"""
        with open(filename, "r") as f:
            return json.load(f)
    
    def save_trades(self, filename, trades):
        """保存交易记录"""
        with open(filename, "w") as f:
            json.dump(trades, f, indent=2, ensure_ascii=False)
    
    def add_trade(self, trade, pool_type="pool_a"):
        """添加交易记录"""
        filename = self.pool_a_file if pool_type == "pool_a" else self.watchlist_file
        
        trades = self.load_trades(filename)
        trades.append(trade)
        self.save_trades(filename, trades)
        
        print(f"已添加 {trade['stock']} {trade['action']} 记录")
    
    def close_trade(self, stock, close_price, close_time, pool_type="pool_a"):
        """平仓"""
        filename = self.pool_a_file if pool_type == "pool_a" else self.watchlist_file
        
        trades = self.load_trades(filename)
        
        for trade in trades:
            if trade["stock"] == stock and trade.get("close_price") is None:
                trade["close_price"] = close_price
                trade["close_time"] = close_time
                
                # 计算盈亏
                open_price = trade["open_price"]
                profit = (close_price - open_price) / open_price * 100
                trade["profit"] = round(profit, 2)
                
                self.save_trades(filename, trades)
                print(f"已平仓 {stock} @ {close_price}, 盈亏: {profit:.2f}%")
                return True
        
        return False
    
    def get_positions(self, pool_type="pool_a"):
        """获取当前持仓"""
        filename = self.pool_a_file if pool_type == "pool_a" else self.watchlist_file
        
        trades = self.load_trades(filename)
        positions = [t for t in trades if t.get("close_price") is None]
        
        return positions
    
    def update_profit(self, stock, current_price, pool_type="pool_a"):
        """更新持仓盈亏"""
        filename = self.pool_a_file if pool_type == "pool_a" else self.watchlist_file
        
        trades = self.load_trades(filename)
        updated = False
        
        for trade in trades:
            if trade["stock"] == stock and trade.get("close_price") is None:
                open_price = trade["open_price"]
                profit = (current_price - open_price) / open_price * 100
                trade["profit"] = round(profit, 2)
                trade["current_price"] = current_price
                updated = True
        
        if updated:
            self.save_trades(filename, trades)
        
        return updated


if __name__ == "__main__":
    recorder = TradeRecorder()
    
    # 测试
    print("=== 交易记录测试 ===")
    
    # 添加买入
    recorder.add_trade({
        "stock": "测试股票",
        "action": "BUY",
        "open_price": 10.0,
        "open_time": "2026-03-13 10:00:00",
    })
    
    # 获取持仓
    positions = recorder.get_positions()
    print(f"当前持仓: {len(positions)} 只")
    
    # 更新盈亏
    recorder.update_profit("测试股票", 10.5)
    
    print("测试完成!")
