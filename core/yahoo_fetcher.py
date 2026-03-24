#!/usr/bin/env python3
"""
Yahoo Finance 数据获取模块 (通过VPN代理)
功能：获取股票分钟级数据，合并到现有数据库

使用方法：
    python yahoo_fetcher.py              # 获取所有股票
    python yahoo_fetcher.py 比亚迪       # 获取单只股票
    python yahoo_fetcher.py --merge     # 合并数据
"""
import os
import sys
import json
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta

# VPN 代理
PROXIES = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# 项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# A股代码转港股代码映射 (部分股票有港股)
A_TO_HK = {
    "sz002594": "1211.HK",   # 比亚迪
    "sh601012": "601012.HK", # 隆基绿能
    "sh600519": "600519.SH", # 贵州茅台 (A股)
    "sz000333": "03333.HK",  # 美的
    "sh600089": "600089.SH", # 特变电工 (A股)
    "sh600507": "600507.SH", # 长江电力 (A股)
    "sh600276": "600276.SH", # 恒瑞医药 (A股)
    "sh600585": "600585.SH", # 海螺水泥 (A股)
    "sh600436": "600436.SH", # 片仔癀 (A股)
}

# 股票配置
STOCKS = {
    "铜陵有色": {"code": "sz000630", "type": "A"},
    "天山铝业": {"code": "sz002532", "type": "A"},
    "神火股份": {"code": "sz000933", "type": "A"},
    "特变电工": {"code": "sh600089", "type": "A"},
    "水晶光电": {"code": "sz002273", "type": "A"},
    "立讯精密": {"code": "sz002475", "type": "A"},
    "歌尔股份": {"code": "sz002241", "type": "A"},
    "美的集团": {"code": "sz000333", "type": "A"},
    "徐工机械": {"code": "sz000425", "type": "A"},
    "海兴电力": {"code": "sh603556", "type": "A"},
    "三花智控": {"code": "sz002050", "type": "A"},
    "高能环境": {"code": "sh603588", "type": "A"},
    "中国核建": {"code": "sh601611", "type": "A"},
    "通富微电": {"code": "sz002156", "type": "A"},
    "日久光电": {"code": "sz003015", "type": "A"},
    "融发核电": {"code": "sz002366", "type": "A"},
    "新集能源": {"code": "sh601918", "type": "A"},
    "中曼石油": {"code": "sh603619", "type": "A"},
    "TCL中环": {"code": "sz002129", "type": "A"},
    "TCL科技": {"code": "sz000100", "type": "A"},
    "三七互娱": {"code": "sz002555", "type": "A"},
    "上峰水泥": {"code": "sz000887", "type": "A"},
    "东山精密": {"code": "sz002384", "type": "A"},
    "中兴通讯": {"code": "sz000063", "type": "A"},
    "中宠股份": {"code": "sz002891", "type": "A"},
    "中科创达": {"code": "sh600485", "type": "A"},
    "亿纬锂能": {"code": "sz300014", "type": "A"},
    "依依股份": {"code": "sz001215", "type": "A"},
    "兖矿能源": {"code": "sh600188", "type": "A"},
    "兴森科技": {"code": "sz002436", "type": "A"},
    "北摩高科": {"code": "sz002985", "type": "A"},
    "北新建材": {"code": "sz000786", "type": "A"},
    "北方稀土": {"code": "sh600111", "type": "A"},
    "华天科技": {"code": "sz002185", "type": "A"},
    "华阳集团": {"code": "sz002821", "type": "A"},
    "安宁股份": {"code": "sz002755", "type": "A"},
    "宝武镁业": {"code": "sz002756", "type": "A"},
    "恒瑞医药": {"code": "sh600276", "type": "A"},
    "恺英网络": {"code": "sz002517", "type": "A"},
    "新希望": {"code": "sz000876", "type": "A"},
    "方大炭素": {"code": "sh600516", "type": "A"},
    "晶澳科技": {"code": "sz002459", "type": "A"},
    "欧菲光": {"code": "sz002456", "type": "A"},
    "比亚迪": {"code": "sz002594", "type": "HK", "hk_code": "1211.HK"},
    "比音勒芬": {"code": "sz002832", "type": "A"},
    "汉钟精机": {"code": "sh601158", "type": "A"},
    "江淮汽车": {"code": "sh600418", "type": "A"},
    "浙江世宝": {"code": "sz002703", "type": "A"},
    "浙江医药": {"code": "sz002163", "type": "A"},
    "海螺水泥": {"code": "sh600585", "type": "A"},
    "润贝航科": {"code": "sz001215", "type": "A"},
    "滨江集团": {"code": "sz002244", "type": "A"},
    "漫步者": {"code": "sz002351", "type": "A"},
    "片仔癀": {"code": "sh600436", "type": "A"},
    "牧原股份": {"code": "sz002714", "type": "A"},
    "珠江啤酒": {"code": "sz000858", "type": "A"},
    "申通快递": {"code": "sz002468", "type": "A"},
    "百利电气": {"code": "sh600292", "type": "A"},
    "维远股份": {"code": "sh600300", "type": "A"},
    "贵州茅台": {"code": "sh600519", "type": "A"},
    "长江电力": {"code": "sh600507", "type": "A"},
    "阳光电源": {"code": "sz300274", "type": "A"},
    "隆基绿能": {"code": "sh601012", "type": "HK", "hk_code": "601012.HK"},
    "东方电缆": {"code": "sh601606", "type": "A"},
    "国电南瑞": {"code": "sh600406", "type": "A"},
    "华友钴业": {"code": "sh603799", "type": "A"},
    "中际联合": {"code": "sh601305", "type": "A"},
    "中闽能源": {"code": "sh600163", "type": "A"},
}


