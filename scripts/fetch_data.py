#!/usr/bin/env python3
"""
数据获取模块 - 使用 iFinD HTTP API
功能：获取股票分钟数据并合并到现有数据库

用法：
    python fetch_data.py --days 7           # 获取最近7个交易日
    python fetch_data.py --hours 1          # 获取最近1小时
    python fetch_data.py --start 2026-03-01 --end 2026-03-23  # 指定时间段
    python fetch_data.py --stock 神火股份   # 只获取单只股票
    python fetch_data.py --all             # 获取所有股票
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS
from core.fetcher_ifind import IFinDFetcher


class DataFetcher:
    """数据获取与合并"""

    def __init__(self, db_dir=None):
        self.fetcher = IFinDFetcher()
        self.db_dir = db_dir or os.path.join(BASE_DIR, "data")
        os.makedirs(self.db_dir, exist_ok=True)

    def _get_stock_file(self, symbol, code):
        """获取股票数据库文件路径"""
        code_clean = code.replace('sz', '').replace('sh', '')
        return os.path.join(self.db_dir, f"{symbol}_{code_clean}_min1.csv")

    def _load_existing_data(self, symbol, code):
        """加载现有数据"""
        file_path = self._get_stock_file(symbol, code)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                df['day'] = pd.to_datetime(df['day'])
                return df.sort_values('day')
            except:
                pass
        return pd.DataFrame()

    def _save_data(self, symbol, code, df):
        """保存数据到CSV"""
        file_path = self._get_stock_file(symbol, code)
        df = df.sort_values('day').reset_index(drop=True)
        df.to_csv(file_path, index=False, encoding='utf-8')

    def _merge_data(self, old_df, new_df):
        """合并新旧数据
        规则：
        - 新数据时间点覆盖旧数据
        - 如果新数据时间长度没有旧数据长，保留旧数据
        """
        if old_df.empty:
            return new_df
        if new_df.empty:
            return old_df

        # 合并
        combined = pd.concat([old_df, new_df], ignore_index=True)
        # 按时间去重，保留新数据
        combined = combined.drop_duplicates(subset=['day'], keep='last')
        # 排序
        combined = combined.sort_values('day').reset_index(drop=True)

        return combined

    def fetch_and_merge(self, symbol, code, days=None, hours=None, start_date=None, end_date=None):
        """获取并合并数据（智能增量获取，节省配额）"""
        # 转换代码格式
        code_ifind = self.fetcher._convert_code(code)
        
        # 加载现有数据，检查最新日期
        old_df = self._load_existing_data(symbol, code)
        old_count = len(old_df)
        
        if old_df is not None and not old_df.empty:
            latest_date = old_df['day'].max()
            latest_str = latest_date.strftime('%Y-%m-%d %H:%M')
        else:
            latest_date = None
            latest_str = "无历史数据"

        # 确定获取范围（智能判断）
        if hours:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            fetch_days = max(1, hours // 24 + 1)
        elif start_date and end_date:
            end_time = datetime.strptime(end_date, '%Y-%m-%d')
            start_time = datetime.strptime(start_date, '%Y-%m-%d')
            fetch_days = (end_time - start_time).days + 1
        elif days:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            fetch_days = days
        else:
            fetch_days = 7

        # 智能优化：如果有历史数据，只获取增量部分
        if latest_date is not None and hours is None and start_date is None:
            # 计算需要获取的天数（从最新日期到今天）
            days_since = (datetime.now() - latest_date).days
            if days_since <= 0:
                # 今天已有数据，无需获取
                print(f"  {symbol}: 最新数据 {latest_str}，今日已存在，跳过")
                return 0
            elif days_since <= 3:
                # 3天内数据，只获取需要的部分
                fetch_days = days_since + 1
                print(f"  {symbol}: 本地最新 {latest_str}，获取最近 {fetch_days} 天")
            else:
                # 数据较旧，提示用户
                print(f"  {symbol}: 本地最新 {latest_str}，数据较旧，建议用 --days 指定范围")

        # 获取新数据
        new_df = self.fetcher.get_minute_data(code_ifind, days=fetch_days)
        
        if new_df is None or new_df.empty:
            print(f"  {symbol}: 获取数据失败")
            return 0

        # 过滤掉已有的旧数据（避免重复获取）
        if latest_date is not None and not new_df.empty:
            new_df = new_df[new_df['day'] > latest_date]
            if new_df.empty:
                print(f"  {symbol}: 无新增数据")
                return 0
            print(f"  {symbol}: 过滤后新增 {len(new_df)} 条")

        # 合并数据
        merged_df = self._merge_data(old_df, new_df)

        # 保存
        self._save_data(symbol, code, merged_df)

        new_count = len(merged_df)
        added = new_count - old_count
        
        print(f"  {symbol}: {old_count} → {new_count} 条 ({'+' if added >= 0 else ''}{added})")
        return added

    def run(self, stocks=None, days=None, hours=None, start_date=None, end_date=None):
        """运行数据获取"""
        if not self.fetcher._get_access_token():
            print("获取access_token失败！")
            return {}

        results = {}
        target_stocks = stocks if stocks else ALL_STOCKS

        for symbol, info in target_stocks.items():
            try:
                count = self.fetch_and_merge(
                    symbol, 
                    info['code'],
                    days=days,
                    hours=hours,
                    start_date=start_date,
                    end_date=end_date
                )
                results[symbol] = count
            except Exception as e:
                print(f"  {symbol}: 错误 - {e}")
                results[symbol] = 0

        return results


def main():
    parser = argparse.ArgumentParser(description='数据获取 - iFinD HTTP API')
    parser.add_argument('--days', type=int, help='获取最近N个交易日的数据')
    parser.add_argument('--hours', type=int, help='获取最近N小时的数据')
    parser.add_argument('--start', type=str, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--stock', type=str, help='只获取指定股票')
    parser.add_argument('--all', action='store_true', help='获取所有股票')
    args = parser.parse_args()

    # 验证参数
    if not any([args.days, args.hours, args.start, args.all]):
        parser.print_help()
        print("\n请指定获取方式：--days, --hours, --start/--end, 或 --all")
        return

    fetcher = DataFetcher()

    # 确定目标股票
    stocks = None
    if args.stock:
        if args.stock in ALL_STOCKS:
            stocks = {args.stock: ALL_STOCKS[args.stock]}
        else:
            print(f"股票 '{args.stock}' 不在配置中")
            return

    # 确定获取方式
    mode = f"最近{args.hours}小时" if args.hours else f"最近{args.days}天" if args.days else f"{args.start} 至 {args.end}"
    print(f"\n=== 数据获取 ({mode}) ===\n")

    results = fetcher.run(
        stocks=stocks,
        days=args.days,
        hours=args.hours,
        start_date=args.start,
        end_date=args.end
    )

    # 统计
    success = sum(1 for v in results.values() if v > 0)
    total_added = sum(v for v in results.values() if v > 0)
    
    print(f"\n=== 完成 ===")
    print(f"成功: {success}/{len(results)}")
    print(f"新增数据: {total_added} 条")


if __name__ == "__main__":
    main()
