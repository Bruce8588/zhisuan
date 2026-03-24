# 智算系统

基于利弗莫尔规则的股票趋势分析系统。

## 目录结构

```
智算/
├── core/                      # 核心模块
│   ├── trend.py              # 趋势判断（核心不变）
│   └── fetcher_ifind.py      # iFinD数据获取
├── config/                   # 配置
│   └── stocks.py             # 股票配置
├── data/                     # 数据库（分钟级别数据）
├── output/                   # 输出目录
│   ├── 趋势判断/             # 每分钟趋势判断
│   ├── 实时动态/             # 最新数据+趋势
│   └── 行情记录/             # 每日行情记录
├── scripts/                   # 运行脚本
│   ├── run.py               # 主运行程序
│   ├── fetch_data.py        # 数据获取
│   ├── analyze_trend.py      # 趋势判断
│   ├── generate_realtime.py  # 生成实时动态
│   └── generate_records.py    # 生成行情记录
└── venv311/                 # Python环境
```

## 快速开始

### 列出所有股票
```bash
python scripts/run.py --list
```

### 单只股票完整流程
```bash
python scripts/run.py --step all --stock 神火股份
```

### 获取数据
```bash
# 获取最近7天
python scripts/run.py --step fetch --days 7

# 获取最近1小时
python scripts/run.py --step fetch --hours 1

# 指定时间段
python scripts/run.py --step fetch --start 2026-03-01 --end 2026-03-23
```

### 生成趋势判断
```bash
python scripts/run.py --step trend
```

### 生成输出
```bash
python scripts/run.py --step realtime   # 实时动态
python scripts/run.py --step records     # 行情记录
```

### 完整流程
```bash
python scripts/run.py --step pipeline   # 数据获取+趋势+输出
python scripts/run.py --step all         # 全部（7天数据）
```

## 输出文件

1. **数据库** (`data/`)
   - 股票代码_分钟数据.csv
   - 格式：时间, 开盘, 最高, 最低, 收盘, 成交量

2. **趋势判断库** (`output/趋势判断/`)
   - 股票名称_趋势判断.csv
   - 每分钟的趋势状态

3. **实时动态** (`output/实时动态/`)
   - 股票名称_实时动态.csv
   - 最新数据+当前趋势

4. **行情记录** (`output/行情记录/`)
   - 股票名称_行情记录.csv
   - 最近10天每日记录

## 数据获取规则

- 新数据时间点覆盖旧数据
- 如果新数据时间长度没有旧数据长，保留旧数据
- 自动合并去重

## 趋势状态

- `up` - 上升趋势
- `up_natural` - 上升后自然回撤
- `up_rally` - 上升回升
- `up_secondary` - 二次回撤
- `up_break` - 向上突破
- `down` - 下跌趋势
- `down_natural` - 下跌后自然反弹
- `down_rally` - 下跌回升
- `down_secondary` - 二次反弹
- `down_break` - 向下突破
