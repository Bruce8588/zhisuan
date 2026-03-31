#!/usr/bin/env python3
"""
用修复后的代码重新分析全市场分钟趋势数据
使用2024年底最终状态作为初始配置
"""
import pandas as pd
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.trend import init_state, update_trend
from config.rules import TREND_NAMES

TREND_DIR = os.path.join(BASE_DIR, "output_allmarket", "趋势判断")
INIT_FILE = os.path.join(BASE_DIR, "output_daily_2015_2024", "最终状态摘要.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_allmarket", "趋势判断_new")
os.makedirs(OUTPUT_DIR, exist_ok=True)

init_df = pd.read_csv(INIT_FILE)
init_states = {}
for _, row in init_df.iterrows():
    code = str(int(row['code'])).zfill(6)
    init_states[code] = {
        "trend": row["趋势"],
        "key_high": row["key_high"] if pd.notna(row.get("key_high")) else None,
        "key_low": row["key_low"] if pd.notna(row.get("key_low")) else None,
        "n_low": row["n_low"] if pd.notna(row.get("n_low")) else None,
        "n_high": row["n_high"] if pd.notna(row.get("n_high")) else None,
        "rally_high": row["rally_high"] if pd.notna(row.get("rally_high")) else None,
        "rally_low": row["rally_low"] if pd.notna(row.get("rally_low")) else None,
        "secondary_low": row["secondary_low"] if pd.notna(row.get("secondary_low")) else None,
        "secondary_high": row["secondary_high"] if pd.notna(row.get("secondary_high")) else None,
    }

def extract_code(fname):
    name = fname.replace('_趋势判断.csv', '')
    if name.startswith('sh') or name.startswith('sz'):
        return name[2:]
    return name

def process_one(args):
    fname, code, init_config = args
    try:
        df = pd.read_csv(os.path.join(TREND_DIR, fname))
        if len(df) < 10:
            return None
        state = init_state(init_config)
        records = []
        for _, row in df.iterrows():
            price = float(row["当前价格"])
            state = update_trend(state, price, price)
            records.append({
                "时间": row["时间"], "当前价格": price,
                "趋势代码": state["trend"],
                "趋势名称": TREND_NAMES.get(state["trend"], state["trend"]),
                "key_high": state["key_high"], "key_low": state["key_low"],
                "n_low": state["n_low"], "n_high": state["n_high"],
                "rally_high": state["rally_high"], "rally_low": state["rally_low"],
                "secondary_low": state["secondary_low"], "secondary_high": state["secondary_high"],
                "break_low": state.get("break_low"), "break_high": state.get("break_high"),
            })
        result = pd.DataFrame(records)
        result.to_csv(os.path.join(OUTPUT_DIR, fname), index=False, encoding="utf-8")
        return fname
    except Exception as e:
        return None

def main():
    files = [f for f in os.listdir(TREND_DIR) if f.endswith('_趋势判断.csv')]
    tasks = []
    for fname in files:
        code = extract_code(fname)
        if code in init_states:
            tasks.append((fname, code, init_states[code]))
    
    print(f"总任务: {len(tasks)} / {len(files)}")
    start_time = datetime.now()
    success = 0
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_one, t): t for t in tasks}
        for future in as_completed(futures):
            if future.result():
                success += 1
            if success % 500 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"成功: {success}/{len(tasks)} | 耗时: {elapsed:.0f}s")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n完成! 成功: {success}/{len(tasks)} | 耗时: {elapsed:.1f}s")
    print(f"输出: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
