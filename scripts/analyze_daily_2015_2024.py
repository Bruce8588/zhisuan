#!/usr/bin/env python3
"""
全市场日线数据趋势分析 (2015-2024)
"""
import os
import sys
import pandas as pd
import time
from datetime import datetime
from glob import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.trend import init_state, update_trend
from config.rules import TREND_NAMES

# 配置 - 日线数据
DATA_DIR = os.path.join(BASE_DIR, "data_daily_2015_2024")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_daily_2015_2024", "趋势判断")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_code_from_filename(filename):
    """从文件名提取代码: 000630_day.csv -> 000630"""
    return filename.replace('_day.csv', '')


def analyze_stock(code, df_data):
    """分析单只股票"""
    try:
        first_high = float(df_data.iloc[0]["high"])
        
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
        print(f"处理 {code} 时出错: {e}")
        return None


def main():
    start_time = datetime.now()
    
    print("=" * 60)
    print("全市场日线数据趋势分析 (2015-2024)")
    print("=" * 60)
    print(f"数据目录: {DATA_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    
    files = sorted(glob(os.path.join(DATA_DIR, "*_day.csv")))
    total = len(files)
    
    print(f"股票数量: {total}")
    print()
    
    success = 0
    results = []
    
    for i, filepath in enumerate(files):
        code = get_code_from_filename(os.path.basename(filepath))
        
        try:
            df_data = pd.read_csv(filepath)
            df_data["day"] = pd.to_datetime(df_data["day"])
            df_data = df_data.sort_values("day").reset_index(drop=True)
            
            result = analyze_stock(code, df_data)
            
            if result is not None and len(result) > 0:
                output_file = os.path.join(OUTPUT_DIR, f"{code}_趋势判断.csv")
                result.to_csv(output_file, index=False, encoding="utf-8")
                success += 1
                
                # 获取最后一条记录作为最终状态
                last = result.iloc[-1]
                results.append({
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
                })
                
                if (i + 1) % 200 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"进度: {i+1}/{total} ({100*(i+1)/total:.1f}%) | 成功: {success} | 耗时: {elapsed:.0f}s")
            else:
                if (i + 1) % 200 == 0:
                    print(f"进度: {i+1}/{total} - {code} 无结果")
        except Exception as e:
            if (i + 1) % 200 == 0:
                print(f"进度: {i+1}/{total} - {code} 失败: {e}")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"  成功: {success}/{total}")
    print(f"  总耗时: {elapsed:.0f}s ({elapsed/60:.1f}分钟)")
    print(f"  输出目录: {OUTPUT_DIR}")
    
    # 保存最终状态摘要
    if results:
        summary_file = os.path.join(os.path.dirname(OUTPUT_DIR), "最终状态摘要.csv")
        pd.DataFrame(results).to_csv(summary_file, index=False, encoding="utf-8")
        print(f"  状态摘要: {summary_file}")


if __name__ == "__main__":
    main()
