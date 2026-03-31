#!/usr/bin/env python3
"""
全市场分钟趋势重新分析 - 使用2024年底状态初始化（并行版）
直接从现有趋势结果读取数据，用收盘价代替high/low重新计算
"""
import os
import sys

# 设置 fork 模式（macOS Python 3.13 需要）
import multiprocessing
try:
    multiprocessing.set_start_method('fork', force=True)
except RuntimeError:
    pass

import pandas as pd
import numpy as np
from datetime import datetime
from glob import glob
from concurrent.futures import ProcessPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.trend import init_state, update_trend
from config.rules import TREND_NAMES

# 配置
INPUT_DIR = os.path.join(BASE_DIR, "output_allmarket", "趋势判断")
INIT_STATE_FILE = os.path.join(BASE_DIR, "output_daily_2015_2024", "最终状态摘要.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_allmarket", "趋势判断_new")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_init_states():
    """加载2024年底的最终状态"""
    df = pd.read_csv(INIT_STATE_FILE)
    states = {}
    for _, row in df.iterrows():
        code = f'{int(row["code"]):06d}'
        states[code] = {
            "trend": row["趋势"],
            "key_high": row["key_high"] if pd.notna(row["key_high"]) else None,
            "key_low": row["key_low"] if pd.notna(row["key_low"]) else None,
            "n_low": row["n_low"] if pd.notna(row["n_low"]) else None,
            "n_high": row["n_high"] if pd.notna(row["n_high"]) else None,
            "rally_high": row["rally_high"] if pd.notna(row["rally_high"]) else None,
            "rally_low": row["rally_low"] if pd.notna(row["rally_low"]) else None,
            "secondary_low": row["secondary_low"] if pd.notna(row["secondary_low"]) else None,
            "secondary_high": row["secondary_high"] if pd.notna(row["secondary_high"]) else None,
            "break_low": row["break_low"] if "break_low" in row and pd.notna(row["break_low"]) else None,
            "break_high": row["break_high"] if "break_high" in row and pd.notna(row["break_high"]) else None,
        }
    print(f"加载了 {len(states)} 只股票的初始状态")
    return states


def get_code_from_filename(filename):
    """从文件名提取代码: sh600000_趋势判断.csv -> 600000"""
    name = filename.replace('_趋势判断.csv', '')
    if name.startswith('sh') or name.startswith('sz'):
        name = name[2:]
    return name


def reanalyze_stock(args):
    """重新分析单只股票"""
    filepath, code, init_config = args
    
    try:
        df_input = pd.read_csv(filepath)
        df_input["时间"] = pd.to_datetime(df_input["时间"])
        df_input = df_input.sort_values("时间").reset_index(drop=True)
        
        state = init_state(init_config)
        
        n = len(df_input)
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
            close = float(df_input.iloc[i]["当前价格"])
            high = close
            low = close
            
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
        
        result = pd.DataFrame({
            "时间": df_input["时间"],
            "当前价格": df_input["当前价格"],
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
            "break_low": state["break_low"] if state["break_low"] else np.nan,
            "break_high": state["break_high"] if state["break_high"] else np.nan,
        })
        
        output_file = os.path.join(OUTPUT_DIR, f"{code}_趋势判断.csv")
        result.to_csv(output_file, index=False, encoding="utf-8")
        
        # 获取最后状态
        last = result.iloc[-1]
        return {
            "code": code,
            "日期": last["时间"],
            "趋势": last["趋势代码"],
            "key_high": last["key_high"],
            "key_low": last["key_low"],
            "n_low": last["n_low"],
            "n_high": last["n_high"],
            "rally_high": last["rally_high"],
            "rally_low": last["rally_low"],
            "secondary_low": last["secondary_low"],
            "secondary_high": last["secondary_high"],
            "break_low": last["break_low"],
            "break_high": last["break_high"],
        }
    except Exception as e:
        print(f"处理 {code} 出错: {e}")
        return None


def main():
    start_time = datetime.now()
    
    print("=" * 60)
    print("全市场分钟趋势重新分析 - 并行版")
    print("=" * 60)
    
    # 加载初始状态
    init_states = load_init_states()
    
    files = sorted(glob(os.path.join(INPUT_DIR, "*.csv")))
    total = len(files)
    print(f"股票数量: {total}")
    print(f"并行进程: 8")
    print()
    
    # 构建参数列表，只处理有初始状态的
    args_list = []
    for filepath in files:
        filename = os.path.basename(filepath)
        code = get_code_from_filename(filename)
        if code in init_states:
            args_list.append((filepath, filename.replace('_趋势判断.csv', ''), init_states[code]))
    
    print(f"需要处理: {len(args_list)} 只")
    print()
    
    results = []
    completed = 0
    
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(reanalyze_stock, args): args[1] for args in args_list}
        
        for future in as_completed(futures):
            code = futures[future]
            result = future.result()
            completed += 1
            
            if result is not None:
                results.append(result)
            
            if completed % 500 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = completed / elapsed
                remaining = (len(args_list) - completed) / rate if rate > 0 else 0
                print(f"进度: {completed}/{len(args_list)} ({100*completed/len(args_list):.1f}%) | 成功: {len(results)} | 耗时: {elapsed:.0f}s | 预计剩余: {remaining:.0f}s")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"  成功: {len(results)}/{len(args_list)}")
    print(f"  总耗时: {elapsed:.0f}s ({elapsed/60:.1f}分钟)")
    print(f"  输出目录: {OUTPUT_DIR}")
    
    # 保存最终状态摘要
    if results:
        summary_file = os.path.join(OUTPUT_DIR, "最终状态摘要.csv")
        pd.DataFrame(results).to_csv(summary_file, index=False, encoding="utf-8")
        print(f"  状态摘要: {summary_file}")


if __name__ == "__main__":
    main()
