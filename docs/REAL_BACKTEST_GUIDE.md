# 真实数据回测指南

## 📌 重要说明

### 当前回测结果的真实情况

**之前的7天回测使用的是Mock数据**，包括：
- ❌ 模拟的价格数据（generate_mock_price_data.py）
- ❌ 模拟的信号数据（generate_test_signals.py）
- ✅ 回测引擎逻辑正确（已验证）
- ✅ 止盈止损机制正确（已验证）

**参考价值**：
- ✅ 可以验证回测系统的正确性
- ✅ 可以测试不同参数的影响
- ❌ **不能代表真实市场表现**

### 为什么需要在服务器上运行？

在当前环境中，币安API返回 `403 Forbidden`（IP被限制），无法获取真实数据。

**需要在服务器上运行才能：**
- ✅ 访问币安API获取真实K线数据
- ✅ 访问OI（持仓量）数据
- ✅ 使用真实的analyze_symbol分析
- ✅ 生成真实的交易信号

---

## 🚀 在服务器上运行真实回测

### 方案选择

#### ⭐ **推荐：基于固定币种池回测（简单）**

**优点**：
- ✅ 不需要实现复杂的选币逻辑
- ✅ 使用真实K线、OI、CVD数据
- ✅ 能真实验证analyze_symbol效果
- ✅ 能验证止盈止损策略
- ✅ 计算量可控

**缺点**：
- ❌ 没有动态选币过程
- ❌ 可能遗漏一些黑马币

#### **完整流程回测（复杂）**

**需要**：
- 历史24h ticker数据（难以获取）
- 每个时间点重建候选池
- 计算Z24、Triple Sync
- 新币检测

**难点**：
- ❌ 币安不提供历史ticker API
- ❌ 需要预先存储大量数据
- ❌ 计算量巨大

---

## 📋 操作步骤（在服务器上）

### Step 1: 准备环境

```bash
# SSH登录服务器
ssh user@your-server

# 进入项目目录
cd ~/cryptosignal

# 确认币安API可访问
python3 -c "from ats_core.sources.binance_safe import get_klines; print('✅ OK' if get_klines('BTCUSDT','1h',2) else '❌ Failed')"
```

### Step 2: 运行真实回测

#### 方案A：快速回测（7天，30个币，2小时间隔）

```bash
# 这是最推荐的配置
python3 tools/run_real_backtest.py --days 7 --interval 2
```

**预计时间**：10-20分钟
**API调用**：约 (7*24/2) * 30 = 2520 次分析

#### 方案B：密集回测（7天，30个币，1小时间隔）

```bash
# 更密集的扫描
python3 tools/run_real_backtest.py --days 7 --interval 1
```

**预计时间**：20-40分钟
**API调用**：约 (7*24) * 30 = 5040 次分析

#### 方案C：指定币种回测

```bash
# 只回测特定币种（更快）
python3 tools/run_real_backtest.py --days 7 --interval 2 \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT
```

**预计时间**：3-5分钟
**API调用**：约 (7*24/2) * 5 = 420 次分析

### Step 3: 查看结果

```bash
# 查看最新的回测报告
ls -lt data/backtest/reports/ | head -5

# 查看报告内容
cat data/backtest/reports/backtest_*.json | jq .

# 查看数据库中的信号
python3 -c "
from ats_core.database.models import db, Signal
session = db.get_session()
count = session.query(Signal).count()
print(f'数据库中共有 {count} 个信号')
"
```

---

## ⚙️ 配置说明

### 默认币种池（30个）

```python
# Tier 1: 超大市值（10个）
'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT',

# Tier 2: 大市值山寨（10个）
'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'ETCUSDT',
'FILUSDT', 'APTUSDT', 'NEARUSDT', 'ICPUSDT', 'VETUSDT',

# Tier 3: 热门山寨（10个）
'ARBUSDT', 'OPUSDT', 'SUIUSDT', 'INJUSDT', 'TIAUSDT',
'SEIUSDT', 'WLDUSDT', 'RNDRUSDT', 'FETUSDT', 'RENDERUSDT',
```

### 参数建议

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `--days` | 7 | 回测天数，建议从小范围开始 |
| `--interval` | 2 | 扫描间隔（小时），平衡速度和精度 |
| `--symbols` | 默认30个 | 可以指定更少的币种加快速度 |

### 预计资源消耗

| 配置 | 时间 | API调用 | 内存 |
|------|------|---------|------|
| 7天 × 30币 × 2h | 10-20分钟 | ~2500次 | ~500MB |
| 7天 × 30币 × 1h | 20-40分钟 | ~5000次 | ~800MB |
| 7天 × 10币 × 2h | 3-5分钟 | ~840次 | ~200MB |

