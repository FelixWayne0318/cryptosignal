# Prime强度和调制器工作机制详解

**创建时间**: 2025-11-04
**目的**: 详细解释Prime强度计算、B层调制器、四门调节的工作机制

---

## 问题1: Prime强度的16指的是什么？

### 答案：16是**绝对值**，Prime强度只有正值（0-100），没有负值

### 详细解释

**代码位置**: `ats_core/pipeline/analyze_symbol.py:738-782`

```python
prime_strength = 0.0  # 初始化为0

# 1. 基础强度（60分）
base_strength = confidence * 0.6  # confidence是abs(weighted_score)，范围0-100
prime_strength += base_strength   # 0-60分

# 2. 概率加成（40分）
if P_chosen >= 0.60:
    prob_bonus = min(40.0, (P_chosen - 0.60) / 0.15 * 40.0)
    prime_strength += prob_bonus  # 最多+40分

# prime_strength_before_gates范围: 0-100

# 3. 四门调节（乘法，降低0-50%）
gate_multiplier = 0.6 ~ 1.0  # 范围：60%-100%
prime_strength *= gate_multiplier

# prime_strength最终范围: 0-100（只有正值）
```

### 计算实例（PUMPUSDT）

```
输入：
- confidence = 32
- P_chosen = 0.601
- DataQual = 0.90
- Execution = 0.48 (L=0时 → 0.5 + 0/200 = 0.5，但日志显示0.48)
- gates_ev = 0.20
- gates_probability = 0.20

计算过程：
1. base_strength = 32 × 0.6 = 19.2

2. prob_bonus:
   P_chosen = 0.601 >= 0.60 ✓
   prob_bonus = (0.601 - 0.60) / 0.15 × 40.0
              = 0.001 / 0.15 × 40.0
              = 0.27

3. prime_strength_before_gates = 19.2 + 0.27 = 19.47

4. gate_multiplier:
   - DataQual: 0.7 + 0.3 × 0.90 = 0.97
   - Execution: 0.6 + 0.4 × 0.48 = 0.792
   - EV: 0.20 > 0，不惩罚
   - Probability: 0.20 > 0，不惩罚
   - Combined: 0.97 × 0.792 = 0.768

5. prime_strength_final = 19.47 × 0.768 = 14.95 ≈ 15.0
```

### 阈值判断

```python
# analyze_symbol.py:856
prime_strength_threshold = 16  # 成熟币标准阈值

is_prime = (prime_strength >= prime_strength_threshold)
# 15.0 >= 16 → False ❌ 拒绝
```

**结论**:
- Prime强度范围：**0-100**（只有正值，无负值）
- 阈值16指的是：**prime_strength >= 16**
- 不是"±16范围内"

---

## 问题2: B层调制器是怎么工作的？一票否决还是平滑调节？

### 答案：B层调制器是**平滑调节**，**绝不一票否决**

### 核心原则

**代码位置**: `ats_core/modulators/modulator_chain.py:8-12`

```python
"""
核心原则：**不能搞一票否决**
- 所有调制器只做连续调整，无硬拒绝
- L=0 → position_mult=30%（最小仓位，仍可交易）
- S=-100 → confidence降低但不拒绝
- F/I只调整Teff和cost，无阈值门槛
"""
```

### 4个B层调制器的详细工作机制

#### 1. L调制器（流动性）

**影响对象**: 仓位倍数 + 成本调整

```python
# modulator_chain.py:191-259
def _modulate_L(L_score, L_components, symbol):
    # L范围：-100 到 +100

    # 仓位倍数：[0.30, 1.00]
    normalized_L = (L_score + 100.0) / 200.0  # [-100,+100] → [0,1]
    position_mult = 0.30 + 0.70 * sqrt(normalized_L)

    # L=+100 → position_mult = 1.00 (100%仓位)
    # L=0    → position_mult = 0.61 (61%仓位)
    # L=-100 → position_mult = 0.30 (30%仓位) ← **仍可交易！**

    # 成本调整：[-0.20, +0.20]
    cost_eff = -0.20 * (2 * normalized_L - 1)

    # L=+100 → cost_eff = -0.20 (降低成本)
    # L=-100 → cost_eff = +0.20 (增加成本)

    return position_mult, cost_eff, meta
```

**关键点**：
- ❌ **无一票否决**：L=-100时仍有30%最小仓位
- ✅ **平滑调节**：L越低，仓位越小，但永不为0

