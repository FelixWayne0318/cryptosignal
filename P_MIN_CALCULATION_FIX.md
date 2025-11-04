# P_MIN计算公式过严导致所有信号被过滤

**日期**: 2025-11-04
**问题级别**: 🚨 CRITICAL
**影响范围**: 所有信号（特别是小edge信号）

---

## 问题概述

修复EV计算后，系统扫描200个币种仍产生0个信号。所有信号都被`P < p_min_adjusted`软约束过滤。

## 根本原因

### 当前公式（analyze_symbol.py:647）

```python
base_p_min = 0.58  # 从config读取
safety_margin = 0.005
p_min = base_p_min + safety_margin / (abs(edge) + 1e-6)
p_min_adjusted = p_min + modulator_output.p_min_adj
```

### 问题分析

**公式缺陷**：`safety_margin / abs(edge)` 在edge小时产生过大adjustment。

**实际案例**：

| 币种 | edge | adjustment | p_min | P_chosen | 结果 |
|------|------|-----------|-------|----------|------|
| RENDERUSDT | 0.1141 | 0.044 | 0.624 | 0.552 | ❌ 被拒 |
| GUSDT | 0.1271 | 0.039 | 0.619 | 0.551 | ❌ 被拒 |
| HMSTRUSDT | 0.0834 | 0.060 | 0.640 | 0.566 | ❌ 被拒 |
| INJUSDT | 0.1622 | 0.031 | 0.611 | 0.535 | ❌ 被拒 |

**结论**：即使P>0.55的信号也被过滤，因为动态p_min太高（0.60-0.64）。

## 设计意图 vs 实际效果

### 设计意图（合理）
- edge越小，风险越大，应要求更高的概率
- 通过动态调整p_min实现风险控制

### 实际效果（过严）
- adjustment幅度过大（0.03-0.06）
- 即使是中等概率信号（P=0.55）也被拒绝
- 系统几乎无法产生任何信号

## 修复方案

### 方案1：限制最大adjustment（推荐）

```python
# 修复前
p_min = base_p_min + safety_margin / (abs(edge) + 1e-6)

# 修复后
adjustment = safety_margin / (abs(edge) + 1e-6)
adjustment = min(adjustment, 0.02)  # 限制最大调整为0.02
p_min = base_p_min + adjustment
```

**效果**：
- edge=0.11时，p_min=0.58+0.02=0.60（而不是0.624）
- P=0.55的信号仍被拒（合理）
- P=0.60+的信号可通过

### 方案2：使用对数缩放

```python
import math
adjustment = safety_margin * math.log(1 + 1/abs(edge))
p_min = base_p_min + adjustment
```

**效果**：调整幅度随edge减小缓慢增加。

### 方案3：简化公式（激进）

```python
# 直接使用base_p_min，不做动态调整
p_min = base_p_min  # 0.58
```

**效果**：
- 所有币种统一标准
- 依赖Prime强度来过滤低质量信号
- 简单直接

## 推荐修复

采用**方案1**（限制最大adjustment=0.02）：

```python
# analyze_symbol.py:647
base_p_min = publish_cfg.get("prime_prob_min", 0.58)
safety_margin = modulator_output.L_meta.get("safety_margin", 0.005)

# 修复：限制adjustment最大值，避免过度惩罚小edge信号
adjustment = safety_margin / (abs(edge) + 1e-6)
adjustment = min(adjustment, 0.02)  # 最大调整0.02
p_min = base_p_min + adjustment
```

## 预期效果

### 修复前（当前状态）
- 扫描200币种 → 0个信号
- p_min范围：0.59-0.64
- P>0.55的信号几乎全被拒

### 修复后（预期）
- 扫描200币种 → 10-30个信号
- p_min范围：0.58-0.60
- P>0.60的高质量信号可通过

## 相关修复

### 已完成
1. ✅ EV计算（软约束） - commit 1507ca5
2. ✅ gates_ev计算（显示） - commit d511503

### 待完成
3. ⏳ p_min计算公式限制
4. ⏳ 测试验证信号产生率

## 风险评估

### 修复风险
- 降低p_min可能增加误报率
- 但Prime强度仍会过滤低质量信号

### 不修复风险
- 系统完全无法产生信号
- 失去实用价值

## 结论

p_min计算公式的初衷是合理的，但实现过于激进。通过限制adjustment最大值，可以在保持风险控制的同时恢复系统可用性。

**紧急程度**: 🔥 最高优先级
**修复难度**: ⭐ 简单（1行代码）
**影响范围**: 🌍 全局（所有信号）

---

**状态**: 待修复
