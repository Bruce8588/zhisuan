#!/usr/bin/env python3
"""多组参数测试"""
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

def load_signals(year):
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
            if entry_date.year != year: continue
            entry_price = row['close']
            signals.append({'code': code, 'entry_date': entry_date, 'entry_price': entry_price, 'result': result, 'entry_idx': i})
    return signals

def simulate(signals, stop_loss_pct, take_profit_pct, use_sl, use_tp, hold_days):
    if not signals: return None
    portfolio = []
    cash = 100000
    position_size = 0.10
    max_positions = 10
    trades = []
    start_date = pd.Timestamp(f'{signals[0]["entry_date"].year}-01-02')
    end_date = pd.Timestamp('2026-03-25')
    current_date = start_date
    
    # 预计算所有信号
    signal_list = []
    for s in signals:
        entry_price = s['entry_price']
        stop_loss = entry_price * stop_loss_pct if use_sl else None
        take_profit = entry_price * take_profit_pct if use_tp else None
        triggered = None
        trigger_day = None
        trigger_price = None
        result = s['result']
        i = s['entry_idx']
        
        max_d = min(hold_days, 20)
        for d in range(2, max_d + 1):
            if i + d >= len(result): break
            day_data = result.iloc[i + d]
            day_high = day_data['high']
            day_low = day_data['low']
            if use_sl and day_low <= stop_loss:
                triggered = 'stop_loss'
                trigger_day = d
                trigger_price = stop_loss
                break
            elif use_tp and day_high >= take_profit:
                triggered = 'take_profit'
                trigger_day = d
                trigger_price = take_profit
                break
        
        if triggered is None:
            if i + hold_days < len(result):
                trigger_day = hold_days
                trigger_price = result.iloc[i + hold_days]['close']
                triggered = 'expire'
            else: continue
        
        exit_date = result.iloc[i + trigger_day]['day']
        buy_fee = max(entry_price * 100 * BUY_FEE, MIN_FEE)
        sell_fee = max(trigger_price * 100 * SELL_FEE, MIN_FEE)
        net_ret = (trigger_price * (1 - SELL_FEE) - entry_price * (1 + BUY_FEE)) / (entry_price * (1 + BUY_FEE))
        
        signal_list.append({
            'code': s['code'], 'entry_date': s['entry_date'], 'exit_date': exit_date,
            'entry_price': entry_price, 'exit_price': trigger_price,
            'result': triggered, 'holding_days': trigger_day,
            'return': net_ret, 'return_pct': net_ret * 100,
            'buy_fee': buy_fee, 'sell_fee': sell_fee
        })
    
    df_signals = pd.DataFrame(signal_list)
    if len(df_signals) == 0: return None
    df_signals = df_signals.sort_values('entry_date').reset_index(drop=True)
    
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
                portfolio.append(signal.to_dict())
        
        current_date += pd.Timedelta(days=1)
    
    for p in portfolio:
        cash += cash * position_size * p['return']
        trades.append({**p, 'final_value': cash})
    
    return pd.DataFrame(trades)

# 测试配置
configs = [
    {"name": "止损3%止盈6%", "sl": 0.97, "tp": 1.06, "use_sl": True, "use_tp": True, "hold": 8},
    {"name": "不止损不止盈", "sl": 0, "tp": 0, "use_sl": False, "use_tp": False, "hold": 8},
    {"name": "止损6%止盈10%", "sl": 0.94, "tp": 1.10, "use_sl": True, "use_tp": True, "hold": 8},
]

print("加载2025年信号...")
signals_2025 = load_signals(2025)
print(f"2025年信号: {len(signals_2025)}")

print("加载2026年信号...")
signals_2026 = load_signals(2026)
print(f"2026年信号: {len(signals_2026)}")

print("\n" + "="*70)
print("参数测试结果")
print("="*70)

for config in configs:
    print(f"\n【{config['name']}】")
    print("-"*50)
    
    # 2025年
    df_2025 = simulate(signals_2025, config['sl'], config['tp'], config['use_sl'], config['use_tp'], config['hold'])
    if df_2025 is not None and len(df_2025) > 0:
        ret_2025 = (df_2025['final_value'].iloc[-1] / 100000 - 1) * 100
        wr_2025 = (df_2025['return'] > 0).sum() / len(df_2025) * 100
        stop_2025 = (df_2025['result'] == 'stop_loss').sum()
        tp_2025 = (df_2025['result'] == 'take_profit').sum()
        expire_2025 = (df_2025['result'] == 'expire').sum()
        print(f"  2025年: 收益{ret_2025:+.2f}%, 交易{len(df_2025)}笔, 胜率{wr_2025:.1f}%, 止损{stop_2025}, 止盈{tp_2025}, 到期{expire_2025}")
        df_2025.to_csv(f"{BASE}/output/回测结果/param_{config['name'].replace('%','').replace(' ','')}.csv", index=False)
        ret_2025_val = ret_2025
    else:
        print(f"  2025年: 无数据")
        ret_2025_val = 0
    
    # 2026年
    df_2026 = simulate(signals_2026, config['sl'], config['tp'], config['use_sl'], config['use_tp'], config['hold'])
    if df_2026 is not None and len(df_2026) > 0:
        ret_2026 = (df_2026['final_value'].iloc[-1] / 100000 - 1) * 100
        wr_2026 = (df_2026['return'] > 0).sum() / len(df_2026) * 100
        stop_2026 = (df_2026['result'] == 'stop_loss').sum()
        tp_2026 = (df_2026['result'] == 'take_profit').sum()
        expire_2026 = (df_2026['result'] == 'expire').sum()
        print(f"  2026年: 收益{ret_2026:+.2f}%, 交易{len(df_2026)}笔, 胜率{wr_2026:.1f}%, 止损{stop_2026}, 止盈{tp_2026}, 到期{expire_2026}")
        ret_2026_val = ret_2026
    else:
        print(f"  2026年: 无数据")
        ret_2026_val = 0
    
    print(f"  两年合计: {ret_2025_val + ret_2026_val:+.2f}%")
