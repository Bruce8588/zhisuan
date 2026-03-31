#!/usr/bin/env python3
"""2025年策略回测"""
import os, sys, pandas as pd, numpy as np
from datetime import datetime
from glob import glob

BASE = "/Users/isenfengming/.openclaw/workspace/工作台/智算"
TREND_DIR = os.path.join(BASE, "output_daily_2025", "趋势判断")
IND_DIR = os.path.join(BASE, "data_daily_indicators")
OUTPUT_DIR = os.path.join(BASE, "output", "回测结果")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data(code):
    trend_file = os.path.join(TREND_DIR, f"{code}_趋势判断.csv")
    ind_file = os.path.join(IND_DIR, f"{code}_indicators.csv")
    if not os.path.exists(trend_file) or not os.path.exists(ind_file):
        return None
    
    df_t = pd.read_csv(trend_file)
    df_t['时间'] = pd.to_datetime(df_t['时间'])
    df_t = df_t.sort_values('时间').reset_index(drop=True)
    
    df_i = pd.read_csv(ind_file)
    df_i['day'] = pd.to_datetime(df_i['day'])
    df_i = df_i.sort_values('day').reset_index(drop=True)
    
    result = df_t[['时间', '当前价格', '趋势代码']].copy()
    result = result.merge(df_i[['day', 'DIF', 'TD_Buy_Count']], left_on='时间', right_on='day', how='left')
    result.drop('day', axis=1, inplace=True)
    return result

def backtest_a(df, holding=10):
    """策略A: 自然回撤 + TD9"""
    if df is None or 'TD_Buy_Count' not in df.columns:
        return []
    trades = []
    for i in range(len(df) - holding):
        row = df.iloc[i]
        if row['趋势代码'] != 'up_natural': continue
        if pd.isna(row.get('TD_Buy_Count')) or row['TD_Buy_Count'] != 9: continue
        entry = row['当前价格']
        rets = [(df.iloc[i+d]['当前价格'] - entry) / entry for d in range(1, holding+1)]
        trades.append({'strategy': 'A_TD', 'entry_date': row['时间'], 'entry_price': entry,
                       **{f'holding_{d}d': rets[d-1] for d in range(1, holding+1)}})
    return trades

def backtest_b(df, holding=10):
    """策略B: 自然回撤 + MACD金叉"""
    if df is None or 'DIF' not in df.columns:
        return []
    trades = []
    for i in range(1, len(df) - holding):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        if row['趋势代码'] != 'up_natural': continue
        if pd.isna(row.get('DIF')) or pd.isna(prev.get('DIF')): continue
        if not (row['DIF'] > 0 and prev['DIF'] <= 0): continue
        entry = row['当前价格']
        rets = [(df.iloc[i+d]['当前价格'] - entry) / entry for d in range(1, holding+1)]
        trades.append({'strategy': 'B_MACD', 'entry_date': row['时间'], 'entry_price': entry,
                       **{f'holding_{d}d': rets[d-1] for d in range(1, holding+1)}})
    return trades

def analyze(trades, name):
    if not trades:
        print(f"{name}: 无信号"); return
    df = pd.DataFrame(trades)
    print(f"\n{'='*60}")
    print(f"{name}: {len(trades)} 个信号")
    print(f"{'='*60}")
    print(f"{'持有':<6} {'信号数':<8} {'胜率':<10} {'平均收益':<10}")
    for d in range(1, 11):
        col = f'holding_{d}d'
        if col in df.columns:
            v = df[col].dropna()
            if len(v) > 0:
                wr = (v > 0).sum() / len(v) * 100
                ar = v.mean() * 100
                print(f"{d}天    {len(v):<8} {wr:.1f}%      {ar:+.2f}%")
    return df

def main():
    start = datetime.now()
    files = sorted(glob(os.path.join(TREND_DIR, "*_趋势判断.csv")))
    print(f"2025年策略回测 | {len(files)} 只股票")
    
    a_trades, b_trades = [], []
    for i, f in enumerate(files):
        code = os.path.basename(f).replace("_趋势判断.csv", "")
        df = load_data(code)
        if df is None: continue
        a_trades.extend(backtest_a(df))
        b_trades.extend(backtest_b(df))
        if (i+1) % 1000 == 0:
            print(f"进度: {i+1}/{len(files)} | A:{len(a_trades)} B:{len(b_trades)} | {(datetime.now()-start).total_seconds():.0f}s")
    
    print(f"\n完成! 耗时: {(datetime.now()-start).total_seconds():.0f}s")
    
    df_a = analyze(a_trades, "策略A: 自然回撤+TD9")
    df_b = analyze(b_trades, "策略B: 自然回撤+MACD金叉")
    
    if a_trades: pd.DataFrame(a_trades).to_csv(os.path.join(OUTPUT_DIR, "backtest_2025_strategy_A_TD.csv"), index=False)
    if b_trades: pd.DataFrame(b_trades).to_csv(os.path.join(OUTPUT_DIR, "backtest_2025_strategy_B_MACD.csv"), index=False)
    print(f"\n已保存到: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
