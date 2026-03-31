#!/usr/bin/env python3
"""
TD9策略回测 - 真实资金模拟 v5（按日历日迭代）
修复了之前版本按信号日期迭代导致的价格追踪bug
"""
import os, pandas as pd
from datetime import datetime, timedelta
from glob import glob
from collections import defaultdict

BASE = "/Users/isenfengming/.openclaw/workspace/工作台/智算"

# 参数
INITIAL_CAPITAL = 1000000
POSITION_SIZE = 0.20
MAX_POSITIONS = 5
STOP_LOSS = 0.94
TAKE_PROFIT = 1.20
MAX_HOLDING = 8
START_YEAR = 2020


def main():
    start_time = datetime.now()
    print("=" * 60)
    print("TD9策略回测 - 真实资金模拟 v5 (按日历日迭代)")
    print("=" * 60)
    print(f"初始资金: {INITIAL_CAPITAL/10000:.0f}万 | 仓位: {POSITION_SIZE*100:.0f}%")
    print(f"最大持仓: {MAX_POSITIONS}只 | 止损: {STOP_LOSS*100:.0f}% | 止盈: {TAKE_PROFIT*100:.0f}%")
    print(f"最大持有: {MAX_HOLDING}天")
    print("=" * 60)
    
    TREND_2024 = f"{BASE}/output_daily_2015_2024/趋势判断"
    IND_2024 = f"{BASE}/data_daily_indicators_2015_2024"
    PRICE_2024 = f"{BASE}/data_daily_indicators_2015_2024"
    
    TREND_2025 = f"{BASE}/output_daily_2025/趋势判断"
    IND_2025 = f"{BASE}/data_daily_indicators"
    PRICE_2025 = f"{BASE}/data_daily_indicators"
    
    print("\n加载数据...")
    
    # 加载价格和信号
    prices = defaultdict(dict)  # {code: {date: close}}
    signals = []  # [(date, code, entry_price, stop_loss)]
    
    # 2020-2024
    files = sorted(glob(f"{TREND_2024}/*.csv"))
    for idx, f in enumerate(files):
        code = os.path.basename(f).replace("_趋势判断.csv", "")
        
        # 价格
        pf = f"{PRICE_2024}/{code}_indicators.csv"
        if os.path.exists(pf):
            try:
                df = pd.read_csv(pf)
                df['day'] = pd.to_datetime(df['day'])
                df = df[df['day'].dt.year >= START_YEAR]
                for _, row in df.iterrows():
                    if pd.notna(row.get('close')):
                        prices[code][row['day']] = row['close']
            except: pass
        
        # 信号
        indf = f"{IND_2024}/{code}_indicators.csv"
        if os.path.exists(indf):
            try:
                df_t = pd.read_csv(f)
                df_t['时间'] = pd.to_datetime(df_t['时间'])
                df_t = df_t[df_t['时间'].dt.year >= START_YEAR]
                
                df_i = pd.read_csv(indf)
                df_i['day'] = pd.to_datetime(df_i['day'])
                df_i = df_i[df_i['day'].dt.year >= START_YEAR]
                
                df = df_t[['时间', '当前价格', '趋势代码', 'n_low']].copy()
                df = df.merge(df_i[['day', 'TD_Buy_Count']], left_on='时间', right_on='day', how='left')
                
                for _, row in df.iterrows():
                    if row['趋势代码'] == 'up_natural' and row['TD_Buy_Count'] == 9:
                        if pd.notna(row['n_low']) and row['n_low'] > 0:
                            signals.append((row['时间'], code, row['当前价格'], row['n_low']))
            except: pass
        
        if (idx + 1) % 1000 == 0:
            print(f"  2020-2024: {idx+1}/{len(files)}")
    
    # 2025
    files = sorted(glob(f"{TREND_2025}/*.csv"))
    for idx, f in enumerate(files):
        code = os.path.basename(f).replace("_趋势判断.csv", "")
        
        pf = f"{PRICE_2025}/{code}_indicators.csv"
        if os.path.exists(pf):
            try:
                df = pd.read_csv(pf)
                df['day'] = pd.to_datetime(df['day'])
                for _, row in df.iterrows():
                    if pd.notna(row.get('close')):
                        prices[code][row['day']] = row['close']
            except: pass
        
        indf = f"{IND_2025}/{code}_indicators.csv"
        if os.path.exists(indf):
            try:
                df_t = pd.read_csv(f)
                df_t['时间'] = pd.to_datetime(df_t['时间'])
                
                df_i = pd.read_csv(indf)
                df_i['day'] = pd.to_datetime(df_i['day'])
                
                df = df_t[['时间', '当前价格', '趋势代码', 'n_low']].copy()
                df = df.merge(df_i[['day', 'TD_Buy_Count']], left_on='时间', right_on='day', how='left')
                
                for _, row in df.iterrows():
                    if row['趋势代码'] == 'up_natural' and row['TD_Buy_Count'] == 9:
                        if pd.notna(row['n_low']) and row['n_low'] > 0:
                            signals.append((row['时间'], code, row['当前价格'], row['n_low']))
            except: pass
    
    # 按日期排序
    signals.sort(key=lambda x: x[0])
    print(f"\n加载完成: {len(prices)}只股票, {len(signals)}个信号")
    
    # ========== 核心修复：按日历日迭代 ==========
    # 构建信号字典: {date: [signals on this date]}
    signals_by_date = defaultdict(list)
    for date, code, entry_price, stop_loss in signals:
        signals_by_date[date].append({'date': date, 'code': code, 'entry_price': entry_price, 'stop_loss': stop_loss})
    
    # 获取所有交易日期
    all_dates = sorted(prices.get(list(prices.keys())[0], {}).keys())
    trading_dates = [d for d in all_dates if d.year >= START_YEAR]
    print(f"交易日数量: {len(trading_dates)}")
    
    # 开始模拟
    cash = INITIAL_CAPITAL
    positions = []  # [{code, entry_price, entry_date, days_held}]
    closed = []
    
    print("\n开始模拟（按日历日迭代）...")
    
    for i, trade_date in enumerate(trading_dates):
        # 1. 检查持仓是否需要平仓
        new_positions = []
        for pos in positions:
            pos['days_held'] += 1
            
            # 获取当日收盘价
            cur_price = prices.get(pos['code'], {}).get(trade_date)
            if cur_price is None:
                # 日期不存在（周末/节假日），跳过但不增加持有天数
                pos['days_held'] -= 1
                new_positions.append(pos)
                continue
            
            # 更新持仓期间的价格区间
            pos['high'] = max(pos.get('high', pos['entry_price']), cur_price)
            pos['low'] = min(pos.get('low', pos['entry_price']), cur_price)
            pos['last_price'] = cur_price
            
            # 止损
            if pos['low'] <= pos['entry_price'] * STOP_LOSS:
                cash *= (1 - 0.06 * POSITION_SIZE)
                closed.append({**pos, 'exit_date': trade_date, 'exit_price': pos['entry_price'] * STOP_LOSS, 'return': -0.06, 'result': 'stop_loss'})
            # 止盈
            elif pos['high'] >= pos['entry_price'] * TAKE_PROFIT:
                cash *= (1 + 0.20 * POSITION_SIZE)
                closed.append({**pos, 'exit_date': trade_date, 'exit_price': pos['entry_price'] * TAKE_PROFIT, 'return': 0.20, 'result': 'take_profit'})
            # 到期
            elif pos['days_held'] >= MAX_HOLDING:
                ret = (cur_price - pos['entry_price']) / pos['entry_price']
                cash *= (1 + ret * POSITION_SIZE)
                closed.append({**pos, 'exit_date': trade_date, 'exit_price': cur_price, 'return': ret, 'result': 'expired'})
            else:
                new_positions.append(pos)
        
        positions = new_positions
        
        # 2. 处理当日新信号
        if len(positions) < MAX_POSITIONS:
            available = MAX_POSITIONS - len(positions)
            for sig in signals_by_date[trade_date][:available]:
                shares = int((cash * POSITION_SIZE) / sig['entry_price'] / 100) * 100
                if shares > 0:
                    positions.append({
                        'code': sig['code'],
                        'entry_price': sig['entry_price'],
                        'stop_loss': sig['stop_loss'],
                        'entry_date': trade_date,
                        'days_held': 0,
                        'high': sig['entry_price'],
                        'low': sig['entry_price'],
                        'last_price': sig['entry_price']
                    })
        
        if (i + 1) % 500 == 0:
            print(f"  已处理 {i+1}/{len(trading_dates)} 天")
    
    # 期末清算
    for pos in positions:
        price = pos.get('last_price', pos['entry_price'])
        ret = (price - pos['entry_price']) / pos['entry_price']
        ret = max(ret, -0.06)
        ret = min(ret, 0.20)
        cash *= (1 + ret * POSITION_SIZE)
        closed.append({**pos, 'exit_date': 'final', 'exit_price': price, 'return': ret, 'result': 'final'})
    
    df = pd.DataFrame(closed)
    
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"初始资金: {INITIAL_CAPITAL/10000:.0f}万 | 最终资金: {cash/10000:.2f}万 | 总收益: {(cash-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.2f}%")
    print(f"总交易: {len(df)} | 止损: {(df['result']=='stop_loss').sum()} | 止盈: {(df['result']=='take_profit').sum()} | 到期: {(df['result']=='expired').sum()}")
    
    print("\n" + "=" * 60)
    print("年度表现")
    print("=" * 60)
    print(f"{'年份':<6} {'收益':>10} {'夏普':>8} {'最大回撤':>10} {'交易':>6} {'胜率':>6}")
    print("-" * 60)
    
    df['year'] = pd.to_datetime(df['entry_date']).dt.year
    
    for year in sorted(df['year'].unique()):
        yd = df[df['year'] == year].sort_values('entry_date')
        capital = INITIAL_CAPITAL
        curve = [capital]
        for _, t in yd.iterrows():
            capital *= (1 + t['return'] * POSITION_SIZE)
            curve.append(capital)
        
        ret = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        
        rets = [(curve[i]-curve[i-1])/curve[i-1] for i in range(1, len(curve))]
        if len(rets) > 0 and np.std(rets) > 0:
            sharpe = (np.mean(rets)*252 - 0.03) / (np.std(rets)*np.sqrt(252))
        else:
            sharpe = 0
        
        peak = INITIAL_CAPITAL
        maxdd = 0
        for c in curve:
            if c > peak: peak = c
            dd = (peak - c) / peak * 100
            if dd > maxdd: maxdd = dd
        
        wr = (yd['return'] > 0).sum() / len(yd) * 100
        print(f"{year:<6} {ret:>+9.2f}% {sharpe:>+7.2f} {maxdd:>+9.2f}% {len(yd):>6d} {wr:>5.1f}%")
    
    print("=" * 60)
    
    # 保存
    out = f"{BASE}/output/回测结果/TD9_真实资金模拟_v5_2020_2025.csv"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(f"\n耗时: {(datetime.now()-start_time).total_seconds():.0f}秒")
    print(f"已保存: {out}")


if __name__ == "__main__":
    import numpy as np
    main()