---

## 🔧 如果遇到问题

### 问题1：币安API 403错误

```
❌ 币安API测试失败: HTTP Error 403: Forbidden
```

**原因**：服务器IP被币安限制

**解决**：
1. 检查是否在国内服务器（需要代理）
2. 检查IP是否被封禁
3. 尝试使用备用API（如果有）

### 问题2：analyze_symbol失败

```
⚠️  BTCUSDT 分析失败: ...
```

**原因**：数据不足、网络问题、币种不存在

**解决**：
- 这是正常的，部分币种可能数据不足
- 如果失败率>30%，检查网络和API
- 可以跳过这些币种

### 问题3：运行时间过长

**优化方案**：
1. 减少币种数量（10-15个）
2. 增大扫描间隔（4小时）
3. 缩短回测时间（3天）

```bash
# 快速测试配置
python3 tools/run_real_backtest.py --days 3 --interval 4 \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT
```

---

## 📊 输出内容

### 1. 终端输出

```
真实数据回测引擎
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 时间范围: 2025-10-18 到 2025-10-25
🪙  币种池: 30个币种
⏱️  扫描间隔: 2小时
💾 保存信号: 是

⏰ [12.5%] 2025-10-19 12:00 | 已生成: 5 (⭐2 + 👀3)
  ⭐ 信号#1: BTCUSDT LONG @ 67234.50 (Prob: 67.8%)
  👀 信号#2: ETHUSDT SHORT @ 3456.78 (Prob: 61.2%)
  ...

扫描统计
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总扫描次数:     84
总分析次数:     2520
成功率:         96.8%
生成信号:       45
  ⭐ Prime:     18 (40.0%)
  👀 Watch:     27 (60.0%)
信号生成率:     1.79%
```

### 2. 回测报告

保存在：`data/backtest/reports/backtest_YYYYMMDD_HHMMSS.json`

包含：
- 详细的交易记录
- 性能指标
- 权益曲线
- 配置信息

### 3. 数据库信号

如果启用了保存（默认启用），信号会保存到：
- 表：`signals`
- 数据库：`data/database/cryptosignal.db`

---

## 💡 最佳实践

### 1. 先小范围测试

```bash
# 测试1天，5个币
python3 tools/run_real_backtest.py --days 1 --interval 2 \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT
```

### 2. 逐步扩大范围

```bash
# 测试3天，15个币
python3 tools/run_real_backtest.py --days 3 --interval 2

# 正式回测7天，30个币
python3 tools/run_real_backtest.py --days 7 --interval 2
```

### 3. 对比不同参数

```bash
# 保存不同配置的结果，对比效果
python3 tools/run_real_backtest.py --days 7 --interval 1  # 密集
python3 tools/run_real_backtest.py --days 7 --interval 2  # 标准
python3 tools/run_real_backtest.py --days 7 --interval 4  # 稀疏
```

### 4. 分析结果

```python
# 对比多次回测结果
import json
from pathlib import Path

reports_dir = Path('data/backtest/reports')
reports = sorted(reports_dir.glob('backtest_*.json'))

for report_file in reports[-5:]:  # 最近5次
    with open(report_file) as f:
        data = json.load(f)
        metrics = data['metrics']
        print(f"{report_file.name}:")
        print(f"  胜率: {metrics['win_rate']*100:.1f}%")
        print(f"  收益: {metrics['total_return']*100:+.2f}%")
        print(f"  盈利因子: {metrics['profit_factor']:.2f}")
        print()
```

---

## 🎯 总结

### Mock数据回测（当前）
- ✅ 验证系统逻辑
- ✅ 快速测试
- ❌ 不能代表真实表现

### 真实数据回测（服务器）
- ✅ 真实市场表现
- ✅ 可信的回测结果
- ❌ 需要服务器环境
- ❌ 需要更长时间

### 行动建议

1. **立即行动**：在服务器上运行简单测试
   ```bash
   python3 tools/run_real_backtest.py --days 1 --symbols BTCUSDT ETHUSDT
   ```

2. **验证效果**：如果运行成功，扩大范围
   ```bash
   python3 tools/run_real_backtest.py --days 7
   ```

3. **分析结果**：基于真实数据优化策略

4. **持续改进**：每周运行一次，监控效果

---

**需要我协助在服务器上运行吗？**

如果您想在服务器上运行，可以：
1. 直接运行上述命令
2. 或者把结果日志发给我，我帮您分析

选币回测确实复杂，**建议先用固定币种池测试**，等系统稳定后再考虑动态选币回测。
