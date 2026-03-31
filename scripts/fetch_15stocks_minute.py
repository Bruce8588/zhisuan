#!/usr/bin/env python3
"""
fetch_15stocks_minute.py
获取15只股票从2012年至今的分钟数据
"""
import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

REFRESH_TOKEN = "eyJzaWduX3RpbWUiOiIyMDI2LTAzLTI4IDA5OjMzOjUzIn0=.eyJ1aWQiOiI4NTU2ODc3MDciLCJ1c2VyIjp7InJlZnJlc2hUb2tlbkV4cGlyZWRUaW1lIjoiMjAyNi0wNC0yMyAxOTo0MDoyMCIsInVzZXJJZCI6Ijg1NTY4NzcwNyJ9fQ==.29C5E8EFBA711E08F0693A654AAE070C2964F7EBEF8D7F15E7735F68EDE1DCEB"

TOKEN_URL = "https://quantapi.51ifind.com/api/v1/get_access_token"
HIGH_FREQ_URL = "https://quantapi.51ifind.com/api/v1/high_frequency"

STOCKS = {
    "000630.SZ": "铜陵有色",
    "002532.SZ": "天山铝业",
    "000933.SZ": "神火股份",
    "600089.SH": "特变电工",
    "002273.SZ": "水晶光电",
    "002475.SZ": "立讯精密",
    "002241.SZ": "歌尔股份",
    "000333.SZ": "美的集团",
    "000425.SZ": "徐工机械",
    "603556.SH": "海兴电力",
    "002050.SZ": "三花智控",
    "603588.SH": "高能环境",
    "601611.SH": "中国核建",
    "002156.SZ": "通富微电",
    "003015.SZ": "日久光电",
}

DATA_DIR = os.path.join(BASE_DIR, "data_minute_2010")
START_YEAR = 2012


def get_access_token():
    headers = {"Content-Type": "application/json", "refresh_token": REFRESH_TOKEN}
    resp = requests.post(TOKEN_URL, headers=headers, timeout=30)
    result = resp.json()
    if result.get("errorcode") == 0:
        return result["data"]["access_token"]
    return None


def get_minute_data(token, code, start_date, end_date):
    data = {
        "codes": code,
        "indicators": "high,low,close",
        "starttime": start_date.strftime("%Y-%m-%d 09:15:00"),
        "endtime": end_date.strftime("%Y-%m-%d 15:15:00"),
        "functionpara": {"Interval": "1", "Fill": "Original"}
    }
    headers = {"Content-Type": "application/json", "access_token": token}
    resp = requests.post(HIGH_FREQ_URL, json=data, headers=headers, timeout=120)
    result = resp.json()
    
    if result.get("errorcode") == 0 and result.get("tables"):
        table = result["tables"][0]
        time_list = table.get("time", [])
        table_data = table.get("table", {})
        if not time_list:
            return None
        n = len(time_list)
        row_data = {"day": time_list}
        for field in ("high", "low", "close"):
            arr = table_data.get(field, [])
            if not isinstance(arr, list):
                arr = []
            row_data[field] = arr[:n] if len(arr) != n else arr
        df = pd.DataFrame(row_data)
        df["day"] = pd.to_datetime(df["day"])
        df = df.dropna(subset=["high", "low", "close"])
        return df
    return None


def fetch_stock_data(code, name):
    """获取单只股票数据"""
    csv_file = os.path.join(DATA_DIR, f"{code}_{name}_分钟.csv")
    
    # 检查是否已有数据
    if os.path.exists(csv_file):
        try:
            existing = pd.read_csv(csv_file, nrows=1)
            print(f"  [已存在] {name}，跳过")
            return True
        except:
            pass
    
    print(f"\n  获取 {name} ({code})...")
    
    all_data = []
    current_year = datetime.now().year
    
    # 按月获取数据
    for year in range(START_YEAR, current_year + 1):
        for month in range(1, 13):
            start = datetime(year, month, 1)
            
            # 计算月末
            if month == 12:
                end = datetime(year, 12, 31)
            else:
                end = datetime(year, month + 1, 1) - timedelta(days=1)
            
            # 跳过未来日期
            if start > datetime.now():
                break
            if end > datetime.now():
                end = datetime.now()
            
            df = get_minute_data(token, code, start, end)
            if df is not None and len(df) > 0:
                all_data.append(df)
            
            time.sleep(0.3)
        
        time.sleep(1)
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["day"], keep="last")
        combined = combined.sort_values("day").reset_index(drop=True)
        combined.to_csv(csv_file, index=False, encoding="utf-8")
        print(f"  ✓ {name}: {len(combined)} 条数据已保存")
        return True
    else:
        print(f"  ✗ {name}: 无数据")
        return False


# 主程序
print("=" * 60)
print("获取15只股票分钟数据 (2012年至今)")
print("=" * 60)

token = get_access_token()
if not token:
    print("获取token失败!")
    sys.exit(1)

print(f"Token获取成功")
print(f"保存目录: {DATA_DIR}")

for i, (code, name) in enumerate(STOCKS.items()):
    print(f"\n[{i+1}/{len(STOCKS)}]", end="")
    success = fetch_stock_data(code, name)
    if not success:
        print(f"  警告: {name} 无数据")

print("\n" + "=" * 60)
print("完成!")
print("=" * 60)
