# v6.6 架构设计讨论文档

**时间**: 2025-11-03
**版本**: v6.6 架构设计方案
**状态**: 讨论中

---

## 📋 讨论议题

基于 `ANALYSIS_FI_MODULATORS_AND_QUALITY_FACTORS.md` 的分析，用户提出4个深层次架构问题：

1. **L/S作为调制器**: L和S作为质量指标，和F、I共同作为调制器，这种设计是不是更好？
2. **四门系统必要性**: 逻辑和阈值已经很清楚了，四门系统是否有存在必要？
3. **Q因子数据优化**: Q不需要后，应该不再读取这部分数据，加快加载速度
4. **止盈止损功能**: 发布信号时应该加入入场价和止盈止损

---

## 问题1：L/S/F/I 统一调制器架构

### 1.1 当前方案 (v6.5.1)

**质量指标分类**:

| 指标 | 性质 | 当前用途 | 输出范围 |
|------|------|---------|---------|
| **L** (流动性) | 质量 | 执行层硬门槛（Gate3） | 0-100 |
| **S** (结构) | 质量 | 置信度调制 | ±100 |
| **F** (拥挤度) | 质量/环境 | B层调制器（Teff/cost/p_min） | ±100 |
| **I** (独立性) | 质量/环境 | B层调制器（Teff/cost/p_min） | ±100 |

**架构**:
```
A层(6因子) → edge
B层(F/I) → 调制Teff/cost/p_min
Q层-L → 执行硬门槛
Q层-S → 置信度调制
```

### 1.2 用户建议方案

**统一调制器架构**:

| 指标 | 性质 | 建议用途 | 调制对象 |
|------|------|---------|---------|
| **L** (流动性) | 执行质量 | 调制器 | cost_eff, 仓位 |
| **S** (结构) | 信号质量 | 调制器 | confidence, Teff |
| **F** (拥挤度) | 市场环境 | 调制器 | Teff, p_min |
| **I** (独立性) | 相关性 | 调制器 | Teff, cost_eff |

**架构**:
```
A层(6因子) → edge → probability

B层(4调制器):
  - L: 调制cost_eff, position_size
  - S: 调制confidence, Teff
  - F: 调制Teff, p_min
  - I: 调制Teff, cost_eff
```

### 1.3 深度对比分析

#### 方案A：当前方案（分层使用）

**优势**:
1. **语义清晰**:
   - L的执行风险 → 硬门槛（流动性差=无法成交）
   - S的信号质量 → 软调制（结构差≠拒绝，只是降低置信度）
   - F/I的环境因素 → 参数调制

2. **风控合理**:
   - 流动性是**硬约束**：spread>25bps 或 impact>7bps → 拒绝开仓
   - 避免"流动性陷阱"：即使概率99%，流动性极差也不开仓

3. **实现简单**:
   - 各层职责明确
   - 调试和监控容易

**劣势**:
1. **不够统一**: L/S/F/I都是质量指标，用法却不同
2. **硬门槛风险**: L的硬门槛可能过滤掉一些高收益机会
3. **灵活性差**: 无法根据L的好坏动态调整仓位

---

#### 方案B：统一调制器架构

**优势**:
1. **架构统一**: 所有质量指标都用调制器模式，一致性强

2. **更灵活**:
   - L好 → 100%仓位，L差 → 50%仓位（而不是完全拒绝）
   - S好 → 提高Teff（更激进），S差 → 降低Teff（更保守）
   - F/I/L/S协同作用

3. **平滑调节**: 避免硬门槛的"0或1"，改为连续调节

4. **可扩展**: 未来新增质量指标，直接加入调制器层

**劣势**:
1. **复杂度高**: 4个调制器同时作用，参数调优困难

2. **风控风险**:
   - 流动性极差的币种可能仍会开仓（只是仓位小）
   - 可能导致"小仓位+高滑点"的双重损失

3. **调试困难**: 4个调制器的交互作用难以监控

4. **过度保守**: 4个调制器都作用，可能导致信号量骤减

---

### 1.4 混合方案（推荐）

**设计思路**: L保持硬门槛，S/F/I作为调制器

**理由**:
- **L的特殊性**: 流动性是**执行风险**，不是**预测风险**
  - 流动性差 = 无法成交或高滑点（物理约束）
  - 即使概率100%，流动性差也会导致亏损（滑点>收益）

- **S/F/I的软约束**: 都是**预测/环境风险**
  - 结构差 = 信号可靠性低（可以降低置信度/仓位）
  - 拥挤度高 = 市场环境不利（可以提高门槛）
  - 独立性低 = 跟随大盘（可以更保守）

