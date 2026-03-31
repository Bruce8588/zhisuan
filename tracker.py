#!/usr/bin/env python3
"""
股票行情追踪器
功能：
    python tracker.py --query TCL中环    # 查询单只股票趋势
    python tracker.py --web              # 启动Web界面
    python tracker.py --all              # 批量分析所有股票
    python tracker.py --fetch            # 获取最新数据并分析
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

# 添加项目根目录（智算目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config.stocks import ALL_STOCKS
from config.rules import TREND_NAMES
from core.trend import TrendAnalyzer
from core.fetcher_ifind import IFinDFetcher
from query import query_by_name, query_all, get_latest_from_csv, get_market, get_trend_description

# 输出目录
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "趋势判断")

# ========== Web 界面 ==========
app = Flask(__name__)


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智算2.0 - 股票趋势查询</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 { 
            text-align: center; 
            margin: 30px 0;
            font-size: 2em;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        input[type="text"] {
            flex: 1;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid #333;
            border-radius: 10px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            outline: none;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus { border-color: #00d4ff; }
        button {
            padding: 15px 30px;
            font-size: 16px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-query { background: linear-gradient(135deg, #00d4ff, #7b2cbf); color: #fff; }
        .btn-query:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0,212,255,0.3); }
        .btn-all { background: #2d3436; color: #fff; }
        .btn-all:hover { background: #3d4446; }
        .btn-fetch { background: #e17055; color: #fff; }
        .btn-fetch:hover { background: #d35400; }
        .result {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
        }
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .stock-name { font-size: 1.5em; font-weight: bold; color: #00d4ff; }
        .trend-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
        }
        .trend-up { background: #00b894; }
        .trend-down { background: #d63031; }
        .trend-neutral { background: #636e72; }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .info-item {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
        }
        .info-label { color: #888; font-size: 0.85em; margin-bottom: 5px; }
        .info-value { font-size: 1.2em; font-weight: bold; }
        .key-points {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .key-points h3 { margin-bottom: 15px; color: #00d4ff; }
        .key-point-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .interpretation {
            background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(123,44,191,0.1));
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #00d4ff;
        }
        .interpretation h3 { color: #00d4ff; margin-bottom: 10px; }
        .error { color: #d63031; padding: 20px; text-align: center; }
        .loading { text-align: center; padding: 40px; color: #888; }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #666;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 智算2.0 股票趋势查询</h1>
        
        <div class="search-box">
            <input type="text" id="stockInput" placeholder="输入股票名称，如：TCL中环、比亚迪、神火股份" onkeypress="handleKeyPress(event)">
            <button class="btn-query" onclick="queryStock()">查询</button>
            <button class="btn-all" onclick="queryAll()">全部</button>
            <button class="btn-fetch" onclick="fetchNew()">更新数据</button>
        </div>
        
        <div id="result"></div>
        
        <div class="footer">
            <p>数据来源：iFinD · 更新时间显示为CSV最后记录时间</p>
        </div>
    </div>
    
    <script>
        function handleKeyPress(e) {
            if (e.key === 'Enter') queryStock();
        }
        
        async function queryStock() {
            const name = document.getElementById('stockInput').value.trim();
            if (!name) return;
            
            document.getElementById('result').innerHTML = '<div class="loading">查询中...</div>';
            
            try {
                const response = await fetch(`/api/query?name=${encodeURIComponent(name)}`);
                const data = await response.json();
                renderResult(data);
            } catch (e) {
                document.getElementById('result').innerHTML = `<div class="error">查询失败: ${e.message}</div>`;
            }
        }
        
        async function queryAll() {
            document.getElementById('result').innerHTML = '<div class="loading">加载中...</div>';
            
            try {
                const response = await fetch('/api/all');
                const data = await response.json();
                renderAll(data);
            } catch (e) {
                document.getElementById('result').innerHTML = `<div class="error">加载失败: ${e.message}</div>`;
            }
        }
        
        async function fetchNew() {
            if (!confirm('确定要获取最新数据吗？这可能需要几分钟。')) return;
            
            document.getElementById('result').innerHTML = '<div class="loading">正在获取最新数据，请稍候...</div>';
            
            try {
                const response = await fetch('/api/fetch', { method: 'POST' });
                const data = await response.json();
                if (data.status === 'ok') {
                    queryAll();
                } else {
                    document.getElementById('result').innerHTML = `<div class="error">获取失败: ${data.message}</div>`;
                }
            } catch (e) {
                document.getElementById('result').innerHTML = `<div class="error">获取失败: ${e.message}</div>`;
            }
        }
        
        function getTrendClass(code) {
            if (code.startsWith('up')) return 'trend-up';
            if (code.startsWith('down')) return 'trend-down';
            return 'trend-neutral';
        }
        
        function renderResult(data) {
            if (data.error) {
                document.getElementById('result').innerHTML = `<div class="error">${data.error}</div>`;
                return;
            }
            
            const trendClass = getTrendClass(data.trend_code);
            
            document.getElementById('result').innerHTML = `
                <div class="result">
                    <div class="result-header">
                        <div class="stock-name">${data.symbol}</div>
                        <div class="trend-badge ${trendClass}">${data.trend_name}</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">代码</div>
                            <div class="info-value">${data.code}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">市场</div>
                            <div class="info-value">${data.market}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">当前价格</div>
                            <div class="info-value" style="color: #00d4ff;">${data.price}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">更新时间</div>
                            <div class="info-value">${data.update_time}</div>
                        </div>
                    </div>
                    
                    <div class="key-points">
                        <h3>📌 关键点</h3>
                        <div class="key-point-row">
                            <span>key_high</span>
                            <span>${data.key_high || '无'}</span>
                        </div>
                        <div class="key-point-row">
                            <span>key_low</span>
                            <span>${data.key_low || '无'}</span>
                        </div>
                        <div class="key-point-row">
                            <span>n_low / n_high</span>
                            <span>${data.n_low || '无'} / ${data.n_high || '无'}</span>
                        </div>
                    </div>
                    
                    <div class="interpretation">
                        <h3>📈 趋势解读</h3>
                        <p>${data.description}</p>
                    </div>
                </div>
            `;
        }
        
        function renderAll(data) {
            if (!data.stocks || data.stocks.length === 0) {
                document.getElementById('result').innerHTML = '<div class="error">暂无数据</div>';
                return;
            }
            
            let html = '<div class="result"><h3 style="margin-bottom:20px;">📈 股票趋势总览</h3>';
            html += '<table style="width:100%;border-collapse:collapse;">';
            html += '<tr style="border-bottom:1px solid rgba(255,255,255,0.1);">';
            html += '<th style="text-align:left;padding:10px;">股票</th>';
            html += '<th style="text-align:right;padding:10px;">价格</th>';
            html += '<th style="text-align:center;padding:10px;">趋势</th>';
            html += '<th style="text-align:left;padding:10px;">趋势名称</th></tr>';
            
            for (const s of data.stocks) {
                const trendClass = getTrendClass(s.trend_code);
                html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">`;
                html += `<td style="padding:10px;">${s.stock}</td>`;
                html += `<td style="text-align:right;padding:10px;color:#00d4ff;">${s.price}</td>`;
                html += `<td style="text-align:center;padding:10px;"><span class="trend-badge ${trendClass}">${s.trend}</span></td>`;
                html += `<td style="padding:10px;">${s.trend_name}</td></tr>`;
            }
            
            html += '</table></div>';
            document.getElementById('result').innerHTML = html;
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/query')
def api_query():
    name = request.args.get('name', '')
    
    # 查找股票
    if name in ALL_STOCKS:
        symbol = name
        info = ALL_STOCKS[symbol]
    else:
        matches = [k for k in ALL_STOCKS.keys() if name in k]
        if len(matches) == 1:
            symbol = matches[0]
            info = ALL_STOCKS[symbol]
        elif len(matches) > 1:
            return jsonify({'error': f'匹配到多个股票: {", ".join(matches)}'})
        else:
            return jsonify({'error': f'未找到股票: {name}'})
    
    # 获取最新数据
    latest = get_latest_from_csv(symbol, info["code"])
    
    if latest is None:
        return jsonify({'error': f'{symbol} 暂无数据，请先点击"更新数据"'})
    
    price = float(latest["当前价格"])
    trend_code = latest["趋势代码"]
    trend_name = latest["趋势名称"]
    
    state = {
        "key_high": latest.get("key_high"),
        "key_low": latest.get("key_low"),
        "n_low": latest.get("n_low"),
        "n_high": latest.get("n_high"),
    }
    
    def fmt(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return f"{v:.2f}"
    
    return jsonify({
        "symbol": symbol,
        "code": info["code"],
        "market": get_market(info["code"]),
        "price": f"¥{price:.2f}",
        "trend_code": trend_code,
        "trend_name": trend_name,
        "key_high": fmt(state['key_high']),
        "key_low": fmt(state['key_low']),
        "n_low": fmt(state['n_low']),
        "n_high": fmt(state['n_high']),
        "description": get_trend_description(trend_code, price, state),
        "update_time": latest.get("时间", "未知")
    })


@app.route('/api/all')
def api_all():
    results = []
    for symbol, info in ALL_STOCKS.items():
        latest = get_latest_from_csv(symbol, info["code"])
        if latest is not None:
            price = float(latest["当前价格"])
            results.append({
                "stock": symbol,
                "code": info["code"],
                "price": f"¥{price:.2f}",
                "trend": latest["趋势代码"],
                "trend_name": latest["趋势名称"]
            })
    
    return jsonify({"stocks": results})


@app.route('/api/fetch', methods=['POST'])
def api_fetch():
    try:
        # 获取所有股票最新数据
        fetcher = IFinDFetcher()
        analyzer = TrendAnalyzer()
        
        count = 0
        for symbol, info in ALL_STOCKS.items():
            try:
                code_ifind = fetcher._convert_code(info["code"])
                df = fetcher.get_minute_data(code_ifind, days=1)
                
                if df is not None and len(df) > 0:
                    analyzer.analyze_stock(symbol, info)
                    count += 1
            except Exception as e:
                print(f"获取 {symbol} 失败: {e}")
        
        return jsonify({"status": "ok", "count": count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ========== CLI 命令 ==========
def cmd_query(stock_name):
    """查询单只股票"""
    result = query_by_name(stock_name, fetch_new=False)
    print(result)


def cmd_all():
    """查询所有股票"""
    query_all()


def cmd_fetch():
    """获取最新数据并分析"""
    print("=== 获取所有股票最新数据 ===\n")
    fetcher = IFinDFetcher()
    analyzer = TrendAnalyzer()
    
    count = 0
    for symbol, info in ALL_STOCKS.items():
        try:
            print(f"处理 {symbol}...")
            code_ifind = fetcher._convert_code(info["code"])
            df = fetcher.get_minute_data(code_ifind, days=1)
            
            if df is not None and len(df) > 0:
                analyzer.analyze_stock(symbol, info)
                count += 1
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")
    
    print(f"\n✅ 完成，共处理 {count} 只股票")


def main():
    parser = argparse.ArgumentParser(description="股票行情追踪器")
    parser.add_argument("--query", type=str, help="查询股票趋势")
    parser.add_argument("--all", action="store_true", help="显示所有股票趋势")
    parser.add_argument("--fetch", action="store_true", help="获取最新数据")
    parser.add_argument("--web", action="store_true", help="启动Web界面")
    parser.add_argument("--port", type=int, default=5000, help="Web服务端口")
    
    args = parser.parse_args()
    
    if args.web:
        print(f"🚀 启动Web服务: http://localhost:{args.port}")
        app.run(host='0.0.0.0', port=args.port, debug=False)
    elif args.query:
        cmd_query(args.query)
    elif args.all:
        cmd_all()
    elif args.fetch:
        cmd_fetch()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
