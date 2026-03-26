#!/usr/bin/env python3
"""
交易策略回测 - 自选股版
使用自选股的正确趋势分析结果
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class StrategyBacktester:
    """策略回测器"""

    def __init__(self):
        self.trend_dir = os.path.join(BASE_DIR, "output", "趋势判断")
        self.indicator_dir = os.path.join(BASE_DIR, "data_daily_indicators")
        self.price_dir = os.path.join(BASE_DIR, "data_daily")
        self.results_dir = os.path.join(BASE_DIR, "output", "回测结果")
        os.makedirs(self.results_dir, exist_ok=True)

    def normalize_code(self, code):
        """标准化代码格式"""
        code = code.lower()
        code = code.replace('sh', '').replace('sz', '')
        return code

    def load_and_aggregate_trend(self, symbol):
        """加载趋势数据并聚合到日级别"""
        trend_file = None
        for f in os.listdir(self.trend_dir):
            if f.startswith(symbol) and '趋势判断' in f and '_默认配置' not in f and '_2025' not in f and '_2026' not in f:
                trend_file = os.path.join(self.trend_dir, f)
                break
        
        if not trend_file or not os.path.exists(trend_file):
            return None
        
        try:
            df = pd.read_csv(trend_file)
            if '时间' not in df.columns or '趋势代码' not in df.columns:
                return None
            df['day'] = pd.to_datetime(df['时间']).dt.date
            daily = df.groupby('day').agg({'趋势代码': 'last', '当前价格': 'last'}).reset_index()
            daily['day'] = pd.to_datetime(daily['day'])
            return daily.rename(columns={'趋势代码': 'trend'})
        except:
            return None

    def load_indicator(self, code):
        """加载指标数据"""
        code_norm = self.normalize_code(code)
        indicator_file = os.path.join(self.indicator_dir, f"{code_norm}_indicators.csv")
        if not os.path.exists(indicator_file):
            return None
        try:
            df = pd.read_csv(indicator_file)
            df['day'] = pd.to_datetime(df['day'])
            return df
        except:
            return None

    def load_price(self, code):
        """加载价格数据"""
        code_norm = self.normalize_code(code)
        price_file = os.path.join(self.price_dir, f"{code_norm}_day.csv")
        if not os.path.exists(price_file):
            return None
        try:
            df = pd.read_csv(price_file)
            df['day'] = pd.to_datetime(df['day'])
            return df[['day', 'close']]
        except:
            return None

    def get_macd_signals(self, df):
        """MACD金叉信号"""
        signals = []
        for i in range(1, len(df)):
            dif_prev = df['DIF'].iloc[i-1]
            dif_now = df['DIF'].iloc[i]
            dea_prev = df['DEA'].iloc[i-1]
            dea_now = df['DEA'].iloc[i]
            if dif_prev <= dea_prev and dif_now > dea_now:
                signals.append(df['day'].iloc[i])
        return signals

    def get_td_signals(self, df):
        """TD买入信号（计数达到9）"""
        signals = []
        for i in range(len(df)):
            if df['TD_Buy_Count'].iloc[i] == 9:
                signals.append(df['day'].iloc[i])
        return signals

    def calculate_returns(self, price_df, buy_date, hold_days):
        """计算持有N天后的收益率"""
        buy_date = pd.Timestamp(buy_date)
        buy_row = price_df[price_df['day'] == buy_date]
        if buy_row.empty:
            return None
        buy_price = buy_row['close'].iloc[0]
        
        sell_candidates = price_df[price_df['day'] > buy_date]
        if len(sell_candidates) < hold_days:
            return None
        
        sell_date = sell_candidates['day'].iloc[hold_days - 1]
        sell_row = price_df[price_df['day'] == sell_date]
        if sell_row.empty:
            return None
        sell_price = sell_row['close'].iloc[0]
        
        return (sell_price - buy_price) / buy_price

    def run_backtest(self):
        """运行回测"""
        from config.stocks import ALL_STOCKS
        
        holding_periods = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        all_results = defaultdict(list)
        
        total = len(ALL_STOCKS)
        print(f"开始回测，共 {total} 只自选股...")
        print(f"持有期限: {holding_periods}")
        print()
        
        for idx, (symbol, info) in enumerate(ALL_STOCKS.items()):
            code = info.get('code', '')
            
            trend_df = self.load_and_aggregate_trend(symbol)
            indicator_df = self.load_indicator(code)
            price_df = self.load_price(code)
            
            if trend_df is None or indicator_df is None or price_df is None:
                continue
            
            merged = trend_df.merge(indicator_df, on='day', how='inner')
            if merged.empty:
                continue
            
            up_natural = merged[merged['trend'] == 'up_natural']
            if len(up_natural) < 10:
                continue
            
            td_signals = set(self.get_td_signals(up_natural))
            macd_signals = set(self.get_macd_signals(up_natural))
            both_signals = td_signals & macd_signals
            
            if len(td_signals) == 0 and len(macd_signals) == 0:
                continue
            
            strategies = {
                'TD买入': td_signals,
                'MACD买入': macd_signals,
                'TD+MACD同时买入': both_signals
            }
            
            for strategy_name, signals in strategies.items():
                for buy_date in signals:
                    for hold_days in holding_periods:
                        ret = self.calculate_returns(price_df, buy_date, hold_days)
                        if ret is not None:
                            all_results[f"{strategy_name}_{hold_days}天"].append(ret)
            
            print(f"[{idx+1}/{total}] {symbol}: 自然回撤{len(up_natural)}天, TD{len(td_signals)}个, MACD{len(macd_signals)}个")
        
        print(f"\n计算完成，正在生成报告...")
        self.generate_report(all_results, holding_periods)
        return all_results

    def generate_report(self, all_results, holding_periods):
        """生成统计报告"""
        strategies = ['TD买入', 'MACD买入', 'TD+MACD同时买入']
        
        report_file = os.path.join(self.results_dir, f"自选股策略回测_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        with open(report_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['策略回测结果 - 自选股'])
            writer.writerow([f'回测时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
            writer.writerow([f'使用正确初始配置的日线趋势数据'])
            writer.writerow([])
            writer.writerow(['持有天数', '样本数', '平均收益(%)', '胜率(%)', '平均盈利(%)', '平均亏损(%)'])
            
            for strategy in strategies:
                writer.writerow([f'--- {strategy} ---'])
                for hold_days in holding_periods:
                    key = f"{strategy}_{hold_days}天"
                    returns = all_results[key]
                    
                    if len(returns) == 0:
                        writer.writerow([f'{hold_days}天', 0, 'N/A', 'N/A', 'N/A', 'N/A'])
                        continue
                    
                    avg_ret = np.mean(returns) * 100
                    win_rate = np.sum(np.array(returns) > 0) / len(returns) * 100
                    avg_win = np.mean([r for r in returns if r > 0]) * 100 if any(r > 0 for r in returns) else 0
                    avg_loss = np.mean([r for r in returns if r < 0]) * 100 if any(r < 0 for r in returns) else 0
                    
                    writer.writerow([f'{hold_days}天', len(returns), f'{avg_ret:.2f}', f'{win_rate:.1f}', f'{avg_win:.2f}', f'{avg_loss:.2f}'])
        
        print(f"\n报告已保存: {report_file}")
        self.print_summary(all_results, strategies, holding_periods)
        return report_file

    def print_summary(self, all_results, strategies, holding_periods):
        """打印汇总表"""
        print("\n" + "=" * 80)
        print("策略回测结果汇总")
        print("=" * 80)
        
        for strategy in strategies:
            print(f"\n【{strategy}】")
            print(f"{'持有天数':<10} {'样本数':<10} {'平均收益':<12} {'胜率':<10} {'平均盈利':<12} {'平均亏损':<12}")
            print("-" * 76)
            
            for hold_days in holding_periods:
                key = f"{strategy}_{hold_days}天"
                returns = all_results[key]
                
                if len(returns) == 0:
                    print(f"{hold_days:<10} {'N/A':<10}")
                    continue
                
                avg_ret = np.mean(returns) * 100
                win_rate = np.sum(np.array(returns) > 0) / len(returns) * 100
                avg_win = np.mean([r for r in returns if r > 0]) * 100 if any(r > 0 for r in returns) else 0
                avg_loss = np.mean([r for r in returns if r < 0]) * 100 if any(r < 0 for r in returns) else 0
                
                print(f"{hold_days:<10} {len(returns):<10} {avg_ret:>10.2f}%   {win_rate:>8.1f}%   {avg_win:>10.2f}%   {avg_loss:>10.2f}%")


def main():
    backtester = StrategyBacktester()
    backtester.run_backtest()


if __name__ == "__main__":
    main()
