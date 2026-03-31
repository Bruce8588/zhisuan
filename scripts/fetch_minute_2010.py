#!/usr/bin/env python3
"""
fetch_minute_2010.py
使用iFinD获取15只股票2010年至今的分钟数据
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

# 用户提供的新token
REFRESH_TOKEN = "eyJzaWduX3RpbWUiOiIyMDI2LTAzLTI4IDA5OjMzOjUzIn0=.eyJ1aWQiOiI4NTU2ODc3MDciLCJ1c2VyIjp7InJlZnJlc2hUb2tlbkV4cGlyZWRUaW1lIjoiMjAyNi0wNC0yMyAxOTo0MDoyMCIsInVzZXJJZCI6Ijg1NTY4NzcwNyJ9fQ==.29C5E8EFBA711E08F0693A654AAE070C2964F7EBEF8D7F15E7735F68EDE1DCEB"

TOKEN_URL = "https://quantapi.51ifind.com/api/v1/get_access_token"
HIGH_FREQ_URL = "https://quantapi.51ifind.com/api/v1/high_frequency"

# 15只趋势检验股票
STOCKS = {
    "铜陵有色": "000630.SZ",
    "天山铝业": "002532.SZ",
    "神火股份": "000933.SZ",
    "特变电工": "600089.SH",
    "水晶光电": "002273.SZ",
    "立讯精密": "002475.SZ",
    "歌尔股份": "002241.SZ",
    "美的集团": "000333.SZ",
    "徐工机械": "000425.SZ",
    "海兴电力": "603556.SH",
    "三花智控": "002050.SZ",
    "高能环境": "603588.SH",
    "中国核建": "601611.SH",
    "通富微电": "002156.SZ",
    "日久光电": "003015.SZ",
}

DATA_DIR = os.path.join(BASE_DIR, "data_minute_2010")


class IFinDFetcher:
    def __init__(self, refresh_token):
        self.refresh_token = refresh_token
        self.access_token = None
        self.token_expire_time = None
        
    def _get_access_token(self):
        """获取 access_token"""
        if self.access_token and self.token_expire_time:
            if datetime.now() < self.token_expire_time:
                return self.access_token
        
        headers = {"Content-Type": "application/json", "refresh_token": self.refresh_token}
        try:
            response = requests.post(TOKEN_URL, headers=headers, timeout=30)
            result = response.json()
            if result.get("errorcode") == 0:
                self.access_token = result["data"]["access_token"]
                self.token_expire_time = datetime.now() + timedelta(days=7)
                print(f"✓ access_token 获取成功")
                return self.access_token
            else:
                print(f"✗ 获取access_token失败: {result.get('errmsg', '未知错误')}")
                return None
        except Exception as e:
            print(f"✗ 请求access_token失败: {e}")
            return None
    
    def get_minute_data_range(self, code, start_date, end_date):
        """获取指定日期范围的1分钟K线数据"""
        if not self.access_token:
            self._get_access_token()
        
        if not self.access_token:
            return None
        
        data = {
            "codes": code,
            "indicators": "high,low,close",
            "starttime": start_date.strftime("%Y-%m-%d 09:15:00"),
            "endtime": end_date.strftime("%Y-%m-%d 15:15:00"),
            "functionpara": {
                "Interval": "1",
                "Fill": "Original"
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(HIGH_FREQ_URL, json=data, headers=headers, timeout=120)
            result = response.json()
            
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
                
                # 过滤盘后数据
                df = df[(df["day"].dt.hour < 15) | 
                        ((df["day"].dt.hour == 14) & (df["day"].dt.minute <= 57))]
                
                return df
            else:
                errmsg = result.get('errmsg', '未知错误')
                if "token" in str(errmsg).lower():
                    self.access_token = None
                    return self.get_minute_data_range(code, start_date, end_date)
                print(f"  API错误: {errmsg}")
                return None
                
        except Exception as e:
            print(f"  请求异常: {e}")
            return None


def fetch_stock_data(fetcher, name, code, start_year=2010):
    """获取单只股票多年数据，按年分段获取"""
    print(f"\n{'='*50}")
    print(f"获取 {name} ({code}) 从{start_year}年至今...")
    print(f"{'='*50}")
    
    all_data = []
    current_year = datetime.now().year
    
    for year in range(start_year, current_year + 1):
        start_date = datetime(year, 1, 1)
        
        # 结束日期：如果是今年，取当前日期；否则取年底
        if year == current_year:
            end_date = datetime.now()
        else:
            end_date = datetime(year, 12, 31)
        
        print(f"\n  {year}年: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        # 一年内分批获取（每3个月一段）
        for month_start in range(1, 13, 3):
            month_end = min(month_start + 2, 12)
            if year == current_year and month_start > end_date.month:
                break
            
            seg_start = datetime(year, month_start, 1)
            if year == current_year and month_end > end_date.month:
                seg_end = end_date
            else:
                if month_end == 12:
                    seg_end = datetime(year, 12, 31)
                else:
                    seg_end = datetime(year, month_end + 1, 1) - timedelta(days=1)
                if seg_end > end_date:
                    seg_end = end_date
            
            df = fetcher.get_minute_data_range(code, seg_start, seg_end)
            
            if df is not None and len(df) > 0:
                all_data.append(df)
                print(f"    获得 {len(df)} 条数据")
            else:
                print(f"    无数据")
            
            time.sleep(0.5)  # 避免请求过快
        
        # 每年结束后休息一下
        time.sleep(1)
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["day"], keep="last")
        combined = combined.sort_values("day").reset_index(drop=True)
        print(f"\n  ✓ 总计获得 {len(combined)} 条数据")
        print(f"  时间范围: {combined['day'].min()} ~ {combined['day'].max()}")
        return combined
    else:
        print(f"\n  ✗ 未能获取任何数据")
        return None


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("=" * 60)
    print("iFinD 分钟数据获取 (2010年至今)")
    print("=" * 60)
    
    fetcher = IFinDFetcher(REFRESH_TOKEN)
    
    # 先获取token
    if not fetcher._get_access_token():
        print("获取access_token失败，程序退出")
        return
    
    print(f"\n数据将保存到: {DATA_DIR}")
    print(f"共 {len(STOCKS)} 只股票")
    
    # 逐一获取每只股票数据
    for name, code in STOCKS.items():
        csv_file = os.path.join(DATA_DIR, f"{code}_{name}_分钟数据.csv")
        
        # 检查是否已有数据
        existing_count = 0
        if os.path.exists(csv_file):
            try:
                existing_df = pd.read_csv(csv_file, nrows=1)
                existing_count = len(pd.read_csv(csv_file))
                print(f"\n[跳过] {name} 已有 {existing_count} 条数据 (文件已存在)")
                continue
            except:
                pass
        
        df = fetch_stock_data(fetcher, name, code, start_year=2010)
        
        if df is not None and len(df) > 0:
            df.to_csv(csv_file, index=False, encoding="utf-8")
            print(f"  ✓ 已保存到: {csv_file}")
    
    print("\n" + "=" * 60)
    print("全部完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
