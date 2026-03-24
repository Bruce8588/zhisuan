#!/usr/bin/env python3
"""
iFinD HTTP API 数据获取模块 v2.0
功能：使用 iFinD HTTP API 获取股票分钟K线数据

【优势】
- 无需安装本地SDK，纯HTTP请求
- 支持1/3/5/15/30/60分钟数据
- 数据格式统一

【refresh_token获取】
1. Windows超级命令客户端: 工具 → refresh_token查询/更新
2. 网页版本超级命令: 账号信息查看
"""
import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# iFinD HTTP API 配置
REFRESH_TOKEN = "eyJzaWduX3RpbWUiOiIyMDI2LTAzLTIzIDE2OjUwOjA5In0=.eyJ1aWQiOiI4NTU2ODc3MDciLCJ1c2VyIjp7InJlZnJlc2hUb2tlbkV4cGlyZWRUaW1lIjoiMjAyNi0wNC0yMiAxNDowMDo1OSIsInVzZXJJZCI6Ijg1NTY4NzcwNyJ9fQ==.13B61C0754D763C3991A1420EA1E901933C532616FA66A5D43A9D52DA1A9C62A"

# API 地址
TOKEN_URL = "https://quantapi.51ifind.com/api/v1/get_access_token"
HIGH_FREQ_URL = "https://quantapi.51ifind.com/api/v1/high_frequency"