**架构**:
```
A层(6因子): T/M/C/V/O/B → edge

B层(3调制器):
  - S(结构): 调制confidence, Teff
  - F(拥挤): 调制Teff, p_min
  - I(独立): 调制Teff, cost_eff

硬门槛层:
  - L(流动性): spread≤25bps AND impact≤7bps AND |OBI|≤0.3
```

**调制公式设计**:

```python
# S调制器（结构质量）
structure_quality = (S + 100) / 200  # ±100 → [0,1]
confidence_adj = confidence * (0.7 + 0.6 * structure_quality)
Teff_S = T0 * (0.9 + 0.2 * structure_quality)  # S好→更激进

# F调制器（拥挤度）
F_normalized = (F + 100) / 200
Teff_F = T0 * (1.0 + 0.3 * (F_normalized - 0.5))  # F高→更保守
p_min_F = p0 + 0.05 * (F_normalized - 0.5)

# I调制器（独立性）
I_normalized = (I + 100) / 200
Teff_I = T0 * (1.1 - 0.2 * I_normalized)  # I高→更激进
cost_eff_I = 0.003 - 0.002 * I_normalized  # I高→降低成本惩罚

# 综合Teff
Teff = T0 * (Teff_S/T0) * (Teff_F/T0) * (Teff_I/T0)
Teff = clip(Teff, T_min=25, T_max=100)
```

---

## 问题2：四门系统的必要性

### 2.1 当前四门系统

**实现**: `ats_core/gates/integrated_gates.py`

```python
Gate1: DataQual >= 0.90        # 数据质量
Gate2: EV > 0                  # 期望值
Gate3: Execution OK            # 执行质量（spread/impact/OBI）
Gate4: P >= p_min, ΔP >= Δp_min # 概率阈值
```

**职责分析**:

| 门槛 | 检查内容 | 是否可内化 | 建议 |
|------|---------|-----------|------|
| Gate1 | DataQual >= 0.90 | ✅ 可内化到analyze_symbol开头 | **合并** |
| Gate2 | EV > 0 | ✅ 可内化到概率计算后 | **合并** |
| Gate3 | Execution | ✅ 可内化到L因子硬门槛 | **合并** |
| Gate4 | Probability | ✅ 可内化到概率计算后 | **合并** |

### 2.2 简化方案

**目标**: 移除独立的四门系统，逻辑内化到`analyze_symbol.py`

**新架构**:

```python
def analyze_symbol(...):
    # Step 0: 数据质量检查（原Gate1）
    if dataqual < 0.90:
        return None, {"reject_reason": "DataQual < 0.90"}

    # Step 1-2: 计算因子 + edge
    edge, confidence = scorecard(...)

    # Step 3: B层调制（S/F/I）
    Teff, cost_eff, p_min = modulate(S, F, I)

    # Step 4: 概率计算
    P = map_probability_sigmoid(edge, prior, quality, Teff)

    # Step 5: EV检查（原Gate2）
    EV = calculate_ev(P, cost_eff)
    if EV <= 0:
        return None, {"reject_reason": "EV <= 0"}

    # Step 6: 执行质量检查（原Gate3，基于L因子）
    if spread_bps > 25 or impact_bps > 7 or abs(OBI) > 0.3:
        return None, {"reject_reason": "Execution quality failed"}

    # Step 7: 概率阈值检查（原Gate4）
    if P < p_min or delta_P < delta_p_min:
        return None, {"reject_reason": "Probability threshold failed"}

    # Step 8: 返回信号
    return signal, metadata
```

**优势**:
1. **代码简洁**: 移除`integrated_gates.py`，逻辑集中在`analyze_symbol.py`
2. **性能提升**: 减少函数调用层级
3. **调试方便**: 单文件追踪，容易理解
4. **灵活性强**: 容易调整检查顺序

**劣势**:
1. **analyze_symbol.py变长**: 但可以用子函数拆分
2. **测试复杂度**: 门槛逻辑和计算逻辑耦合

### 2.3 建议

**渐进式简化**:

**Phase 1**: 保留`integrated_gates.py`，但简化为单个函数
```python
def check_publishing_gates(signal_data, exec_metrics):
    """统一的发布门槛检查"""
    checks = {
        "dataqual": signal_data["dataqual"] >= 0.90,
        "ev": signal_data["ev"] > 0,
        "execution": check_execution(exec_metrics),
        "probability": signal_data["P"] >= signal_data["p_min"]
    }
    return all(checks.values()), checks
```

**Phase 2**: 逐步内化到`analyze_symbol.py`，移除独立的gates模块

---

## 问题3：Q因子数据加载优化

### 3.1 当前Q因子数据流

**数据源**: aggTrades（聚合成交数据）

**文件**: `ats_core/pipeline/analyze_symbol.py`

