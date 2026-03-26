#!/usr/bin/env python3
"""
MACD 和 TD 九转序列 计算模块
功能：对日线数据计算MACD和TD序列指标

MACD指标：
- DIF = EMA12 - EMA26
- DEA = DIF的9日EMA
- MACD柱 = (DIF - DEA) * 2

TD九转序列：
- 买入序列：连续9天收盘价低于4天前收盘价
- 卖出序列：连续9天收盘价高于4天前收盘价

用法：
    python calculate_indicators.py --stock 600089
    python calculate_indicators.py --all
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class IndicatorCalculator:
    """MACD 和 TD九转序列 计算器"""

    def __init__(self, data_dir=None, output_dir=None):
        self.data_dir = data_dir or os.path.join(BASE_DIR, "data_daily")
        self.output_dir = output_dir or os.path.join(BASE_DIR, "data_daily_indicators")
        os.makedirs(self.output_dir, exist_ok=True)

    def calculate_macd(self, df, fast=12, slow=26, signal=9):
        """计算MACD指标
        
        参数:
            df: 包含close列的DataFrame
            fast: 快线周期（默认12）
            slow: 慢线周期（默认26）
            signal: 信号线周期（默认9）
        
        返回:
            DataFrame: 包含 DIF, DEA, MACD柱
        """
        # 计算EMA
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        
        # DIF = EMA12 - EMA26
        dif = ema_fast - ema_slow
        
        # DEA = DIF的9日EMA
        dea = dif.ewm(span=signal, adjust=False).mean()
        
        # MACD柱 = (DIF - DEA) * 2
        macd = (dif - dea) * 2
        
        return pd.DataFrame({
            'DIF': dif,
            'DEA': dea,
            'MACD': macd
        })

    def calculate_td_sequential(self, df):
        """计算TD九转序列
        
        买入序列：连续9天收盘价 < 4天前收盘价（计数从1到9）
        卖出序列：连续9天收盘价 > 4天前收盘价（计数从1到9）
        
        返回:
            DataFrame: 包含 TD_Buy_Count, TD_Sell_Count
        """
        close = df['close'].values
        n = len(close)
        
        # TD买入计数
        td_buy = np.zeros(n)
        td_sell = np.zeros(n)
        
        buy_count = 0
        sell_count = 0
        
        for i in range(4, n):
            # 买入序列：今天收盘 < 4天前收盘
            if close[i] < close[i - 4]:
                buy_count += 1
                td_buy[i] = buy_count
            else:
                buy_count = 0
            
            # 卖出序列：今天收盘 > 4天前收盘
            if close[i] > close[i - 4]:
                sell_count += 1
                td_sell[i] = sell_count
            else:
                sell_count = 0
        
        return pd.DataFrame({
            'TD_Buy_Count': td_buy,
            'TD_Sell_Count': td_sell
        })

    def calculate_all(self, df):
        """计算所有指标"""
        result = df.copy()
        
        # MACD
        macd_df = self.calculate_macd(result)
        result['DIF'] = macd_df['DIF']
        result['DEA'] = macd_df['DEA']
        result['MACD'] = macd_df['MACD']
        
        # TD九转
        td_df = self.calculate_td_sequential(result)
        result['TD_Buy_Count'] = td_df['TD_Buy_Count'].astype(int)
        result['TD_Sell_Count'] = td_df['TD_Sell_Count'].astype(int)
        
        return result

    def process_stock(self, code):
        """处理单只股票"""
        input_file = os.path.join(self.data_dir, f"{code}_day.csv")
        output_file = os.path.join(self.output_dir, f"{code}_indicators.csv")
        
        if not os.path.exists(input_file):
            return code, 0, "输入文件不存在"
        
        try:
            df = pd.read_csv(input_file)
            if 'close' not in df.columns or len(df) < 30:
                return code, 0, "数据不足"
            
            # 计算指标
            result = self.calculate_all(df)
            
            # 保存
            result.to_csv(output_file, index=False, encoding='utf-8')
            
            return code, len(result), "成功"
        except Exception as e:
            return code, 0, str(e)

    def process_all(self, max_workers=4):
        """处理所有股票"""
        # 获取所有日线数据文件
        stock_codes = []
        for f in os.listdir(self.data_dir):
            if f.endswith('_day.csv'):
                code = f.replace('_day.csv', '')
                stock_codes.append(code)
        
        print(f"\n=== 计算 MACD 和 TD九转 指标 ===")
        print(f"股票数量: {len(stock_codes)}")
        print(f"输出目录: {self.output_dir}")
        print()
        
        success = 0
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.process_stock, code): code for code in stock_codes}
            for i, future in enumerate(as_completed(futures)):
                code, count, status = future.result()
                results[code] = status
                if status == "成功":
                    success += 1
                    if (i+1) % 500 == 0:
                        print(f"进度: {i+1}/{len(stock_codes)}, 成功: {success}")
                else:
                    print(f"[{i+1}/{len(stock_codes)}] {code}: {status}")
        
        print(f"\n=== 完成 ===")
        print(f"成功: {success}/{len(stock_codes)}")
        return results

    def show_stock_indicators(self, code, days=30):
        """显示单只股票的最新指标"""
        file_path = os.path.join(self.output_dir, f"{code}_indicators.csv")
        
        if not os.path.exists(file_path):
            print(f"指标文件不存在: {file_path}")
            return
        
        df = pd.read_csv(file_path)
        df['day'] = pd.to_datetime(df['day'])
        
        print(f"\n=== {code} 最新指标 (最近{days}天) ===\n")
        
        # 显示最新数据
        latest = df.tail(days).copy()
        
        # MACD
        latest_macd = latest[['day', 'close', 'DIF', 'DEA', 'MACD']].copy()
        latest_macd['day'] = latest_macd['day'].dt.strftime('%Y-%m-%d')
        print("MACD指标:")
        print(latest_macd.to_string(index=False))
        
        # TD九转
        print("\nTD九转序列:")
        td_cols = latest[['day', 'close', 'TD_Buy_Count', 'TD_Sell_Count']].copy()
        td_cols['day'] = td_cols['day'].dt.strftime('%Y-%m-%d')
        # 只显示有计数的
        td_nonzero = td_cols[(td_cols['TD_Buy_Count'] > 0) | (td_cols['TD_Sell_Count'] > 0)]
        if len(td_nonzero) > 0:
            print(td_nonzero.to_string(index=False))
        else:
            print("无活跃计数")
        
        # 金叉/死叉检测
        print("\n信号检测:")
        if len(df) >= 2:
            dif_now = df['DIF'].iloc[-1]
            dif_prev = df['DIF'].iloc[-2]
            dea_now = df['DEA'].iloc[-1]
            dea_prev = df['DEA'].iloc[-2]
            
            # MACD金叉：DIF上穿DEA
            if dif_now > dea_now and dif_prev <= dea_prev:
                print("  ✓ MACD 金叉 (DIF上穿DEA)")
            # MACD死叉：DIF下穿DEA
            elif dif_now < dea_now and dif_prev >= dea_prev:
                print("  ✗ MACD 死叉 (DIF下穿DEA)")
            
            # MACD柱由绿变红（红柱）
            macd_now = df['MACD'].iloc[-1]
            macd_prev = df['MACD'].iloc[-2]
            if macd_now > 0 and macd_prev <= 0:
                print("  ✓ MACD 绿翻红")
            elif macd_now < 0 and macd_prev >= 0:
                print("  ✗ MACD 红翻绿")
            
            # TD9计数
            td_buy = df['TD_Buy_Count'].iloc[-1]
            td_sell = df['TD_Sell_Count'].iloc[-1]
            if td_buy == 9:
                print("  ✓ TD买入序列完成(9) - 潜在买入信号!")
            if td_sell == 9:
                print("  ✗ TD卖出序列完成(9) - 潜在卖出信号!")


def main():
    parser = argparse.ArgumentParser(description='MACD 和 TD九转序列 计算')
    parser.add_argument('--stock', type=str, help='股票代码')
    parser.add_argument('--all', action='store_true', help='处理所有股票')
    parser.add_argument('--days', type=int, default=30, help='显示最近N天数据')
    
    args = parser.parse_args()
    
    calculator = IndicatorCalculator()
    
    if args.stock:
        # 显示单只股票
        code = args.stock.replace('.SH', '').replace('.SZ', '').replace('sh', '').replace('sz', '')
        calculator.process_stock(code)
        calculator.show_stock_indicators(code, args.days)
    
    elif args.all:
        # 处理所有
        calculator.process_all()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
