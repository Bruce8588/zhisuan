# 智算系统 - AI 指南

**给后续接手此项目的AI阅读**

---

## 核心原则

### 1. 趋势判断模块神圣不可侵犯
`core/trend.py` 是系统的**核心**，经过长时间验证正确：
- 不要修改 trend.py 的任何逻辑
- 不要修改 config/rules.py 中的规则常量
- 如果发现问题，先确认是数据问题，不是规则问题

### 2. 模块化思维
- **第一模块**：数据获取（从iFinD API获取数据，合并到数据库）
- **第二模块**：趋势判断 + 输出生成（趋势判断库、实时动态、行情记录）
- 每个脚本独立运行，可单独测试
- 遵循现有目录结构，不要随意创建新目录

### 3. 数据优先
- 数据是系统的基础，确保数据获取正常
- 合并数据时：新数据覆盖旧数据，保留更长历史
- 定期检查数据完整性

---

## 项目结构

```
智算/
├── core/                      # 核心模块（不修改trend.py）
│   ├── trend.py             # ❌ 不要修改
│   └── fetcher_ifind.py    # iFinD HTTP API数据获取
├── config/                   # 配置
│   ├── stocks.py           # 股票列表（可添加/删除）
│   └── rules.py           # ❌ 不要修改
├── data/                    # 数据库（分钟数据CSV，自动生成）
├── output/                  # 输出（自动生成）
│   ├── 趋势判断/           # 每分钟趋势判断（CSV）
│   ├── 实时动态/           # 最新数据+趋势（CSV）
│   └── 行情记录/           # 趋势变化记录（XLSX）
├── scripts/                 # 运行脚本
│   ├── run.py             # 主程序入口
│   ├── fetch_data.py      # 第一模块：数据获取
│   ├── analyze_trend.py    # 第二模块：趋势判断
│   ├── generate_realtime.py # 第二模块：实时动态
│   └── generate_records.py  # 第二模块：行情记录
└── venv311/               # Python环境
```

---

## 模块运行

### 第一模块：数据获取
```bash
# 获取7天数据
python scripts/run.py --step fetch --days 7

# 获取1小时数据（盘中使用）
python scripts/run.py --step fetch --hours 1

# 指定时间段
python scripts/run.py --step fetch --start 2026-03-01 --end 2026-03-23
```

### 第二模块：趋势判断+输出生成
```bash
# 运行趋势判断
python scripts/run.py --step trend

# 生成实时动态
python scripts/run.py --step realtime

# 生成行情记录
python scripts/run.py --step records

# 运行第二模块全部（趋势判断+实时动态+行情记录）
python scripts/run.py --step trend && python scripts/run.py --step realtime && python scripts/run.py --step records
```

### 完整流程
```bash
# 单只股票完整流程
python scripts/run.py --step all --stock 神火股份

# 获取数据后立即分析
python scripts/run.py --step pipeline
```

---

## 输出文件格式

### 1. 数据库 (data/)
- 文件：`股票名称_代码_min1.csv`
- 内容：每分钟的价格数据
- 格式：day, open, high, low, close, volume

### 2. 趋势判断库 (output/趋势判断/)
- 文件：`股票名称_趋势判断.csv`
- 内容：每分钟的完整趋势状态
- 格式：
  - 时间、当前价格、趋势代码、趋势名称
  - 关键高、关键低、n低、n高、回升高、回升低、次级低点、次级高点、突破低、突破高

### 3. 实时动态 (output/实时动态/)
- 文件：`股票名称_实时动态.csv`
- 内容：最近5分钟价格 + 当前趋势
- 格式：注释格式，包含更新时间、当前趋势、所有关键参数、最近5分钟价格序列

