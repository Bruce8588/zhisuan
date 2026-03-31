#!/usr/bin/env python3
"""
TD9策略回测 - 20%仓位，5只满仓，止损6%止盈20%
回测范围：2020-2026
"""
import os, sys, pandas as pd, numpy as np
from datetime import datetime, timedelta
from glob import glob
from collections import defaultdict

BASE = "/Users/isenfengming/.openclaw/workspace/工作台/智算"

# 数据路径
TREND_DIR_2020 = os.path.join(BASE, "output_daily_2015_2024", "趋势判断")  # 2015-2024
IND_DIR_2020 = os.path.join(BASE, "data_daily_indicators_2015_2024")  # 2015-2024
TREND_DIR_2025 = os.path.join(BASE, "output_daily_2025", "趋势判断")  # 2025
IND_DIR_2025 = os.path.join(BASE, "data_daily_indicators")  # 2025

# 参数
POSITION_SIZE = 0.20  # 20%仓位
MAX_POSITIONS = 5     # 最多5只
STOP_LOSS = 0.94      # 止损6%
TAKE_PROFIT = 1.20   # 止盈20%
MAX_HOLDING = 8       # 最多持有8天
START_YEAR = 2020      # 回测开始年份


def load_data_2020(code):
    """加载2020-2024数据"""
    trend_file = os.path.join(TREND_DIR_2020, f"{code}_趋势判断.csv")
    ind_file = os.path.join(IND_DIR_2020, f"{code}_indicators.csv")
    if not os.path.exists(trend_file) or not os.path.exists(ind_file):
        return None
    try:
        df_t = pd.read_csv(trend_file)
        df_t['时间'] = pd.to_datetime(df_t['时间'])
        df_t = df_t[df_t['时间'].dt.year >= START_YEAR]  # 只取2020年之后的
        df_t = df_t.sort_values('时间').reset_index(drop=True)
        
        df_i = pd.read_csv(ind_file)
        df_i['day'] = pd.to_datetime(df_i['day'])
        df_i = df_i[df_i['day'].dt.year >= START_YEAR]
        df_i = df_i.sort_values('day').reset_index(drop=True)
        
        result = df_t[['时间', '当前价格', '趋势代码', 'n_low']].copy()
        result = result.merge(df_i[['day', 'TD_Buy_Count']], left_on='时间', right_on='day', how='left')
        result.drop('day', axis=1, inplace=True)
        return result
    except:
        return None


def load_data_2025(code):
    """加载2025数据"""
    trend_file = os.path.join(TREND_DIR_2025, f"{code}_趋势判断.csv")
    ind_file = os.path.join(IND_DIR_2025, f"{code}_indicators.csv")
    if not os.path.exists(trend_file) or not os.path.exists(ind_file):
        return None
    try:
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
    except:
        return None


def backtest_strategy(df, initial_capital=100000):
    """TD9策略回测 - 带仓位管理"""
    if df is None or len(df) < MAX_HOLDING:
        return None
    
    trades = []
    cash = initial_capital
    positions = {}  # {持仓ID: {entry_price, entry_date, days_held, code}}
    position_id = 0
    
    for i in range(len(df) - 1):
        row = df.iloc[i]
        current_date = row['时间']
        
        # 检查持仓是否到期或触发止损/止盈
        positions_to_close = []
        for pid, pos in positions.items():
            days_held = (current_date - pos['entry_date']).days
            if days_held >= MAX_HOLDING:
                # 到期卖出
                exit_price = row['当前价格']
                ret = (exit_price - pos['entry_price']) / pos['entry_price']
                trades.append({
                    'code': pos['code'],
                    'entry_date': pos['entry_date'],
                    'exit_date': current_date,
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'return': ret,
                    'holding_days': days_held,
                    'result': 'expired'
                })
                cash *= (1 + ret * POSITION_SIZE)
                positions_to_close.append(pid)
            else:
                # 检查止损/止盈
                exit_price = row['当前价格']
                if exit_price <= pos['entry_price'] * STOP_LOSS:
                    # 止损
                    ret = -0.06
                    trades.append({
                        'code': pos['code'],
                        'entry_date': pos['entry_date'],
                        'exit_date': current_date,
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'return': ret,
                        'holding_days': days_held,
                        'result': 'stop_loss'
                    })
                    cash *= (1 + ret * POSITION_SIZE)
                    positions_to_close.append(pid)
                elif exit_price >= pos['entry_price'] * TAKE_PROFIT:
                    # 止盈
                    ret = 0.20
                    trades.append({
                        'code': pos['code'],
                        'entry_date': pos['entry_date'],
                        'exit_date': current_date,
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'return': ret,
                        'holding_days': days_held,
                        'result': 'take_profit'
                    })
                    cash *= (1 + ret * POSITION_SIZE)
                    positions_to_close.append(pid)
        
        # 移除已平仓的持仓
        for pid in positions_to_close:
            del positions[pid]
        
        # 检查是否有新信号
        if row['趋势代码'] == 'up_natural':
            if pd.notna(row.get('TD_Buy_Count')) and row['TD_Buy_Count'] == 9:
                if len(positions) < MAX_POSITIONS:
                    # 未满仓，可以买入
                    entry_price = row['当前价格']
                    stop_loss = row['n_low']
                    if pd.notna(stop_loss):
                        # 记录持仓
                        positions[position_id] = {
                            'entry_price': entry_price,
                            'entry_date': current_date,
                            'days_held': 0,
                            'code': df.iloc[i].name
                        }
                        position_id += 1
    
    # 平掉所有剩余持仓（用最后一天的价格）
    if positions and len(df) > 0:
        last_row = df.iloc[-1]
        for pid, pos in positions.items():
            exit_price = last_row['当前价格']
            days_held = (last_row['时间'] - pos['entry_date']).days
            ret = (exit_price - pos['entry_price']) / pos['entry_price']
            # 实际执行止损/止盈检查
            if exit_price <= pos['entry_price'] * STOP_LOSS:
                ret = -0.06
                result = 'stop_loss'
            elif exit_price >= pos['entry_price'] * TAKE_PROFIT:
                ret = 0.20
                result = 'take_profit'
            else:
                result = 'end_backtest'
            trades.append({
                'code': pos['code'],
                'entry_date': pos['entry_date'],
                'exit_date': last_row['时间'],
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'return': ret,
                'holding_days': days_held,
                'result': result
            })
            cash *= (1 + ret * POSITION_SIZE)
    
    return {
        'trades': trades,
        'final_capital': cash,
        'total_return': (cash - initial_capital) / initial_capital
    }


