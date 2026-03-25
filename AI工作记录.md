# 智算系统工作记录

**日期**: 2026-03-23
**操作者**: AI (code)

---

## 一、项目概述

智算系统是一个基于**利弗莫尔规则**的股票趋势分析系统，通过分析分钟级别的股票数据，判断股票当前趋势状态。

### 核心功能
1. **数据获取** - 从 iFinD HTTP API 获取股票分钟K线数据
2. **趋势判断** - 根据利弗莫尔规则对每条分钟数据进行趋势分析
3. **输出生成** - 生成趋势判断库、实时动态、行情记录

---

## 二、趋势检查规则（重要！）

**目的**：验证程序趋势分析是否正确

**两种检查方法**：

1. **方法一：详细验证**
   - 选定一批股票
   - 逐帧对比程序判断 vs 人工判断
   - 找出分歧点，分析问题原因

2. **方法二：初步正确率检验**（快速普查）
   - 只对趋势检查表里的15只股票进行检验
   - 快速评估程序的正确率
   - 不需要逐帧分析，只看最终结果是否一致

**不一致处理**：
如果某只股票输出趋势和正确趋势不一样，AI要：
- 把该股票从初始配置点开始的所有趋势变化列出来
- 帮助操作者排查问题
- AI自己也要根据趋势判断规则，对股票趋势进行分析

**趋势检查记录**：
- 路径：`docs/趋势检查.md`
- 已记录：15只股票在2个时间点（3月6日、3月10日）的趋势对比

## 三、初始配置的理解

**初始配置的含义**：
- 是对**2026年2月24日**那个时间点的趋势和关键点的描述
- 因为没有参考点和初始趋势，就无法正确进行趋势转换
- 初始配置的参考点是**2月24日**，不是数据的起点（1月5日）

**初始配置的问题**：
- 程序把2月24日的初始配置状态，应用到了1月5日就开始的所有数据上
- 1月5日~2月24日的数据实际上在初始配置参考点**之前**，不应套用2月24日的状态

**新方案**：
- 暂时禁用初始配置（不删除，只是不用）
- 程序默认：第一条数据 = up（上升趋势），第一个价格 = key_high（关键高点）
- 让系统自己从数据里学习趋势
│   ├── fetch_data.py       # 数据获取
│   ├── analyze_trend.py    # 趋势判断
│   ├── generate_realtime.py # 实时动态
│   └── generate_records.py   # 行情记录
├── services/                 # 服务
├── docs/                    # 文档
└── venv311/                 # Python环境
```

---

## 三、模块化实现

### 1. 数据获取模块 (fetch_data.py)

**功能**: 使用 iFinD HTTP API 获取数据并合并

**核心逻辑**:
```python
# 合并规则
- 新数据时间点覆盖旧数据
- 如果新数据时间长度没有旧数据长，保留旧数据
- 自动去重、排序
```

**使用方式**:
```bash
python scripts/run.py --step fetch --days 7      # 最近7天
python scripts/run.py --step fetch --hours 1      # 最近1小时
python scripts/run.py --step fetch --start 2026-03-01 --end 2026-03-23
```

**API配置**:
- refresh_token 保存在 `core/fetcher_ifind.py`
- API地址: `https://quantapi.51ifind.com/api/v1/high_frequency`
- 返回格式: `{"errorcode": 0, "tables": [{"thscode": "000933.SZ", "time": [...], "table": {...}}]}`

### 2. 趋势判断模块 (analyze_trend.py)

**功能**: 对数据库每条数据进行趋势判断

**核心逻辑**:
```python
# 读取数据库 → 初始化状态 → 逐条分析 → 保存趋势判断库
# 状态包含: trend, key_high, key_low, n_low, n_high, rally_high, rally_low 等
```

**输出**: `output/趋势判断/股票名称_趋势判断.csv`

### 3. 实时动态模块 (generate_realtime.py)

**功能**: 从趋势判断库提取最新数据

**输出**: `output/实时动态/股票名称_实时动态.csv`

### 4. 行情记录模块 (generate_records.py)

**功能**: 生成每日行情记录（最近10天）

**输出**: `output/行情记录/股票名称_行情记录.csv`

### 5. 主运行程序 (run.py)

**功能**: 模块化调用，支持单独运行或组合运行

```bash
# 单步运行
python scripts/run.py --step fetch --days 7
python scripts/run.py --step trend
python scripts/run.py --step realtime
python scripts/run.py --step records

# 组合运行
python scripts/run.py --step pipeline   # 获取+趋势+输出
python scripts/run.py --step all       # 全部（含7天数据）

# 单只股票
python scripts/run.py --step all --stock 神火股份
```

