#!/usr/bin/env python3
"""
数据获取模块
功能：从东方财富获取股票1分钟K线数据，合并到数据库

【重要经验 2026-03-14】
1. akshare需要Python 3.8+，系统Python 3.6不支持
2. akshare分钟数据接口：
   - 错误: ak.stock_zh_a_minute() - 周末返回空
   - 正确: ak.stock_zh_a_hist_min_em() - 获取完整历史数据
3. 代码格式：
   - 错误: 'sz000630', 'sh600089'（带前缀）
   - 正确: '000630', '600089'（纯数字）
4. 列名格式：
   - akshare返回: '时间', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '均价'
   - 需要转换为: 'day', 'open', 'close', 'high', 'low', 'volume', 'amount'
"""
import os
import sys

# 尝试使用Python 3.11（akshare需要）
if sys.version_info < (3, 8):
    import subprocess
    # 尝试用python3.11重新运行
    try:
        result = subprocess.run(['python3.11', '-c', 'import akshare'], 
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            # 有python3.11且有akshare，替换解释器
            os.execv(sys.executable.replace('/python', '/python3.11'), 
                    [sys.executable.replace('/python', '/python3.11')] + sys.argv)
    except:
        pass
import pandas as pd
from datetime import datetime
import time
import json
import urllib.request

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class DataFetcher:
    """数据获取器"""
    
    def __init__(self, db_dir=None):
        self.db_dir = db_dir or os.path.join(BASE_DIR, "data")
        os.makedirs(self.db_dir, exist_ok=True)
    
    def get_realtime_eastmoney(self, eastmoney_code):
        """东方财富API获取实时数据"""
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={eastmoney_code}&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f57,f58,f59,f60"
        try:
            response = urllib.request.urlopen(url, timeout=5)
            data = json.loads(response.read().decode('utf-8'))
            return data.get('data', {})
        except Exception as e:
            print(f"    东方财富API失败: {e}")
            return None
    
    def get_realtime_tencent(self, code):
        """腾讯财经API获取实时数据"""
        # 转换代码: sz000630 -> sh000630, sh600089 -> sh600089
        tencent_code = code.replace('sz', 'sz').replace('sh', 'sh')
        if code.startswith('sz'):
            tencent_code = 'sz' + code.replace('sz', '')
        elif code.startswith('sh'):
            tencent_code = 'sh' + code.replace('sh', '')
        
        url = f"https://qt.gtimg.cn/q={tencent_code}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=5)
            content = response.read().decode('utf-8', errors='ignore')
            
            # 解析返回数据
            # 格式: v_sh601012="1~¡~601012~18.81~18.68~18.77~2474675~1182379~..."
            if '=' in content and '~' in content:
                parts = content.split('="')[1].strip('"').split('~')
                if len(parts) >= 10:
                    return {
                        'code': parts[2],
                        'current': float(parts[3]) if parts[3] else 0,  # 当前价
                        'open': float(parts[4]) if parts[4] else 0,      # 开盘价
                        'high': float(parts[5]) if parts[5] else 0,       # 最高价
                        'low': float(parts[6]) if parts[6] else 0,        # 最低价
                        'volume': int(parts[7]) if parts[7] else 0,       # 成交量
                        'amount': int(parts[8]) if parts[8] else 0,       # 成交额
                    }
            return None
        except Exception as e:
            # print(f"    腾讯财经API失败: {e}")
            return None
    
    def fetch_minute_data(self, symbol, code, eastmoney_code=None):
        """获取单只股票1分钟K线数据（增量获取）
        
        优先级：
        1. 读取数据库最新时间
        2. akshare - 获取今天所有1分钟数据
        3. 过滤增量（只取数据库之后的数据）
        4. 过滤盘后数据（14:57之后不参与趋势判断，因为14:57是收盘）
        5. 东方财富API - 获取实时1条数据
        """
        print(f"  尝试获取 {symbol} ({code})...")
        
        # 0. 检查数据库最新时间
        db_file = os.path.join(self.db_dir, f"{symbol}_{code}_min1.csv")
        last_time = None
        if os.path.exists(db_file):
            try:
                old_data = pd.read_csv(db_file)
                if 'day' in old_data.columns:
                    old_data['day'] = pd.to_datetime(old_data['day'])
                    last_time = old_data['day'].max()
                    print(f"    数据库最新: {last_time}")
            except:
                pass
        
        result_df = None
        
        # 1. akshare获取历史分钟数据（优先使用正确的接口）
        # 添加重试机制
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                import akshare as ak
                from datetime import datetime, timedelta
                # 转换为纯数字代码（去掉sz/sh前缀）
                symbol_num = code.replace('sz', '').replace('sh', '')
                
                # 获取最近1天的数据
                today = datetime.now().strftime('%Y-%m-%d')
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                # 使用 stock_zh_a_hist_min_em 获取最近1天数据
                df = ak.stock_zh_a_hist_min_em(symbol=symbol_num, period='1', adjust='qfq', 
                                               start_date=yesterday, end_date=today)
                
                if df is not None and len(df) > 0:
                    # 格式化列名
                    if '时间' in df.columns:
                        df.rename(columns={'时间': 'day'}, inplace=True)
                    elif 'date' in df.columns:
                        df.rename(columns={'date': 'day'}, inplace=True)
                    
                    # 转换日期格式
                    if 'day' in df.columns:
                        df['day'] = pd.to_datetime(df['day'])
                        
                        # 过滤盘后数据（只保留14:57之前的数据）
                        df = df[(df['day'].dt.hour < 15) | ((df['day'].dt.hour == 14) & (df['day'].dt.minute <= 57))]
                        
                        if len(df) > 0:
                            print(f"    akshare最近1天: {len(df)} 条")
                            result_df = df
                        else:
                            print(f"    akshare: 无最近1天数据")
                    break  # 成功获取，跳出重试循环
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    akshare失败 (尝试 {attempt+1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                else:
                    print(f"    akshare失败: {e}")
        
        # 3. 东方财富API - 获取实时数据（添加重试机制）
        if eastmoney_code:
            for attempt in range(max_retries):
                try:
                    realtime_data = self.get_realtime_eastmoney(eastmoney_code)
                    
                    if realtime_data:
                        current_price = realtime_data.get('f43', 0) / 100 if realtime_data.get('f43') else 0
                        high = realtime_data.get('f44', 0) / 100 if realtime_data.get('f44') else current_price
                        low = realtime_data.get('f45', 0) / 100 if realtime_data.get('f45') else current_price
                        volume = realtime_data.get('f47', 0) or 0
                        amount = realtime_data.get('f48', 0) or 0
                        
                        if current_price > 0:
                            now = datetime.now()
                            
                            # 过滤盘后数据（只保留14:57之前的数据）
                            if now.hour >= 15 and (now.hour > 15 or now.minute > 57):
                                print(f"    东方财富: 盘后数据，跳过")
                            else:
                                realtime_df = pd.DataFrame([{
                                    'day': now.strftime('%Y-%m-%d %H:%M:%S'),
                                    'open': current_price,
                                    'high': high,
                                    'low': low,
                                    'close': current_price,
                                    'volume': volume,
                                    'amount': amount,
                                }])
                                print(f"    东方财富: 1 条实时数据")
                                break  # 成功获取，跳出重试循环
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                        else:
                            print(f"    东方财富API失败: 无返回数据")
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"    东方财富API失败 (尝试 {attempt+1}/{max_retries}): {e}")
                        time.sleep(retry_delay)
                    else:
                        print(f"    东方财富API失败: {e}")
        
        # 3.5 腾讯财经API - 备选实时数据源
        if result_df is None or len(result_df) == 0:
            try:
                tencent_data = self.get_realtime_tencent(code)
                if tencent_data and tencent_data.get('current', 0) > 0:
                    now = datetime.now()
                    # 过滤盘后数据
                    if now.hour < 15 or (now.hour == 14 and now.minute <= 57):
                        realtime_df = pd.DataFrame([{
                            'day': now.strftime('%Y-%m-%d %H:%M:%S'),
                            'open': tencent_data.get('open', tencent_data.get('current', 0)),
                            'high': tencent_data.get('high', tencent_data.get('current', 0)),
                            'low': tencent_data.get('low', tencent_data.get('current', 0)),
                            'close': tencent_data.get('current', 0),
                            'volume': tencent_data.get('volume', 0),
                            'amount': tencent_data.get('amount', 0),
                        }])
                        print(f"    腾讯财经: 1 条实时数据")
                        if result_df is not None and len(result_df) > 0:
                            result_df = pd.concat([result_df, realtime_df], ignore_index=True)
                        else:
                            result_df = realtime_df
            except Exception as e:
                pass
        
        # 4. baostock - 备选数据源
        if result_df is None or len(result_df) == 0:
            for attempt in range(max_retries):
                try:
                    import baostock as bs
                    from datetime import datetime, timedelta
                    
                    # 转换代码格式
                    bs_code = code.replace('sz', 'sz.').replace('sh', 'sh.')
                    
                    # 登录
                    lg = bs.login()
                    if lg.error_code != '0':
                        bs.logout()
                        continue
                    
                    # 获取最近1天分钟数据
                    today = datetime.now().strftime('%Y-%m-%d')
                    yesterday = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')  # baostock需要前一天
                    
                    rs = bs.query_history_k_data_plus(bs_code,
                        "date,time,code,open,high,low,close,volume",
                        start_date=yesterday,
                        end_date=today,
                        frequency="5",  # 5分钟K线
                        adjustflag="2")
                    
                    data_list = []
                    while (rs.error_code == '0') & rs.next():
                        data_list.append(rs.get_row_data())
                    
                    bs.logout()
                    
                    if len(data_list) > 0:
                        df_bs = pd.DataFrame(data_list, columns=rs.fields)
                        
                        if 'time' in df_bs.columns and 'date' in df_bs.columns:
                            # 处理时间格式：20260313093500000 -> 2026-03-13 09:35:00
                            def parse_time(t):
                                t = str(t)
                                if len(t) >= 14:
                                    return f"{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:14]}"
                                return t
                            
                            df_bs['day'] = df_bs['time'].apply(parse_time)
                            df_bs['day'] = pd.to_datetime(df_bs['day'])
                            
                            # 重命名列
                            df_bs.rename(columns={
                                'open': 'open',
                                'high': 'high', 
                                'low': 'low',
                                'close': 'close',
                                'volume': 'volume'
                            }, inplace=True)
                            
                            # 过滤今天的数据
                            today_str = datetime.now().strftime('%Y-%m-%d')
                            df_bs = df_bs[df_bs['day'].dt.strftime('%Y-%m-%d') == today_str]
                            
                            if len(df_bs) > 0:
                                df_bs = df_bs[['day', 'open', 'high', 'low', 'close', 'volume']].copy()
                                print(f"    baostock: {len(df_bs)} 条")
                                result_df = df_bs
                                break
                            
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        pass
        
        if result_df is not None and len(result_df) > 0:
            return result_df
        
        print(f"    无新数据")
        return None
    
    def merge_to_db(self, symbol, code, new_data):
        """合并数据到数据库"""
        db_file = os.path.join(self.db_dir, f"{symbol}_{code}_min1.csv")
        
        if new_data is None:
            return False
        
        # 确保日期格式统一
        if 'day' in new_data.columns:
            new_data['day'] = pd.to_datetime(new_data['day'])
        
        # 数据验证：过滤无效数据
        if new_data is not None and len(new_data) > 0:
            try:
                # 确保列名标准化
                column_map = {
                    '开盘': 'open', '收盘': 'close', 
                    '最高': 'high', '最低': 'low',
                    '成交量': 'volume', '成交额': 'amount'
                }
                for old_col, new_col in column_map.items():
                    if old_col in new_data.columns:
                        new_data.rename(columns={old_col: new_col}, inplace=True)
                
                # 检查必要列是否存在
                required_cols = ['open', 'close', 'high', 'low', 'volume']
                has_all_cols = all(col in new_data.columns for col in required_cols)
                
                if has_all_cols:
                    # 过滤条件：
                    # 1. 开盘价为0但收盘价不为0（异常数据）
                    # 2. 最高价 < 最低价（异常数据）
                    # 3. 成交量为负（异常数据）
                    # 4. 收盘价为0（异常数据）
                    valid_mask = ~(
                        ((new_data['open'] == 0) & (new_data['close'] != 0)) |
                        (new_data['high'] < new_data['low']) |
                        (new_data['volume'] < 0) |
                        (new_data['close'] == 0)
                    )
                    new_data = new_data[valid_mask]
            except Exception as e:
                # 如果验证失败，跳过验证
                pass
        
        if new_data is None or len(new_data) == 0:
            return False
        
        if os.path.exists(db_file):
            # 读取现有数据
            old_data = pd.read_csv(db_file)
            old_data["day"] = pd.to_datetime(old_data["day"])
            
            # 重置索引
            old_data = old_data.reset_index(drop=True)
            new_data = new_data.reset_index(drop=True)
            
            # 合并并去重
            combined = pd.concat([old_data, new_data], ignore_index=True)
            combined = combined.drop_duplicates(subset=["day"], keep="last")
            combined = combined.sort_values("day").reset_index(drop=True)
            
            # 清理空列和末尾逗号问题
            combined = combined.dropna(axis=1, how='all')  # 删除全空列
            combined = combined.loc[:, (combined != '').any(axis=0)]  # 删除全空字符串列
            
            combined.to_csv(db_file, index=False, encoding="utf-8")
        else:
            # 清理空列
            new_data = new_data.reset_index(drop=True)
            new_data = new_data.dropna(axis=1, how='all')
            new_data = new_data.loc[:, (new_data != '').any(axis=0)]
            new_data.to_csv(db_file, index=False, encoding="utf-8")
        
        return True
    
    def update_stock(self, symbol, info):
        """更新单只股票数据"""
        code = info.get("code")
        eastmoney_code = info.get("eastmoney")
        
        df = self.fetch_minute_data(symbol, code, eastmoney_code)
        if df is not None and len(df) > 0:
            self.merge_to_db(symbol, code, df)
            print(f"  {symbol}: {len(df)} 条数据已保存")
            return len(df)
        return 0
    
    def update_all(self, stocks):
        """更新所有股票"""
        results = {}
        for symbol, info in stocks.items():
            count = self.update_stock(symbol, info)
            results[symbol] = count
            time.sleep(1)  # 避免请求过快
        return results


if __name__ == "__main__":
    from config.stocks import POOL_A, WATCHLIST
    
    fetcher = DataFetcher()
    
    print("=== 更新股票池A ===")
    fetcher.update_all(POOL_A)
    
    print("\n=== 更新自选股 ===")
    fetcher.update_all(WATCHLIST)
    
    print("\n数据获取完成!")
