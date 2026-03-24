---
name: quant-monitor-v2
description: 智算2.0系统管理技能。定期检查数据完整性、验证数据准确性、独立做趋势判断、对比智算1.0和智算2.0的结果。
---

# 智算2.0系统管理 Skill

## 快速使用（推荐）

**直接运行检查脚本：**
```bash
cd /home/admin/.openclaw/workspace/quant_v2
python3 /home/admin/.openclaw/workspace/skills/quant-monitor-v2/check_system.py
```

运行后会自动完成：
1. 数据完整性检查
2. 数据准确性验证
3. 手工趋势验证（14:57收盘时刻）
4. 输出完整报告

---

## 完整工作流程

### 第1步：数据完整性检查
- 检查所有股票数据文件大小（<1000 bytes = 无数据）
- 统计有数据/无数据股票数量
- 报告最后更新时间

### 第2步：趋势分布统计
- 读取所有趋势判断文件
- 统计各趋势代码的数量分布

### 第3步：数据准确性验证
- 上网获取实时价格（东方财富API）
- 对比系统收盘价与实时价格
- 标记差异 > 0.5% 的股票

### 第4步：手工趋势验证（关键！）
**必须使用完整利弗莫尔规则，不能用简化版！**

阈值：
- RALLY = 1.06 (上涨6%)
- PULLBACK = 0.94 (下跌6%)
- BREAK = 0.97 (跌破3%)

**重要**：必须使用14:57（收盘时刻）的趋势，不是盘后22:33的趋势！

### 第5步：对比系统与手工结果
- 对比系统判断 vs 手工验证
- 统计准确率

### 第6步：排查不一致股票
- 如果有不一致，详细分析
- 确认是用14:57趋势还是22:33趋势
- 找出是系统bug还是验证方法错误

### 第7步：发送完整报告
- 整合所有结果
- 发送到飞书群

---

## 完整检查脚本

脚本位置：`/home/admin/.openclaw/workspace/skills/quant-monitor-v2/check_system.py`

功能：
- 自动读取所有股票数据
- 获取14:57收盘时刻的趋势
- 使用完整利弗莫尔规则手工验证
- 输出完整检查报告

运行命令：
```bash
cd /home/admin/.openclaw/workspace/quant_v2
python3 /home/admin/.openclaw/workspace/skills/quant-monitor-v2/check_system.py
```

---

## 手工验证规则速查

### 上升趋势体系

| 趋势 | 转换条件 |
|------|----------|
| up | 价格 > key_high → 更新key_high |
| up | 价格 < key_high × 0.94 → up_natural |
| up_natural | 价格 > n_low × 1.06 → up_rally |
| up_natural | 价格 < n_low → 更新n_low |
| up_rally | 价格 > key_high → up |
| up_rally | 价格 < rally_high × 0.94 → up_secondary |
| up_secondary | 价格 > rally_high → up_rally |
| up_secondary | 价格 < n_low → up_break |
| up_break | 价格 > n_low × 1.06 → up_rally |
| up_break | 价格 < n_low × 0.97 → down |

### 下跌趋势体系

| 趋势 | 转换条件 |
|------|----------|
| down | 价格 < key_low → 更新key_low |
| down | 价格 > key_low × 1.06 → down_natural |
| down_natural | 价格 < n_high × 0.94 → down_rally |
| down_natural | 价格 > n_high → 更新n_high |
| down_rally | 价格 < key_low → down |
| down_rally | 价格 > rally_low × 1.06 → down_secondary |
| down_secondary | 价格 > n_high → down_break |
| down_secondary | 价格 < rally_low → down_rally |
| down_break | 价格 > n_high × 1.03 → up |
| down_break | 价格 < break_high × 0.94 → down_rally |

---

## 前置条件

### 1. 数据目录
- 智算2.0: `/home/admin/.openclaw/workspace/quant_v2/`
- 趋势规则: `/home/admin/.openclaw/workspace/quant_v2/docs/趋势规则.md`