---

## 四、iFinD HTTP API 集成

### 获取 Token
```python
refresh_token = "eyJ..."  # 从同花顺超级命令获取

# 请求
POST https://quantapi.51ifind.com/api/v1/get_access_token
Headers: {"Content-Type": "application/json", "refresh_token": refresh_token}

# 返回
{"errorcode": 0, "data": {"access_token": "cf0ff7e..."}}
```

### 获取1分钟数据
```python
POST https://quantapi.51ifind.com/api/v1/high_frequency
Headers: {"Content-Type": "application/json", "access_token": token}
Body: {
    "codes": "000933.SZ",
    "indicators": "open,high,low,close,volume",
    "starttime": "2026-03-16 09:15:00",
    "endtime": "2026-03-23 15:15:00",
    "functionpara": {"Interval": "1", "Fill": "Original"}
}
```

---

## 五、代码规范

### 核心原则
1. **趋势判断模块 (trend.py) 不可修改** - 这是系统的核心，经过验证正确
2. **模块独立运行** - 每个脚本可以单独运行
3. **数据合并逻辑** - 新数据覆盖旧数据，保留更长的历史

### 目录约定
- 数据库: `data/股票名称_代码_min1.csv`
- 趋势判断: `output/趋势判断/股票名称_趋势判断.csv`
- 实时动态: `output/实时动态/股票名称_实时动态.csv`
- 行情记录: `output/行情记录/股票名称_行情记录.csv`

### 股票代码格式
- 配置文件: `sz000933`, `sh600089`
- iFinD API: `000933.SZ`, `600089.SH`
- 文件名: `000933`, `600089`

---

## 六、注意事项

### 数据量限制
- iFinD API 对分钟数据有下载量限制
- 建议: 每次获取不超过7天数据
- 可以多次获取短时间段累加

### Token有效期
- refresh_token 有效期与账号到期日一致
- access_token 有效期7天
- 代码会自动刷新 access_token

### 数据时间过滤
- 只保留 14:57 之前的数据（排除盘后数据）
- 格式: `df = df[(df["day"].dt.hour < 15) | ((df["day"].dt.hour == 14) & (df["day"].dt.minute <= 57))]`

---

## 七、未来改进方向

1. **定时任务** - 添加 crontab 自动运行
2. **交易信号** - 根据趋势变化生成买卖信号
3. **模拟交易** - 基于信号的模拟交易功能
4. **数据备份** - 定期备份数据库
5. **监控告警** - 趋势变化时推送通知

---

## 八、快速测试

```bash
cd /Users/isenfengming/.openclaw/workspace/工作台/智算
source venv311/bin/activate

# 列出股票
python scripts/run.py --list

# 测试单只股票
python scripts/run.py --step all --stock 神火股份

# 查看输出
cat output/实时动态/神火股份_实时动态.csv
cat output/趋势判断/神火股份_趋势判断.csv | tail -5
```

---

## 九、今日更新 (2026-03-23 下午)

### 1. 实时动态格式改进
- 从只输出最后一条改为输出最近5分钟价格 + 完整趋势参数
- 格式：注释头部包含所有趋势参数，下方是最近5分钟价格序列

### 2. 行情记录格式改进
- 参考手工记录的格式，每行一个趋势变化点
- 使用XLSX格式，列宽行高自适应
- 列：时间（升序）、各趋势列、关键价格、比值、备注（完整趋势名称）

### 3. 手工记录格式参考
```
时间,上升趋势,自然回撤趋势,回升趋势,次级回撤运动,下跌趋势,自然回升趋势,回撤趋势,次级回升运动,比值,备注
2026-02-24,,,,,29.76,,,,1.032594,下跌趋势
2026-02-25,,,,,,32.35,,,0.982689,自然回升趋势
```

### 4. 数据库清理
- 删除重复的CSV文件，合并数据
- 当前：67只股票

### 5. iFinD API配额问题
- 本月配额已用完（1,520,710+）
- 无法继续获取数据，需等下个月重置

### 6. 输出文件最终格式

**趋势判断库 (CSV)**:
- 每分钟完整趋势状态
- 包含所有关键参数

**实时动态 (CSV)**:
```
# 神火股份 实时动态
# 更新时间: 2026-03-23 14:59:00
# 当前趋势: 回升 (up_rally)
# 关键高: 39.48
# 关键低: 29.76
# ...
# 最近5分钟价格:
时间,价格
2026-03-23 14:55:00,29.84
2026-03-23 14:56:00,29.91
...
```

**行情记录 (XLSX)**:
- 自适应列宽行高
- 时间升序排列
- 每行一个趋势变化点
