#!/usr/bin/env python3
"""
使用output_allmarket中的时间、价格数据
用正确的初始配置重新做趋势判断
"""
import os
import sys
import pandas as pd
from datetime import datetime

BASE_DIR = "/Users/isenfengming/.openclaw/workspace/工作台/智算"
sys.path.insert(0, BASE_DIR)

from core.trend import init_state, update_trend
from config.rules import TREND_NAMES

# 输入输出目录
INPUT_DIR = os.path.join(BASE_DIR, "output_allmarket", "趋势判断")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_minute_2025", "趋势判断")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 15只检查股票的正确初始配置（从docs/趋势检查.md提取）
CORRECT_CONFIG = {
    "sz000630": {
        "trend": "up_rally", "key_high": 9.19, "key_low": None, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "铜陵有色"
    },
    "sz002532": {
        "trend": "down_rally", "key_high": None, "key_low": 16.68, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": 17.05, 
        "secondary_low": None, "secondary_high": None, "name": "天山铝业"
    },
    "sz000933": {
        "trend": "down", "key_high": None, "key_low": 29.76, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "神火股份"
    },
    "sh600089": {
        "trend": "up_rally", "key_high": 32.99, "key_low": None, 
        "n_low": None, "n_high": None, "rally_high": 30.21, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "特变电工"
    },
    "sz002273": {
        "trend": "up", "key_high": 28.63, "key_low": None, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "水晶光电"
    },
    "sz002475": {
        "trend": "down", "key_high": None, "key_low": 49.26, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "立讯精密"
    },
    "sz002241": {
        "trend": "down", "key_high": None, "key_low": 25.6, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "歌尔股份"
    },
    "sz000333": {
        "trend": "up_rally", "key_high": 83.17, "key_low": None, 
        "n_low": 75, "n_high": None, "rally_high": 81.16, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "美的集团"
    },
    "sz000425": {
        "trend": "up", "key_high": 12.83, "key_low": None, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "徐工机械"
    },
    "sh603556": {
        "trend": "down_natural", "key_high": None, "key_low": 36.49, 
        "n_low": None, "n_high": 39.11, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "海兴电力"
    },
    "sz002050": {
        "trend": "up_rally", "key_high": 60.77, "key_low": None, 
        "n_low": 49.08, "n_high": None, "rally_high": 55.02, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "三花智控"
    },
    "sh603588": {
        "trend": "up", "key_high": 11.3, "key_low": None, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "高能环境"
    },
    "sh601611": {
        "trend": "down_rally", "key_high": None, "key_low": 15.1, 
        "n_low": None, "n_high": 16.08, "rally_high": None, "rally_low": 15.11, 
        "secondary_low": None, "secondary_high": None, "name": "中国核建"
    },
    "sz002156": {
        "trend": "down_natural", "key_high": None, "key_low": 46.16, 
        "n_low": None, "n_high": 49.8, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "通富微电"
    },
    "sz003015": {
        "trend": "up", "key_high": 17.85, "key_low": None, 
        "n_low": None, "n_high": None, "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None, "name": "日久光电"
    },
}

# 正确趋势（用于验证）
CORRECT_TRENDS = {
    "铜陵有色": {"init": "up_rally", "3.6": "up_secondary", "3.10": "up_secondary"},
    "天山铝业": {"init": "down_rally", "3.6": "up_natural", "3.10": "up_break"},
    "神火股份": {"init": "down", "3.6": "down_rally", "3.10": "down_rally"},
    "特变电工": {"init": "up_rally", "3.6": "up", "3.10": "up"},
    "水晶光电": {"init": "up", "3.6": "up_rally", "3.10": "down_natural"},
    "立讯精密": {"init": "down", "3.6": "down", "3.10": "down_natural"},
    "歌尔股份": {"init": "down", "3.6": "down", "3.10": "down"},
    "美的集团": {"init": "up_rally", "3.6": "up_secondary", "3.10": "up_secondary"},
    "徐工机械": {"init": "up", "3.6": "up_natural", "3.10": "up_rally"},
    "海兴电力": {"init": "down_natural", "3.6": "up", "3.10": "up"},
    "三花智控": {"init": "up_rally", "3.6": "down", "3.10": "down_natural"},
    "高能环境": {"init": "up", "3.6": "up", "3.10": "up"},
    "中国核建": {"init": "down_rally", "3.6": "up", "3.10": "up"},
    "通富微电": {"init": "down_natural", "3.6": "down_secondary", "3.10": "down_natural"},
    "日久光电": {"init": "up", "3.6": "up", "3.10": "up_natural"},
}


