#!/usr/bin/env python3
"""
全市场日线数据获取 - 2015-2024年
用于长期趋势分析
"""
import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 用户提供的token
REFRESH_TOKEN = "eyJzaWduX3RpbWUiOiIyMDI2LTAzLTI2IDE1OjI2OjE2In0=.eyJ1aWQiOiI4NTU2ODc3MDciLCJ1c2VyIjp7InJlZnJlc2hUb2tlbkV4cGlyZWRUaW1lIjoiMjAyNi0wNC0yMyAxOTo0MDoyMCIsInVzZXJJZCI6Ijg1NTY4NzcwNyJ9fQ==.3612ED239655EB698D584B1B2090893CB2AB48CEA4FBFBF3B834BB4E1674C682"

TOKEN_URL = "https://quantapi.51ifind.com/api/v1/get_access_token"
HISTORY_URL = "https://quantapi.51ifind.com/api/v1/cmd_history_quotation"

DATA_DIR = os.path.join(BASE_DIR, "data_daily_2015_2024")
os.makedirs(DATA_DIR, exist_ok=True)


class DailyDataFetcher:
    """iFinD 日线数据获取器"""

    def __init__(self):
        self.access_token = None
        self.token_expire_time = None

    def _get_access_token(self):
        """获取 access_token"""
        if self.access_token and self.token_expire_time:
            if datetime.now() < self.token_expire_time:
                return self.access_token

        headers = {"Content-Type": "application/json", "refresh_token": REFRESH_TOKEN}
        try:
            response = requests.post(TOKEN_URL, headers=headers, timeout=30)
            result = response.json()
            if result.get("errorcode") == 0:
                self.access_token = result["data"]["access_token"]
                self.token_expire_time = datetime.now() + timedelta(days=7)
                print(f"✓ Token获取成功")
                return self.access_token
            else:
                print(f"✗ Token失败: {result.get('errmsg')}")
                return None
        except Exception as e:
            print(f"✗ Token请求失败: {e}")
            return None

    def _convert_code(self, code):
        """转换代码格式"""
        code = code.lower().replace('sz', '').replace('sh', '')
        if len(code) == 6:
            if code.startswith('0') or code.startswith('3'):
                return f"{code}.SZ"
            elif code.startswith('6'):
                return f"{code}.SH"
        return code

    def get_daily_data(self, code, start_date='20150101', end_date='20241231'):
        """获取日线数据"""
        if not self.access_token:
            self._get_access_token()

        if not self.access_token:
            return None

        data = {
            "codes": code,
            "indicators": "open,high,low,close,volume",
            "startdate": start_date,
            "enddate": end_date,
        }

        headers = {
            "Content-Type": "application/json",
            "access_token": self.access_token
        }

        try:
            response = requests.post(HISTORY_URL, json=data, headers=headers, timeout=60)
            result = response.json()

            if result.get("errorcode") == 0 and result.get("tables"):
                table = result["tables"][0]
                time_list = table.get("time", [])
                table_data = table.get("table", {})

                if not time_list:
                    return None

                n = len(time_list)
                row_data = {"day": time_list}
                for field in ("open", "high", "low", "close", "volume"):
                    arr = table_data.get(field, [])
                    if not isinstance(arr, list):
                        arr = []
                    row_data[field] = arr[:n] if len(arr) != n else arr

                df = pd.DataFrame(row_data)
                df["day"] = pd.to_datetime(df["day"])
                df = df.dropna(subset=["close"])
                return df
            else:
                if "token" in str(result.get('errmsg', '')).lower():
                    self.access_token = None
                return None

        except Exception as e:
            return None

    def save_data(self, code, df):
        """保存日线数据"""
        if df is None or df.empty:
            return 0

        code_clean = code.lower().replace('sz', '').replace('sh', '')
        file_path = os.path.join(DATA_DIR, f"{code_clean}_day.csv")

        df = df.sort_values("day").reset_index(drop=True)
        df.to_csv(file_path, index=False, encoding='utf-8')
        return len(df)

    def fetch_all(self, db_source=None, interval=0.5):
        """获取全市场所有股票的日线数据"""
        if db_source is None:
            db_source = os.path.join(BASE_DIR, "data_allmarket")

        # 获取所有股票代码
        stock_codes = []
        for fname in os.listdir(db_source):
            if fname.endswith('_min1.csv'):
                code_part = fname.replace('_min1.csv', '')
                stock_codes.append((code_part, code_part))

        print(f"\n=== 获取全市场日线数据 2015-2024 ===")
        print(f"股票数量: {len(stock_codes)}")
        print(f"时间范围: 2015-01-01 ~ 2024-12-31")
        print(f"请求间隔: {interval}秒")
        print()

        if not self._get_access_token():
            print("Token获取失败！")
            return {}

        results = {}
        success_count = 0
        fail_count = 0

        for i, (symbol, code) in enumerate(stock_codes):
            code_ifind = self._convert_code(code)
            df = self.get_daily_data(code_ifind)

            if df is not None and len(df) > 0:
                count = self.save_data(code, df)
                success_count += 1
                results[symbol] = count
                if (i + 1) % 100 == 0:
                    print(f"[{i+1}/{len(stock_codes)}] {symbol}: {count}条 ✓")
            else:
                fail_count += 1
                results[symbol] = 0
                print(f"[{i+1}/{len(stock_codes)}] {symbol}: 失败")

            # 间隔0.5秒 + 随机波动
            time.sleep(interval + random.uniform(0, 0.2))

        print(f"\n=== 完成 ===")
        print(f"成功: {success_count}/{len(stock_codes)}")
        print(f"失败: {fail_count}/{len(stock_codes)}")
        print(f"输出目录: {DATA_DIR}")

        return results


def main():
    fetcher = DailyDataFetcher()
    fetcher.fetch_all(interval=0.5)


if __name__ == "__main__":
    main()
