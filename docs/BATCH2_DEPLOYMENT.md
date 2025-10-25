# 批次2部署指南：回测系统

## 概述

批次2实现了完整的回测系统，可以基于历史信号和价格数据模拟交易，评估策略性能。

## 新增功能

### 1. 回测引擎 (ats_backtest/engine.py)
- **BacktestEngine**: 事件驱动的回测模拟引擎
- **BacktestTrade**: 交易数据类
- 支持止损/止盈检测
- 多头/空头双向交易
- 并发持仓管理（可配置最大数量）
- 信号TTL（时间有效期）
- 手续费计算（0.04%）
- 权益曲线追踪

### 2. 数据加载器 (ats_backtest/data_loader.py)
- **BacktestDataLoader**: 历史数据加载器
- 从数据库加载历史信号
- 从币安API获取历史K线数据
- 文件缓存系统（避免重复API调用）
- 自动数据准备流程

### 3. 性能指标计算 (ats_backtest/metrics.py)
- 基本统计：总交易数、胜率、盈亏比
- 盈亏统计：总收益、平均盈利、平均亏损、利润因子
- 风险指标：最大回撤、夏普比率、索提诺比率、卡玛比率
- 高级分析：连胜连败、月度收益、分方向统计
- 出场原因分析（TP1/TP2/SL/过期）

### 4. 报告生成器 (ats_backtest/report.py)
- 格式化性能报告输出
- 交易列表打印
- 权益曲线显示
- JSON报告导出
- CSV交易明细导出

### 5. 命令行工具 (tools/run_backtest.py)
- 一键执行完整回测流程
- 灵活的时间范围选择
- 币种和概率过滤
- 可配置回测参数
- 多种输出格式

## 部署步骤

### 1. 拉取最新代码

```bash
cd /root/cryptosignal
git pull origin claude/analyze-system-improvements-011CUTZA4j28R7iSVXcgcAs9
```

### 2. 确认文件结构

```bash
# 检查新增文件
ls -la ats_backtest/
# 应该看到：
# __init__.py
# engine.py
# data_loader.py
# metrics.py
# report.py

ls -la tools/run_backtest.py
```

### 3. 确认权限

```bash
# 确保脚本可执行
chmod +x tools/run_backtest.py
```

### 4. 准备数据

回测需要两类数据：
1. **历史信号**：已在批次1中保存到数据库
2. **历史价格**：将从币安API获取（首次会较慢，后续使用缓存）

确保有足够的历史信号：

```bash
# 查看数据库中的信号数量
python3 scripts/query_stats.py --days 30
```

如果信号太少，可以先运行几次分析积累数据：

```bash
# 运行分析并保存信号
python3 tools/manual_run.py --send --top 20
```

## 使用方法

### 基础用法

```bash
# 回测最近30天（默认）
python3 tools/run_backtest.py

# 回测最近7天
python3 tools/run_backtest.py --days 7

# 回测指定时间段
python3 tools/run_backtest.py --start 2024-01-01 --end 2024-01-31
```

### 高级用法

```bash
# 只回测特定币种
python3 tools/run_backtest.py --symbols BTCUSDT ETHUSDT

# 只回测高概率信号（>=65%）
python3 tools/run_backtest.py --min-prob 0.65

# 使用更大的仓位和更多并发持仓
python3 tools/run_backtest.py --capital 20000 --position-size 0.05 --max-trades 10

# 调整信号有效期
python3 tools/run_backtest.py --ttl 12

# 保存报告和导出CSV
python3 tools/run_backtest.py --save-report --export-csv

# 简化输出（只显示摘要）
python3 tools/run_backtest.py --quiet
```

### 完整参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--days N` | 回测最近N天 | 30 |
| `--start YYYY-MM-DD` | 开始日期 | - |
| `--end YYYY-MM-DD` | 结束日期 | - |
| `--symbols [...]` | 指定币种列表 | 全部 |
| `--min-prob 0.X` | 最小概率过滤 | 无 |
| `--capital N` | 初始资金 | 10000 |
| `--position-size 0.XX` | 每单仓位比例 | 0.02 (2%) |
| `--max-trades N` | 最大同时持仓数 | 5 |
| `--ttl N` | 信号有效期（小时） | 8 |
| `--no-cache` | 不使用价格缓存 | 使用缓存 |
| `--save-report` | 保存JSON报告 | 不保存 |
| `--export-csv` | 导出CSV | 不导出 |
| `--quiet` | 简化输出 | 详细输出 |

## 测试验证

### 1. 快速测试

```bash
# 回测最近7天（数据量小，速度快）
python3 tools/run_backtest.py --days 7
```

预期输出：
```
======================================================================
  CryptoSignal Backtest Engine
======================================================================

📊 Step 1: Loading Data
----------------------------------------------------------------------
======================================================================
  Preparing Backtest Data
======================================================================
Period: 2024-XX-XX to 2024-XX-XX

✅ Loaded XX signals from database

📊 Extracted X unique symbols from signals

📈 Loading price data for X symbols...
...

🔄 Step 2: Running Backtest Simulation
----------------------------------------------------------------------
✅ Backtest completed
   Simulated XX trades

📈 Step 3: Calculating Metrics
----------------------------------------------------------------------
✅ Metrics calculated

📄 Step 4: Generating Report
----------------------------------------------------------------------

======================================================================
  BACKTEST PERFORMANCE REPORT
======================================================================

📊 TRADING STATISTICS
  Total Trades:          XX
  Winning Trades:        XX (XX.X%)
  Losing Trades:         XX (XX.X%)
  ...

💰 P&L STATISTICS
  Total Return:          +X.XX%
  ...

📉 RISK METRICS
  Max Drawdown:          X.XX%
  Sharpe Ratio:          X.XX
  ...
```

