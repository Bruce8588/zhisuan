#!/usr/bin/env python3
"""
生成行情记录
功能：根据趋势判断库，按手工记录格式生成行情记录

格式：
- 每行 = 一个趋势变化的关键价格点
- 包含当前价格与关键价格的比值
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS

# 趋势代码到列名的映射
TREND_COLUMNS = {
    "up": "上升趋势",
    "up_natural": "自然回撤趋势",
    "up_rally": "回升趋势",
    "up_secondary": "次级回撤运动",
    "up_break": "向上突破",
    "down": "下跌趋势",
    "down_natural": "自然回升趋势",
    "down_rally": "回撤趋势",
    "down_secondary": "次级回升运动",
    "down_break": "向下突破",
}


class RecordsGenerator:
    """行情记录生成器"""

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(BASE_DIR, "output")
        self.records_dir = os.path.join(self.output_dir, "行情记录")
        os.makedirs(self.records_dir, exist_ok=True)

    def _get_trend_file(self, symbol):
        """获取趋势判断文件路径"""
        trend_dir = os.path.join(self.output_dir, "趋势判断")
        return os.path.join(trend_dir, f"{symbol}_趋势判断.csv")

    def _get_records_file(self, symbol):
        """获取行情记录文件路径"""
        return os.path.join(self.records_dir, f"{symbol}_行情记录.csv")

    def _calculate_ratio(self, current_price, key_price):
        """计算比例"""
        if current_price and key_price and key_price > 0:
            return round(current_price / key_price, 6)
        return ""

    def _get_key_price(self, trend_code, row):
        """根据趋势代码获取关键价格"""
        key_prices = {
            "up": row.get("key_high"),
            "up_natural": row.get("n_low"),
            "up_rally": row.get("rally_high"),
            "up_secondary": row.get("secondary_low"),
            "up_break": row.get("break_low"),
            "down": row.get("key_low"),
            "down_natural": row.get("n_high"),
            "down_rally": row.get("rally_low"),
            "down_secondary": row.get("secondary_high"),
            "down_break": row.get("break_high"),
        }
        return key_prices.get(trend_code)

    def generate_stock_v2(self, symbol):
        """生成单只股票的行情记录 V2 - 按手工格式"""
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

        df["时间"] = pd.to_datetime(df["时间"])
        df = df.sort_values("时间", ascending=False)  # 降序获取最近数据
        df["日期"] = df["时间"].dt.date
        dates = sorted(df["日期"].unique())[:10]  # 取最近的10天，然后升序排列
        dates = sorted(dates)  # 升序，从早到晚

        # 按手工格式生成
        # 列: 时间, 上升趋势, 自然回撤趋势, 回升趋势, 次级回撤运动, 下跌趋势, 自然回升趋势, 回撤趋势, 次级回升运动, 比值, 备注
        columns = ["时间", "上升趋势", "自然回撤趋势", "回升趋势", "次级回撤运动",
                   "下跌趋势", "自然回升趋势", "回撤趋势", "次级回升运动", "比值", "备注"]
        result_df = pd.DataFrame(columns=columns)

        prev_trend = None
        count = 0

        for date in dates:
            day_df = df[df["日期"] == date]
            if len(day_df) == 0:
                continue

            # 获取当天最后一条数据
            last_row = day_df.iloc[0]
            current_trend = last_row["趋势代码"]
            current_price = last_row["当前价格"]

            # 趋势变化时记录
            if current_trend != prev_trend:
                row_data = {
                    "时间": date,
                    "上升趋势": "", "自然回撤趋势": "", "回升趋势": "", "次级回撤运动": "",
                    "下跌趋势": "", "自然回升趋势": "", "回撤趋势": "", "次级回升运动": "",
                    "比值": "", "备注": ""
                }

                # 填充对应趋势的价格
                key_price = self._get_key_price(current_trend, last_row)
                col_name = TREND_COLUMNS.get(current_trend, current_trend)
                if col_name in row_data:
                    row_data[col_name] = key_price if key_price else current_price

                # 计算比值
                if key_price and key_price > 0:
                    row_data["比值"] = round(current_price / key_price, 6)
                
                # 备注栏显示趋势名称
                row_data["备注"] = TREND_COLUMNS.get(current_trend, current_trend)

                result_df = pd.concat([result_df, pd.DataFrame([row_data])], ignore_index=True)
                prev_trend = current_trend
                count += 1

        # 保存为xlsx格式并设置列宽
        if len(result_df) > 0:
            output_file = self._get_records_file(symbol).replace(".csv", ".xlsx")
            try:
                from openpyxl import Workbook
                from openpyxl.utils.dataframe import dataframe_to_rows
                
                wb = Workbook()
                ws = wb.active
                
                # 写入数据
                for r in dataframe_to_rows(result_df, index=False, header=True):
                    ws.append(r)
                
                # 设置列宽自适应（根据内容）
                for col in ws.columns:
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        try:
                            if cell.value:
                                # 中文字符宽度加倍
                                cell_len = len(str(cell.value))
                                chinese_count = sum(1 for c in str(cell.value) if '\u4e00' <= c <= '\u9fff')
                                adjusted_len = cell_len + chinese_count
                                max_length = max(max_length, adjusted_len)
                        except:
                            pass
                    ws.column_dimensions[column].width = max(max_length + 2, 8)
                
                # 设置行高自适应
                for row in ws.iter_rows():
                    max_height = 15
                    for cell in row:
                        try:
                            if cell.value:
                                lines = len(str(cell.value)) // 15 + 1
                                max_height = max(max_height, lines * 15)
                        except:
                            pass
                    ws.row_dimensions[row[0].row].height = max_height
                
                wb.save(output_file)
            except ImportError:
                # 如果没有openpyxl，保存为csv
                output_file = self._get_records_file(symbol)
                result_df.to_csv(output_file, index=False, encoding="utf-8")
            
            print(f"  {symbol}: {count} 条记录")
            return result_df

        print(f"  {symbol}: 无趋势变化")
        return None

    def run(self, stocks=None):
        """运行生成"""
        results = {}
        target_stocks = stocks if stocks else ALL_STOCKS

        for symbol in target_stocks.keys():
            try:
                result = self.generate_stock_v2(symbol)
                results[symbol] = len(result) if result is not None else 0
            except Exception as e:
                print(f"  {symbol}: 错误 - {e}")
                results[symbol] = 0

        return results


def main():
    parser = argparse.ArgumentParser(description='生成行情记录')
    parser.add_argument('--stock', type=str, help='只生成指定股票')
    args = parser.parse_args()

    generator = RecordsGenerator()

    stocks = None
    if args.stock:
        if args.stock in ALL_STOCKS:
            stocks = {args.stock: ALL_STOCKS[args.stock]}
        else:
            print(f"股票 '{args.stock}' 不在配置中")
            return

    print(f"\n=== 生成行情记录 ===\n")

    results = generator.run(stocks=stocks)

    success = sum(1 for v in results.values() if v > 0)
    total = sum(v for v in results.values() if v > 0)

    print(f"\n=== 完成 ===")
    print(f"成功: {success}/{len(results)}")
    print(f"总记录: {total} 条")
    print(f"输出目录: {generator.records_dir}")


if __name__ == "__main__":
    main()