def analyze_stock(code, df_data, init_config):
    """分析单只股票"""
    state = init_state(init_config)
    
    records = []
    for _, row in df_data.iterrows():
        high = float(row["当前价格"])  # 用当前价格作为high和low
        low = float(row["当前价格"])
        close = float(row["当前价格"])
        
        state = update_trend(state, high, low)
        
        records.append({
            "时间": row["时间"],
            "当前价格": close,
            "趋势代码": state["trend"],
            "趋势名称": TREND_NAMES.get(state["trend"], state["trend"]),
            "key_high": state["key_high"],
            "key_low": state["key_low"],
            "n_low": state["n_low"],
            "n_high": state["n_high"],
        })
    
    return pd.DataFrame(records)


def get_trend(df, date):
    """获取指定日期的趋势"""
    dt = pd.to_datetime(date)
    df_check = df[df["时间"].astype(str).str.startswith(str(dt.date()))]
    if len(df_check) > 0:
        return df_check.iloc[-1]["趋势代码"]
    return None


def main():
    print("=" * 70)
    print("15只检查股票 - 使用正确配置重新趋势判断")
    print("=" * 70)
    print(f"输入目录: {INPUT_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    
    results = []
    
    for code, config in CORRECT_CONFIG.items():
        name = config["name"]
        print(f"处理 {name}({code})...")
        
        input_file = os.path.join(INPUT_DIR, f"{code}_趋势判断.csv")
        
        if not os.path.exists(input_file):
            print(f"  ❌ 输入文件不存在")
            continue
        
        try:
            # 读取原始数据（只读取前两列）
            df_original = pd.read_csv(input_file, usecols=[0, 1])
            
            # 重命名列
            df_original.columns = ["时间", "当前价格"]
            
            # 分析
            result = analyze_stock(code, df_original, config)
            
            # 保存结果
            output_file = os.path.join(OUTPUT_DIR, f"{code}_趋势判断.csv")
            result.to_csv(output_file, index=False, encoding="utf-8")
            
            # 验证
            trend_224 = get_trend(result, "2026-02-24")
            trend_36 = get_trend(result, "2026-03-06")
            trend_310 = get_trend(result, "2026-03-10")
            
            correct = CORRECT_TRENDS[name]
            t1_ok = trend_224 == correct["init"]
            t2_ok = trend_36 == correct["3.6"]
            t3_ok = trend_310 == correct["3.10"]
            
            status = "✅" if (t1_ok and t2_ok and t3_ok) else "❌"
            
            print(f"  2.24: {trend_224} {'✅' if t1_ok else '❌'}")
            print(f"  3.6:  {trend_36} {'✅' if t2_ok else '❌'}")
            print(f"  3.10: {trend_310} {'✅' if t3_ok else '❌'}")
            print(f"  结果: {status}")
            
            results.append({
                "name": name, "code": code,
                "trend_224": trend_224, "trend_36": trend_36, "trend_310": trend_310,
                "status": status
            })
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            results.append({"name": name, "code": code, "status": f"错误: {e}"})
        
        print()
    
    # 总结
    print("=" * 70)
    print("总结")
    print("=" * 70)
    
    correct_count = sum(1 for r in results if r.get("status") == "✅")
    total = len([r for r in results if r.get("status") in ["✅", "❌"]])
    
    print(f"完全一致: {correct_count}/{total} ({correct_count/total*100:.0f}%)" if total > 0 else "无有效结果")


if __name__ == "__main__":
    main()
