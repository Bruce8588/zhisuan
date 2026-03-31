#!/usr/bin/env python3
"""2026年1-3月TD策略回测"""
import pandas as pd
import numpy as np
import os
from glob import glob

BASE = "/Users/isenfengming/.openclaw/workspace/工作台/智算"
TREND_DIR = f"{BASE}/output_daily_2025/趋势判断"
DATA_DIR = f"{BASE}/data_daily"
IND_DIR = f"{BASE}/data_daily_indicators"

BUY_FEE = 0.0004
SELL_FEE = 0.0014
MIN_FEE = 5

files = sorted(glob(f"{TREND_DIR}/*_趋势判断.csv"))

signals = []
for f in files:
    code = os.path.basename(f).replace("_趋势判断.csv", "")
    data_file = f"{DATA_DIR}/{code}_day.csv"
    ind_file = f"{IND_DIR}/{code}_indicators.csv"
    if not os.path.exists(data_file) or not os.path.exists(ind_file):
        continue
    
    df_d = pd.read_csv(data_file)
    df_d['day'] = pd.to_datetime(df_d['day'])
    df_d = df_d.sort_values('day').reset_index(drop=True)
    df_t = pd.read_csv(f)
    df_t['day'] = pd.to_datetime(df_t['时间'])
    df_t = df_t.sort_values('day').reset_index(drop=True)
    df_i = pd.read_csv(ind_file)
    df_i['day'] = pd.to_datetime(df_i['day'])
    df_i = df_i.sort_values('day').reset_index(drop=True)
    
    result = df_d[['day', 'close', 'high', 'low']].merge(
        df_t[['day', '趋势代码']], on='day', how='inner'
    ).merge(df_i[['day', 'TD_Buy_Count']], on='day', how='left')
    
    for i in range(len(result) - 20):
        row = result.iloc[i]
        if row['趋势代码'] != 'up_natural': continue
        if pd.isna(row.get('TD_Buy_Count')) or row['TD_Buy_Count'] != 9: continue
        
        entry_date = row['day']
        if entry_date.year != 2026: continue
        entry_price = row['close']
        
        stop_loss_pct = 0.97
        take_profit_pct = 1.20
        
        triggered = None
        trigger_day = None
        trigger_price = None
        
        for d in range(2, 21):
            if i + d >= len(result): break
            day_data = result.iloc[i + d]
            if day_data['low'] <= entry_price * stop_loss_pct:
                triggered = 'stop_loss'
                trigger_day = d
                trigger_price = entry_price * stop_loss_pct
                break
            elif day_data['high'] >= entry_price * take_profit_pct:
                triggered = 'take_profit'
                trigger_day = d
                trigger_price = entry_price * take_profit_pct
                break
        
        if triggered is None:
            if i + 8 < len(result):
                trigger_day = 8
                trigger_price = result.iloc[i + 8]['close']
                triggered = 'expire'
            else: continue
        
        exit_date = result.iloc[i + trigger_day]['day']
        buy_fee = max(entry_price * 100 * BUY_FEE, MIN_FEE)
        sell_fee = max(trigger_price * 100 * SELL_FEE, MIN_FEE)
        net_ret = (trigger_price * (1 - SELL_FEE) - entry_price * (1 + BUY_FEE)) / (entry_price * (1 + BUY_FEE))
        
        signals.append({
            'code': code, 'entry_date': entry_date, 'exit_date': exit_date,
            'entry_price': entry_price, 'exit_price': trigger_price,
            'result': triggered, 'holding_days': trigger_day,
            'return': net_ret, 'return_pct': net_ret * 100
        })

df_signals = pd.DataFrame(signals)
df_signals = df_signals.sort_values('entry_date').reset_index(drop=True)
print(f"2026年总信号: {len(df_signals)}")
if len(df_signals) > 0:
    print(f"数据范围: {df_signals['entry_date'].min()} ~ {df_signals['entry_date'].max()}")

# 模拟交易
portfolio = []
cash = 100000
position_size = 0.10
max_positions = 10
trades = []

start_date = pd.Timestamp('2026-01-02')
end_date = pd.Timestamp('2026-03-25')
current_date = start_date

while current_date <= end_date:
    to_sell = [p for p in portfolio if p['exit_date'] <= current_date]
    for p in to_sell:
        cash += cash * position_size * p['return']
        trades.append({**p, 'final_value': cash})
        portfolio.remove(p)
    
    if len(portfolio) < max_positions:
        available_slots = max_positions - len(portfolio)
        day_signals = df_signals[
            (df_signals['entry_date'] == current_date) & 
            (~df_signals['code'].isin([p['code'] for p in portfolio]))
        ]
        for _, signal in day_signals.head(available_slots).iterrows():
            portfolio.append({**signal.to_dict()})
    
    current_date += pd.Timedelta(days=1)

for p in portfolio:
    cash += cash * position_size * p['return']
    trades.append({**p, 'final_value': cash})

df_trades = pd.DataFrame(trades)

print(f"\n{'='*50}")
print(f"2026年1-3月模拟交易")
print(f"{'='*50}")
print(f"初始资金: 100,000 元")
print(f"最终资金: {cash:,.2f} 元")
print(f"总收益率: {(cash/100000-1)*100:.2f}%")
print(f"总交易次数: {len(df_trades)}")
print(f"止损: {(df_trades['result']=='stop_loss').sum()}")
print(f"止盈: {(df_trades['result']=='take_profit').sum()}")
print(f"到期: {(df_trades['result']=='expire').sum()}")
if len(df_trades) > 0:
    print(f"胜率: {(df_trades['return']>0).sum()/len(df_trades)*100:.1f}%")
    print(f"平均收益: {df_trades['return'].mean()*100:.2f}%")

for r in ['stop_loss', 'take_profit', 'expire']:
    sub = df_trades[df_trades['result'] == r]
    if len(sub) > 0:
        print(f"  {r}: {len(sub)}笔, 平均{sub['return'].mean()*100:.2f}%")

df_trades.to_csv(f"{BASE}/output/回测结果/backtest_2026.csv", index=False)
print("\n结果已保存")
