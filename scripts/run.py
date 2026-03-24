#!/usr/bin/env python3
"""
智算系统 - 主运行脚本
功能：模块化运行数据获取、趋势判断、生成输出

用法：
    # 获取数据
    python run.py --step fetch --days 7              # 获取最近7天
    python run.py --step fetch --hours 1             # 获取最近1小时
    python run.py --step fetch --start 2026-03-01 --end 2026-03-23  # 指定时间段
    
    # 生成输出
    python run.py --step trend                       # 生成趋势判断库
    python run.py --step realtime                    # 生成实时动态
    python run.py --step records                     # 生成行情记录
    
    # 一键运行
    python run.py --step all                        # 运行所有步骤
    python run.py --step pipeline                    # 完整流程（获取+趋势+输出）
    
    # 单只股票
    python run.py --step all --stock 神火股份        # 单只股票完整流程
    
    # 列出股票
    python run.py --list                            # 列出所有股票
"""
import os
import sys
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS


def list_stocks():
    """列出所有股票"""
    print("\n=== 股票列表 ===\n")
    print(f"{'名称':<10} {'代码':<12} {'趋势'}")
    print("-" * 40)
    for name, info in sorted(ALL_STOCKS.items()):
        trend = info.get('trend', 'unknown')
        print(f"{name:<10} {info['code']:<12} {trend}")


def run_fetch(days=None, hours=None, start_date=None, end_date=None, stock=None):
    """运行数据获取"""
    from scripts.fetch_data import DataFetcher

    fetcher = DataFetcher()

    stocks = None
    if stock:
        if stock in ALL_STOCKS:
            stocks = {stock: ALL_STOCKS[stock]}
        else:
            print(f"股票 '{stock}' 不在配置中")
            return False

    mode = f"最近{hours}小时" if hours else f"最近{days}天" if days else f"{start_date} 至 {end_date}"
    print(f"\n{'='*50}")
    print(f"步骤1: 数据获取 ({mode})")
    print(f"{'='*50}\n")

    results = fetcher.run(
        stocks=stocks,
        days=days,
        hours=hours,
        start_date=start_date,
        end_date=end_date
    )

    success = sum(1 for v in results.values() if v > 0)
    print(f"\n数据获取完成: {success}/{len(results)}")


def run_trend(stock=None):
    """运行趋势判断"""
    from scripts.analyze_trend import TrendAnalyzer

    analyzer = TrendAnalyzer()

    stocks = None
    if stock:
        if stock in ALL_STOCKS:
            stocks = {stock: ALL_STOCKS[stock]}
        else:
            print(f"股票 '{stock}' 不在配置中")
            return False

    print(f"\n{'='*50}")
    print(f"步骤2: 趋势判断")
    print(f"{'='*50}\n")

    results = analyzer.run(stocks=stocks)

    success = sum(1 for v in results.values() if v > 0)
    total = sum(v for v in results.values() if v > 0)
    print(f"\n趋势判断完成: {success}/{len(results)} (共{total}条)")


def run_realtime(stock=None):
    """生成实时动态"""
    from scripts.generate_realtime import RealtimeGenerator

    generator = RealtimeGenerator()

    stocks = None
    if stock:
        if stock in ALL_STOCKS:
            stocks = {stock: ALL_STOCKS[stock]}
        else:
            print(f"股票 '{stock}' 不在配置中")
            return False

    print(f"\n{'='*50}")
    print(f"步骤3: 生成实时动态")
    print(f"{'='*50}\n")

    results = generator.run(stocks=stocks)

    success = sum(1 for v in results.values() if v > 0)
    print(f"\n实时动态完成: {success}/{len(results)}")


def run_records(stock=None):
    """生成行情记录"""
    from scripts.generate_records import RecordsGenerator

    generator = RecordsGenerator()

    stocks = None
    if stock:
        if stock in ALL_STOCKS:
            stocks = {stock: ALL_STOCKS[stock]}
        else:
            print(f"股票 '{stock}' 不在配置中")
            return False

    print(f"\n{'='*50}")
    print(f"步骤4: 生成行情记录")
    print(f"{'='*50}\n")

    results = generator.run(stocks=stocks)

    success = sum(1 for v in results.values() if v > 0)
    print(f"\n行情记录完成: {success}/{len(results)}")


def main():
    parser = argparse.ArgumentParser(
        description='智算系统 - 模块化运行',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --list                              # 列出所有股票
  python run.py --step fetch --days 7                # 获取最近7天数据
  python run.py --step fetch --hours 1              # 获取最近1小时数据
  python run.py --step trend                        # 生成趋势判断库
  python run.py --step realtime                      # 生成实时动态
  python run.py --step records                      # 生成行情记录
  python run.py --step pipeline                     # 完整流程
  python run.py --step all --stock 神火股份         # 单只股票完整流程
        """
    )

    parser.add_argument('--list', action='store_true', help='列出所有股票')
    parser.add_argument('--step', type=str, choices=['fetch', 'trend', 'realtime', 'records', 'all', 'pipeline'],
                       help='运行步骤: fetch-获取数据, trend-趋势判断, realtime-实时动态, records-行情记录, pipeline-完整流程, all-全部')
    parser.add_argument('--days', type=int, default=7, help='获取最近N天数据 (默认7)')
    parser.add_argument('--hours', type=int, help='获取最近N小时数据')
    parser.add_argument('--start', type=str, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--stock', type=str, help='指定股票名称')

    args = parser.parse_args()

    # 列出股票
    if args.list:
        list_stocks()
        return

    if not args.step:
        parser.print_help()
        print("\n请指定 --step")
        print("\n快速开始:")
        print("  python run.py --step pipeline           # 完整流程")
        print("  python run.py --step fetch --days 7    # 获取7天数据")
        print("  python run.py --step trend             # 趋势判断")
        return

    start_time = datetime.now()
    print(f"\n{'='*50}")
    print(f"智算系统启动 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    # 执行步骤
    if args.step == 'fetch':
        run_fetch(days=args.days, hours=args.hours, 
                  start_date=args.start, end_date=args.end,
                  stock=args.stock)

    elif args.step == 'trend':
        run_trend(stock=args.stock)

    elif args.step == 'realtime':
        run_realtime(stock=args.stock)

    elif args.step == 'records':
        run_records(stock=args.stock)

    elif args.step == 'pipeline':
        # 完整流程：数据获取 → 趋势判断 → 实时动态 → 行情记录
        run_fetch(days=args.days, hours=args.hours,
                  start_date=args.start, end_date=args.end,
                  stock=args.stock)
        run_trend(stock=args.stock)
        run_realtime(stock=args.stock)
        run_records(stock=args.stock)

    elif args.step == 'all':
        # 全部：数据获取(7天) → 趋势判断 → 实时动态 → 行情记录
        run_fetch(days=7, stock=args.stock)
        run_trend(stock=args.stock)
        run_realtime(stock=args.stock)
        run_records(stock=args.stock)

    # 完成
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'='*50}")
    print(f"智算系统完成 - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"耗时: {duration:.1f} 秒")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
