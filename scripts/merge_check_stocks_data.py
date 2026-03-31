#!/usr/bin/env python3
"""
合并15只检查股票的连贯数据
2015-2024: 日线数据
2025-2026: 分钟数据（从output_allmarket提取）
"""
import os
import pandas as pd

BASE_DIR = "/Users/isenfengming/.openclaw/workspace/工作台/智算"

# 15只检查股票
STOCKS = {
    "sz000630": "铜陵有色",
    "sz002532": "天山铝业",
    "sz000933": "神火股份",
    "sh600089": "特变电工",
    "sz002273": "水晶光电",
    "sz002475": "立讯精密",
    "sz002241": "歌尔股份",
    "sz000333": "美的集团",
    "sz000425": "徐工机械",
    "sh603556": "海兴电力",
    "sz002050": "三花智控",
    "sh603588": "高能环境",
    "sh601611": "中国核建",
    "sz002156": "通富微电",
    "sz003015": "日久光电",
}

# 代码转换：sz000630 -> 000630 (用于日线数据)
def to_day_code(exchange_code):
    code = exchange_code[2:]  # 去掉sz/sh
    return code

def extract_code(exchange_code):
    return exchange_code[2:]

def main():
    OUTPUT_DIR = os.path.join(BASE_DIR, "data_check_stocks")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 70)
    print("合并15只检查股票的连贯数据")
    print("=" * 70)
    
    for exchange_code, name in STOCKS.items():
        print(f"\n处理 {name}({exchange_code})...")
        
        day_code = extract_code(exchange_code)
        
        # 1. 读取2015-2024日线数据
        file_2015_2024 = os.path.join(BASE_DIR, "data_daily_2015_2024", f"{day_code}_day.csv")
        if os.path.exists(file_2015_2024):
            df_old = pd.read_csv(file_2015_2024)
            df_old["day"] = pd.to_datetime(df_old["day"])
            df_old = df_old.sort_values("day")
            print(f"  2015-2024: {len(df_old)} 条 ({df_old['day'].min()} ~ {df_old['day'].max()})")
        else:
            print(f"  2015-2024: 文件不存在")
            df_old = pd.DataFrame()
        
        # 2. 读取2025-2026分钟数据
        minute_file = os.path.join(BASE_DIR, "output_allmarket", "趋势判断", f"{exchange_code}_趋势判断.csv")
        if os.path.exists(minute_file):
            df_minute = pd.read_csv(minute_file, usecols=[0, 1])  # 只读取时间和价格
            df_minute.columns = ["时间", "收盘"]
            df_minute["时间"] = pd.to_datetime(df_minute["时间"])
            df_minute = df_minute.sort_values("时间")
            print(f"  2025-2026: {len(df_minute)} 条 ({df_minute['时间'].min()} ~ {df_minute['时间'].max()})")
        else:
            print(f"  2025-2026: 文件不存在")
            df_minute = pd.DataFrame()
        
        # 3. 合并数据
        if len(df_old) > 0 and len(df_minute) > 0:
            # 日线数据：选择需要的列
            df_old_renamed = df_old.rename(columns={
                "day": "时间",
                "close": "收盘",
                "high": "最高",
                "low": "最低"
            })
            df_old_renamed = df_old_renamed[["时间", "收盘", "最高", "最低"]]
            df_old_renamed["时间"] = pd.to_datetime(df_old_renamed["时间"]).dt.strftime("%Y-%m-%d")
            df_old_renamed["类型"] = "日线"
            
            # 分钟数据
            df_minute["类型"] = "分钟"
            
            # 合并
            df_combined = pd.concat([df_old_renamed, df_minute], ignore_index=True)
            # 统一转换为datetime再排序
            df_combined["时间_dt"] = pd.to_datetime(df_combined["时间"])
            df_combined = df_combined.sort_values("时间_dt").drop(columns=["时间_dt"]).reset_index(drop=True)
            
            # 保存
            output_file = os.path.join(OUTPUT_DIR, f"{exchange_code}_{name}_连贯数据.csv")
            df_combined.to_csv(output_file, index=False, encoding="utf-8")
            print(f"  合并后: {len(df_combined)} 条")
            print(f"  保存至: {output_file}")
        else:
            print(f"  跳过（数据不完整）")
    
    print("\n" + "=" * 70)
    print("完成！")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
