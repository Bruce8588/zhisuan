#!/usr/bin/env python3
"""
全市场股票趋势分析 - 高速版
使用向量化操作提升性能
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from glob import glob
from concurrent.futures import ProcessPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.trend import init_state, update_trend
from config.rules import TREND_NAMES

DATA_DIR = os.path.join(BASE_DIR, "data_allmarket")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_allmarket", "趋势判断")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_code_from_filename(filename):
    name = filename.replace('_min1.csv', '')
    if '_' in name:
        return name.rsplit('_', 1)[-1]
    return name


def analyze_stock_fast(args):
    """快速分析单只股票"""
    filepath, code = args
    
    try:
        df = pd.read_csv(filepath)
        df["day"] = pd.to_datetime(df["day"])
        df = df.sort_values("day").reset_index(drop=True)
        
        if len(df) < 100:
            return code, 0
        
        # 初始化状态
        first_high = float(df.iloc[0]["high"])
        state = init_state({
            "trend": "up",
            "key_high": first_high,
            "key_low": None,
            "n_low": None,
            "n_high": None,
            "rally_high": None,
            "rally_low": None,
            "secondary_low": None,
            "secondary_high": None,
            "break_low": None,
            "break_high": None,
        })
        
        # 预分配数组
        n = len(df)
        trends = np.empty(n, dtype=object)
        key_highs = np.empty(n, dtype=float)
        key_lows = np.empty(n, dtype=float)
        n_lows = np.full(n, np.nan)
        n_highs = np.full(n, np.nan)
        rally_highs = np.full(n, np.nan)
        rally_lows = np.full(n, np.nan)
        secondary_lows = np.full(n, np.nan)
        secondary_highs = np.full(n, np.nan)
        
        for i in range(n):
            high = float(df.iloc[i]["high"])
            low = float(df.iloc[i]["low"])
            
            state = update_trend(state, high, low)
            
            trends[i] = state["trend"]
            key_highs[i] = state["key_high"]
            key_lows[i] = state["key_low"] if state["key_low"] else np.nan
            n_lows[i] = state["n_low"] if state["n_low"] else np.nan
            n_highs[i] = state["n_high"] if state["n_high"] else np.nan
            rally_highs[i] = state["rally_high"] if state["rally_high"] else np.nan
            rally_lows[i] = state["rally_low"] if state["rally_low"] else np.nan
            secondary_lows[i] = state["secondary_low"] if state["secondary_low"] else np.nan
            secondary_highs[i] = state["secondary_high"] if state["secondary_high"] else np.nan
        
        # 构建结果DataFrame
        result = pd.DataFrame({
            "时间": df["day"],
            "当前价格": df["close"],
            "趋势代码": trends,
            "趋势名称": [TREND_NAMES.get(t, t) for t in trends],
            "key_high": key_highs,
            "key_low": key_lows,
            "n_low": n_lows,
            "n_high": n_highs,
            "rally_high": rally_highs,
            "rally_low": rally_lows,
            "secondary_low": secondary_lows,
            "secondary_high": secondary_highs,
        })
        
        output_file = os.path.join(OUTPUT_DIR, f"{code}_趋势判断.csv")
        result.to_csv(output_file, index=False, encoding="utf-8")
        
        return code, len(result)
    except Exception as e:
        return code, 0


def main():
    start_time = datetime.now()
    
    print("=" * 60)
    print("全市场股票趋势分析 - 高速版")
    print("=" * 60)
    
    files = sorted(glob(os.path.join(DATA_DIR, "*_min1.csv")))
    total = len(files)
    
    args_list = [(f, get_code_from_filename(os.path.basename(f))) for f in files]
    
    print(f"数据目录: {DATA_DIR}")
    print(f"股票数量: {total}")
    print(f"并行进程: 8")
    print()
    
    results = []
    completed = 0
    
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(analyze_stock_fast, args): args for args in args_list}
        
        for future in as_completed(futures):
            code, count = future.result()
            completed += 1
            if completed % 200 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"进度: {completed}/{total} ({100*completed/total:.1f}%) | 耗时: {elapsed:.0f}s")
            
            if count > 0:
                results.append(code)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"  成功: {len(results)} 只")
    print(f"  总耗时: {elapsed:.0f}s ({elapsed/60:.1f}分钟)")
    print(f"  输出目录: {OUTPUT_DIR}")
    
    # 保存摘要
    summary_file = os.path.join(os.path.dirname(OUTPUT_DIR), "分析结果.csv")
    pd.DataFrame({"code": results}).to_csv(summary_file, index=False, encoding="utf-8")
    print(f"  结果摘要: {summary_file}")


if __name__ == "__main__":
    main()
