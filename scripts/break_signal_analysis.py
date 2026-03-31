"""
break_signal_analysis.py
研究：down_break（破底翻）vs up_break（破顶翻）后的持有收益对比

持有期：1、5、10、20、30个交易日
信号定义：
  - 买入信号(down_break)：前一天是down/down_secondary/down_rally，当天转为up
  - 卖出信号(up_break)：前一天是up/up_secondary/up_rally，当天转为down
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import sys
import time
warnings.filterwarnings('ignore')

# 路径配置
DATA_DIR = Path("/Users/isenfengming/.openclaw/workspace/工作台/量化系统/智算/output_daily_2015_2024/趋势判断")
OUTPUT_DIR = Path("/Users/isenfengming/.openclaw/workspace/工作台/量化系统/智算/output_break_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 自选股列表（81只）
SELECTED_STOCKS = {
    "000630", "002532", "000933", "600089", "002273", "002475", "002241", "000333",
    "000425", "603556", "002050", "603588", "601611", "002156", "003015", "002366",
    "601918", "603619", "002129", "000100", "002555", "000887", "002384", "000063",
    "002891", "300496", "300014", "001215", "600188", "002436", "002985", "000786",
    "600111", "002185", "002821", "002755", "002756", "600276", "002517", "000876",
    "600516", "002459", "002456", "002594", "002832", "601158", "600418", "002703",
    "002163", "600585", "001896", "002244", "002351", "600436", "002714", "000858",
    "002468", "600292", "600300", "600519", "600507", "300274", "601012", "601606",
    "600406", "603799", "605305", "600163", "600104", "603156", "002373", "688196",
    "600066", "603170", "002920", "600756", "603288", "000792", "002036", "601127",
    "002637"
}

# 持有期
HOLDING_PERIODS = [1, 5, 10, 20, 30]

# 下跌趋势相关状态（转为up意味着break）
DOWN_STATES = {'down', 'down_secondary', 'down_rally'}
# 上涨趋势相关状态（转为down意味着break）
UP_STATES = {'up', 'up_secondary', 'up_rally'}


def load_stock_data(stock_file: Path) -> pd.DataFrame:
    """加载单只股票的趋势数据"""
    df = pd.read_csv(stock_file)
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间').reset_index(drop=True)
    return df


def detect_break_signals(df: pd.DataFrame) -> tuple:
    """
    检测刚进入趋势的信号
    
    买入信号：趋势变为 up（刚进入上升趋势）→ 做多
    卖出信号：趋势变为 down（刚进入下跌趋势）→ 做空
    
    Returns:
        (buy_signals, sell_signals): 两个DataFrame，包含信号日期和价格
    """
    buy_signals = []  # 进入up -> 买入(做多)
    sell_signals = []  # 进入down -> 卖出(做空)
    
    for i in range(1, len(df)):
        prev_state = df.iloc[i-1]['趋势代码']
        curr_state = df.iloc[i]['趋势代码']
        
        # 买入信号：刚进入上升趋势
        if curr_state == 'up' and prev_state != 'up':
            buy_signals.append({
                '日期': df.iloc[i]['时间'],
                '价格': df.iloc[i]['当前价格'],
                '信号类型': '进入up',
                '前一状态': prev_state,
                '方向': '做多'
            })
        
        # 卖出信号：刚进入下跌趋势
        elif curr_state == 'down' and prev_state != 'down':
            sell_signals.append({
                '日期': df.iloc[i]['时间'],
                '价格': df.iloc[i]['当前价格'],
                '信号类型': '进入down',
                '前一状态': prev_state,
                '方向': '做空'
            })
    
    return pd.DataFrame(buy_signals), pd.DataFrame(sell_signals)


def calculate_holding_returns(df: pd.DataFrame, signals: pd.DataFrame, holding_periods: list) -> pd.DataFrame:
    """
    计算信号发生后固定持有期的收益
    
    Args:
        df: 股票完整数据
        signals: 信号列表（日期、价格、方向）
        holding_periods: 持有期列表
    
    Returns:
        收益DataFrame，每行一个信号，包含各持有期收益
    """
    if signals.empty:
        return pd.DataFrame()
    
    returns_list = []
    
    for _, signal in signals.iterrows():
        signal_date = signal['日期']
        entry_price = signal['价格']
        direction = signal.get('方向', '做多')  # 默认做多
        is_short = (direction == '做空')
        
        # 找到信号发生后第N个交易日的价格
        signal_idx = df[df['时间'] == signal_date].index
        if len(signal_idx) == 0:
            continue
        signal_idx = signal_idx[0]
        
        row_returns = {'信号日期': signal_date, '入场价格': entry_price, '方向': direction}
        
        for n in holding_periods:
            target_idx = signal_idx + n
            
            # 超出数据范围
            if target_idx >= len(df):
                row_returns[f'持有{n}日收益'] = np.nan
                row_returns[f'持有{n}日涨跌幅'] = np.nan
                continue
            
            end_price = df.iloc[target_idx]['当前价格']
            
            # 计算涨跌幅
            change_pct = (end_price - entry_price) / entry_price * 100
            
            # 如果是做空，取反
            if is_short:
                change_pct = -change_pct
            
            row_returns[f'持有{n}日涨跌幅'] = change_pct
        
        returns_list.append(row_returns)
    
    return pd.DataFrame(returns_list)


def analyze_all_stocks():
    """分析自选股"""
    all_buy_returns = []
    all_sell_returns = []
    
    stock_files = list(DATA_DIR.glob("*_趋势判断.csv"))
    print(f"找到 {len(stock_files)} 只股票，筛选自选股 {len(SELECTED_STOCKS)} 只")
    
    filtered_files = [f for f in stock_files if any(s in f.name for s in SELECTED_STOCKS)]
    print(f"匹配到 {len(filtered_files)} 只自选股")
    
    processed = 0
    for stock_file in filtered_files:
        processed += 1
        if processed % 20 == 0:
            print(f"进度: {processed}/{len(filtered_files)}")
        
        df = load_stock_data(stock_file)
        
        # 检测信号
        buy_signals, sell_signals = detect_break_signals(df)
        
        # 计算收益
        if not buy_signals.empty:
            buy_returns = calculate_holding_returns(df, buy_signals, HOLDING_PERIODS)
            if not buy_returns.empty:
                buy_returns['股票代码'] = stock_file.stem.replace('_趋势判断', '')
                all_buy_returns.append(buy_returns)
        
        if not sell_signals.empty:
            sell_returns = calculate_holding_returns(df, sell_signals, HOLDING_PERIODS)
            if not sell_returns.empty:
                sell_returns['股票代码'] = stock_file.stem.replace('_趋势判断', '')
                all_sell_returns.append(sell_returns)
    
    # 合并所有股票
    if all_buy_returns:
        buy_df = pd.concat(all_buy_returns, ignore_index=True)
    else:
        buy_df = pd.DataFrame()
    
    if all_sell_returns:
        sell_df = pd.concat(all_sell_returns, ignore_index=True)
    else:
        sell_df = pd.DataFrame()
    
    return buy_df, sell_df


def summarize_results(buy_df: pd.DataFrame, sell_df: pd.DataFrame):
    """汇总统计"""
    print("\n" + "="*60)
    print("【买入信号(刚进入上升趋势)收益统计】")
    print("="*60)
    print(f"样本数量: {len(buy_df)}")
    
    for n in HOLDING_PERIODS:
        col = f'持有{n}日涨跌幅'
        if col in buy_df.columns:
            valid = buy_df[col].dropna()
            if len(valid) > 0:
                print(f"\n持有{n}日 ({len(valid)}个有效样本):")
                print(f"  平均收益: {valid.mean():.2f}%")
                print(f"  中位数: {valid.median():.2f}%")
                print(f"  上涨概率: {(valid > 0).mean()*100:.1f}%")
                print(f"  最大涨幅: {valid.max():.2f}%")
                print(f"  最大跌幅: {valid.min():.2f}%")
                print(f"  标准差: {valid.std():.2f}%")
    
    print("\n" + "="*60)
    print("【卖出信号(刚进入下跌趋势)收益统计 - 做空】")
    print("="*60)
    print(f"样本数量: {len(sell_df)}")
    
    for n in HOLDING_PERIODS:
        col = f'持有{n}日涨跌幅'
        if col in sell_df.columns:
            valid = sell_df[col].dropna()
            if len(valid) > 0:
                print(f"\n持有{n}日 ({len(valid)}个有效样本):")
                print(f"  平均做空收益: {valid.mean():.2f}%")
                print(f"  中位数: {valid.median():.2f}%")
                print(f"  正收益概率(做空赚钱): {(valid > 0).mean()*100:.1f}%")
                print(f"  最大涨幅(做空亏损): {valid.max():.2f}%")
                print(f"  最大跌幅(做空盈利): {valid.min():.2f}%")
                print(f"  标准差: {valid.std():.2f}%")


def main():
    print("开始分析【刚进入上升趋势】vs【刚进入下跌趋势】的收益对比...")
    print(f"数据目录: {DATA_DIR}")
    print(f"持有期: {HOLDING_PERIODS}")
    
    # 分析所有股票
    buy_df, sell_df = analyze_all_stocks()
    
    # 保存原始数据
    if not buy_df.empty:
        buy_df.to_csv(OUTPUT_DIR / "进入up买入信号收益.csv", index=False)
        print(f"\n买入信号数据已保存: {OUTPUT_DIR / '进入up买入信号收益.csv'}")
    
    if not sell_df.empty:
        sell_df.to_csv(OUTPUT_DIR / "进入down卖出信号收益.csv", index=False)
        print(f"卖出信号数据已保存: {OUTPUT_DIR / '进入down卖出信号收益.csv'}")
    
    # 汇总统计
    summarize_results(buy_df, sell_df)
    
    # 保存统计摘要
    summary_data = []
    for n in HOLDING_PERIODS:
        col = f'持有{n}日涨跌幅'
        row = {'持有期': f'{n}日'}
        
        if not buy_df.empty and col in buy_df.columns:
            valid = buy_df[col].dropna()
            if len(valid) > 0:
                row['买入信号_平均收益'] = round(valid.mean(), 2)
                row['买入信号_上涨概率'] = round((valid > 0).mean()*100, 1)
                row['买入信号_样本数'] = len(valid)
        
        if not sell_df.empty and col in sell_df.columns:
            valid = sell_df[col].dropna()
            if len(valid) > 0:
                row['卖出信号_平均收益'] = round(valid.mean(), 2)
                row['卖出信号_上涨概率'] = round((valid > 0).mean()*100, 1)
                row['卖出信号_样本数'] = len(valid)
        
        summary_data.append(row)
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(OUTPUT_DIR / "趋势进入信号收益对比摘要.csv", index=False)
    print(f"\n摘要已保存: {OUTPUT_DIR / '趋势进入信号收益对比摘要.csv'}")
    
    print("\n✅ 分析完成！")


if __name__ == "__main__":
    main()