class IFinDFetcher:
    """iFinD HTTP API 数据获取器"""

    def __init__(self, refresh_token=None, db_dir=None):
        self.refresh_token = refresh_token or REFRESH_TOKEN
        self.access_token = None
        self.token_expire_time = None
        self.db_dir = db_dir or os.path.join(BASE_DIR, "data")
        os.makedirs(self.db_dir, exist_ok=True)

    def _get_access_token(self):
        """获取 access_token（自动管理token有效期）"""
        # 检查是否需要刷新token（token有效期7天）
        if self.access_token and self.token_expire_time:
            if datetime.now() < self.token_expire_time:
                return self.access_token

        headers = {"Content-Type": "application/json", "refresh_token": self.refresh_token}
        try:
            response = requests.post(TOKEN_URL, headers=headers, timeout=30)
            result = response.json()
            if result.get("errorcode") == 0:
                self.access_token = result["data"]["access_token"]
                # token有效期7天
                self.token_expire_time = datetime.now() + timedelta(days=7)
                print(f"✓ iFinD access_token 获取成功")
                return self.access_token
            else:
                print(f"✗ 获取access_token失败: {result.get('errmsg', '未知错误')}")
                return None
        except Exception as e:
            print(f"✗ 请求access_token失败: {e}")
            return None

    def get_minute_data(self, code, days=7):
        """获取N天的1分钟K线数据
        
        参数:
            code: 股票代码（格式：000001.SZ 或 600000.SH）
            days: 获取最近N天的数据，默认7天
        
        返回:
            DataFrame: 包含 day, open, high, low, close, volume
        """
        if not self.access_token:
            self._get_access_token()
        
        if not self.access_token:
            return None

        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        data = {
            "codes": code,
            "indicators": "high,low,close",
            "starttime": start_time.strftime("%Y-%m-%d 09:15:00"),
            "endtime": end_time.strftime("%Y-%m-%d 15:15:00"),
            "functionpara": {
                "Interval": "1",  # 1分钟
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
                    print(f"  无数据返回")
                    return None
                
                # 构建DataFrame
                df = pd.DataFrame({
                    "day": time_list,
                    "open": table_data.get("open", []),
                    "high": table_data.get("high", []),
                    "low": table_data.get("low", []),
                    "close": table_data.get("close", []),
                    "volume": table_data.get("volume", [])
                })
                
                # 转换日期格式
                df["day"] = pd.to_datetime(df["day"])
                
                # 过滤盘后数据（只保留14:57之前）
                df = df[(df["day"].dt.hour < 15) | 
                        ((df["day"].dt.hour == 14) & (df["day"].dt.minute <= 57))]
                
                return df
            else:
                print(f"  API错误: {result.get('errmsg', '未知错误')}")
                # token过期，尝试刷新
                if "token" in str(result.get('errmsg', '')).lower():
                    self.access_token = None
                    return self.get_minute_data(code, days)
                return None
                
        except Exception as e:
            print(f"  请求异常: {e}")
            return None

    def update_stock(self, symbol, code, days=7):
        """更新单只股票数据并保存到CSV"""
        # 转换代码格式: sz000933 -> 000933.SZ
        code_ifind = self._convert_code(code)
        
        print(f"获取 {symbol} ({code_ifind})...")
        df = self.get_minute_data(code_ifind, days)
        
        if df is not None and len(df) > 0:
            # 保存到CSV
            code_clean = code.replace('sz', '').replace('sh', '')
            db_file = os.path.join(self.db_dir, f"{symbol}_{code_clean}_min1.csv")
            
            if os.path.exists(db_file):
                old_df = pd.read_csv(db_file)
                old_df["day"] = pd.to_datetime(old_df["day"])
                # 合并去重
                df = pd.concat([old_df, df], ignore_index=True)
                df = df.drop_duplicates(subset=["day"], keep="last")
                df = df.sort_values("day").reset_index(drop=True)
            
            df.to_csv(db_file, index=False, encoding="utf-8")
            print(f"  ✓ 已保存 {len(df)} 条数据到 {db_file}")
            return len(df)
        else:
            print(f"  ✗ 获取数据失败")
            return 0

    def update_stocks(self, stocks, days=7):
        """批量更新多只股票"""
        results = {}
        for symbol, info in stocks.items():
            code = info.get("code", "")
            count = self.update_stock(symbol, code, days)
            results[symbol] = count
        return results

    def _convert_code(self, code):
        """转换代码格式: sz000933 -> 000933.SZ"""
        code = code.lower().replace('sz', '').replace('sh', '')
        if len(code) == 6:
            if code.startswith('0') or code.startswith('3'):
                return f"{code}.SZ"
            elif code.startswith('6'):
                return f"{code}.SH"
        return code

    def scan_database(self):
        """扫描数据库，返回统计信息"""
        import glob
        
        files = glob.glob(os.path.join(self.db_dir, "*.csv"))
        
        stats = {
            "total_files": len(files),
            "total_size": 0,
            "latest_dates": {},
            "min_records": None,
            "max_records": None
        }
        
        records = []
        
        for f in files:
            name = os.path.basename(f)
            size = os.path.getsize(f)
            stats["total_size"] += size
            
            try:
                df = pd.read_csv(f, nrows=1)
                if "day" in df.columns:
                    df_full = pd.read_csv(f)
                    count = len(df_full)
                    last_day = df_full["day"].max()
                    records.append((name, count, last_day, size))
            except:
                records.append((name, 0, None, size))
        
        records.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "total_files": stats["total_files"],
            "total_size": stats["total_size"],
            "files": records
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="iFinD HTTP API 数据获取")
    parser.add_argument("--scan", action="store_true", help="扫描数据库")
    parser.add_argument("--days", type=int, default=7, help="获取最近N天数据")
    parser.add_argument("--stock", type=str, help="指定股票代码")
    parser.add_argument("--all", action="store_true", help="更新所有股票")
    args = parser.parse_args()
    
    fetcher = IFinDFetcher()
    
    if args.scan:
        print("=== 扫描数据库 ===\n")
        stats = fetcher.scan_database()
        print(f"文件总数: {stats['total_files']}")
        print(f"总大小: {stats['total_size'] / 1024 / 1024:.2f} MB")
        print(f"\n数据条数排名:")
        for name, count, last_day, size in stats["files"][:10]:
            print(f"  {count:4d}条  {last_day}  {name}")
        return
    
    # 获取测试token
    print("=== iFinD HTTP API 测试 ===\n")
    token = fetcher._get_access_token()
    if not token:
        print("获取token失败！")
        return
    
    if args.stock:
        # 更新单只股票
        from config.stocks import ALL_STOCKS
        stock_name = args.stock
        if stock_name in ALL_STOCKS:
            info = ALL_STOCKS[stock_name]
            fetcher.update_stock(stock_name, info["code"], args.days)
        else:
            print(f"股票 '{stock_name}' 不在配置中")
    
    elif args.all:
        # 更新所有股票
        from config.stocks import ALL_STOCKS
        print(f"更新所有股票 (最近{args.days}天)...\n")
        results = fetcher.update_stocks(ALL_STOCKS, args.days)
        print(f"\n=== 完成 ===")
        success = sum(1 for v in results.values() if v > 0)
        print(f"成功: {success}/{len(results)}")


if __name__ == "__main__":
    main()
