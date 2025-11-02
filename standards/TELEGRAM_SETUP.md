# 电报信号发送设置指南

## 📋 系统状态

✅ **系统可以运行了！**

已完成：
- ✅ 四道闸系统（DataQual + EV + Execution + Probability）
- ✅ 电报配置文件
- ✅ 新版信号扫描器（带四道闸）
- ✅ F/I调节器集成

## 🚀 快速开始

### 1. 电报配置已完成

配置文件：`config/telegram.json`

```json
{
  "enabled": true,
  "bot_token": "7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70",
  "chat_id": "-1003142003085"
}
```

**频道信息**：
- Bot: 量灵通@analysis_token_bot
- 频道: 链上望远镜
- Chat ID: -1003142003085

### 2. 运行方式

#### A. 测试模式（不发送电报，仅显示结果）

```bash
# 测试2个币种
python scripts/signal_scanner_v2.py --symbols BTCUSDT,ETHUSDT --dry-run

# 测试5个币种
python scripts/signal_scanner_v2.py --symbols BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT --dry-run
```

#### B. 正式运行（发送到电报）

```bash
# 扫描5个主流币种并发送Prime信号
python scripts/signal_scanner_v2.py

# 自定义币种列表
python scripts/signal_scanner_v2.py --symbols BTCUSDT,ETHUSDT,BNBUSDT
```

### 3. 输出示例

**控制台输出**：
```
============================================================
🚀 CryptoSignal v6.0 信号扫描器 (带四道闸)
============================================================
✅ 电报配置已加载
   频道ID: -1003142003085

📊 开始扫描 5 个币种...
============================================================

[1/5] 🔍 分析 BTCUSDT...
   ✅ 通过全部四道闸
   📈 概率: 72.3%
   💰 EV: 0.0245
   📊 DataQual: 0.952
   📤 已发送到电报

[2/5] 🔍 分析 ETHUSDT...
   ❌ 未通过: 闸2 ev, 闸4 probability

...

============================================================
📊 扫描完成
============================================================
   总扫描: 5 个币种
   通过闸门: 1 个
   被拦截: 4 个
   通过率: 20.0%
============================================================
```

**电报消息格式**：
```
🎯 ✅ CryptoSignal v6.0 信号

📊 交易对: BTCUSDT
💰 价格: $43,521.25
📈 概率: 72.3%

━━━━━━━━━━━━━━━━━━
📋 四道闸检查

✅ 闸1 - 数据质量
   DataQual: 0.952 ≥ 0.900

✅ 闸2 - 期望收益
   EV: 0.0245 > 0.0000
   μ_win: 0.034, μ_loss: 0.014

✅ 闸3 - 执行层
   Spread: 8.5 bps
   Impact: 9.2 bps
   OBI: 0.15

✅ 闸4 - 概率门槛
   p: 0.723 ≥ 0.600
   ΔP: 0.042 ≥ 0.030

━━━━━━━━━━━━━━━━━━
🎛️ B层调节器

F (拥挤度): 0.35
I (独立性): 0.72

━━━━━━━━━━━━━━━━━━
📌 系统信息

🔧 版本: v6.0 + 四道闸
⚡ 架构: A/B/C/D 四层
📦 状态: 通过全部闸门

⏰ 2025-10-31 22:30:15
```

## 🎯 四道闸说明

系统**严格**检查四道闸门，只有**全部通过**才会发送信号：

### 闸1 - 数据质量 (DataQual ≥ 0.90)
- 检查：缺失率、乱序率、延迟、对账
- 目的：确保数据质量可靠
- 公式：`DataQual = 1 - (0.35·miss + 0.15·ooOrder + 0.20·drift + 0.30·mismatch)`

### 闸2 - 期望收益 (EV > 0)
- 检查：期望价值必须为正
- 目的：不发布负期望信号
- 公式：`EV = P·μ_win - (1-P)·μ_loss - cost_eff`

### 闸3 - 执行层 (impact/spread/OBI在限制内)
- 检查：
  - `impact_bps ≤ 10` (标准) / `≤ 7` (新币)
  - `spread_bps ≤ 35` (标准) / `≤ 30` (新币)
  - `|OBI| ≤ 0.30` (标准) / `≤ 0.25` (新币)
