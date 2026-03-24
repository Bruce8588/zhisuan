#!/usr/bin/env python3
"""
趋势判断模块
功能：对数据库每条数据进行趋势判断，生成趋势判断库

用法：
    python analyze_trend.py                    # 分析所有股票
    python analyze_trend.py --stock 神火股份   # 只分析单只股票
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS
from config.rules import TREND_NAMES
from core.trend import init_state, update_trend


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self, db_dir=None, output_dir=None):
        self.db_dir = db_dir or os.path.join(BASE_DIR, "data")
        self.output_dir = output_dir or os.path.join(BASE_DIR, "output")
        self.trend_dir = os.path.join(self.output_dir, "趋势判断")
        os.makedirs(self.trend_dir, exist_ok=True)

    def _get_stock_file(self, symbol, code):
        """获取股票数据库文件路径"""
        return os.path.join(self.db_dir, f"{symbol}_{code}_min1.csv")

    def _get_trend_file(self, symbol):
        """获取趋势判断文件路径"""
        return os.path.join(self.trend_dir, f"{symbol}_趋势判断.csv")

    def analyze_stock(self, symbol, info):
        """分析单只股票"""
        code = info["code"]
        db_file = self._get_stock_file(symbol, code)

        if not os.path.exists(db_file):
            print(f"  {symbol}: 数据库文件不存在")
            return None

        # 读取数据
        try:
            df = pd.read_csv(db_file)
        except Exception as e:
            print(f"  {symbol}: 读取数据库失败 - {e}")
            return None

        if len(df) == 0:
            print(f"  {symbol}: 数据库为空")
            return None

        # 处理列名
        column_map = {
            '时间': 'day', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume'
        }
        for old_col, new_col in column_map.items():
            if old_col in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)

        df["day"] = pd.to_datetime(df["day"])
        df = df.sort_values("day").reset_index(drop=True)

        # 初始化状态
        state = init_state(info)

        # 分析每条数据
        records = []
        for _, row in df.iterrows():
            high = float(row["high"]) if pd.notna(row["high"]) else None
            low = float(row["low"]) if pd.notna(row["low"]) else None

            state = update_trend(state, high, low)

            records.append({
                "时间": row["day"],
                "当前价格": row["close"],
                "趋势代码": state["trend"],
                "趋势名称": TREND_NAMES.get(state["trend"], state["trend"]),
                "key_high": state["key_high"],
                "key_low": state["key_low"],
                "n_low": state["n_low"],
                "n_high": state["n_high"],
                "rally_high": state["rally_high"],
                "rally_low": state["rally_low"],
                "secondary_low": state["secondary_low"],
                "secondary_high": state["secondary_high"],
                "break_low": state["break_low"],
                "break_high": state["break_high"],
            })

        # 保存趋势判断库
        result_df = pd.DataFrame(records)
        output_file = self._get_trend_file(symbol)
        result_df.to_csv(output_file, index=False, encoding="utf-8")

        print(f"  {symbol}: 已分析 {len(records)} 条数据")
        return result_df

    def run(self, stocks=None):
        """运行趋势分析"""
        results = {}
        target_stocks = stocks if stocks else ALL_STOCKS

        for symbol, info in target_stocks.items():
            try:
                result = self.analyze_stock(symbol, info)
                results[symbol] = len(result) if result is not None else 0
            except Exception as e:
                print(f"  {symbol}: 错误 - {e}")
                results[symbol] = 0

        return results


def main():
    parser = argparse.ArgumentParser(description='趋势判断 - 生成趋势判断库')
    parser.add_argument('--stock', type=str, help='只分析指定股票')
    args = parser.parse_args()

    analyzer = TrendAnalyzer()

    # 确定目标股票
    stocks = None
    if args.stock:
        if args.stock in ALL_STOCKS:
            stocks = {args.stock: ALL_STOCKS[args.stock]}
        else:
            print(f"股票 '{args.stock}' 不在配置中")
            return

    print(f"\n=== 趋势判断 ===\n")

    results = analyzer.run(stocks=stocks)

    # 统计
    success = sum(1 for v in results.values() if v > 0)
    total = sum(results.values())

    print(f"\n=== 完成 ===")
    print(f"成功: {success}/{len(results)}")
    print(f"总数据: {total} 条")
    print(f"输出目录: {analyzer.trend_dir}")


if __name__ == "__main__":
    main()