### 2. 验证缓存功能

```bash
# 第一次运行（会从API获取数据）
time python3 tools/run_backtest.py --days 7

# 第二次运行（使用缓存，应该快很多）
time python3 tools/run_backtest.py --days 7
```

缓存文件位置：`data/backtest/cache/`

### 3. 验证报告保存

```bash
# 保存报告
python3 tools/run_backtest.py --days 7 --save-report --export-csv

# 查看生成的文件
ls -lh data/backtest/reports/
```

应该看到：
- `backtest_YYYYMMDD_HHMMSS.json` (JSON报告)
- `trades_YYYYMMDD_HHMMSS.csv` (交易明细CSV)

## 输出说明

### 性能报告内容

1. **TRADING STATISTICS**: 交易统计
   - 总交易数、胜率、盈亏笔数

2. **P&L STATISTICS**: 盈亏统计
   - 总收益率、平均盈利/亏损、利润因子、最佳/最差交易

3. **CAPITAL**: 资金统计
   - 初始资金、最终资金、净利润

4. **RISK METRICS**: 风险指标
   - 最大回撤、回撤持续时间
   - 夏普比率、索提诺比率、卡玛比率

5. **POSITION BEHAVIOR**: 持仓行为
   - 平均持仓时间
   - 最大连胜/连败

6. **DIRECTION ANALYSIS**: 方向分析
   - 多头/空头交易数量和胜率

7. **EXIT REASONS**: 出场原因
   - TP1/TP2/SL/过期 各占比

8. **MONTHLY RETURNS**: 月度收益
   - 每月收益率明细

9. **PERFORMANCE RATING**: 性能评级
   - 根据胜率给出总体评价

### 关键指标解读

- **Win Rate (胜率)**: >50%为及格，>60%为优秀
- **Profit Factor (利润因子)**: >1.5为良好，>2为优秀
- **Sharpe Ratio (夏普比率)**: >1为良好，>2为优秀
- **Max Drawdown (最大回撤)**: <20%为良好，<10%为优秀

## 常见问题

### 1. "No signals found for this period"

**原因**：数据库中没有该时间段的历史信号

**解决**：
```bash
# 查看现有信号
python3 scripts/query_stats.py --recent 50

# 如果信号太少，先运行分析积累数据
python3 tools/manual_run.py --send --top 20
```

### 2. "No data returned from API"

**原因**：币安API返回空数据（可能是币种下架或时间范围问题）

**解决**：
- 检查币种是否还在交易
- 调整时间范围
- 使用 `--symbols` 指定有效的币种

### 3. 首次运行很慢

**原因**：需要从币安API获取历史价格数据

**正常现象**：
- 首次运行每个币种需要1-2秒
- 数据会被缓存到 `data/backtest/cache/`
- 后续运行会快很多

### 4. 缓存数据不更新

**原因**：使用了旧的缓存数据

**解决**：
```bash
# 清除缓存
rm -rf data/backtest/cache/

# 或者使用 --no-cache 参数
python3 tools/run_backtest.py --no-cache
```

## 数据文件位置

```
cryptosignal/
├── data/
│   └── backtest/
│       ├── cache/              # 价格数据缓存
│       │   └── SYMBOL_interval_start_end.json
│       └── reports/            # 回测报告
│           ├── backtest_YYYYMMDD_HHMMSS.json
│           └── trades_YYYYMMDD_HHMMSS.csv
```

## 性能优化建议

### 1. 使用缓存
默认开启，会显著提升重复回测速度

### 2. 限制币种
如果只关心特定币种，使用 `--symbols` 参数

### 3. 合理设置时间范围
- 短期测试：--days 7
- 常规测试：--days 30
- 长期测试：--start/--end 指定具体日期

### 4. 批量回测
可以写shell脚本批量测试不同参数：

```bash
#!/bin/bash
# test_parameters.sh

for prob in 0.50 0.55 0.60 0.65 0.70; do
  echo "Testing min_prob=$prob"
  python3 tools/run_backtest.py --min-prob $prob --quiet
done
```

## 下一步

完成批次2测试后，可以：

1. **分析结果**：查看哪些参数组合效果最好
2. **调整策略**：根据回测结果优化信号生成逻辑
3. **继续批次3**：实现单元测试和性能优化

## 技术细节

### 回测逻辑

1. **信号加载**：从数据库读取历史信号
2. **价格加载**：获取对应时间段的K线数据
3. **时间推进**：逐个时间点模拟
4. **开仓检测**：检查是否有新信号，是否可以开仓
5. **持仓检查**：每个时间点检查所有持仓的SL/TP
6. **平仓处理**：触发SL/TP或过期时平仓
7. **权益更新**：记录每个时间点的权益

### 止损止盈逻辑

**多头**：
- 止损：当前价 <= SL
- 止盈1：当前价 >= TP1
- 止盈2：当前价 >= TP2

**空头**：
- 止损：当前价 >= SL
- 止盈1：当前价 <= TP1
- 止盈2：当前价 <= TP2

### 手续费

- 开仓手续费：0.02%
- 平仓手续费：0.02%
- 总计：0.04%

已在PnL计算中扣除。

## 支持

如有问题，请检查：
1. 日志输出中的错误信息
2. 数据库是否有足够的历史信号
3. 币安API是否正常访问
4. 服务器网络连接是否正常
