---
name: quant-monitor
description: 监测智算系统并推送实时动态图片到飞书群。当用户要求查看智算系统实时动态、定时推送任务、启动智算系统后自动报告时使用此Skill。
---

# quant-monitor Skill

监测智算系统并推送实时动态图片到飞书群。

## 核心特性

**自动链接智算2.0配置**：
- 股票列表从 `/home/admin/.openclaw/workspace/quant_v2/config/stocks.py` 动态读取
- 当前配置：67只股票
- 未来增加股票只需修改智算2.0配置，自动同步

## 触发条件

- 用户要求查看智算系统实时动态
- 定时推送任务
- 启动智算系统后自动报告
- 检查股票状态

## 功能

1. **检查股票状态** (`python generate_image.py check`)
   - 从智算2.0配置读取股票列表
   - 检查每只股票是否有实时动态文件
   - 输出：有数据/无数据 统计

2. **更新实时动态** (`python generate_image.py update`)
   - 从东方财富获取67只股票实时数据
   - 批量写入实时动态markdown文件
   - 自动从智算2.0配置读取trend字段

3. **生成图片** (`python generate_image.py [股票名]`)
   - 随机选择一只股票生成图片
   - 指定股票名生成指定股票图片

4. **发送到飞书群**
   - 读取实时动态文件
   - 生成白色背景HTML表格截图
   - 发送到飞书群 `oc_f07d5dd203165b72de2a5bfb5317750e`

## 执行步骤

1. 读取智算2.0配置 `config/stocks.py` 获取股票列表
2. 检查/更新实时动态文件
3. 生成HTML（白色背景，蓝色表头）
4. 用 Chrome headless 截图
5. 通过 OpenClaw message 发送到飞书群

## 图片规格

- 窗口大小: 500x650
- 背景: 白色 #fff
- 表头: 蓝色 #1890ff
- 文字: 黑色 #333

## 输出格式

发送图片到飞书群，附带文字 "📊 实时动态 - {股票名}"

## 命令行用法

```bash
# 检查股票状态
python generate_image.py check

# 更新所有股票实时动态
python generate_image.py update

# 生成指定股票图片
python generate_image.py 铜陵有色

# 生成随机股票图片
python generate_image.py
```