#### 2. S调制器（结构）

**影响对象**: 信心倍数 + 温度倍数

```python
# modulator_chain.py:261-315
def _modulate_S(S_score, confidence_base):
    # S范围：-100 到 +100
    normalized_S = S_score / 100.0  # [-100,+100] → [-1,+1]

    # 信心倍数：[0.70, 1.30]
    confidence_mult = 1.0 + 0.30 * normalized_S

    # S=+100 → confidence_mult = 1.30 (信心提升30%)
    # S=0    → confidence_mult = 1.00 (不变)
    # S=-100 → confidence_mult = 0.70 (信心降低30%) ← **不拒绝！**

    # 温度倍数：[0.85, 1.15]
    Teff_S = 1.0 - 0.15 * normalized_S

    # S=+100 → Teff=0.85 (P提升)
    # S=-100 → Teff=1.15 (P降低)

    confidence_final = confidence_base * confidence_mult

    return confidence_mult, Teff_S, meta
```

**关键点**：
- ❌ **无一票否决**：S=-100时confidence降低到70%，但不拒绝
- ✅ **平滑调节**：S越差，信心越低，概率越低

#### 3. F调制器（资金领先）

**影响对象**: 温度倍数 + p_min调整

```python
# modulator_chain.py:317-361
def _modulate_F(F_score):
    # F范围：-100 到 +100
    normalized_F = F_score / 100.0

    # 温度倍数：[0.80, 1.20]
    Teff_F = 1.0 - 0.20 * normalized_F

    # F=+100 (资金领先) → Teff=0.80 (P提升)
    # F=-100 (价格领先) → Teff=1.20 (P降低)

    # p_min调整：[-0.02, +0.02]
    p_min_adj = -0.02 * normalized_F

    # F=+100 → p_min_adj=-0.02 (放宽门槛)
    # F=-100 → p_min_adj=+0.02 (收紧门槛)

    return Teff_F, p_min_adj, meta
```

**关键点**：
- ❌ **无一票否决**：F负值时只是降低概率和提高门槛
- ✅ **平滑调节**：无阈值检查

#### 4. I调制器（独立性）

**影响对象**: 温度倍数 + 成本调整

```python
# modulator_chain.py:363-407
def _modulate_I(I_score):
    # I范围：-100 到 +100
    normalized_I = I_score / 100.0

    # 温度倍数：[0.85, 1.15]
    Teff_I = 1.0 - 0.15 * normalized_I

    # I=+100 (独立性高) → Teff=0.85 (P提升)
    # I=-100 (跟随性强) → Teff=1.15 (P降低)

    # 成本调整：[-0.15, +0.15]
    cost_eff = -0.15 * normalized_I

    # I=+100 → cost_eff=-0.15 (降低成本)
    # I=-100 → cost_eff=+0.15 (增加成本)

    return Teff_I, cost_eff, meta
```

**关键点**：
- ❌ **无一票否决**：I负值时只是降低概率和增加成本
- ✅ **平滑调节**：无阈值检查

### 融合机制

```python
# modulator_chain.py:409-448
def _fuse(output, confidence_base):
    # 1. Teff乘法融合（L不参与）
    Teff_final = T0 × Teff_S × Teff_F × Teff_I

    # 2. cost加法融合
    cost_final = cost_base + cost_eff_L + cost_eff_I

    # 3. confidence由S独占
    confidence_final = confidence_base × confidence_mult_S

    return Teff_final, cost_final, confidence_final
```

### 极端情况测试

**测试案例**: L=0, S=-100, F=-80, I=-60

```python
# modulator_chain.py:561-586 (测试代码)
L=0:    position_mult = 0.50 (50%仓位，仍可交易✅)
S=-100: confidence_mult = 0.70 (信心降低30%)
        Teff_S = 1.15 (P降低)
F=-80:  Teff_F = 1.16 (P降低)
I=-60:  Teff_I = 1.09 (P降低)

融合结果:
Teff_final = 2.0 × 1.15 × 1.16 × 1.09 = 2.90
cost_final = 0.0015 + 0.10 + 0.09 = 0.20

P基准 = 70% → P调整后 = 58% (大幅降低)
position = 50% (仍可交易)

结论: 即使所有调制器都极差，仍然不会一票否决！
只是仓位变小（50%）、概率降低（58%）、成本增加
```

---

## 问题3: 四门调节是怎么工作的？一票否决还是平滑调节？