- 目的：确保可交易性，避免流动性陷阱

### 闸4 - 概率门槛 (p ≥ p_min, ΔP ≥ Δp_min)
- 检查：概率达标 且 概率变化显著
- 目的：过滤弱信号
- 动态调节：`p_min = p0 + θF·max(0,gF) + θI·min(0,gI)`
  - F高（拥挤）→ 门槛提高
  - I低（相关）→ 门槛提高

## 🔧 系统架构

```
A层（方向因子）
 ├─ T/M/S/V/C/O/Q/L/B
 └─ 输出: 方向分 ∈ [-100, 100]

B层（调节器）
 ├─ F (拥挤度), I (独立性)
 └─ 调节: Teff, cost_eff, p_min
     ⚠️  不参与方向性评分！

C层（执行层）
 ├─ spread_bps, impact_bps, OBI
 └─ 闸3检查

D层（概率→发布）
 ├─ P = σ(S/Teff)
 ├─ EV = P·μ_win - (1-P)·μ_loss - cost
 └─ 四道闸 → 电报
```

## ⚠️ 重要修改

**v6.0 → v6.0+四道闸 变更**：

1. ✅ **F/I已从评分中移除**
   - 旧版：F权重10%, I权重6.7%
   - 新版：F/I仅调节温度/成本/门槛
   - 符合standards/specifications/MODULATORS.md规范

2. ✅ **四道闸必须全部通过**
   - 旧版：仅概率阈值
   - 新版：DataQual + EV + Execution + Probability

3. ✅ **执行层指标**
   - 当前：基于K线OHLC估算（简化版）
   - 后续：可升级为真实depth流计算

## 📊 预期信号数量

四道闸系统**非常严格**，预期通过率：

- **测试数据**：0-10%（随机模拟）
- **实际数据**：10-30%（真实市场）
- **Prime信号**：高质量、低频率

这是**正常的**！四道闸的目的就是**宁缺毋滥**，确保每个信号都有：
- ✅ 可靠的数据质量
- ✅ 正期望收益
- ✅ 良好的流动性
- ✅ 显著的概率优势

## 🚨 使用真实数据

**当前状态**：使用**模拟数据**进行测试

如需使用**真实市场数据**：

1. 替换 `simulate_signal_data()` 函数
2. 连接到实时WebSocket数据流
3. 调用实际的因子计算模块
4. 使用真实的K线和订单簿数据

示例：
```python
# 替换为：
from ats_core.pipeline.analyze_symbol import analyze_symbol
result = analyze_symbol(symbol, klines_1h, klines_4h, ...)
```

## 🔗 相关文件

- 📝 配置：`config/telegram.json`
- 🚀 扫描器：`scripts/signal_scanner_v2.py`
- 🔧 四道闸：`ats_core/gates/integrated_gates.py`
- 📊 EV计算：`ats_core/scoring/expected_value.py`
- 🎛️ F/I调节：`ats_core/modulators/fi_modulators.py`
- 📈 执行指标：`ats_core/execution/metrics_estimator.py`
- 📡 电报发送：`ats_core/outputs/publisher.py`

## ❓ 常见问题

**Q: 为什么没有信号通过？**
A: 四道闸非常严格，模拟数据通过率很低。使用真实数据后会改善。

**Q: 可以降低门槛吗？**
A: 可以调整 `ats_core/gates/integrated_gates.py` 中的阈值，但**不推荐**。四道闸的严格性是为了保证信号质量。

**Q: 如何查看详细日志？**
A: 所有闸门检查结果都会在控制台输出。可以在代码中添加更详细的日志。

**Q: 能否直接使用旧的扫描器？**
A: 可以使用 `scripts/realtime_signal_scanner.py`，但它**没有**四道闸检查，信号质量无法保证。

## 📈 下一步优化

1. **P1**: 集成真实市场数据
2. **P1**: 替换depth流为真实订单簿数据
3. **P1**: WS连接优化（组合流架构）
4. **P2**: 定时扫描功能（每N分钟）
5. **P2**: 信号去重和冷却机制

---

**系统已就绪，可以立即发送信号！** 🚀
