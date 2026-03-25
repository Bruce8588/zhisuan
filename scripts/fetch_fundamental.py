#!/usr/bin/env python3
"""
基本面数据获取脚本
使用 iFinD HTTP API 获取股票基本面数据

功能：
- 市盈率 (PE TTM)
- 市净率 (PB)
- 总市值
- 流通市值
- 实时价格
- 涨跌幅
等

用法：
    python fetch_fundamental.py              # 获取所有股票基本面
    python fetch_fundamental.py --stock 神火股份  # 只获取单只股票
    python fetch_fundamental.py --scan       # 查看现有数据
"""
import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS

OUTPUT_DIR = os.path.join(BASE_DIR, "data_fundamental")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# iFinD API 配置
REFRESH_TOKEN = "eyJzaWduX3RpbWUiOiIyMDI2LTAzLTI0IDIxOjI2OjI4In0=.eyJ1aWQiOiI4NTU2ODc3MDciLCJ1c2VyIjp7InJlZnJlc2hUb2tlbkV4cGlyZWRUaW1lIjoiMjAyNi0wNC0yMyAxOTo0MDoyMCIsInVzZXJJZCI6Ijg1NTY2ODc3MDd9fQ==.E2C78E713CE0CDDE2E882969D4B4ABA0D3D266BA6284256BF7040C0A83273F0A"
TOKEN_URL = "https://quantapi.51ifind.com/api/v1/get_access_token"
RT_URL = "https://quantapi.51ifind.com/api/v1/real_time_quotation"