### 答案：四门调节是**平滑调节**，**但DataQual门有软性警告**

### 四门详解

#### Gate 1: DataQual（数据质量）

**计算公式**:

```python
# analyze_symbol.py:702-716
gates_data_qual = 1.0  # 默认值

# 从DataQualMonitor获取
can_publish, gates_data_qual, reason = dataqual_monitor.can_publish_prime(
    symbol, kline_cache=kline_cache
)

# 注意：can_publish布尔值没有被用于一票否决！
# 只使用gates_data_qual（0-1的分数）
```

**影响方式**:

```python
# analyze_symbol.py:757-762
gate_multiplier *= (0.7 + 0.3 * gates_data_qual)

# DataQual=1.0 → multiplier × 1.00 (无影响)
# DataQual=0.9 → multiplier × 0.97 (-3%)
# DataQual=0.8 → multiplier × 0.94 (-6%)
# DataQual=0.5 → multiplier × 0.85 (-15%)
# DataQual=0.0 → multiplier × 0.70 (-30%) ← **仍不拒绝！**
```

**关键点**：
- ❌ **无一票否决**：即使DataQual=0，只是降低30%
- ⚠️ **有软性警告**：can_publish=False时会记录，但不阻止

#### Gate 2: EV（期望值）

**计算公式**:

```python
# analyze_symbol.py:718-722
gates_ev = 2 * P_chosen - 1 - modulator_output.cost_final

# 示例：
# P=0.70, cost=0.002 → EV = 2×0.70 - 1 - 0.002 = 0.398 (有利)
# P=0.55, cost=0.003 → EV = 2×0.55 - 1 - 0.003 = 0.097 (略有利)
# P=0.50, cost=0.002 → EV = 2×0.50 - 1 - 0.002 = -0.002 (不利)
```

**影响方式**:

```python
# analyze_symbol.py:770-773
if gates_ev < 0:
    ev_penalty = max(0.7, 1.0 + gates_ev * 0.3)
    gate_multiplier *= ev_penalty

# EV > 0     → 无影响
# EV = 0     → 无影响
# EV = -0.5  → multiplier × 0.85 (-15%)
# EV = -1.0  → multiplier × 0.70 (-30%) ← **仍不拒绝！**
```

**关键点**：
- ❌ **无一票否决**：EV负值最多降低30%
- ✅ **平滑调节**：EV越负，惩罚越大

#### Gate 3: Execution（执行质量）

**计算公式**:

```python
# analyze_symbol.py:724-729
gates_execution = 0.5 + L / 200.0

# L=+100 → execution=1.0 (优秀)
# L=0    → execution=0.5 (中性)
# L=-100 → execution=0.0 (极差)
```

**影响方式**:

```python
# analyze_symbol.py:764-768
gate_multiplier *= (0.6 + 0.4 * gates_execution)

# Execution=1.0 → multiplier × 1.00 (无影响)
# Execution=0.5 → multiplier × 0.80 (-20%)
# Execution=0.0 → multiplier × 0.60 (-40%) ← **最大惩罚！**
```

**关键点**：
- ❌ **无一票否决**：L=-100时降低40%，但不拒绝
- ⚠️ **影响最大**：这是四门中惩罚最重的（-40%）

#### Gate 4: Probability（概率门）

**计算公式**:

```python
# analyze_symbol.py:731-736
gates_probability = 2 * P_chosen - 1

# P=1.0  → probability=+1.0 (优秀)
# P=0.75 → probability=+0.5 (良好)
# P=0.5  → probability=0.0 (中性)
# P=0.25 → probability=-0.5 (差)
```

**影响方式**:

```python
# analyze_symbol.py:775-778
if gates_probability < 0:
    prob_penalty = max(0.8, 1.0 + gates_probability * 0.2)
    gate_multiplier *= prob_penalty

# P > 0.5  → 无影响
# P = 0.5  → 无影响
# P = 0.25 → multiplier × 0.90 (-10%)
# P = 0.0  → multiplier × 0.80 (-20%) ← **仍不拒绝！**
```

**关键点**：
- ❌ **无一票否决**：P=0时最多降低20%
- ✅ **平滑调节**：P越低，惩罚越大

### 四门综合影响

**最坏情况**（所有门都极差）:

```
DataQual = 0.0  → × 0.70
Execution = 0.0 → × 0.60
EV = -1.0       → × 0.70
Probability=-1.0→ × 0.80

gate_multiplier = 0.70 × 0.60 × 0.70 × 0.80 = 0.235 (降低76.5%)
```

