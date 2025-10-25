# 回测系统完整指南

## 概述

CryptoSignal回测系统支持两种回测模式：

1. **信号回测** - 基于数据库中已生成的历史信号进行回测
2. **完整流程回测** - 模拟完整workflow（选币+分析+发布+交易）

## 架构

```
ats_backtest/
├── __init__.py          # 模块导出
├── engine.py            # 回测引擎核心
├── data_loader.py       # 数据加载器
├── metrics.py           # 性能指标计算
└── report.py            # 报告生成
```

## 信号回测模式（已完成）

### 功能

- 从数据库加载历史信号
- 模拟开平仓和止盈止损
- 跟踪权益曲线
- 计算性能指标

### 使用方法

```bash
# 基础回测
python3 tools/run_backtest.py --days 30

# 高级选项
python3 tools/run_backtest.py \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --capital 20000 \
  --position-size 0.05 \
  --max-trades 10 \
  --min-prob 0.65 \
  --save-report \
  --export-csv
```

### 参数说明

- `--days N` - 回测最近N天（默认30）
- `--start` / `--end` - 指定时间范围
- `--capital` - 初始资金（默认10000 USDT）
- `--position-size` - 每单仓位比例（默认0.02 = 2%）
- `--max-trades` - 最大同时持仓数（默认5）
- `--ttl` - 信号有效期（小时，默认8）
- `--min-prob` - 最小概率过滤
- `--symbols` - 指定币种
- `--save-report` - 保存JSON报告
- `--export-csv` - 导出CSV
- `--quiet` - 简化输出

## Bug修复记录

### Bug #1: equity_curve格式不匹配 (metrics.py)

**问题**: `_calculate_drawdown` 函数期望 `(timestamp, equity)` 元组格式，但引擎输出的是包含 `{'time', 'equity', 'open_trades', ...}` 的字典格式。

**错误信息**:
```
ValueError: too many values to unpack (expected 2)
```

**修复**: 修改metrics.py中所有访问equity_curve的函数，支持dict和tuple两种格式：

```python
for point in equity_curve:
    if isinstance(point, dict):
        timestamp = point['time']
        equity = point['equity']
    else:
        timestamp, equity = point
```

影响函数：
- `_calculate_drawdown()`
- `calculate_metrics()` (获取final_equity)
- `_calculate_monthly_returns()`

### Bug #2: equity_curve格式不匹配 (report.py)

**问题**: `print_equity_curve` 函数同样期望元组格式。

**错误信息**:
```
KeyError: 1
```

**修复**: 同样支持dict和tuple格式。

### Bug #3: exit_reason大小写敏感

**问题**: engine.py设置exit_reason为小写（'tp1', 'tp2', 'sl'），但metrics.py检查时使用大写（'TP1', 'TP2', 'SL'），导致统计为0。

**修复**: 使用`exit_reason.lower()`统一转小写比较：

```python
exit_reasons = {
    'tp1': len([t for t in trades if t.exit_reason and t.exit_reason.lower() == 'tp1']),
    'tp2': len([t for t in trades if t.exit_reason and t.exit_reason.lower() == 'tp2']),
    'sl': len([t for t in trades if t.exit_reason and t.exit_reason.lower() == 'sl']),
    'expired': len([t for t in trades if t.exit_reason and t.exit_reason.lower() == 'expired']),
}
```

## 测试工具

### 1. generate_test_signals.py

生成模拟历史信号用于测试回测系统。

```bash
# 基础用法
python3 tools/generate_test_signals.py --days 30 --signals 50

# 使用真实API价格
python3 tools/generate_test_signals.py --days 14 --signals 30 --real-prices

# 指定时间范围
python3 tools/generate_test_signals.py \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --signals 100
```

特性：
- 支持Mock价格（默认，无需API）
- 支持真实Binance API价格
- 生成符合系统格式的完整信号
- 包含7维分数、概率、止盈止损
- 自动判断Prime/Watch