class FundamentalFetcher:
    """iFinD 基本面数据获取器"""
    
    def __init__(self, refresh_token=None):
        self.refresh_token = refresh_token or REFRESH_TOKEN
        self.access_token = None
        self.token_expire_time = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Content-Type': 'application/json',
        })
    
    def _get_access_token(self):
        """获取 access_token（自动管理token有效期）"""
        if self.access_token and self.token_expire_time:
            if datetime.now() < self.token_expire_time:
                return self.access_token
        
        try:
            resp = self.session.post(TOKEN_URL, json={"refresh_token": self.refresh_token}, timeout=15)
            result = resp.json()
            if result.get("errorcode") == 0:
                self.access_token = result["data"]["access_token"]
                # token有效期7天
                self.token_expire_time = datetime.now() + timedelta(days=7)
                print(f"✓ iFinD access_token 获取成功")
                return self.access_token
            else:
                print(f"✗ Token获取失败: {result.get('errmsg')}")
                return None
        except Exception as e:
            print(f"✗ Token请求失败: {e}")
            return None
    
    def _convert_code(self, code):
        """转换代码格式: sz000933 -> 000933.SZ"""
        code = code.lower().replace('sz', '').replace('sh', '')
        if len(code) == 6:
            if code.startswith('0') or code.startswith('3'):
                return f"{code}.SZ"
            elif code.startswith('6'):
                return f"{code}.SH"
        return code
    
    def fetch_single(self, symbol, code, retry=3):
        """获取单只股票基本面数据"""
        if not self._get_access_token():
            return None
        
        code_ifind = self._convert_code(code)
        
        params = {
            "codes": code_ifind,
            "indicators": "open,high,low,latest,change,changeRatio,volume,turnover,pe_ttm,pb,totalCapital,freeCapital",
        }
        
        headers = {
            "Content-Type": "application/json",
            "access_token": self.access_token
        }
        
        for attempt in range(retry):
            try:
                resp = self.session.post(RT_URL, json=params, headers=headers, timeout=15)
                result = resp.json()
                
                if result.get("errorcode") != 0:
                    if attempt < retry - 1:
                        time.sleep(1)
                        continue
                    print(f"  {symbol}: 获取失败 - {result.get('errmsg')}")
                    return None
                
                tables = result.get("tables", [])
                if not tables:
                    return None
                
                table = tables[0]
                data = table.get("table", {})
                
                # 提取数据
                return {
                    'symbol': symbol,
                    'code': code,
                    'code_ifind': code_ifind,
                    'name': symbol,  # iFinD不返回名称，用配置中的
                    'price': data.get('latest', [None])[0] if data.get('latest') else None,
                    'open': data.get('open', [None])[0] if data.get('open') else None,
                    'high': data.get('high', [None])[0] if data.get('high') else None,
                    'low': data.get('low', [None])[0] if data.get('low') else None,
                    'change': data.get('change', [None])[0] if data.get('change') else None,
                    'change_pct': data.get('changeRatio', [None])[0] if data.get('changeRatio') else None,
                    'volume': data.get('volume', [None])[0] if data.get('volume') else None,
                    'turnover': data.get('turnover', [None])[0] if data.get('turnover') else None,
                    'pe': data.get('pe_ttm', [None])[0] if data.get('pe_ttm') else None,
                    'pb': data.get('pb', [None])[0] if data.get('pb') else None,
                    'total_market': data.get('totalCapital', [None])[0] if data.get('totalCapital') else None,
                    'float_market': data.get('freeCapital', [None])[0] if data.get('freeCapital') else None,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
                
            except Exception as e:
                if attempt < retry - 1:
                    time.sleep(2)
                    continue
                print(f"  {symbol}: 错误 - {e}")
                return None
        
        return None
    
    def fetch_all(self, stocks=None, batch_size=20):
        """批量获取基本面数据"""
        if not self._get_access_token():
            return []
        
        target = stocks if stocks else ALL_STOCKS
        results = []
        total = len(target)
        
        print(f"\n获取 {total} 只股票基本面数据...")
        print("=" * 50)
        
        # 批量获取（每批20只）
        symbols = list(sorted(target.items()))
        
        for i in range(0, total, batch_size):
            batch = dict(symbols[i:i+batch_size])
            batch_results = self._fetch_batch(batch)
            results.extend(batch_results)
            
            progress = min(i + batch_size, total)
            print(f"  进度: {progress}/{total}")
        
        print(f"\n成功获取: {len(results)}/{total}")
        return results
    
    def _fetch_batch(self, stocks, retry=2):
        """批量获取一群股票"""
        codes = [self._convert_code(info['code']) for _, info in stocks.items()]
        codes_str = ",".join(codes)
        
        params = {
            "codes": codes_str,
            "indicators": "open,high,low,latest,change,changeRatio,volume,turnover,pe_ttm,pb,totalCapital,freeCapital",
        }
        
        headers = {
            "Content-Type": "application/json",
            "access_token": self.access_token
        }
        
        for attempt in range(retry):
            try:
                resp = self.session.post(RT_URL, json=params, headers=headers, timeout=30)
                result = resp.json()
                
                if result.get("errorcode") != 0:
                    if attempt < retry - 1:
                        time.sleep(2)
                        continue
                    return []
                
                tables = result.get("tables", [])
                results = []
                
                for table in tables:
                    thscode = table.get("thscode", "")
                    data = table.get("table", {})
                    symbol = self._code_to_symbol(thscode, stocks)
                    
                    if not symbol:
                        continue
                    
                    results.append({
                        'symbol': symbol,
                        'code': stocks.get(symbol, {}).get('code', ''),
                        'code_ifind': thscode,
                        'name': symbol,
                        'price': data.get('latest', [None])[0] if data.get('latest') else None,
                        'open': data.get('open', [None])[0] if data.get('open') else None,
                        'high': data.get('high', [None])[0] if data.get('high') else None,
                        'low': data.get('low', [None])[0] if data.get('low') else None,
                        'change': data.get('change', [None])[0] if data.get('change') else None,
                        'change_pct': data.get('changeRatio', [None])[0] if data.get('changeRatio') else None,
                        'volume': data.get('volume', [None])[0] if data.get('volume') else None,
                        'turnover': data.get('turnover', [None])[0] if data.get('turnover') else None,
                        'pe': data.get('pe_ttm', [None])[0] if data.get('pe_ttm') else None,
                        'pb': data.get('pb', [None])[0] if data.get('pb') else None,
                        'total_market': data.get('totalCapital', [None])[0] if data.get('totalCapital') else None,
                        'float_market': data.get('freeCapital', [None])[0] if data.get('freeCapital') else None,
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    })
                
                return results
                
            except Exception as e:
                if attempt < retry - 1:
                    time.sleep(2)
                    continue
                print(f"  批量获取失败: {e}")
                return []
        
        return []
    
    def _code_to_symbol(self, code_ifind, stocks):
        """将iFinD代码转为股票名称"""
        # code_ifind: 000933.SZ -> sz000933
        code_clean = code_ifind.replace('.SZ', '').replace('.SH', '').lower()
        if code_ifind.endswith('.SZ'):
            code_config = 'sz' + code_clean
        else:
            code_config = 'sh' + code_clean
        
        for name, info in stocks.items():
            if info.get('code', '').lower() == code_config:
                return name
        
        # 尝试直接匹配
        for name, info in stocks.items():
            if code_ifind.lower() == self._convert_code(info['code']).lower():
                return name
        
        return None
    
    def save_to_csv(self, results, filename='fundamental.csv'):
        """保存为CSV"""
        if not results:
            print("无数据可保存")
            return None
        
        df = pd.DataFrame(results)
        
        # 格式化市值（转换为亿元）
        if 'total_market' in df.columns:
            df['total_market_yi'] = df['total_market'].apply(lambda x: round(x / 1e8, 2) if x else None)
        if 'float_market' in df.columns:
            df['float_market_yi'] = df['float_market'].apply(lambda x: round(x / 1e8, 2) if x else None)
        
        # 格式化PE、PB
        if 'pe' in df.columns:
            df['pe'] = df['pe'].apply(lambda x: round(x, 2) if x else None)
        if 'pb' in df.columns:
            df['pb'] = df['pb'].apply(lambda x: round(x, 2) if x else None)
        
        output_file = os.path.join(OUTPUT_DIR, filename)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"已保存: {output_file}")
        return df
    
    def save_to_json(self, results, filename='fundamental.json'):
        """保存为JSON"""
        if not results:
            print("无数据可保存")
            return
        
        output_file = os.path.join(OUTPUT_DIR, filename)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"已保存: {output_file}")
    
    def scan_existing(self):
        """扫描现有数据"""
        existing_file = os.path.join(OUTPUT_DIR, 'fundamental.csv')
        if os.path.exists(existing_file):
            df = pd.read_csv(existing_file)
            print(f"\n现有数据: {len(df)} 只股票")
            if 'update_time' in df.columns and len(df) > 0:
                print(f"更新时间: {df['update_time'].iloc[0]}")
            print(f"保存位置: {existing_file}")
            return df
        else:
            print("\n暂无基本面数据")
            return None


