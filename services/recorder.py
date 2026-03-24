#!/usr/bin/env python3.11
"""
记录功能模块
功能：实时动态（最近5分钟趋势和价格）+ 行情记录（趋势转变）
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.rules import TREND_NAMES


class Recorder:
    """记录器"""
    
    def __init__(self, db_dir=None, output_dir=None):
        self.db_dir = db_dir or os.path.join(BASE_DIR, "data")
        self.output_dir = output_dir or os.path.join(BASE_DIR, "output")
        
        # 目录
        self.realtime_dir = os.path.join(self.output_dir, "实时动态")
        self.market_dir = os.path.join(self.output_dir, "行情记录")
        self.trend_dir = os.path.join(self.output_dir, "趋势判断")
        
        for d in [self.realtime_dir, self.market_dir]:
            os.makedirs(d, exist_ok=True)
    
    def _convert_columns(self, df):
        """转换列名：英文 -> 中文"""
        column_map = {
            'day': '时间',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'close': '收盘',
            'volume': '成交量',
            'amount': '成交额',
        }
        for eng, chn in column_map.items():
            if eng in df.columns:
                df[chn] = df[eng]
        return df
    
    def generate_realtime(self, symbol, info):
        """生成实时动态（最近5分钟趋势和价格）"""
        code = info["code"]
        db_file = os.path.join(self.db_dir, f"{symbol}_{code}_min1.csv")
        
        if not os.path.exists(db_file):
            return None
        
        # 读取数据并转换列名
        df = pd.read_csv(db_file)
        df = self._convert_columns(df)
        
        # 转换时间并排序
        df["时间"] = pd.to_datetime(df["时间"])
        df = df.sort_values("时间")
        
        # 获取最新可用数据的日期（而非今天）
        latest_date = df["时间"].max().date()
        df_latest = df[df["时间"].dt.date == latest_date]
        
        # 判断是否收盘（15:00之后）
        now = datetime.now()
        market_close = now.replace(hour=14, minute=55, second=0, microsecond=0)
        
        if now > market_close:
            # 收盘后：取收盘前最后5分钟（14:55-15:00）
            df_latest = df_latest[(df_latest["时间"].dt.hour == 14) & (df_latest["时间"].dt.minute >= 55)]
            df_result = df_latest.tail(5)
            time_label = "收盘前5分钟"
        else:
            # 交易时段：取最近5分钟
            df_result = df_latest.tail(5)
            time_label = "最近5分钟"
        
        if len(df_result) == 0:
            return None
        
        # 读取趋势
        trend_file = os.path.join(self.trend_dir, f"{symbol}_趋势判断.csv")
        trend_name = "未知"
        if os.path.exists(trend_file):
            trend_df = pd.read_csv(trend_file)
            if len(trend_df) > 0:
                latest_trend = trend_df.iloc[-1]
                trend = latest_trend["趋势代码"]
                trend_name = latest_trend.get("趋势名称", TREND_NAMES.get(trend, trend))
        
        # 生成实时动态
        latest = df_result.iloc[-1]
        
        content = f"""## {symbol} 实时动态

**当前趋势**: {trend_name}
**最新价格**: {latest['收盘']}
**时间**: {latest['时间']}
**数据范围**: {time_label}

### {time_label}