### 2. generate_mock_price_data.py

生成模拟K线数据，用于回测缓存。

```bash
# 生成所有币种的Mock数据
python3 tools/generate_mock_price_data.py --days 30

# 生成指定币种
python3 tools/generate_mock_price_data.py \
  --days 30 \
  --symbols BTCUSDT ETHUSDT SOLUSDT
```

特性：
- 生成逼真的OHLCV数据
- 包含随机波动和趋势
- 保存为回测缓存格式
- 支持自定义时间范围

## 性能指标说明

### 基本统计
- **Total Trades** - 总交易数
- **Winning Trades** - 盈利交易数
- **Losing Trades** - 亏损交易数
- **Win Rate** - 胜率

### 盈亏统计
- **Total Return** - 总收益率
- **Total PnL** - 总盈亏金额
- **Average Win/Loss** - 平均盈利/亏损
- **Best/Worst Trade** - 最佳/最差交易
- **Profit Factor** - 利润因子（总盈利/总亏损）

### 风险指标
- **Max Drawdown** - 最大回撤
- **Max DD Duration** - 最大回撤持续时间
- **Sharpe Ratio** - 夏普比率
- **Sortino Ratio** - 索提诺比率
- **Calmar Ratio** - 卡玛比率

### 持仓分析
- **Avg Holding Time** - 平均持仓时间
- **Max Win/Loss Streak** - 最大连胜/连败

### 方向分析
- **Long/Short Trades** - 做多/做空交易数
- **Long/Short Win Rate** - 做多/做空胜率

### 出场原因
- **Take Profit 1/2** - 止盈1/2触发次数
- **Stop Loss** - 止损触发次数
- **Expired** - 过期平仓次数

## 回测结果示例

```
📊 BACKTEST SUMMARY

Trades: 30 | Win Rate: 60.0%
Total Return: +1.02% | Max DD: 0.23%
Profit Factor: 1.94 | Sharpe: 0.32
Final Capital: $10101.64
```

## 注意事项

### 1. 数据要求

- 信号数据：存储在SQLite数据库 `data/database/cryptosignal.db`
- 价格数据：从Binance API获取或使用缓存

### 2. 缓存机制

价格数据会自动缓存到 `data/backtest/cache/` 目录：
- 文件格式：`{SYMBOL}_1h_{START}_{END}.json`
- 支持gzip压缩检测
- 使用 `--no-cache` 强制重新获取

### 3. API限制

Binance API有速率限制：
- 1200 请求/分钟
- 建议使用缓存或Mock数据测试

### 4. 测试环境

如果Binance API不可用（403 Forbidden）：
1. 使用Mock价格生成信号
2. 使用Mock数据生成K线缓存
3. 运行回测系统

## 完整流程回测（开发中）

### 目标

模拟完整的交易workflow：
1. **选币** - Base Pool + Overlay Pool
2. **分析** - analyze_symbol逐个分析
3. **发布** - Prime/Watch判定
4. **交易** - 模拟开平仓

### 优势

- 更真实地反映系统表现
- 测试选币策略有效性
- 发现边缘case
- 优化参数配置

### 使用方法（待实现）

```bash
python3 tools/run_workflow_backtest.py \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --capital 10000
```

## 开发路线图

- [x] 回测引擎核心功能
- [x] 数据加载器（信号+价格）
- [x] 性能指标计算
- [x] 报告生成和导出
- [x] Bug修复（3个）
- [x] 测试工具开发
- [ ] 完整流程回测（选币+分析+发布）
- [ ] 参数优化工具
- [ ] 策略对比分析
- [ ] Web可视化界面

## 相关文档

- [新币策略](./NEW_COIN_STRATEGY.md)
- [选币池更新策略](./POOL_UPDATE_STRATEGY.md)
- [完整工作流程](./COMPLETE_WORKFLOW.md)