### 2. 需要联网
- 用于获取实时价格验证数据准确性

---

## 文件结构

```
quant-monitor-v2/
├── SKILL.md              # 本文件
└── check_system.py      # 完整检查脚本（直接运行）
```

---

## 使用示例

### 场景1：快速检查
```bash
cd /home/admin/.openclaw/workspace/quant_v2
python3 /home/admin/.openclaw/workspace/skills/quant-monitor-v2/check_system.py
```

### 场景2：单独检查数据完整性
```bash
cd /home/admin/.openclaw/workspace/quant_v2
python3 -c "
import pandas as pd
import glob, os
for f in sorted(glob.glob('data/*_min1.csv')):
    size = os.path.getsize(f)
    name = f.split('/')[-1].split('_')[0]
    status = '✅' if size > 1000 else '❌'
    print(f'{status} {name}')
"
```

### 场景3：单独验证某只股票
```bash
cd /home/admin/.openclaw/workspace/quant_v2
python3 -c "
import pandas as pd
df = pd.read_csv('output/趋势判断/水晶光电_趋势判断.csv')
print(df.tail(3))
"
```

---

## 常见问题

### Q: 数据不完整怎么办？
A: 运行数据获取脚本更新数据

### Q: 趋势判断不一致怎么办？
A: 
1. 确认使用的是14:57趋势，不是22:33盘后趋势
2. 使用完整利弗莫尔规则手工验证
3. 排除验证方法错误后再判断是否是系统bug

### Q: 实时价格获取失败怎么办？
A: 检查网络连接，或使用备用数据源

---

## 数据获取经验（2026-03-14）

### akshare接口问题

**问题**：akshare分钟数据接口返回空数据

**解决**：
- 错误接口：`ak.stock_zh_a_minute()` - 周末返回空
- 正确接口：`ak.stock_zh_a_hist_min_em()` - 获取完整历史数据

### 代码格式问题

**问题**：带前缀的代码无法获取数据

**解决**：
- 错误格式：`'sz000630'`, `'sh600089'`
- 正确格式：`'000630'`, `'600089'`（纯数字，去掉sz/sh前缀）

### 列名格式

akshare返回的列名是中文，需要转换：
- `'时间'` → `'day'`
- `'开盘'` → `'open'`
- `'收盘'` → `'close'`
- `'最高'` → `'high'`
- `'最低'` → `'low'`
- `'成交量'` → `'volume'`
- `'成交额'` → `'amount'`

### Python版本问题

- akshare需要Python 3.8+
- 系统默认Python 3.6不支持
- 使用 `python3.11` 运行

### 快速获取数据脚本

```bash
cd /home/admin/.openclaw/workspace/quant_v2

# 使用python3.11运行
python3.11 -c "
import sys
sys.path.insert(0, '.')
from config.stocks import ALL_STOCKS
import akshare as ak
import pandas as pd
import os, time

for name, info in ALL_STOCKS.items():
    code = info['code']
    symbol_num = code.replace('sz', '').replace('sh', '')
    db_file = f'data/{name}_{code}_min1.csv'
    
    if os.path.exists(db_file):
        os.remove(db_file)
    
    try:
        df = ak.stock_zh_a_hist_min_em(symbol=symbol_num, period='1', adjust='qfq')
        if df is not None and len(df) > 0:
            if '时间' in df.columns:
                df.rename(columns={'时间': 'day'}, inplace=True)
            df['day'] = pd.to_datetime(df['day'])
            df = df[(df['day'].dt.hour < 15) | ((df['day'].dt.hour == 14) & (df['day'].dt.minute <= 57))]
            df.to_csv(db_file, index=False)
            print(f'{name}: {len(df)}条')
    except Exception as e:
        print(f'{name}: 失败 - {e}')
    time.sleep(0.3)
"
```

---

*最后更新：2026-03-14*
