#!/usr/bin/env python3
"""
三重检验 - 15只检查股票
使用趋势检查表中记录的完整初始配置
"""
import os
import sys
import pandas as pd
from datetime import datetime

BASE_DIR = "/Users/isenfengming/.openclaw/workspace/工作台/智算"
sys.path.insert(0, BASE_DIR)

from core.trend import init_state, update_trend
from config.rules import TREND_NAMES

OUTPUT_DIR = os.path.join(BASE_DIR, "output_minute_2025", "趋势判断")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 15只检查股票的完整配置（从docs/趋势检查.md提取的2.24初始配置）
CHECK_STOCKS_CONFIG = {
    "630": {
        "trend": "up_rally", "key_high": 9.19, "key_low": None, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "铜陵有色"
    },
    "2532": {
        "trend": "down_rally", "key_high": None, "key_low": 16.68, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": 17.05, 
        "secondary_low": None, "secondary_high": None,
        "name": "天山铝业"
    },
    "933": {
        "trend": "down", "key_high": None, "key_low": 29.76, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "神火股份"
    },
    "600089": {
        "trend": "up_rally", "key_high": 32.99, "key_low": None, 
        "n_low": None, "n_high": None, 
        "rally_high": 30.21, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "特变电工"
    },
    "2273": {
        "trend": "up", "key_high": 28.63, "key_low": None, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "水晶光电"
    },
    "2475": {
        "trend": "down", "key_high": None, "key_low": 49.26, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "立讯精密"
    },
    "2241": {
        "trend": "down", "key_high": None, "key_low": 25.6, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "歌尔股份"
    },
    "333": {
        "trend": "up_rally", "key_high": 83.17, "key_low": None, 
        "n_low": 75, "n_high": None, 
        "rally_high": 81.16, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "美的集团"
    },
    "425": {
        "trend": "up", "key_high": 12.83, "key_low": None, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "徐工机械"
    },
    "603556": {
        "trend": "down_natural", "key_high": None, "key_low": 36.49, 
        "n_low": None, "n_high": 39.11, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "海兴电力"
    },
    "2050": {
        "trend": "up_rally", "key_high": 60.77, "key_low": None, 
        "n_low": 49.08, "n_high": None, 
        "rally_high": 55.02, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "三花智控"
    },
    "603588": {
        "trend": "up", "key_high": 11.3, "key_low": None, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "高能环境"
    },
    "601611": {
        "trend": "down_rally", "key_high": None, "key_low": 15.1, 
        "n_low": None, "n_high": 16.08, 
        "rally_high": None, "rally_low": 15.11, 
        "secondary_low": None, "secondary_high": None,
        "name": "中国核建"
    },
    "2156": {
        "trend": "down_natural", "key_high": None, "key_low": 46.16, 
        "n_low": None, "n_high": 49.8, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "通富微电"
    },
    "3015": {
        "trend": "up", "key_high": 17.85, "key_low": None, 
        "n_low": None, "n_high": None, 
        "rally_high": None, "rally_low": None, 
        "secondary_low": None, "secondary_high": None,
        "name": "日久光电"
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


def get_trend(df, date):
    """获取指定日期的趋势"""
    dt = pd.to_datetime(date)
    df_check = df[df["时间"].dt.date == dt.date()]
    if len(df_check) > 0:
        return df_check.iloc[-1]["趋势代码"]
    return None


def main():
    DATA_DIR = os.path.join(BASE_DIR, "data_daily")
    
    print("=" * 70)
    print("三重检验 - 15只检查股票（使用趋势检查表配置）")
    print("=" * 70)
    print(f"数据目录: {DATA_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    
    results = []
    
    for code, config in CHECK_STOCKS_CONFIG.items():
        name = config["name"]
        print(f"处理 {name}({code})...")
        
        # 查找数据文件
        data_file = None
        for f in os.listdir(DATA_DIR):
            if code in f and f.endswith('_day.csv'):
                data_file = os.path.join(DATA_DIR, f)
                break
        
        if data_file is None:
            print(f"  ❌ 数据文件不存在")
            results.append({"name": name, "code": code, "status": "无数据"})
            continue
        
        try:
            df_data = pd.read_csv(data_file)
            df_data["day"] = pd.to_datetime(df_data["day"])
            df_data = df_data.sort_values(by="day").reset_index(drop=True)
            
            # 只处理2025年及之后的数据
            df_data = df_data[df_data["day"] >= "2025-01-01"]
            
            if len(df_data) < 10:
                print(f"  ❌ 数据太少")
                results.append({"name": name, "code": code, "status": "数据不足"})
                continue
            
            result = analyze_stock(code, df_data, config)
            
            # 保存结果
            output_file = os.path.join(OUTPUT_DIR, f"{code}_趋势判断.csv")
            result.to_csv(output_file, index=False, encoding="utf-8")
            
            # 获取三个时间点的趋势
            trend_224 = get_trend(result, "2026-02-24")
            trend_36 = get_trend(result, "2026-03-06")
            trend_310 = get_trend(result, "2026-03-10")
            
            # 验证
            correct = CORRECT_TRENDS[name]
            t1_ok = trend_224 == correct["init"]
            t2_ok = trend_36 == correct["3.6"]
            t3_ok = trend_310 == correct["3.10"]
            
            status = "✅" if (t1_ok and t2_ok and t3_ok) else "❌"
            
            print(f"  2.24: {trend_224} {'✅' if t1_ok else '❌'} (正确={correct['init']})")
            print(f"  3.6:  {trend_36} {'✅' if t2_ok else '❌'} (正确={correct['3.6']})")
            print(f"  3.10: {trend_310} {'✅' if t3_ok else '❌'} (正确={correct['3.10']})")
            print(f"  结果: {status}")
            
            results.append({
                "name": name,
                "code": code,
                "trend_224": trend_224,
                "trend_36": trend_36,
                "trend_310": trend_310,
                "t1_ok": t1_ok,
                "t2_ok": t2_ok,
                "t3_ok": t3_ok,
                "status": status
            })
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            results.append({"name": name, "code": code, "status": f"错误: {e}"})
        
        print()
    
    # 统计结果
    print("=" * 70)
    print("总结")
    print("=" * 70)
    
    correct_count = sum(1 for r in results if r.get("status") == "✅")
    total = len([r for r in results if r.get("status") in ["✅", "❌"]])
    
    print(f"完全一致: {correct_count}/{total} ({correct_count/total*100:.0f}%)" if total > 0 else "无有效结果")
    
    # 打印不一致的详情
    print("\n不一致的股票:")
    for r in results:
        if r.get("status") == "❌":
            print(f"  {r['name']}: 2.24={r.get('trend_224')}, 3.6={r.get('trend_36')}, 3.10={r.get('trend_310')}")


if __name__ == "__main__":
    main()
