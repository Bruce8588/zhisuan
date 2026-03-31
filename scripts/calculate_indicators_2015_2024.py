#!/usr/bin/env python3
"""
MACD 和 TD 九转序列 计算 - 2015-2024年日线数据
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from glob import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class IndicatorCalculator:
    """MACD 和 TD九转序列 计算器"""

    def __init__(self, data_dir=None, output_dir=None):
        self.data_dir = data_dir or os.path.join(BASE_DIR, "data_daily_2015_2024")
        self.output_dir = output_dir or os.path.join(BASE_DIR, "data_daily_indicators_2015_2024")
        os.makedirs(self.output_dir, exist_ok=True)

    def calculate_macd(self, df, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        close = df['close']
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd = (dif - dea) * 2
        return dif, dea, macd

    def calculate_td(self, df):
        """计算TD九转序列"""
        close = df['close']
        td_buy_count = pd.Series(0, index=close.index)
        td_sell_count = pd.Series(0, index=close.index)
        
        for i in range(4, len(close)):
            # 买入序列：收盘价低于4天前
            if close.iloc[i] < close.iloc[i-4]:
                td_buy_count.iloc[i] = td_buy_count.iloc[i-1] + 1 if i > 4 else 1
            # 卖出序列：收盘价高于4天前
            if close.iloc[i] > close.iloc[i-4]:
                td_sell_count.iloc[i] = td_sell_count.iloc[i-1] + 1 if i > 4 else 1
        
        return td_buy_count, td_sell_count

    def calculate(self, code, df):
        """计算单只股票指标"""
        try:
            dif, dea, macd = self.calculate_macd(df)
            td_buy, td_sell = self.calculate_td(df)
            
            result = pd.DataFrame({
                'day': df['day'],
                'close': df['close'],
                'DIF': dif,
                'DEA': dea,
                'MACD': macd,
                'TD_Buy_Count': td_buy,
                'TD_Sell_Count': td_sell,
            })
            return result
        except Exception as e:
            print(f"计算 {code} 失败: {e}")
            return None

    def run_all(self, max_workers=4):
        """计算所有股票"""
        files = glob(os.path.join(self.data_dir, "*_day.csv"))
        total = len(files)
        print(f"开始计算指标，共 {total} 只股票")
        
        success = 0
        start = datetime.now()
        
        for i, filepath in enumerate(files):
            code = os.path.basename(filepath).replace('_day.csv', '')
            df = pd.read_csv(filepath)
            df['day'] = pd.to_datetime(df['day'])
            
            result = self.calculate(code, df)
            if result is not None:
                output_path = os.path.join(self.output_dir, f"{code}_indicators.csv")
                result.to_csv(output_path, index=False)
                success += 1
            
            if (i + 1) % 500 == 0:
                elapsed = (datetime.now() - start).total_seconds()
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate if rate > 0 else 0
                print(f"进度: {i+1}/{total} | 成功: {success} | 耗时: {elapsed:.0f}s | 预计剩余: {remaining:.0f}s")
        
        elapsed = (datetime.now() - start).total_seconds()
        print(f"完成! 成功: {success}/{total} | 总耗时: {elapsed:.0f}s")


if __name__ == "__main__":
    calc = IndicatorCalculator()
    calc.run_all()
