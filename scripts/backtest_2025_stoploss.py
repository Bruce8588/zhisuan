#!/usr/bin/env python3
"""2025年TD策略回测 - 带止损"""
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
    result = df_t[['时间', '当前价格', '趋势代码', 'n_low']].copy()
    result = result.merge(df_i[['day', 'TD_Buy_Count']], left_on='时间', right_on='day', how='left')
    result.drop('day', axis=1, inplace=True)
    return result

def backtest_with_stoploss(df, holding=10):
    if df is None or 'TD_Buy_Count' not in df.columns:
        return []
    trades = []
    for i in range(len(df) - holding):
        row = df.iloc[i]
        if row['趋势代码'] != 'up_natural': continue
        if pd.isna(row.get('TD_Buy_Count')) or row['TD_Buy_Count'] != 9: continue
        entry_price = row['当前价格']
        stop_loss = row['n_low']
        if pd.isna(stop_loss): continue
        
        stop_triggered = False
        stop_day = None
        stop_return = None
        
        for d in range(1, holding + 1):
            price = df.iloc[i + d]['当前价格']
            if price < stop_loss:
                stop_triggered = True
                stop_day = d
                stop_return = (price - entry_price) / entry_price
                break
        
        if stop_triggered:
            trades.append({
                'entry_date': row['时间'], 'entry_price': entry_price, 'stop_loss': stop_loss,
                'exit_day': stop_day, 'exit_price': df.iloc[i + stop_day]['当前价格'],
                'return': stop_return, 'result': 'stop_loss',
                **{f'holding_{d}d': np.nan for d in range(1, 11)}
            })
        else:
            returns = [(df.iloc[i + d]['当前价格'] - entry_price) / entry_price for d in range(1, holding + 1)]
            trades.append({
                'entry_date': row['时间'], 'entry_price': entry_price, 'stop_loss': stop_loss,
                'exit_day': holding, 'exit_price': df.iloc[i + holding]['当前价格'],
                'result': 'hold',
                **{f'holding_{d}d': returns[d-1] for d in range(1, 11)}
            })
    return trades

def main():
    start = datetime.now()
    print(f"TD策略回测 - 带止损 | 数据: 2025-2026")
    files = sorted(glob(os.path.join(TREND_DIR, "*_趋势判断.csv")))
    print(f"股票数量: {len(files)}")
    all_trades = []
    for i, f in enumerate(files):
        code = os.path.basename(f).replace("_趋势判断.csv", "")
        df = load_data(code)
        if df is None: continue
        all_trades.extend(backtest_with_stoploss(df))
        if (i+1) % 1000 == 0:
            print(f"进度: {i+1}/{len(files)} | 信号: {len(all_trades)} | {(datetime.now()-start).total_seconds():.0f}s")
    print(f"完成! 耗时: {(datetime.now()-start).total_seconds():.0f}s")
    
    df_result = pd.DataFrame(all_trades)
    total = len(df_result)
    stop_count = (df_result['result'] == 'stop_loss').sum()
    hold_count = (df_result['result'] == 'hold').sum()
    
    print(f"\n{'='*60}")
    print(f"2025-2026 TD策略(带止损): {total} 信号 (止损:{stop_count} 持有:{hold_count})")
    print(f"{'='*60}")
    print(f"{'持有':<8} {'胜率(全部)':<12} {'平均收益(全部)':<14} {'止损率':<10}")
    print("-" * 60)
    
    for d in range(1, 11):
        col = f'holding_{d}d'
        # 所有在d天内被止损或持有到d天的交易
        valid = df_result[(df_result['exit_day'] >= d) | (df_result['result'] == 'stop_loss')].copy()
        # 对于d天前止损的，用止损收益
        valid[col] = valid.apply(
            lambda row: row[col] if (row['exit_day'] >= d and pd.notna(row[col])) 
            else (row['return'] if row['result'] == 'stop_loss' and row['exit_day'] < d else np.nan), axis=1)
        valid = valid[valid[col].notna()]
        
        if len(valid) > 0:
            wr = (valid[col] > 0).sum() / len(valid) * 100
            ar = valid[col].mean() * 100
            stop_rate = stop_count / total * 100 if d == 1 else (df_result['exit_day'] < d).sum() / total * 100
            print(f"{d}天      {wr:.1f}%        {ar:+.2f}%        {stop_rate:.1f}%")
    
    # 持有到期部分的胜率
    print(f"\n{'='*60}")
    print(f"持有到期的交易 (幸存者): {hold_count}")
    print(f"{'持有':<8} {'胜率(持有)':<12} {'平均收益(持有)':<16}")
    print("-" * 60)
    held = df_result[df_result['result'] == 'hold']
    for d in range(1, 11):
        col = f'holding_{d}d'
        valid = held[held[col].notna()]
        if len(valid) > 0:
            wr = (valid[col] > 0).sum() / len(valid) * 100
            ar = valid[col].mean() * 100
            print(f"{d}天      {wr:.1f}%        {ar:+.2f}%")
    
    df_result.to_csv(os.path.join(OUTPUT_DIR, "backtest_2025_TD_stoploss.csv"), index=False)
    print(f"\n结果已保存")

if __name__ == "__main__":
    main()
