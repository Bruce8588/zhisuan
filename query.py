#!/usr/bin/env python3
"""
股票趋势查询工具
用法：
    python query.py 股票名称           # 查询单只股票
    python query.py --all             # 查询所有股票
    python query.py --stock TCL中环   # 指定股票（别名）
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime

# 添加项目根目录（智算目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS
from config.rules import TREND_NAMES, RALLY_THRESHOLD, PULLBACK_THRESHOLD
from core.trend import TrendAnalyzer
from core.fetcher_ifind import IFinDFetcher

# 输出目录
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "趋势判断")


def get_market(code):
    """根据代码判断市场"""
    code_clean = code.replace('sz', '').replace('sh', '').replace('SZ', '').replace('SH', '')
    if code_clean.startswith('6'):
        return 'SH'
    else:
        return 'SZ'


def get_latest_from_csv(symbol, code):
    """从趋势判断CSV获取最新数据"""
    trend_file = os.path.join(OUTPUT_DIR, f"{symbol}_趋势判断.csv")
    if os.path.exists(trend_file):
        df = pd.read_csv(trend_file)
        if len(df) > 0:
            return df.iloc[-1]
    return None


def get_trend_description(trend_code, price, state):
    """生成趋势解读"""
    if trend_code == "up":
        return f"价格处于上升趋势，key_high={state.get('key_high')}，等待回调后买入机会"
    elif trend_code == "up_natural":
        n_low = state.get('n_low') or price * 0.98
        return f"自然回撤中，n_low={n_low:.2f}，关注是否止跌"
    elif trend_code == "up_rally":
        rally_high = state.get('rally_high') or price * 1.02
        return f"回升阶段，rally_high={rally_high:.2f}，关注能否突破"
    elif trend_code == "up_secondary":
        secondary_low = state.get('secondary_low') or price * 0.96
        return f"次级回撤，secondary_low={secondary_low:.2f}，等待回升信号"
    elif trend_code == "up_break":
        break_low = state.get('break_low') or price * 0.95
        return f"关键支撑{break_low:.2f}已破，注意风险"
    elif trend_code == "down":
        key_low = state.get('key_low') or price * 0.9
        return f"下跌趋势，key_low={key_low:.2f}，等待止跌信号"
    elif trend_code == "down_natural":
        n_high = state.get('n_high') or price * 1.05
        return f"自然回升中，n_high={n_high:.2f}，关注是否突破"
    elif trend_code == "down_rally":
        rally_low = state.get('rally_low') or price * 0.97
        return f"回撤阶段，rally_low={rally_low:.2f}，注意风险"
    elif trend_code == "down_secondary":
        secondary_high = state.get('secondary_high') or price * 1.03
        return f"次级回升，secondary_high={secondary_high:.2f}，关注能否突破"
    elif trend_code == "down_break":
        break_high = state.get('break_high') or price * 1.05
        return f"突破关键阻力{break_high:.2f}，趋势可能反转"
    return "趋势未确定"


def query_stock(symbol, info, fetch_new=False):
    """查询单只股票"""
    code = info["code"]
    stock_code_ifind = IFinDFetcher()._convert_code(code)
    
    # 尝试从CSV获取最新趋势
    latest = get_latest_from_csv(symbol, code)
    
    # 如果需要获取新数据
    if fetch_new or latest is None:
        try:
            print(f"正在获取 {symbol} 最新数据...")
            fetcher = IFinDFetcher()
            df = fetcher.get_minute_data(stock_code_ifind, days=1)
            
            if df is not None and len(df) > 0:
                # 运行趋势分析
                analyzer = TrendAnalyzer()
                result = analyzer.analyze_stock(symbol, info)
                if result is not None and len(result) > 0:
                    latest = result.iloc[-1]
        except Exception as e:
            print(f"获取数据失败: {e}")
    
    # 如果有最新数据
    if latest is not None:
        price = float(latest["当前价格"])
        trend_code = latest["趋势代码"]
        trend_name = latest["趋势名称"]
        
        state = {
            "key_high": latest.get("key_high"),
            "key_low": latest.get("key_low"),
            "n_low": latest.get("n_low"),
            "n_high": latest.get("n_high"),
            "rally_high": latest.get("rally_high"),
            "rally_low": latest.get("rally_low"),
            "secondary_low": latest.get("secondary_low"),
            "secondary_high": latest.get("secondary_high"),
            "break_low": latest.get("break_low"),
            "break_high": latest.get("break_high"),
        }
        
        market = get_market(code)
        desc = get_trend_description(trend_code, price, state)
        update_time = latest.get("时间", "未知")
        
        # 格式化输出
        def fmt(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return "无"
            return f"{v:.2f}"
        
        key_high = fmt(state['key_high'])
        key_low = fmt(state['key_low'])
        n_low = fmt(state['n_low'])
        n_high = fmt(state['n_high'])
        
        output = f"""
📊 {symbol}
├── 代码：{code}
├── 市场：{market}
├── 当前价格：¥{price:.2f}
├── 当前趋势：{trend_code}（{trend_name}）
├── 关键点：
│   ├── key_high：{key_high}
│   ├── key_low：{key_low}
│   └── n_low/n_high：{n_low} / {n_high}
└── 趋势解读：{desc}
└── 更新时间：{update_time}
"""
        return output.strip()
    else:
        return f"❌ {symbol}: 暂无趋势数据，请先运行数据获取"


def query_by_name(stock_name, fetch_new=False):
    """根据股票名称查询"""
    # 精确匹配
    if stock_name in ALL_STOCKS:
        info = ALL_STOCKS[stock_name]
        return query_stock(stock_name, info, fetch_new)
    
    # 模糊匹配
    matches = [k for k in ALL_STOCKS.keys() if stock_name in k]
    if len(matches) == 1:
        symbol = matches[0]
        info = ALL_STOCKS[symbol]
        return query_stock(symbol, info, fetch_new)
    elif len(matches) > 1:
        return f"❌ 匹配到多个股票: {', '.join(matches)}\n请输入更完整的名称"
    else:
        return f"❌ 未找到股票: {stock_name}"


def query_all():
    """查询所有股票"""
    results = []
    for symbol, info in ALL_STOCKS.items():
        latest = get_latest_from_csv(symbol, info["code"])
        if latest is not None:
            price = float(latest["当前价格"])
            trend_code = latest["趋势代码"]
            trend_name = latest["趋势名称"]
            results.append({
                "股票": symbol,
                "代码": info["code"],
                "价格": f"¥{price:.2f}",
                "趋势": trend_code,
                "趋势名称": trend_name
            })
    
    if results:
        df = pd.DataFrame(results)
        print("\n📈 股票趋势总览")
        print("=" * 70)
        print(df.to_string(index=False))
        print("=" * 70)
        return df
    else:
        print("❌ 暂无数据，请先运行数据获取")
        return None


def main():
    parser = argparse.ArgumentParser(description="股票趋势查询工具")
    parser.add_argument("stock_name", nargs="?", help="股票名称")
    parser.add_argument("--all", action="store_true", help="查询所有股票")
    parser.add_argument("--fetch", action="store_true", help="获取最新数据")
    args = parser.parse_args()
    
    if args.all:
        query_all()
    elif args.stock_name:
        result = query_by_name(args.stock_name, fetch_new=args.fetch)
        print(result)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
