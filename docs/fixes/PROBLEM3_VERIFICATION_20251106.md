# 问题3验证报告：p_min调用链分析

**验证日期**: 2025-11-06
**验证人员**: CryptoSignal v6.7 Compliance Team
**问题描述**: 验证FIModulator计算的p_min是否正确传递到Gate 4

---

## 执行摘要

✅ **FourGatesChecker的调用链是正确的**
⚠️ **发现了两条不同的实现路径**
📋 **建议统一实现方式以确保一致性**

---

## 问题3原始描述

```
调制器链里算出 p_min_final，但 Gate 4 又写死 p_min = 0.68。
修正：Gate 4 统一用 p_min_final；
params.publish.prime_prob_min 充当 base，由 F/I 调制得到 final。
否则"资金领先调制器"对白名单阈值不起作用。
```

**核心担忧**:
- Gate 4是否使用了动态调制的p_min？
- 还是写死了某个值（如0.68）？

---

## 验证过程

### 1. FIModulator的p_min计算

**文件**: `ats_core/modulators/fi_modulators.py:211-261`

```python
def calculate_thresholds(
    self,
    F_raw: float,
    I_raw: float,
    symbol: str = "default"
) -> Tuple[float, float, Dict[str, Any]]:
    """
    计算调整后的发布阈值。

    公式:
    p_min = p0 + θF·max(0, gF) + θI·min(0, gI)
    """
    # Normalize and smooth
    g_F = self.smooth_g(symbol, self.normalize_g(F_raw), is_F=True)
    g_I = self.smooth_g(symbol, self.normalize_g(I_raw), is_F=False)

    # Calculate adjusted p_min
    # High F (crowding) increases threshold (harder to publish)
    # Low I (correlated) increases threshold (harder to publish)
    p_min = self.params.p0 + \
            self.params.theta_F * max(0.0, g_F) + \
            self.params.theta_I * min(0.0, g_I)

    # Clamp to reasonable range
    p_min = max(0.50, min(0.75, p_min))

    return p_min, delta_p_min, details
```

**参数**:
- `p0 = 0.58` (基础阈值)
- `theta_F = 0.03` (F调整系数，拥挤时增加阈值)
- `theta_I = -0.02` (I调整系数，独立时降低阈值)

**范围**: `p_min ∈ [0.50, 0.75]`

---

### 2. Gate 4的定义

**文件**: `ats_core/gates/integrated_gates.py:196-239`

```python
def check_gate4_probability(
    self,
    probability: float,
    p_min: float,           # ✅ 参数传入，不写死
    delta_p: float,
    delta_p_min: float
) -> GateResult:
    """
    Gate 4: Probability threshold.

    Checks:
    - p ≥ p_min
    - ΔP ≥ Δp_min (probability change from previous)
    """
    check_p = probability >= p_min  # ✅ 使用传入的p_min
    check_delta = abs(delta_p) >= delta_p_min

    passes = check_p and check_delta

    return GateResult(...)
```

**结论**: Gate 4本身**不写死**p_min，而是接受参数传入。

---

### 3. FourGatesChecker的调用链

**文件**: `ats_core/gates/integrated_gates.py:241-289`

```python
def check_all_gates(
    self,
    symbol: str,
    probability: float,
    execution_metrics: ExecutionMetrics,
    F_raw: float = 0.5,
    I_raw: float = 0.5,
    delta_p: float = 0.0,
    ...
) -> Tuple[bool, Dict[str, GateResult]]:
    """检查所有四个gates"""

    # ✅ 第271行：调用FIModulator获取modulated值
    modulation = self.fi_modulator.modulate(F_raw, I_raw, symbol)

    # ✅ 第272-274行：提取modulated的值
    cost_eff = modulation["cost_eff"]
    p_min = modulation["p_min"]        # ✅ 获取modulated p_min
    delta_p_min = modulation["delta_p_min"]

    # Check each gate
    results = {
        "gate1_dataqual": self.check_gate1_dataqual(symbol),
        "gate2_ev": self.check_gate2_ev(symbol, probability, cost_eff),
        "gate3_execution": self.check_gate3_execution(...),
        # ✅ 第283行：将modulated p_min传递给Gate 4
        "gate4_probability": self.check_gate4_probability(
            probability, p_min, delta_p, delta_p_min
        )
    }

    all_passed = all(result.passed for result in results.values())
    return all_passed, results
```