### 4. 行情记录 (output/行情记录/)
- 文件：`股票名称_行情记录.xlsx`
- 内容：趋势变化记录（手工记录格式）
- **重要**：使用xlsx格式，列宽行高自适应
- 格式：
  - 时间（升序，从早到晚）
  - 上升趋势、自然回撤趋势、回升趋势、次级回撤运动
  - 下跌趋势、自然回升趋势、回撤趋势、次级回升运动
  - 比值（当前价格/关键价格）
  - 备注（完整趋势名称）

---

## 数据流向

```
iFinD API
    ↓ (第一模块)
data/ (数据库，分钟数据CSV)
    ↓ (第二模块)
core/trend.py (趋势判断)
    ↓
output/趋势判断/ (趋势判断库CSV)
    ↓
output/实时动态/ (实时动态CSV)
output/行情记录/ (趋势变化XLSX)
```

---

## iFinD API 配置

**位置**: `core/fetcher_ifind.py`

```python
REFRESH_TOKEN = "eyJ..."
```

**注意**:
- refresh_token 从同花顺超级命令获取
- 有效期与账号到期日一致
- 如果API调用失败，先检查token是否过期

---

## ⚠️ iFinD API 数据配额限制

**重要**：iFinD API 有数据使用量限制

### 当前状态
- 本月已使用：约 1,520,710+
- 配额已超限，无法继续获取数据

### 节省配额策略
1. **减少字段** - 只保留必要指标（趋势判断可能只需close）
2. **分批获取** - 每次7天，分多月获取
3. **按需获取** - 只在交易时间获取最近1小时

### 如果配额超限
- API返回: `sorry, your usage of data has exceeded this month`
- 解决: 等下个月配额重置

---

## 问题排查

### 1. 数据获取失败
```bash
# 检查token
cd /Users/isenfengming/.openclaw/workspace/工作台/智算
source venv311/bin/activate
python3 -c "
from core.fetcher_ifind import IFinDFetcher
f = IFinDFetcher()
token = f._get_access_token()
print('Token:', token[:20] + '...' if token else '失败')
"
```

### 2. 趋势判断结果异常
```bash
# 检查数据
head -5 data/神火股份_000933_min1.csv

# 检查趋势判断
tail -10 output/趋势判断/神火股份_趋势判断.csv
```

### 3. 查看输出文件
```bash
# 实时动态
cat output/实时动态/神火股份_实时动态.csv

# 行情记录（xlsx格式，用Excel打开）
open output/行情记录/神火股份_行情记录.xlsx
```

---

## 添加新股票

1. 编辑 `config/stocks.py`
2. 添加格式:
```python
"股票名称": {
    "code": "sz000000",      # 股票代码
    "trend": "up",            # 初始趋势
    "key_high": 10.0,         # 关键高（可选）
    "key_low": 8.0,          # 关键低（可选）
}
```
3. 运行数据获取
4. 运行趋势分析

---

## 关键文件说明

| 文件 | 说明 | 是否可修改 |
|------|------|----------|
| core/trend.py | 趋势判断核心逻辑 | ❌ 不可 |
| config/rules.py | 趋势规则常量 | ❌ 不可 |
| config/stocks.py | 股票配置 | ✅ 可 |
| core/fetcher_ifind.py | 数据获取 | ✅ 可 |
| scripts/run.py | 主程序 | ✅ 可 |
| scripts/generate_realtime.py | 实时动态生成 | ✅ 可 |
| scripts/generate_records.py | 行情记录生成 | ✅ 可 |

---

## 快速测试流程

```bash
cd /Users/isenfengming/.openclaw/workspace/工作台/智算
source venv311/bin/activate

# 1. 运行第二模块
python scripts/run.py --step trend
python scripts/run.py --step realtime
python scripts/run.py --step records

# 2. 查看结果
cat output/实时动态/神火股份_实时动态.csv
open output/行情记录/神火股份_行情记录.xlsx
```

---

## 联系方式

- 项目所有者: 用户
- 数据源: iFinD HTTP API
- API账号: gdjgss003

---

**最后更新**: 2026-03-23
