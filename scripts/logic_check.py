#!/usr/bin/env python3.11
"""
趋势逻辑检查程序
功能：对比人类判断和程序判断，验证趋势判断逻辑是否正确
"""
import os
import sys
import pandas as pd
from datetime import datetime

BASE_DIR = "/home/admin/.openclaw/workspace/quant_v2"
sys.path.insert(0, BASE_DIR)

from config.stocks import POOL_A


# 正确趋势（指定日期的趋势）
CORRECT_JUDGMENT = {
    # 2026年3月6日正确趋势
    "2026-03-06": {
        "铜陵有色": "up_secondary",
        "天山铝业": "up_natural",
        "神火股份": "down_rally",
        "特变电工": "up",
        "水晶光电": "up_rally",
        "立讯精密": "down",
        "歌尔股份": "down",
        "美的集团": "up_secondary",
        "徐工机械": "up_natural",
        "海兴电力": "up",
        "三花智控": "down",
        "高能环境": "up",
        "中国核建": "up",
        "通富微电": "down_secondary",
        "日久光电": "up",
    },
    # 2026年3月10日正确趋势
    "2026-03-10": {
        "铜陵有色": "up_secondary",
        "天山铝业": "up_break",
        "神火股份": "down_rally",
        "特变电工": "up",
        "水晶光电": "down_natural",
        "立讯精密": "down_natural",
        "歌尔股份": "down",
        "美的集团": "up_secondary",
        "徐工机械": "up_rally",
        "海兴电力": "up",
        "三花智控": "down_natural",
        "高能环境": "up",
        "中国核建": "up",
        "通富微电": "down_natural",
        "日久光电": "up_natural",
    },
}

TREND_NAMES = {
    "up": "上升趋势",
    "up_natural": "自然回撤",
    "up_rally": "回升",
    "up_secondary": "次级回撤",
    "up_break": "破碎",
    "down": "下跌趋势",
    "down_natural": "自然回升",
    "down_rally": "回撤",
    "down_secondary": "次级回升",
    "down_break": "破碎",
}


def check_trend(stock_name, info, check_date):
    """检查单只股票在指定日期的趋势"""
    code = info["code"]
    trend_file = os.path.join(BASE_DIR, "output", "趋势判断", f"{stock_name}_趋势判断.csv")
    
    if not os.path.exists(trend_file):
        return None, "趋势判断文件不存在"
    
    # 读取趋势数据
    df = pd.read_csv(trend_file)
    df["时间"] = pd.to_datetime(df["时间"])
    
    # 筛选指定日期的数据
    check_dt = pd.to_datetime(check_date)
    df_check = df[df["时间"].dt.date == check_dt.date()]
    
    if len(df_check) == 0:
        return None, f"无{check_date}数据"
    
    # 取当天最后一个趋势
    latest = df_check.iloc[-1]
    return latest["趋势代码"], None


def run_check(check_date="2026-03-06"):
    """运行逻辑检查"""
    print("=" * 60)
    print(f"趋势逻辑检查 - {check_date}")
    print("=" * 60)
    
    # 获取对应日期的正确趋势
    if check_date in CORRECT_JUDGMENT:
        correct_trends = CORRECT_JUDGMENT[check_date]
    else:
        print(f"错误: 没有 {check_date} 的正确趋势数据")
        return
    
    results = []
    correct = 0
    wrong = 0
    
    for stock_name, info in POOL_A.items():
        if stock_name not in correct_trends:
            continue
        
        program_trend, error = check_trend(stock_name, info, check_date)
        correct_trend = correct_trends[stock_name]
        
        if error:
            print(f"  {stock_name}: {error}")
            results.append({
                "股票": stock_name,
                "正确趋势": correct_trend,
                "程序趋势": "错误",
                "一致": "❌"
            })
            wrong += 1
            continue
        
        is_correct = program_trend == correct_trend
        match = "✅" if is_correct else "❌"
        
        if is_correct:
            correct += 1
        else:
            wrong += 1
        
        results.append({
            "股票": stock_name,
            "正确趋势": correct_trend,
            "程序趋势": program_trend,
            "一致": match
        })
        
        print(f"  {stock_name}: 正确={correct_trend}, 程序={program_trend} {match}")
    
    print()
    print(f"一致: {correct}/{len(results)} ({correct/len(results)*100:.0f}%)")
    print(f"不一致: {wrong}/{len(results)}")
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-03-06", help="检查日期")
    args = parser.parse_args()
    
    run_check(args.date)