**验证结果**: ✅ **调用链完全正确**

- 第271行：`FIModulator.modulate()` 计算 `p_min`
- 第273行：提取 `p_min = modulation["p_min"]`
- 第283行：传递 `p_min` 到 `check_gate4_probability()`
- Gate 4使用传入的动态`p_min`进行检查

---

### 4. 发现：两条不同的实现路径

在验证过程中，我发现系统实际上有**两种不同的p_min实现**：

#### 路径1: FourGatesChecker (integrated_gates.py)

**使用场景**: Shadow Runner, 独立测试

```python
# 使用 FIModulator
modulation = self.fi_modulator.modulate(F_raw, I_raw, symbol)
p_min = modulation["p_min"]  # 完整的p_min值

# 计算公式
p_min = p0 + θF·max(0, gF) + θI·min(0, gI)
# 范围: [0.50, 0.75]
```

**特点**:
- 使用完整的FIModulator
- 计算完整的p_min值
- 包含F和I的双重调制

---

#### 路径2: analyze_symbol.py (主扫描器)

**使用场景**: 实时信号扫描器，批量扫描

```python
# 使用 ModulatorChain
modulator_output = modulator_chain.modulate_all(...)

# 只使用 p_min_adj (调整量)
base_p_min = publish_cfg.get("prime_prob_min", 0.70)  # 基础值
adjustment = safety_margin / (abs(edge) + 1e-6)       # 安全边际调整
p_min_adjusted = base_p_min + adjustment + modulator_output.p_min_adj

# p_min_adj计算（只考虑F，不考虑I）
p_min_adj_range = 0.01  # [-0.01, +0.01]
p_min_adj = -p_min_adj_range * normalized_F
```

**特点**:
- 使用ModulatorChain（不同实现）
- 只使用p_min_adj（调整量），不是完整p_min
- 只考虑F调制，**不考虑I调制**
- 基础值base_p_min = 0.70（高于FIModulator的0.58）

---

## 差异对比表

| 特性 | FIModulator (路径1) | ModulatorChain (路径2) |
|------|---------------------|------------------------|
| **使用场景** | Shadow Runner | 实时扫描器 |
| **基础阈值** | p0 = 0.58 | base_p_min = 0.70 |
| **F调制** | θF=0.03, max(0, gF) | p_min_adj_range=0.01 |
| **I调制** | θI=-0.02, min(0, gI) | ❌ **不考虑I** |
| **计算方式** | 完整p_min值 | base + adjustment + p_min_adj |
| **范围** | [0.50, 0.75] | [0.50, 0.75] |
| **公式** | p0 + θF·gF + θI·gI | 0.70 + safety + p_min_adj |

---

## 示例计算

### 场景: F=0.8 (拥挤), I=0.3 (相关)

**路径1 (FIModulator)**:
```
g_F = tanh(4.0 * (0.8 - 0.5)) = tanh(1.2) ≈ 0.834
g_I = tanh(4.0 * (0.3 - 0.5)) = tanh(-0.8) ≈ -0.664

p_min = 0.58 + 0.03 * max(0, 0.834) + (-0.02) * min(0, -0.664)
      = 0.58 + 0.03 * 0.834 + (-0.02) * (-0.664)
      = 0.58 + 0.025 + 0.013
      = 0.618
```

**路径2 (ModulatorChain)**:
```
normalized_F = (0.8 - 0.5) / 0.5 = 0.6
p_min_adj = -0.01 * 0.6 = -0.006

假设 safety_margin = 0.005, edge = 0.5:
adjustment = 0.005 / 0.5 = 0.01

p_min_adjusted = 0.70 + 0.01 + (-0.006) = 0.704
```

**差异**: 0.704 - 0.618 = **+0.086** (8.6%)

---

## 验证结论

### ✅ 问题3的原始担忧**不成立**

1. **Gate 4不写死p_min**: Gate 4接受参数传入，不硬编码任何值
2. **FIModulator调用链正确**: `modulate() → p_min → check_gate4_probability()`
3. **F/I调制确实起作用**: FIModulator正确计算了F和I的影响