```python
# Line ~345: Q因子计算
if agg_trades is not None:
    try:
        Q, Q_meta = calculate_liquidation(agg_trades, params.get("liquidation", {}))
    except Exception as e:
        Q, Q_meta = 0, {"error": str(e)}
else:
    Q, Q_meta = 0, {"note": "无aggTrades数据"}
```

**数据加载**: `scripts/realtime_signal_scanner.py`

需要检查aggTrades的获取位置。

### 3.2 优化方案

**目标**: Q因子降权后，停止获取和计算，加快扫描速度

**Step 1**: 在params.json中添加开关
```json
{
  "factors_enabled": {
    "T": true,
    "M": true,
    "C": true,
    "S": false,  // 移至质量层
    "V": true,
    "O": true,
    "B": true,
    "Q": false,  // 禁用
    "F": true,
    "I": true
  }
}
```

**Step 2**: 条件加载数据
```python
# realtime_signal_scanner.py
if params["factors_enabled"].get("Q", False):
    agg_trades = fetch_agg_trades(symbol)  # 只有Q启用时才获取
else:
    agg_trades = None

# analyze_symbol.py
if params["factors_enabled"].get("Q", False) and agg_trades:
    Q, Q_meta = calculate_liquidation(agg_trades, ...)
else:
    Q, Q_meta = 0, {"note": "Q因子已禁用"}
```

**预期收益**:
- 减少API调用：每个币节省1次aggTrades请求
- 加快计算：跳过Q因子计算逻辑
- 估计提速：5-10%（200币种 × 50ms/币 = 10秒 → 节省0.5-1秒）

---

## 问题4：入场价和止盈止损

### 4.1 当前信号内容

**查看当前信号格式**:

需要检查`ats_core/outputs/telegram_fmt.py`或信号输出格式。

### 4.2 止盈止损设计

**需求**:
- **入场价**: 基于当前价+滑点估算
- **止损价**: 基于ATR或技术支撑位
- **止盈价**: 基于风险回报比（RR）

**设计方案**:

```python
def calculate_entry_exit_prices(
    side: str,          # "long" or "short"
    close_now: float,   # 当前价格
    atr_now: float,     # 当前ATR
    spread_bps: float,  # 点差
    impact_bps: float,  # 冲击成本
    P: float,           # 概率
    params: dict
) -> dict:
    """
    计算入场价、止损价、止盈价

    Args:
        side: 方向（"long"/"short"）
        close_now: 当前价格
        atr_now: 当前ATR
        spread_bps: 点差（bps）
        impact_bps: 冲击成本（bps）
        P: 胜率
        params: 参数

    Returns:
        {
            "entry_price": 入场价,
            "stop_loss": 止损价,
            "take_profit": 止盈价,
            "rr_ratio": 风险回报比,
            "stop_loss_pct": 止损百分比,
            "take_profit_pct": 止盈百分比
        }
    """
    # 参数
    stop_loss_atr_mult = params.get("stop_loss_atr_mult", 1.5)  # 止损=1.5×ATR
    min_rr_ratio = params.get("min_rr_ratio", 2.0)  # 最小RR=2.0

    # 入场价（考虑滑点）
    slippage_bps = spread_bps / 2 + impact_bps
    slippage_pct = slippage_bps / 10000

    if side == "long":
        entry_price = close_now * (1 + slippage_pct)  # 买入：向上滑点
    else:
        entry_price = close_now * (1 - slippage_pct)  # 卖出：向下滑点

    # 止损价（基于ATR）
    stop_loss_distance = atr_now * stop_loss_atr_mult

    if side == "long":
        stop_loss = entry_price - stop_loss_distance
        stop_loss_pct = -stop_loss_distance / entry_price
    else:
        stop_loss = entry_price + stop_loss_distance
        stop_loss_pct = -stop_loss_distance / entry_price

    # 止盈价（基于RR比）
    # 方法1: 固定RR比
    # take_profit_distance = stop_loss_distance * min_rr_ratio

    # 方法2: 基于概率的动态RR（推荐）
    # RR = (1-P) / P （Kelly公式推导）
    # 例如：P=0.6 → RR=0.4/0.6=0.67，不够吸引力
    # 所以使用：RR = max(min_rr, (1-P)/P)
    kelly_rr = (1 - P) / P if P > 0.5 else min_rr_ratio
    rr_ratio = max(min_rr_ratio, kelly_rr)

    take_profit_distance = stop_loss_distance * rr_ratio

    if side == "long":
        take_profit = entry_price + take_profit_distance
        take_profit_pct = take_profit_distance / entry_price
    else:
        take_profit = entry_price - take_profit_distance
        take_profit_pct = take_profit_distance / entry_price

    return {
        "entry_price": round(entry_price, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "rr_ratio": round(rr_ratio, 2),
        "stop_loss_pct": round(stop_loss_pct * 100, 2),  # 转为百分比
        "take_profit_pct": round(take_profit_pct * 100, 2),
        "slippage_bps": round(slippage_bps, 2)
    }
```