**实际案例**（用户日志PUMPUSDT）:

```
DataQual = 0.90    → × 0.97
Execution = 0.48   → × 0.792
EV = 0.20 > 0      → × 1.0 (无影响)
Probability=0.20>0 → × 1.0 (无影响)

gate_multiplier = 0.97 × 0.792 × 1.0 × 1.0 = 0.768 (降低23.2%)

prime_strength: 19.47 → 14.95
```

---

## 总结

### 问题1答案

**Prime强度的16是绝对值16，范围0-100，无负值**

- prime_strength只有正值（0-100）
- 阈值16表示：prime_strength >= 16
- 不是"±16范围内"

### 问题2答案

**B层调制器是平滑调节，绝不一票否决**

| 调制器 | 影响 | 最坏情况 | 是否拒绝 |
|--------|------|---------|---------|
| L流动性 | 仓位+成本 | position=30%，仍可交易 | ❌ 不拒绝 |
| S结构 | 信心+温度 | confidence×0.70，降低30% | ❌ 不拒绝 |
| F资金领先 | 温度+门槛 | Teff×1.20，P降低 | ❌ 不拒绝 |
| I独立性 | 温度+成本 | Teff×1.15，P降低 | ❌ 不拒绝 |

**核心原则**：所有调制器只做**连续平滑调整**，无硬阈值拒绝。

### 问题3答案

**四门调节是平滑调节，无一票否决**

| 门 | 计算方式 | 影响范围 | 是否拒绝 |
|----|---------|---------|---------|
| DataQual | 数据新鲜度 | multiplier × (0.70~1.00) | ❌ 不拒绝 |
| EV | 期望值 | EV<0时 × (0.70~1.00) | ❌ 不拒绝 |
| Execution | 流动性L | multiplier × (0.60~1.00) | ❌ 不拒绝 |
| Probability | 概率P | P<0.5时 × (0.80~1.00) | ❌ 不拒绝 |

**综合影响**：
- 最坏情况：gate_multiplier = 0.235（降低76.5%）
- 典型情况：gate_multiplier = 0.60-0.85（降低15-40%）
- **全部平滑调节，无硬拒绝**

---

## 附录：为什么还是没有信号？

### 当前阈值：16

### 可能原因分析

#### 1. Prime强度仍然不足

**日志显示**：最高prime_strength ≈ 15分

**问题**：
```
prime_strength = 15.0
阈值 = 16
15.0 < 16 → 仍被拒绝 ❌
```

#### 2. 概率加成几乎为0

**关键瓶颈**：

```python
# analyze_symbol.py:749-751
if P_chosen >= 0.60:
    prob_bonus = min(40.0, (P_chosen - 0.60) / 0.15 * 40.0)
else:
    prob_bonus = 0.0  # ← 大部分币种P_chosen < 0.60
```

**实际情况**（用户日志）：
- P_chosen大多在0.55-0.59之间
- **P_chosen < 0.60 → prob_bonus = 0**
- 损失了40分的潜在加成！

#### 3. 四门调节降低20-30%

**典型情况**：
```
DataQual=0.90 → -3%
Execution=0.48 → -20%（流动性一般）
Combined → -23%

prime_strength: 19 → 15 (降低21%)
```

### 建议方案

#### 方案A：进一步降低阈值到14（推荐）

```python
# analyze_symbol.py:856
prime_strength_threshold = 14  # 从16降到14
```

**预期效果**：
- 15分可以通过
- 可能产生10-30个信号

#### 方案B：降低prob_bonus门槛

```python
# analyze_symbol.py:749
if P_chosen >= 0.55:  # 从0.60降到0.55
    prob_bonus = min(40.0, (P_chosen - 0.55) / 0.20 * 40.0)
```

**预期效果**：
- P_chosen=0.58的币种可以获得+6分加成
- prime_strength从15提升到21
- 更多币种可以通过阈值16

#### 方案C：同时调整阈值和门槛（激进）

```python
prime_strength_threshold = 12  # 阈值降到12
if P_chosen >= 0.55:  # 门槛降到0.55
```

**预期效果**：
- 可能产生30-60个信号
- 需要密切监控信号质量

---

**文档完成时间**: 2025-11-04
**建议下一步**: 将阈值从16降低到14，观察1天后决定是否继续调整
