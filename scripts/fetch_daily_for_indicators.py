#!/usr/bin/env python3
"""
日线数据获取模块 - 用于 MACD 和 TD 序列分析
功能：获取股票日线数据（开盘、收盘、最高、最低、成交量）

使用场景：
    - MACD（指数平滑移动平均线）分析
    - TD（Tom DeMark）九转序列分析

数据来源：iFinD HTTP API (cmd_history_quotation)
    URL: https://quantapi.51ifind.com/api/v1/cmd_history_quotation

用法：
    python fetch_daily_for_indicators.py --days 250         # 获取最近250个交易日（约1年）
    python fetch_daily_for_indicators.py --all              # 获取全市场所有股票
    python fetch_daily_for_indicators.py --stock 铜陵有色   # 只获取单只股票
    python fetch_daily_for_indicators.py --start 2025-01-01 --end 2026-03-24  # 指定时间段
"""
import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# iFinD HTTP API 配置（用户提供的token）
REFRESH_TOKEN = "eyJzaWduX3RpbWUiOiIyMDI2LTAzLTI2IDEwOjM4OjQwIn0=.eyJ1aWQiOiI4NTU2ODc3MDciLCJ1c2VyIjp7InJlZnJlc2hUb2tlbkV4cGlyZWRUaW1lIjoiMjAyNi0wNC0yMyAxOTo0MDoyMCIsInVzZXJJZCI6Ijg1NTY4NzcwNyJ9fQ==.100363007B5C0DDE3B65B8F965EDECD85E9F2BC98F15009D8BD5D93359F4107C"

# API 地址
TOKEN_URL = "https://quantapi.51ifind.com/api/v1/get_access_token"
HISTORY_URL = "https://quantapi.51ifind.com/api/v1/cmd_history_quotation"


class DailyDataFetcher:
    """iFinD 日线数据获取器（用于MACD和TD分析）"""

    def __init__(self, refresh_token=None, db_dir=None):
        self.refresh_token = refresh_token or REFRESH_TOKEN
        self.access_token = None
        self.token_expire_time = None
        # 日线数据存放目录
        self.db_dir = db_dir or os.path.join(BASE_DIR, "data_daily")
        os.makedirs(self.db_dir, exist_ok=True)

    def _get_access_token(self):
        """获取 access_token（自动管理token有效期）"""
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
                print(f"✓ iFinD access_token 获取成功")
                return self.access_token
            else:
                print(f"✗ 获取access_token失败: {result.get('errmsg', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"✗ 请求access_token失败: {e}")
            return None

    def _convert_code(self, code):
        """转换代码格式: sz000630 -> 000630.SZ, sh600000 -> 600000.SH"""
        code = code.lower().replace('sz', '').replace('sh', '')
        if len(code) == 6:
            if code.startswith('0') or code.startswith('3'):
                return f"{code}.SZ"
            elif code.startswith('6'):
                return f"{code}.SH"
        return code

    def get_daily_data(self, code, start_date=None, end_date=None, days=250):
        """获取日线数据
        
        使用 API: cmd_history_quotation
        
        参数:
            code: 股票代码（格式：000630.SZ 或 600000.SH）
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            days: 如果没有指定日期范围，获取最近N个交易日
        
        返回:
            DataFrame: 包含 day, open, high, low, close, volume
        """
        if not self.access_token:
            self._get_access_token()
        
        if not self.access_token:
            return None

        # 确定时间范围
        if start_date and end_date:
            start_str = start_date.replace('-', '')
            end_str = end_date.replace('-', '')
        else:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            start_str = start_time.strftime('%Y%m%d')
            end_str = end_time.strftime('%Y%m%d')

        data = {
            "codes": code,
            "indicators": "open,high,low,close,volume",
            "startdate": start_str,
            "enddate": end_str,
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
                
                # 构建DataFrame
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
                print(f"  API错误: {result.get('errmsg', 'Unknown error')}")
                if "token" in str(result.get('errmsg', '')).lower():
                    self.access_token = None
                return None
                
        except Exception as e:
            print(f"  请求异常: {e}")
            return None

    def save_data(self, symbol, code, df):
        """保存日线数据到CSV"""
        if df is None or df.empty:
            return 0
        
        # 使用代码作为文件名（与全市场数据一致）
        code_clean = code.lower().replace('sz', '').replace('sh', '')
        file_path = os.path.join(self.db_dir, f"{code_clean}_day.csv")
        
        df = df.sort_values("day").reset_index(drop=True)
        df.to_csv(file_path, index=False, encoding='utf-8')
        return len(df)

    def fetch_and_save(self, symbol, code, start_date=None, end_date=None, days=250):
        """获取并保存单只股票的日线数据"""
        code_ifind = self._convert_code(code)
        df = self.get_daily_data(code_ifind, start_date, end_date, days)
        
        if df is not None and len(df) > 0:
            count = self.save_data(symbol, code, df)
            return count
        return 0

    def fetch_allmarket(self, db_source=None, start_date=None, end_date=None, days=250, max_workers=5):
        """从全市场数据库获取所有股票代码，批量获取日线数据
        
        参数:
            db_source: 全市场数据源目录
            start_date: 开始日期
            end_date: 结束日期
            days: 最近N个交易日
            max_workers: 并行线程数
        """
        if db_source is None:
            db_source = os.path.join(BASE_DIR, "data_allmarket")
        
        # 从全市场数据库获取所有股票代码
        stock_codes = []
        for fname in os.listdir(db_source):
            if fname.endswith('_min1.csv'):
                # 文件名格式: sz000630_min1.csv 或 sh600000_min1.csv
                code_part = fname.replace('_min1.csv', '')
                symbol = code_part  # 暂时用代码作为标识
                stock_codes.append((symbol, code_part))
        
        print(f"\n=== 获取全市场日线数据 ===")
        print(f"股票数量: {len(stock_codes)}")
        print(f"时间范围: {start_date or f'最近{days}天'} ~ {end_date or '今天'}")
        print(f"并行线程: {max_workers}")
        print()
        
        if not self._get_access_token():
            print("获取access_token失败！")
            return {}
        
        results = {}
        success_count = 0
        
        def fetch_one(item):
            symbol, code = item
            try:
                count = self.fetch_and_save(symbol, code, start_date, end_date, days)
                return (symbol, code, count)
            except Exception as e:
                return (symbol, code, 0)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_one, item): item for item in stock_codes}
            for i, future in enumerate(as_completed(futures)):
                symbol, code, count = future.result()
                if count > 0:
                    success_count += 1
                    print(f"[{i+1}/{len(stock_codes)}] {symbol}: {count} 条")
                else:
                    print(f"[{i+1}/{len(stock_codes)}] {symbol}: 失败")
                results[symbol] = count
        
        print(f"\n=== 完成 ===")
        print(f"成功: {success_count}/{len(stock_codes)}")
        return results