**集成到analyze_symbol**:

```python
# analyze_symbol.py，在返回结果前添加
entry_exit = calculate_entry_exit_prices(
    side="long" if side_long else "short",
    close_now=close_now,
    atr_now=atr_now,
    spread_bps=spread_bps,
    impact_bps=impact_bps,
    P=P_chosen,
    params=params.get("entry_exit", {})
)

result.update(entry_exit)
```

**信号输出格式**:

```
🟢 BTCUSDT 做多信号

📊 信号强度: 78/100
📈 胜率: 68%
💰 期望值: +2.3%

🎯 交易参数:
  入场价: $50,125 (+0.25% 滑点)
  止损价: $49,350 (-1.55%)
  止盈价: $51,900 (+3.54%)
  风险回报比: 1:2.28

⚠️ 风险提示:
  最大损失: -1.55% ($775)
  预期盈利: +3.54% ($1,775)
  建议仓位: 3% (基于置信度78%)
```

---

## 第五部分：v6.6 最终架构建议

### 5.1 架构概览

```
═══════════════════════════════════════════════════════════
                    v6.6 统一架构
═══════════════════════════════════════════════════════════

数据质量检查
    ↓
A层：方向因子 (6个，100%权重)
    T(24%) + M(17%) + C(24%) + V(12%) + O(17%) + B(6%)
    ↓
  edge ∈ [-1, +1]
    ↓
B层：调制器 (3个)
    S(结构) → confidence, Teff
    F(拥挤) → Teff, p_min
    I(独立) → Teff, cost_eff
    ↓
  Teff, cost_eff, p_min, confidence_adj
    ↓
概率计算
    P = sigmoid(edge, Teff)
    ↓
执行质量检查（L因子硬门槛）
    spread ≤ 25bps
    impact ≤ 7bps
    |OBI| ≤ 0.3
    ↓
EV检查
    EV = P × profit - (1-P) × (loss + cost_eff)
    EV > 0
    ↓
概率阈值检查
    P ≥ p_min (动态)
    ΔP ≥ Δp_min
    ↓
计算入场/止损/止盈
    entry_price (考虑滑点)
    stop_loss (基于ATR)
    take_profit (基于RR比)
    ↓
发布信号
```

### 5.2 关键改进

| 项目 | v6.5.1 | v6.6 | 改进 |
|------|--------|------|------|
| A层因子数 | 8个 | 6个 | 简化，S/Q移除 |
| B层调制器 | F/I(2个) | S/F/I(3个) | S加入调制器 |
| 质量硬门槛 | L(执行层) | L(执行层) | 保持 |
| 四门系统 | 独立模块 | 内化到analyze_symbol | 简化 |
| Q因子 | 计算但权重0% | 完全禁用，不获取数据 | 提速5-10% |
| 止盈止损 | ❌ 无 | ✅ 完整实现 | 新增功能 |

### 5.3 实施计划

**Phase 1: 核心重构** (8小时)
1. S因子移至B层调制器（3h）
2. 完成Teff接入（2h）
3. 修复I/F double-tanh bug（1h）
4. Q因子完全禁用（1h）
5. 内化四门系统（1h）

**Phase 2: 新功能** (4小时)
1. 实现入场/止损/止盈计算（2h）
2. 更新信号输出格式（1h）
3. 文档更新（1h）

**Phase 3: 测试与优化** (6小时)
1. 单元测试（2h）
2. 回测验证（3h）
3. 参数调优（1h）

**总计**: 18小时

---

## 第六部分：待确认事项

### 6.1 架构决策

- [ ] **问题1**: 是否采用S/F/I三调制器方案（L保持硬门槛）？
- [ ] **问题2**: 是否简化/移除四门系统？
- [ ] **问题3**: 是否禁用Q因子数据加载？
- [ ] **问题4**: 是否实现入场/止损/止盈功能？

### 6.2 参数待定

- [ ] S调制器参数：`confidence_mult`, `Teff_mult`
- [ ] 止损参数：`stop_loss_atr_mult` (默认1.5?)
- [ ] 止盈参数：`min_rr_ratio` (默认2.0?)
- [ ] L硬门槛：`spread_bps` (25?), `impact_bps` (7?)

### 6.3 技术细节

- [ ] S因子范围转换：±100 → [0,1] 的映射公式
- [ ] 多调制器Teff融合：`Teff = f(Teff_S, Teff_F, Teff_I)`
- [ ] 止盈止损的精确计算逻辑

---

**等待用户确认后执行实施计划**
