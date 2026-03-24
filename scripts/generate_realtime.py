#!/usr/bin/env python3
"""
生成实时动态
功能：根据趋势判断库，生成实时动态文件（最新5分钟数据和趋势）

用法：
    python generate_realtime.py                 # 生成所有股票
    python generate_realtime.py --stock 神火股份  # 只生成单只股票
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS


class RealtimeGenerator:
    """实时动态生成器"""

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(BASE_DIR, "output")
        self.realtime_dir = os.path.join(self.output_dir, "实时动态")
        os.makedirs(self.realtime_dir, exist_ok=True)

    def _get_trend_file(self, symbol):
        """获取趋势判断文件路径"""
        trend_dir = os.path.join(self.output_dir, "趋势判断")
        return os.path.join(trend_dir, f"{symbol}_趋势判断.csv")

    def _get_realtime_file(self, symbol):
        """获取实时动态文件路径"""
        return os.path.join(self.realtime_dir, f"{symbol}_实时动态.csv")

    def generate_stock(self, symbol):
        """生成单只股票的实时动态"""
        trend_file = self._get_trend_file(symbol)

        if not os.path.exists(trend_file):
            print(f"  {symbol}: 趋势判断文件不存在")
            return None

        try:
            df = pd.read_csv(trend_file)
        except Exception as e:
            print(f"  {symbol}: 读取趋势判断失败 - {e}")
            return None

        if len(df) == 0:
            print(f"  {symbol}: 趋势判断数据为空")
            return None

        # 获取最后5条数据
        last_5 = df.tail(5)

        # 生成实时动态 - 保留最近5分钟数据 + 当前趋势
        if len(last_5) > 0:
            latest = last_5.iloc[-1]
            
            # 构建输出：最近5分钟价格 + 当前趋势
            records = []
            for i, row in last_5.iterrows():
                records.append({
                    "时间": row["时间"],
                    "价格": row["当前价格"],
                })

            # 保存带趋势的完整版本
            output_file = self._get_realtime_file(symbol)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {symbol} 实时动态\n")
                f.write(f"# 更新时间: {latest['时间']}\n")
                f.write(f"# 当前趋势: {latest['趋势名称']} ({latest['趋势代码']})\n")
                f.write(f"# 关键高: {latest.get('key_high', '')}\n")
                f.write(f"# 关键低: {latest.get('key_low', '')}\n")
                f.write(f"# n低: {latest.get('n_low', '')}\n")
                f.write(f"# n高: {latest.get('n_high', '')}\n")
                f.write(f"# 回升高: {latest.get('rally_high', '')}\n")
                f.write(f"# 回升低: {latest.get('rally_low', '')}\n")
                f.write(f"\n# 最近5分钟价格:\n")
                pd.DataFrame(records).to_csv(f, index=False, encoding='utf-8')

            print(f"  {symbol}: {latest['时间']} | {latest['当前价格']} | {latest['趋势名称']}")
            return pd.DataFrame(records)

        return None

    def run(self, stocks=None):
        """运行生成"""
        results = {}
        target_stocks = stocks if stocks else ALL_STOCKS

        for symbol in target_stocks.keys():
            try:
                result = self.generate_stock(symbol)
                results[symbol] = 1 if result is not None else 0
            except Exception as e:
                print(f"  {symbol}: 错误 - {e}")
                results[symbol] = 0

        return results


def main():
    parser = argparse.ArgumentParser(description='生成实时动态')
    parser.add_argument('--stock', type=str, help='只生成指定股票')
    args = parser.parse_args()

    generator = RealtimeGenerator()

    # 确定目标股票
    stocks = None
    if args.stock:
        if args.stock in ALL_STOCKS:
            stocks = {args.stock: ALL_STOCKS[args.stock]}
        else:
            print(f"股票 '{args.stock}' 不在配置中")
            return

    print(f"\n=== 生成实时动态 ===\n")

    results = generator.run(stocks=stocks)

    # 统计
    success = sum(1 for v in results.values() if v > 0)

    print(f"\n=== 完成 ===")
    print(f"成功: {success}/{len(results)}")
    print(f"输出目录: {generator.realtime_dir}")


if __name__ == "__main__":
    main()