def main():
    parser = argparse.ArgumentParser(
        description='日线数据获取 - 用于MACD和TD序列分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    python fetch_daily_for_indicators.py --days 250          # 最近1年
    python fetch_daily_for_indicators.py --all               # 全市场
    python fetch_daily_for_indicators.py --stock 000630     # 单只股票
        '''
    )
    parser.add_argument('--days', type=int, default=250, help='获取最近N个交易日（默认250）')
    parser.add_argument('--start', type=str, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--stock', type=str, help='只获取指定股票（代码或名称）')
    parser.add_argument('--all', action='store_true', help='获取全市场所有股票')
    parser.add_argument('--workers', type=int, default=5, help='并行线程数（默认5）')
    
    args = parser.parse_args()

    fetcher = DailyDataFetcher()

    if args.stock:
        # 单只股票
        # 尝试从配置中找到股票信息
        from config.stocks import ALL_STOCKS
        stock_name = None
        stock_code = None
        
        # 先看是不是名称
        for name, info in ALL_STOCKS.items():
            if name == args.stock or info.get('code', '').lower() == args.stock.lower():
                stock_name = name
                stock_code = info.get('code', '')
                break
        
        if not stock_code:
            # 可能是纯代码
            stock_code = args.stock
            stock_name = args.stock
        
        print(f"\n=== 获取 {stock_name} 日线数据 ===")
        count = fetcher.fetch_and_save(
            stock_name, 
            stock_code, 
            args.start, 
            args.end, 
            args.days
        )
        print(f"获取到 {count} 条数据")
    
    elif args.all:
        # 全市场
        fetcher.fetch_allmarket(
            start_date=args.start,
            end_date=args.end,
            days=args.days,
            max_workers=args.workers
        )
    
    else:
        parser.print_help()
        print("\n请指定 --stock 或 --all")


if __name__ == "__main__":
    main()