### ⚠️ 发现了新的一致性问题

**两条路径使用不同的实现**:
- FourGatesChecker使用FIModulator（完整公式，包含I）
- analyze_symbol.py使用ModulatorChain（简化版，不含I）

**潜在风险**:
1. **不一致性**: 同样的F/I值，两条路径计算出不同的p_min
2. **I因子缺失**: 主扫描器（路径2）没有考虑I（独立性）调制
3. **基础值不同**: 0.58 vs 0.70，差距12%

---

## 建议

### 短期（本周）

**选项A: 统一到FIModulator**
```python
# analyze_symbol.py中
from ats_core.modulators.fi_modulators import get_fi_modulator

fi_modulator = get_fi_modulator()
modulation = fi_modulator.modulate(F_raw, I_raw, symbol)
p_min = modulation["p_min"]  # 使用完整的FIModulator
```

**优点**:
- 代码统一，逻辑一致
- I因子得到应用
- 与FourGatesChecker完全一致

**缺点**:
- 需要修改analyze_symbol.py
- p_min基础值降低（0.70→0.58），可能增加信号量

---

**选项B: 统一到ModulatorChain**
```python
# integrated_gates.py中
# 改用ModulatorChain的p_min_adj
base_p_min = 0.70
p_min = base_p_min + modulator_output.p_min_adj
```

**优点**:
- 保持当前的高阈值（0.70）
- 改动较小

**缺点**:
- I因子仍然缺失
- 逻辑不如FIModulator完整

---

**选项C: 增强ModulatorChain**
```python
# modulator_chain.py中
# 在_modulate_F中添加I调制
p_min_adj = -p_min_adj_range * normalized_F + theta_I * normalized_I
```

**优点**:
- 补全I因子
- 保持现有架构

**缺点**:
- 需要修改ModulatorChain
- 仍然与FIModulator有差异

---

### 中期（本月）

**统一配置管理**:
```yaml
# system_config.yaml
modulators:
  p_min:
    base: 0.65  # 统一基础值（折中0.58和0.70）
    theta_F: 0.03
    theta_I: -0.02
    range: [0.50, 0.75]
```

**统一计算接口**:
```python
# 新建 ats_core/modulators/unified.py
class UnifiedModulator:
    def calculate_p_min(self, F, I, symbol):
        """统一的p_min计算方法"""
        # 两条路径都调用这个方法
```

---

### 长期（下季度）

**完全统一架构**:
- 废弃ModulatorChain，全部使用FIModulator
- 或者废弃FIModulator，全部使用ModulatorChain
- 但确保只有一种实现

---

## 推荐行动

**立即（今天）**:
1. ✅ **文档化差异**: 本报告已记录差异
2. 📝 **标记TODO**: 在两个文件中添加TODO注释

**本周**:
3. 🔍 **评估影响**: 统计两条路径的使用频率
4. 📊 **对比测试**: 用相同数据测试两条路径的p_min差异

**本月**:
5. 🛠️ **实施统一**: 选择选项A/B/C之一，实施统一
6. ✅ **全面测试**: 确保统一后系统行为符合预期

---

## 附录：代码位置

**FIModulator路径**:
- `ats_core/modulators/fi_modulators.py:211-261` - calculate_thresholds()
- `ats_core/modulators/fi_modulators.py:263-296` - modulate()
- `ats_core/gates/integrated_gates.py:241-289` - check_all_gates()
- `ats_core/gates/integrated_gates.py:196-239` - check_gate4_probability()

**ModulatorChain路径**:
- `ats_core/modulators/modulator_chain.py:327-361` - _modulate_F()
- `ats_core/modulators/modulator_chain.py:98-200` - ModulatorChain class
- `ats_core/pipeline/analyze_symbol.py:537-563` - modulator_chain创建和调用
- `ats_core/pipeline/analyze_symbol.py:646-666` - p_min_adjusted计算

---

**验证完成时间**: 2025-11-06
**结论**: ✅ FourGatesChecker调用链正确 ⚠️ 发现两条路径不一致
**状态**: 问题3原始担忧不成立，但发现了新的一致性问题需要解决
