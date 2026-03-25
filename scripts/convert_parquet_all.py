#!/usr/bin/env python3
"""
全市场数据转换脚本
将桌面 parquet 数据转换为智算格式 CSV（支持全部股票）

用法：
    python convert_parquet_all.py              # 全市场转换
    python convert_parquet_all.py --test       # 测试模式（只处理3个文件）
"""
import os
import sys
import pandas as pd
from glob import glob
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

PARQUET_DIRS = [
    "/Users/isenfengming/Desktop/2025",
    "/Users/isenfengming/Desktop/2026",
]
OUTPUT_DIR = os.path.join(BASE_DIR, "data_allmarket")


def convert_allmarket(test_mode=False):
    """全市场转换主函数"""
    
    print("=" * 60)
    print("全市场 Parquet → CSV 转换")
    print("=" * 60)
    print()
    print(f"数据来源: {PARQUET_DIRS}")
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 获取所有 parquet 文件
    parquet_files = []
    for pq_dir in PARQUET_DIRS:
        if os.path.exists(pq_dir):
            files = sorted(glob(os.path.join(pq_dir, "*.parquet")))
            parquet_files.extend(files)
            print(f"  {pq_dir}: {len(files)} 个文件")
    
    if test_mode:
        parquet_files = parquet_files[:3]
        print(f"\n[测试模式] 只处理前3个文件")
    
    parquet_files.sort()
    print(f"\n总计: {len(parquet_files)} 个文件待处理")
    print()
    
    start_time = datetime.now()
    
    # 第一步：收集所有文件中的股票代码
    print("=" * 60)
    print("步骤1: 扫描股票代码...")
    print("=" * 60)
    
    all_codes = set()
    for i, f in enumerate(parquet_files):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  扫描中 {i+1}/{len(parquet_files)}: {os.path.basename(f)}")
        
        try:
            df = pd.read_parquet(f, columns=['code'])
            all_codes.update(df['code'].unique())
        except Exception as e:
            print(f"    读取失败: {f} - {e}")
    
    all_codes = sorted(all_codes)
    print(f"\n发现股票: {len(all_codes)} 只")
    print()
    
    # 第二步：处理每个文件，按股票分组
    print("=" * 60)
    print("步骤2: 处理文件...")
    print("=" * 60)
    
    # 每个股票的待合并数据
    stock_data = defaultdict(list)
    
    for i, f in enumerate(parquet_files):
        date_label = os.path.basename(f).replace('.parquet', '')
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"  [{i+1}/{len(parquet_files)}] {date_label} ({elapsed:.0f}秒)")
        
        try:
            df = pd.read_parquet(f, columns=['code', 'trade_time', 'high', 'low', 'close'])
            df = df.rename(columns={'trade_time': 'day'})
            df['day'] = pd.to_datetime(df['day'])
            
            # 按股票分组
            for code, grp in df.groupby('code', sort=False):
                grp_out = grp[['day', 'high', 'low', 'close']].copy()
                stock_data[code].append(grp_out)
                
        except Exception as e:
            print(f"    处理失败: {f} - {e}")
    
    print(f"\n收集完成: {len(stock_data)} 只股票")
    print()
    
    # 第三步：合并保存每个股票
    print("=" * 60)
    print("步骤3: 合并保存...")
    print("=" * 60)
    
    saved = 0
    skipped = 0
    
    for code in all_codes:
        chunks = stock_data.get(code, [])
        
        if not chunks:
            skipped += 1
            continue
        
        # 合并
        combined = pd.concat(chunks, ignore_index=True)
        combined = combined.drop_duplicates(subset=['day'], keep='last')
        combined = combined.sort_values('day').reset_index(drop=True)
        
        # 保存
        # 代码格式: 000001.SZ -> sz000001 或 600001.SH -> sh600001
        if code.endswith('.SZ'):
            filename = f"sz{code.replace('.SZ', '')}_min1.csv"
        elif code.endswith('.SH'):
            filename = f"sh{code.replace('.SH', '')}_min1.csv"
        else:
            # 未知格式，直接用code
            filename = f"{code}_min1.csv"
        
        out_file = os.path.join(OUTPUT_DIR, filename)
        combined.to_csv(out_file, index=False, encoding='utf-8')
        saved += 1
        
        if saved % 500 == 0:
            print(f"  已保存: {saved}/{len(all_codes)}")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("转换完成!")
    print("=" * 60)
    print(f"  处理文件: {len(parquet_files)}")
    print(f"  股票数量: {saved} 只")
    print(f"  无数据: {skipped} 只")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  总耗时: {elapsed:.0f} 秒")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='全市场 Parquet → CSV 转换')
    parser.add_argument('--test', action='store_true', help='测试模式（只处理3个文件）')
    args = parser.parse_args()
    
    convert_allmarket(test_mode=args.test)
