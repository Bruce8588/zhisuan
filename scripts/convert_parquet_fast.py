#!/usr/bin/env python3
"""
全市场数据转换脚本 - 高效版
将桌面 parquet 数据转换为智算格式 CSV（支持全部股票）

优化点：
1. 每个文件只读一次
2. 边读边处理，不重复扫描
3. 实时显示进度
"""
import os
import sys
import pandas as pd
from glob import glob
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PARQUET_DIRS = [
    "/Users/isenfengming/Desktop/2025",
    "/Users/isenfengming/Desktop/2026",
]
OUTPUT_DIR = os.path.join(BASE_DIR, "data_allmarket")


def convert_allmarket_fast(test_mode=False):
    """高效全市场转换"""
    
    print("=" * 60)
    print("全市场 Parquet → CSV 转换 (高效版)")
    print("=" * 60)
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 获取所有 parquet 文件
    parquet_files = []
    for pq_dir in PARQUET_DIRS:
        if os.path.exists(pq_dir):
            files = sorted(glob(os.path.join(pq_dir, "*.parquet")))
            parquet_files.extend(files)
    
    if test_mode:
        parquet_files = parquet_files[:3]
    
    total_files = len(parquet_files)
    print(f"数据来源: {PARQUET_DIRS}")
    print(f"文件数: {total_files}")
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    
    start_time = datetime.now()
    
    # 每个股票的待合并数据
    stock_data = defaultdict(list)
    stock_count = set()
    
    # 处理每个文件
    for i, f in enumerate(parquet_files):
        date_label = os.path.basename(f).replace('.parquet', '')
        
        # 每10个文件显示一次进度
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (total_files - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{total_files}] {date_label} | 股票: {len(stock_count)} | 耗时: {elapsed:.0f}s | 预计剩余: {remaining:.0f}s")
        
        try:
            # 只读需要的列
            df = pd.read_parquet(f, columns=['code', 'trade_time', 'high', 'low', 'close'])
            
            # 记录股票代码
            stock_count.update(df['code'].unique())
            
            # 重命名列
            df = df.rename(columns={'trade_time': 'day'})
            df['day'] = pd.to_datetime(df['day'])
            
            # 按股票分组
            for code, grp in df.groupby('code', sort=False):
                grp_out = grp[['day', 'high', 'low', 'close']].copy()
                stock_data[code].append(grp_out)
                
        except Exception as e:
            print(f"    错误: {f} - {e}")
    
    print()
    print("=" * 60)
    print(f"处理完成! 收集到 {len(stock_data)} 只股票的数据")
    print("开始保存...")
    print("=" * 60)
    
    # 保存每个股票
    saved = 0
    for idx, code in enumerate(sorted(stock_data.keys())):
        chunks = stock_data[code]
        
        if not chunks:
            continue
        
        # 合并
        combined = pd.concat(chunks, ignore_index=True)
        combined = combined.drop_duplicates(subset=['day'], keep='last')
        combined = combined.sort_values('day').reset_index(drop=True)
        
        # 保存
        if code.endswith('.SZ'):
            filename = f"sz{code.replace('.SZ', '')}_min1.csv"
        elif code.endswith('.SH'):
            filename = f"sh{code.replace('.SH', '')}_min1.csv"
        else:
            filename = f"{code}_min1.csv"
        
        out_file = os.path.join(OUTPUT_DIR, filename)
        combined.to_csv(out_file, index=False, encoding='utf-8')
        saved += 1
        
        if saved % 500 == 0 or saved == len(stock_data):
            print(f"  保存进度: {saved}/{len(stock_data)}")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("转换完成!")
    print("=" * 60)
    print(f"  处理文件: {total_files}")
    print(f"  股票数量: {saved}")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  总耗时: {elapsed:.0f} 秒 ({elapsed/60:.1f} 分钟)")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='全市场 Parquet → CSV 转换')
    parser.add_argument('--test', action='store_true', help='测试模式')
    args = parser.parse_args()
    
    convert_allmarket_fast(test_mode=args.test)