| 时间 | 开盘 | 最高 | 最低 | 收盘 |
|------|------|------|------|------|
"""
        
        for _, row in df_result.iterrows():
            time_str = row['时间'].strftime('%H:%M')
            content += f"| {time_str} | {row['开盘']} | {row['最高']} | {row['最低']} | {row['收盘']} |\n"
        
        # 保存
        output_file = os.path.join(self.realtime_dir, f"{symbol}_实时动态.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_file
    
    def generate_market_record(self, symbol, info):
        """生成行情记录（每日趋势关键点，10列表格形式）"""
        code = info["code"]
        db_file = os.path.join(self.db_dir, f"{symbol}_{code}_min1.csv")
        trend_file = os.path.join(self.trend_dir, f"{symbol}_趋势判断.csv")
        
        if not os.path.exists(db_file):
            return None
        
        if not os.path.exists(trend_file):
            return None
        
        # 10种趋势列
        TREND_COLUMNS = [
            "上升趋势(up)", "自然回撤(up_natural)", "回升(up_rally)", 
            "次级回撤(up_secondary)", "破碎(up_break)",
            "下跌趋势(down)", "自然回升(down_natural)", "回撤(down_rally)", 
            "次级回升(down_secondary)", "破碎(down_break)"
        ]
        
        trend_map = {
            "up": "上升趋势(up)",
            "up_natural": "自然回撤(up_natural)",
            "up_rally": "回升(up_rally)",
            "up_secondary": "次级回撤(up_secondary)",
            "up_break": "破碎(up_break)",
            "down": "下跌趋势(down)",
            "down_natural": "自然回升(down_natural)",
            "down_rally": "回撤(down_rally)",
            "down_secondary": "次级回升(down_secondary)",
            "down_break": "破碎(down_break)",
        }
        
        # 读取数据
        db_df = pd.read_csv(db_file)
        db_df = self._convert_columns(db_df)
        db_df["时间"] = pd.to_datetime(db_df["时间"])
        db_df = db_df.sort_values("时间").reset_index(drop=True)
        
        trend_df = pd.read_csv(trend_file)
        trend_df["时间"] = pd.to_datetime(trend_df["时间"])
        trend_df = trend_df.sort_values("时间").reset_index(drop=True)
        
        # 合并数据
        merged = pd.merge_asof(
            db_df.sort_values("时间"),
            trend_df.sort_values("时间"),
            direction="backward",
            suffixes=("", "_trend")
        )
        
        # 添加日期列
        merged["日期"] = merged["时间"].dt.date
        
        # 按日期分组，获取每天首次出现的趋势关键点
        result = []
        
        for date, group in merged.groupby("日期"):
            row = {"日期": str(date)}
            for col in TREND_COLUMNS:
                row[col] = ""
            
            # 获取当天数据
            for _, row_data in group.iterrows():
                trend = row_data.get("趋势代码", "")
                if trend and trend in trend_map:
                    col_name = trend_map[trend]
                    
                    # 获取对应的关键点值
                    key_point = None
                    if trend == "up":
                        key_point = row_data.get("key_high")
                    elif trend == "up_natural":
                        key_point = row_data.get("n_low")
                    elif trend == "up_rally":
                        key_point = row_data.get("rally_high")
                    elif trend == "up_secondary":
                        key_point = row_data.get("secondary_low")
                    elif trend == "up_break":
                        key_point = row_data.get("break_low")
                    elif trend == "down":
                        key_point = row_data.get("key_low")
                    elif trend == "down_natural":
                        key_point = row_data.get("n_high")
                    elif trend == "down_rally":
                        key_point = row_data.get("rally_low")
                    elif trend == "down_secondary":
                        key_point = row_data.get("secondary_high")
                    elif trend == "down_break":
                        key_point = row_data.get("break_high")
                    
                    # 只记录非空的关键点
                    if key_point is not None and key_point != "" and str(key_point) != "nan":
                        row[col_name] = key_point
            
            result.append(row)
        
        # 生成CSV
        columns = ["日期"] + TREND_COLUMNS
        result_df = pd.DataFrame(result, columns=columns)
        
        output_file = os.path.join(self.market_dir, f"{symbol}_行情记录.csv")
        result_df.to_csv(output_file, index=False, encoding="utf-8")
        
        return output_file
        
        return output_file
    
    def generate_all(self, stocks):
        """生成所有股票的记录"""
        results = {"realtime": [], "market": []}
        
        for symbol, info in stocks.items():
            r = self.generate_realtime(symbol, info)
            if r:
                results["realtime"].append(symbol)
            
            m = self.generate_market_record(symbol, info)
            if m:
                results["market"].append(symbol)
        
        return results


if __name__ == "__main__":
    from config.stocks import POOL_A
    
    recorder = Recorder()
    
    print("=== 生成记录 ===")
    results = recorder.generate_all(POOL_A)
    
    print(f"实时动态: {len(results['realtime'])} 只")
    print(f"行情记录: {len(results['market'])} 只")
    
    print("\n记录完成!")