def main():
    start_time = datetime.now()
    print(f"=" * 60)
    print(f"TD9策略回测 - 参数配置")
    print(f"=" * 60)
    print(f"仓位: {POSITION_SIZE*100}%")
    print(f"最大持仓: {MAX_POSITIONS}只")
    print(f"止损: {STOP_LOSS*100}%")
    print(f"止盈: {TAKE_PROFIT*100}%")
    print(f"最大持有: {MAX_HOLDING}天")
    print(f"回测区间: {START_YEAR}-2026")
    print(f"=" * 60)
    
    # 统计各年份
    yearly_results = defaultdict(lambda: {'trades': [], 'total_return': 0})
    
    # 获取股票列表（用2020-2024的趋势文件）
    files = sorted(glob(os.path.join(TREND_DIR_2020, "*_趋势判断.csv")))
    print(f"\n开始回测... ({len(files)} 只股票)")
    
    all_trades = []
    skip_count = 0
    
    for i, f in enumerate(files):
        code = os.path.basename(f).replace("_趋势判断.csv", "")
        
        # 加载2020-2024数据
        df_2020 = load_data_2020(code)
        # 加载2025数据
        df_2025 = load_data_2025(code)
        
        if df_2020 is not None:
            result = backtest_strategy(df_2020)
            if result:
                all_trades.extend(result['trades'])
        
        if df_2025 is not None:
            result = backtest_strategy(df_2025)
            if result:
                all_trades.extend(result['trades'])
        
        if (i + 1) % 500 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"进度: {i+1}/{len(files)} | 信号: {len(all_trades)} | {elapsed:.0f}秒")
    
    print(f"\n完成! 耗时: {(datetime.now()-start_time).total_seconds():.0f}秒")
    
    if not all_trades:
        print("无交易记录")
        return
    
    # 分析结果
    df_trades = pd.DataFrame(all_trades)
    
    print(f"\n{'=' * 60}")
    print(f"回测结果汇总")
    print(f"{'=' * 60}")
    print(f"总交易次数: {len(df_trades)}")
    print(f"止损次数: {(df_trades['result'] == 'stop_loss').sum()}")
    print(f"止盈次数: {(df_trades['result'] == 'take_profit').sum()}")
    print(f"到期卖出: {(df_trades['result'] == 'expired').sum()}")
    
    # 计算胜率
    winning = (df_trades['return'] > 0).sum()
    losing = (df_trades['return'] < 0).sum()
    print(f"胜率: {winning/len(df_trades)*100:.1f}%")
    
    # 年化收益（简化估算）
    years = 6  # 2020-2026
    total_return = df_trades['return'].sum() * POSITION_SIZE
    cagr = ((1 + total_return) ** (1/years) - 1) * 100
    print(f"累计收益: {total_return*100:.1f}%")
    print(f"简化年化收益: ~{cagr:.1f}%")
    
    # 按年份统计
    print(f"\n{'=' * 60}")
    print(f"年度表现")
    print(f"{'=' * 60}")
    df_trades['year'] = pd.to_datetime(df_trades['entry_date']).dt.year
    for year in sorted(df_trades['year'].unique()):
        year_data = df_trades[df_trades['year'] == year]
        yr_return = year_data['return'].mean() * 100
        yr_count = len(year_data)
        yr_winrate = (year_data['return'] > 0).sum() / yr_count * 100
        print(f"{year}年: {yr_count}笔交易, 胜率{yr_winrate:.1f}%, 平均收益{yr_return:+.2f}%")
    
    # 保存结果
    output_dir = os.path.join(BASE, "output", "回测结果")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "TD9_20pct_5pos_6sl_20tp_2020_2026.csv")
    df_trades.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n详细结果已保存: {output_file}")


if __name__ == "__main__":
    main()
