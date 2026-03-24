#!/usr/bin/env python3
"""
推送模块
功能：发送飞书通知（信号、行情、持仓等）
"""
import os
import sys
import json
import requests
from datetime import datetime

# 飞书Webhook地址
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/84fa2f35-07f3-47a1-8035-0c2af8d2b4a5"


class Notifier:
    """推送器"""
    
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or FEISHU_WEBHOOK
    
    def send_text(self, message):
        """发送文本消息"""
        if not self.webhook_url:
            print("未配置飞书Webhook")
            return False
        
        try:
            data = {
                "msg_type": "text",
                "content": {
                    "text": message
                }
            }
            response = requests.post(self.webhook_url, json=data, timeout=10)
            if response.status_code == 200:
                print(f"✅ 飞书推送成功: {message[:50]}...")
                return True
            else:
                print(f"❌ 飞书推送失败: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 飞书推送异常: {e}")
            return False
    
    def send_signal(self, signals):
        """发送交易信号"""
        if not signals["BUY"] and not signals["SELL"]:
            return None
        
        msg = "📊 交易信号\n\n"
        
        if signals["BUY"]:
            msg += "**买入信号:**\n"
            for s in signals["BUY"]:
                msg += f"- {s['stock']}: {s['reason']} @ {s['price']}\n"
        
        if signals["SELL"]:
            msg += "\n**卖出信号:**\n"
            for s in signals["SELL"]:
                msg += f"- {s['stock']}: {s['reason']} @ {s['price']}\n"
        
        return self.send_text(msg)
    
    def send_positions(self, positions):
        """发送持仓信息"""
        if not positions:
            return None
        
        msg = "📈 当前持仓\n\n"
        
        for p in positions:
            profit = p.get("profit", 0)
            emoji = "🟢" if profit >= 0 else "🔴"
            msg += f"{emoji} {p['stock']}: {p['open_price']} → {p.get('current_price', '?')} ({profit:+.2f}%)\n"
        
        return self.send_text(msg)
    
    def send_market_summary(self, trends):
        """发送市场概览"""
        # 统计趋势分布
        trend_count = {}
        for symbol, trend in trends.items():
            trend_count[trend] = trend_count.get(trend, 0) + 1
        
        msg = "📊 市场概览\n\n"
        
        for trend, count in sorted(trend_count.items()):
            msg += f"- {trend}: {count}只\n"
        
        return self.send_text(msg)


if __name__ == "__main__":
    notifier = Notifier()
    
    # 测试
    notifier.send_text("智算2.0 测试消息")
