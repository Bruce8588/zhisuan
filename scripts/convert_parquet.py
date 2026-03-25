#!/usr/bin/env python3
"""
将桌面 parquet 数据转换为智算格式 CSV
支持 2025 和 2026 文件夹的每日快照
"""
import os
import sys
import pandas as pd
from glob import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS

PARQUET_DIRS = [
    "/Users/isenfengming/Desktop/2025",
    "/Users/isenfengming/Desktop/2026",
]
OUTPUT_DIR = os.path.join(BASE_DIR, "data")


def build_code_map():
    code_to_name = {}
    for name, info in ALL_STOCKS.items():
        raw = info['code']
        if raw.startswith('sz'):
            ifind = raw[2:] + '.SZ'
        elif raw.startswith('sh'):
            ifind = raw[2:] + '.SH'
        else:
            if len(raw) == 6 and raw[0] in ('0', '3'):
                ifind = raw + '.SZ'
            else:
                ifind = raw + '.SH'
        code_to_name[ifind] = name
    return code_to_name


def convert_parquet():
    code_to_name = build_code_map()
    target_codes = set(code_to_name.keys())
    name_to_code = {v: k for k, v in code_to_name.items()}

    print(f"目标股票: {len(target_codes)}")
    print(f"数据来源: {PARQUET_DIRS}")
    print()

    parquet_files = []
    for pq_dir in PARQUET_DIRS:
        files = sorted(glob(os.path.join(pq_dir, "*.parquet")))
        parquet_files.extend(files)
        print(f"  {pq_dir}: {len(files)} 个 parquet 文件")

    parquet_files.sort()
    print(f"共 {len(parquet_files)} 个文件待处理\n")

    stock_dfs = {name: [] for name in ALL_STOCKS}

    for i, f in enumerate(parquet_files):
        date_label = os.path.basename(f).replace('.parquet', '')
        if (i + 1) % 20 == 0 or i == 0 or i == len(parquet_files) - 1:
            print(f"  处理中 {i+1}/{len(parquet_files)}: {date_label}")

        try:
            df = pd.read_parquet(f, columns=['code', 'trade_time', 'high', 'low', 'close'])
        except Exception as e:
            print(f"    读取失败 {f}: {e}")
            continue

        df = df[df['code'].isin(target_codes)]
        if df.empty:
            continue

        df = df.rename(columns={'trade_time': 'day'})
        df['name'] = df['code'].map(code_to_name)

        for name, grp in df.groupby('name', sort=False):
            if name in stock_dfs:
                grp_out = grp[['day', 'high', 'low', 'close']].copy()
                grp_out['day'] = pd.to_datetime(grp_out['day'])
                stock_dfs[name].append(grp_out)

    print(f"\n合并保存 {len(stock_dfs)} 只股票...")

    for name, chunks in stock_dfs.items():
        if not chunks:
            print(f"  {name}: 无数据")
            continue

        combined = pd.concat(chunks, ignore_index=True)
        combined = combined.drop_duplicates(subset=['day'], keep='last')
        combined = combined.sort_values('day').reset_index(drop=True)

        info = ALL_STOCKS[name]
        code = info['code']
        out_file = os.path.join(OUTPUT_DIR, f"{name}_{code}_min1.csv")

        before = 0
        if os.path.exists(out_file):
            old = pd.read_csv(out_file)
            old['day'] = pd.to_datetime(old['day'])
            before = len(old)
            combined = pd.concat([old, combined], ignore_index=True)
            combined = combined.drop_duplicates(subset=['day'], keep='last')
            combined = combined.sort_values('day').reset_index(drop=True)

        print(f"  {name}: {before} → {len(combined)} 条 ({len(combined) - before:+d})")
        combined.to_csv(out_file, index=False, encoding='utf-8')

    print("\n完成！")


if __name__ == "__main__":
    convert_parquet()
