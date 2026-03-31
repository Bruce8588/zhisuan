#!/usr/bin/env python3
"""
全市场分钟数据分析 - 从2025年起
使用2024-12-31日线分析结果作为初始配置
"""
import os
import sys
import pandas as pd
from datetime import datetime
from glob import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.trend import init_state, update_trend
from config.rules import TREND_NAMES
from config.init_2024_12_31 import ALL_STOCKS_2024

# 配置 - 分钟数据
DATA_DIR = os.path.join(BASE_DIR, "data_allmarket")  # 分钟数据目录
OUTPUT_DIR = os.path.join(BASE_DIR, "output_minute_2025", "趋势判断")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def analyze_stock(code, df_data, init_config):
    """分析单只股票"""
    try:
        state = init_state(init_config)
        
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
            })
        
        return pd.DataFrame(records)
    except Exception as e:
        print(f"处理 {code} 时出错: {e}")
        return None


def normalize_code(code):
    """标准化股票代码格式，统一转为6位数字（去掉前导零用于匹配配置）"""
    code_str = str(code).strip()
    # 去掉前导零，用于匹配配置
    return str(int(code_str)) if code_str.isdigit() else code_str


def format_code(code):
    """格式化股票代码为6位带前导零格式（用于文件名）"""
    code_str = str(code).strip()
    if code_str.isdigit():
        return code_str.zfill(6)
    return code_str


def main():
    start_time = datetime.now()
    
    print("=" * 60)
    print("全市场分钟数据分析 - 2025年起")
    print("=" * 60)
    print(f"初始配置: config/init_2024_12_31.py")
    print(f"数据目录: {DATA_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"配置股票数量: {len(ALL_STOCKS_2024)}")
    print()
    
    success = 0
    no_config = 0
    no_data = 0
    
    # 遍历配置文件中的所有股票
    for i, (code, init_config) in enumerate(ALL_STOCKS_2024.items()):
        # 标准化code用于匹配
        normalized_code = normalize_code(code)
        
        # 找到对应的分钟数据文件
        data_file = None
        for f in os.listdir(DATA_DIR):
            if normalized_code in f and f.endswith('_min1.csv'):
                data_file = os.path.join(DATA_DIR, f)
                break
        
        if data_file is None:
            no_data += 1
            continue
        
        try:
            df_data = pd.read_csv(data_file)
            df_data["day"] = pd.to_datetime(df_data["day"])
            
            # 只处理2025年及之后的数据
            df_data = df_data[df_data["day"] >= "2025-01-01"]
            df_data = df_data.sort_values(by="day").reset_index(drop=True)
            
            if len(df_data) < 10:
                continue
            
            result = analyze_stock(normalized_code, df_data, init_config)
            
            if result is not None and len(result) > 0:
                # 使用标准化格式保存（无前导零）
                output_file = os.path.join(OUTPUT_DIR, f"{normalized_code}_趋势判断.csv")
                result.to_csv(output_file, index=False, encoding="utf-8")
                success += 1
                
                if (i + 1) % 200 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"进度: {i+1}/{len(ALL_STOCKS_2024)} ({100*(i+1)/len(ALL_STOCKS_2024):.1f}%) | 成功: {success} | 无数据: {no_data} | 耗时: {elapsed:.0f}s")
            else:
                no_config += 1
        except Exception as e:
            if (i + 1) % 200 == 0:
                print(f"进度: {i+1}/{len(ALL_STOCKS_2024)} - {code} 失败: {e}")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"  成功: {success}")
    print(f"  无数据文件: {no_data}")
    print(f"  无结果: {no_config}")
    print(f"  总耗时: {elapsed:.0f}s ({elapsed/60:.1f}分钟)")
    print(f"  输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
