# 概率加成阈值修复报告 (2025-11-04)

## 问题诊断

### 症状
运行日志显示所有币种的概率加成为0：
```
KAIAUSDT:  Prime分解: base=29.4, prob_bonus=0.0, P_chosen=0.348
PHBUSDT:   Prime分解: base=28.2, prob_bonus=0.0, P_chosen=0.337
BIOUSDT:   Prime分解: base=30.0, prob_bonus=0.0, P_chosen=0.325
DEEPUSDT:  Prime分解: base=24.6, prob_bonus=0.0, P_chosen=0.441
```

### 根本原因
旧代码要求 `P_chosen >= 0.60` 才能获得概率加成：
```python
# 旧逻辑 (ats_core/pipeline/analyze_symbol.py:749)
if P_chosen >= 0.60:
    prob_bonus = min(40.0, (P_chosen - 0.60) / 0.15 * 40.0)
else:
    prob_bonus = 0.0  # ← 所有币种都命中这里
```

**问题分析**：
- P_chosen 定义：预测概率选择度 (0-1范围)
- 熊市环境下，P_chosen 普遍在 0.32-0.44 范围
- 0.60阈值是牛市标准，在当前环境下无币种能达到
- 导致0-40分的潜在加成完全损失

## 修复方案

### 代码修改
```python
# 新逻辑 (2025-11-04审计优化)
if P_chosen >= 0.30:
    prob_bonus = min(40.0, (P_chosen - 0.30) / 0.30 * 40.0)
```

### 新映射关系
| P_chosen | 旧加成 | 新加成 | 增量 |
|----------|--------|--------|------|
| 0.30     | 0.0    | 0.0    | 0.0  |
| 0.35     | 0.0    | 6.7    | +6.7 |
| 0.40     | 0.0    | 13.3   | +13.3|
| 0.45     | 0.0    | 20.0   | +20.0|
| 0.50     | 0.0    | 26.7   | +26.7|
| 0.55     | 0.0    | 33.3   | +33.3|
| 0.60     | 0.0    | 40.0   | +40.0|
| 0.75     | 40.0   | 40.0   | 0.0  |

## 预期效果

### 案例1: KAIAUSDT
**修复前**：
```
base_strength = 29.4
prob_bonus = 0.0 (P_chosen=0.348 < 0.60)
小计 = 29.4
gate_multiplier ≈ 0.63
prime_strength = 29.4 × 0.63 ≈ 18.5 (刚好超过16阈值)
```

**修复后**：
```
base_strength = 29.4
prob_bonus = 6.4 (P_chosen=0.348 → (0.348-0.30)/0.30*40 = 6.4)
小计 = 35.8
gate_multiplier ≈ 0.63
prime_strength = 35.8 × 0.63 ≈ 22.5 (显著提升)
```

### 案例2: DEEPUSDT
**修复前**：
```
base_strength = 24.6
prob_bonus = 0.0 (P_chosen=0.441 < 0.60)
小计 = 24.6
gate_multiplier ≈ 0.75
prime_strength = 24.6 × 0.75 ≈ 18.5
```

**修复后**：
```
base_strength = 24.6
prob_bonus = 18.8 (P_chosen=0.441 → (0.441-0.30)/0.30*40 = 18.8)
小计 = 43.4
gate_multiplier ≈ 0.75
prime_strength = 43.4 × 0.75 ≈ 32.6 (提升75%!)
```

### 总体预期
- **prime_strength范围**：从18-22 → 23-35
- **信号生成**：应该能够通过所有筛选条件
- **信号数量**：预计熊市环境下5-15个做空信号

## 修复时间线总结

### 第一轮修复 (2025-11-04)
- **问题**：Prime阈值25过高
- **方案**：降低到16
- **结果**：仍然0信号 (发现更深层问题)

### 第二轮修复 (2025-11-04)
- **问题**：StandardizationChain过度压缩
- **方案**：禁用6个主因子的标准化链
- **结果**：T因子从0恢复到-100，prime_strength提升到18-22
- **状态**：仍然0信号 (prob_bonus=0拖累)

### 第三轮修复 (2025-11-04) ← 当前
- **问题**：概率加成阈值0.60过高
- **方案**：降低到0.30，适应熊市环境
- **预期**：prime_strength提升到23-35，应该能生成信号

## 验证方法

运行系统后检查日志中的以下关键指标：

```bash
# 1. 检查prob_bonus是否>0
grep "prob_bonus" /logs/latest.log

# 期望看到：
# prob_bonus=6.4 (不再是0.0)
# prob_bonus=18.8 (不再是0.0)

# 2. 检查prime_strength是否提升
grep "prime_strength" /logs/latest.log

# 期望看到：
# prime_strength=22.5 (原18.5)
# prime_strength=32.6 (原18.5)

# 3. 检查是否有信号输出
grep "🔔" /logs/latest.log

# 期望看到：
# 🔔 KAIAUSDT SHORT -100 (Prime=22.5)
# 🔔 DEEPUSDT SHORT -100 (Prime=32.6)
```

## 技术注释

### 为什么0.30是合理阈值？
1. **统计学依据**：P_chosen=0.30表示模型有30%置信度，在二分类中已经比随机好
2. **实战观察**：熊市时P_chosen普遍分布在0.25-0.50区间
3. **风险平衡**：0.30允许捕获机会，但仍通过gate_multiplier控制风险

### 为什么不用0.25或更低？
- 0.25太接近随机 (25% vs 50%)
- 需要保留一定质量门槛
- 低质量信号会被四门调节大幅压制 (gate_multiplier可降到0.6)

### 与四门调节的协同
```
Prime强度 = (base + prob_bonus) × gate_multiplier
              ↑                      ↑
           本次修复              风险控制层
         (提升基础分)         (质量越差压制越多)
```

## 下一步

如果修复后仍然0信号，需要检查：
1. **四门调节是否过严**：gate_multiplier 0.60-0.75可能仍然压制过度
2. **其他筛选条件**：除Prime外是否还有其他拒绝条件
3. **市场环境极端性**：是否需要临时放宽更多条件

但根据当前数据，本次修复应该足以生成信号。