def main():
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description='iFinD 基本面数据获取')
    parser.add_argument('--stock', type=str, help='只获取指定股票')
    parser.add_argument('--scan', action='store_true', help='查看现有数据')
    args = parser.parse_args()
    
    fetcher = FundamentalFetcher()
    
    # 扫描现有数据
    if args.scan:
        fetcher.scan_existing()
        return
    
    # 获取数据
    if args.stock:
        # 单只股票
        if args.stock in ALL_STOCKS:
            info = ALL_STOCKS[args.stock]
            print(f"\n获取 {args.stock} 基本面数据...")
            data = fetcher.fetch_single(args.stock, info['code'])
            if data:
                print(f"\n{'='*50}")
                print(f"{args.stock} ({data['code']})")
                print(f"{'='*50}")
                print(f"  最新价: {data['price']}")
                print(f"  涨跌幅: {data['change_pct']}%")
                print(f"  市盈率(TTM): {data['pe']}")
                print(f"  市净率: {data['pb']}")
                print(f"  总市值: {data['total_market']/1e8:.2f}亿" if data['total_market'] else "  总市值: N/A")
                print(f"  流通市值: {data['float_market']/1e8:.2f}亿" if data['float_market'] else "  流通市值: N/A")
                print(f"  更新时间: {data['update_time']}")
        else:
            print(f"股票 '{args.stock}' 不在配置中")
    else:
        # 所有股票
        print("=" * 50)
        print("iFinD 基本面数据获取")
        print("=" * 50)
        
        results = fetcher.fetch_all()
        
        if results:
            # 保存CSV
            df = fetcher.save_to_csv(results)
            
            # 保存JSON
            fetcher.save_to_json(results)
            
            # 数据预览
            print("\n数据预览:")
            preview_cols = ['symbol', 'price', 'change_pct', 'pe', 'pb', 'total_market_yi']
            available_cols = [c for c in preview_cols if c in df.columns]
            print(df[available_cols].head(20).to_string())


if __name__ == "__main__":
    main()
