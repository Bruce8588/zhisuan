#!/usr/bin/env python3
"""
全市场股票趋势分析
对data_allmarket中的所有股票进行趋势判断
"""
import os
import sys
import pandas as pd
import time
from datetime import datetime
from glob import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.trend import TrendAnalyzer, init_state, update_trend
from config.rules import TREND_NAMES

# 配置
DATA_DIR = os.path.join(BASE_DIR, "data_allmarket")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_allmarket", "趋势判断")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_code_from_filename(filename):
    """从文件名提取代码: 
    - 旧格式: 浦发银行_sh600000_min1.csv -> sh600000
    - 新格式: sh600000_min1.csv -> sh600000
    """
    name = filename.replace('_min1.csv', '')
    # 如果有下划线，取最后一部分
    if '_' in name:
        return name.rsplit('_', 1)[-1]
    # 否则直接返回
    return name


def analyze_stock(code, df_data):
    """分析单只股票"""
    try:
        # 获取第一个价格作为 key_high
        first_high = float(df_data.iloc[0]["high"])
        
        # 初始化状态（从up开始，让趋势自然发展）
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
        
        records = []
        for _, row in df_data.iterrows():
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            
            state = update_trend(state, high, low)
            
            records.append({
                "时间": row["day"],
                "当前价格": close,
                "趋势代码": state["trend"],
                "趋势名称": TREND_NAMES.get(state["trend"], state["trend"]),
                "key_high": state["key_high"],
                "key_low": state["key_low"],
                "n_low": state["n_low"],
                "n_high": state["n_high"],
                "rally_high": state["rally_high"],
                "rally_low": state["rally_low"],
                "secondary_low": state["secondary_low"],
                "secondary_high": state["secondary_high"],
                "break_low": state["break_low"],
                "break_high": state["break_high"],
            })
        
        return pd.DataFrame(records)
    except Exception as e:
        print(f"    错误: {e}")
        return None


def main():
    start_time = datetime.now()
    
    print("=" * 60)
    print("全市场股票趋势分析")
    print("=" * 60)
    
    # 获取所有股票文件
    files = sorted(glob(os.path.join(DATA_DIR, "*_min1.csv")))
    total = len(files)
    
    print(f"数据目录: {DATA_DIR}")
    print(f"股票数量: {total}")
    print()
    
    results = []
    errors = 0
    
    for i, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        code = get_code_from_filename(filename)
        
        if not code:
            errors += 1
            continue
        
        # 每20只显示进度
        if (i + 1) % 20 == 0 or i == 0 or i == total - 1:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (total - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{total}] {code} | 耗时:{elapsed:.0f}s | 预计剩余:{remaining:.0f}s")
        
        try:
            # 读取数据
            df = pd.read_csv(filepath)
            if 'day' not in df.columns:
                df.rename(columns={'时间': 'day'}, inplace=True)
            df["day"] = pd.to_datetime(df["day"])
            df = df.sort_values("day").reset_index(drop=True)
            
            if len(df) < 100:  # 数据太少跳过
                continue
            
            # 分析
            result_df = analyze_stock(code, df)
            
            if result_df is not None and len(result_df) > 0:
                # 保存
                output_file = os.path.join(OUTPUT_DIR, f"{code}_趋势判断.csv")
                result_df.to_csv(output_file, index=False, encoding="utf-8")
                results.append({
                    'code': code,
                    'records': len(result_df),
                    'file': output_file
                })
            
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    错误 {code}: {e}")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"  处理: {len(results)} 只")
    print(f"  错误: {errors} 只")
    print(f"  总耗时: {elapsed:.0f}s ({elapsed/60:.1f}分钟)")
    print(f"  输出目录: {OUTPUT_DIR}")
    print()
    
    # 保存处理结果摘要
    summary_file = os.path.join(os.path.dirname(OUTPUT_DIR), "分析结果.csv")
    summary_df = pd.DataFrame(results)
    if len(summary_df) > 0:
        summary_df.to_csv(summary_file, index=False, encoding="utf-8")
        print(f"  结果摘要: {summary_file}")


if __name__ == "__main__":
    main()