def get_yahoo_symbol(code, stock_type, hk_code=None):
    """转换为Yahoo Finance股票代码"""
    if stock_type == "HK" and hk_code:
        return hk_code
    # A股: sz000630 -> 000630.SZ, sh600089 -> 600089.SH
    return f"{code[2:]}.{'SZ' if code.startswith('sz') else 'SH'}"


def fetch_minute_data(yahoo_symbol, interval="1m", days=7):
    """获取分钟级数据"""
    period1 = int(time.time()) - 86400 * days
    period2 = int(time.time())
    
    # Yahoo Finance API
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    params = {
        "period1": period1,
        "period2": period2,
        "interval": interval
    }
    
    for attempt in range(3):
        try:
            time.sleep(random.uniform(0.5, 1.5))
            resp = requests.get(url, params=params, proxies=PROXIES, 
                              headers=HEADERS, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                result = data.get('chart', {}).get('result', [])
                
                if result and result[0].get('timestamp'):
                    timestamps = result[0]['timestamp']
                    ohlc = result[0]['indicators']['quote'][0]
                    
                    # 构建DataFrame
                    df_data = []
                    for i in range(len(timestamps)):
                        ts = timestamps[i]
                        o = ohlc['open'][i] if ohlc['open'][i] else None
                        h = ohlc['high'][i] if ohlc['high'][i] else None
                        l = ohlc['low'][i] if ohlc['low'][i] else None
                        c = ohlc['close'][i] if ohlc['close'][i] else None
                        v = ohlc.get('volume', [None]*len(timestamps))[i]
                        
                        if o and h and l and c:
                            df_data.append({
                                'day': datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                                'open': o,
                                'high': h,
                                'low': l,
                                'close': c,
                                'volume': v if v else 0
                            })
                    
                    if df_data:
                        return pd.DataFrame(df_data)
            
            elif resp.status_code == 429:
                # 被限流，等待后重试
                time.sleep(random.uniform(3, 7))
                continue
                
        except Exception as e:
            print(f"  错误: {e}")
            time.sleep(1)
    
    return None


def merge_to_db(symbol, code, new_df, period="1m"):
    """合并数据到数据库"""
    if new_df is None or len(new_df) == 0:
        return 0
    
    # 使用正确的文件名格式: 比亚迪_sz002594_min1.csv
    os.makedirs(DATA_DIR, exist_ok=True)
    db_file = os.path.join(DATA_DIR, f"{symbol}_{code}_{period}.csv")
    
    # 确保日期格式
    new_df['day'] = pd.to_datetime(new_df['day'])
    
    if os.path.exists(db_file):
        # 读取现有数据
        old_df = pd.read_csv(db_file)
        old_df['day'] = pd.to_datetime(old_df['day'])
        
        # 合并并去重
        combined = pd.concat([old_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=['day'], keep='last')
        combined = combined.sort_values('day').reset_index(drop=True)
        
        # 保存
        combined.to_csv(db_file, index=False, encoding='utf-8')
        return len(combined) - len(old_df)
    else:
        # 新建文件
        new_df = new_df.sort_values('day').reset_index(drop=True)
        new_df.to_csv(db_file, index=False, encoding='utf-8')
        return len(new_df)


def update_stock(symbol, info, interval="1m", days=7):
    """更新单只股票"""
    code = info['code']
    stock_type = info.get('type', 'A')
    hk_code = info.get('hk_code')
    
    yahoo_symbol = get_yahoo_symbol(code, stock_type, hk_code)
    print(f"获取 {symbol} ({yahoo_symbol})...")
    
    df = fetch_minute_data(yahoo_symbol, interval=interval, days=days)
    
    if df is not None and len(df) > 0:
        # 过滤盘后数据 (14:57之后)
        df['day'] = pd.to_datetime(df['day'])
        df['hour'] = df['day'].dt.hour
        df['minute'] = df['day'].dt.minute
        df = df[(df['hour'] < 15) | ((df['hour'] == 14) & (df['minute'] <= 57))]
        df = df.drop(['hour', 'minute'], axis=1)
        
        # 合并到数据库
        added = merge_to_db(symbol, code, df, period=interval)
        print(f"  ✓ {symbol}: 获取 {len(df)} 条，新增 {added} 条")
        return len(df)
    else:
        print(f"  ✗ {symbol}: 无数据")
        return 0


def update_all_stocks(interval="1m", days=7):
    """更新所有股票"""
    print(f"\n=== 获取所有股票 {interval} 数据 ({days}天) ===\n")
    
    results = {}
    for symbol, info in STOCKS.items():
        count = update_stock(symbol, info, interval=interval, days=days)
        results[symbol] = count
        time.sleep(0.5)  # 避免请求过快
    
    # 统计
    success = sum(1 for v in results.values() if v > 0)
    print(f"\n=== 完成: {success}/{len(STOCKS)} 只股票有数据 ===")
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Yahoo Finance 数据获取')
    parser.add_argument('stock', nargs='?', help='股票名称 (可选)')
    parser.add_argument('--interval', '-i', default='1m', help='数据周期: 1m, 5m, 15m, 1h')
    parser.add_argument('--days', '-d', type=int, default=7, help='获取天数')
    
    args = parser.parse_args()
    
    if args.stock:
        # 更新单只股票
        if args.stock in STOCKS:
            update_stock(args.stock, STOCKS[args.stock], interval=args.interval, days=args.days)
        else:
            print(f"未找到股票: {args.stock}")
            print(f"可用股票: {', '.join(STOCKS.keys())}")
    else:
        # 更新所有
        update_all_stocks(interval=args.interval, days=args.days)
