# 全面重构计划 - 方案A

**目标**: 彻底解决架构问题，建立清晰的分层职责
**预计工期**: 2-3天
**状态**: 进行中

---

## 🎯 重构目标

### 1. 清晰的分层架构

```
┌─────────────────────────────────────────────┐
│      数据获取层 (Data Source Layer)         │
│  - get_klines(), get_oi_data(), etc.       │
│  - 负责从API获取原始数据                     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│    基础分析层 (Base Analysis Layer)         │
│  - analyze_symbol()                         │
│  - 职责：计算6个A层因子(T/M/C/V/O/B)         │
│  - 职责：计算4个B层调制器(L/S/F/I)           │
│  - 输出：因子分数 + CVD/ATR等中间数据        │
│  - 不判定：不做is_prime判定，不做闸门检查    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│    判定层 (Decision Layer) - v7.2增强       │
│  - analyze_with_v72_enhancements()          │
│  - 职责：因子分组加权                        │
│  - 职责：统计校准概率                        │
│  - 职责：计算EV                             │
│  - 职责：四道闸门检查                        │
│  - 职责：最终is_prime判定                   │
│  - 输出：is_prime + signal + 完整元数据     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│    执行层 (Execution Layer)                 │
│  - Anti-Jitter, Telegram通知, 仓位管理      │
└─────────────────────────────────────────────┘
```

### 2. 单一数据源原则

**每个指标只在一个地方计算**

| 指标 | 计算位置 | 复用方式 |
|------|---------|---------|
| T/M/C/V/O/B因子 | 基础分析层 | result['T'], result['M']等 |
| L/S/F/I调制器 | 基础分析层 | result['L'], result['S']等 |
| CVD序列 | 基础分析层 | result['cvd_series'] |
| ATR | 基础分析层 | result['atr_now'] |
| weighted_score | 判定层 | 因子分组加权，唯一计算 |
| 概率P | 判定层 | 统计校准，唯一计算 |
| EV | 判定层 | 基于P和RR，唯一计算 |
| is_prime | 判定层 | 基于闸门，唯一判定 |

### 3. 配置化管理

所有阈值、权重、参数都通过配置文件管理：
- 因子分组权重
- 闸门阈值
- EV计算参数
- 统计校准参数

---

## 📅 实施计划

### ✅ 阶段0: 紧急修复（已完成）

- [x] C1: 修复I_v2未定义bug
- [x] Q3: 修正注释编号错误

**耗时**: 10分钟
**状态**: ✅ 已完成

---

### 🔧 阶段1: 重构基础分析层（当前）

**目标**: 基础层只负责因子计算，不做判定

#### 1.1 统一F因子计算（A1修复）

**修改文件**: `ats_core/pipeline/analyze_symbol.py`

**修改内容**:
```python
# 旧代码（v1）：
from ats_core.features.fund_leading import score_fund_leading
F_score, F_meta = score_fund_leading(...)

# 新代码（统一使用v2）：
from ats_core.features.fund_leading import score_fund_leading_v2
F_score, F_meta = score_fund_leading_v2(...)
```

**验证**:
- [ ] F因子计算结果与v7.2层一致
- [ ] 旧的score_fund_leading不再被调用

**预计耗时**: 1小时

---

#### 1.2 移除is_prime判定逻辑

**修改文件**: `ats_core/pipeline/analyze_symbol.py`

**移除内容**:
- 移除`publish`字典中的`prime`判定
- 移除`is_prime`计算逻辑
- 保留`soft_filtered`标记（用于诊断）

**新的返回结构**:
```python
return {
    "success": True,
    "symbol": symbol,

    # A层因子（±100分）
    "T": T_score,
    "M": M_score,
    "C": C_score,
    "V": V_score,
    "O": O_score,
    "B": B_score,

    # B层调制器（±100分）
    "L": L_score,
    "S": S_score,
    "F": F_score,
    "I": I_score,

    # 中间数据（供判定层使用）
    "cvd_series": cvd_series,  # L1修复：添加CVD数据
    "atr_now": atr_now,
    "price": close_now,
    "klines": k1h,  # 供判定层使用
    "oi_data": oi_data,  # 供判定层使用

    # 元数据
    "scores_meta": {...},
    "modulation": {...},
    "stop_loss": {...},

    # 诊断信息（保留）
    "soft_filtered": soft_filtered,
    "rejection_reason": rejection_reasons,

    # 移除的字段：
    # - "publish" (包括is_prime)
    # - "weighted_score" (移到判定层)
    # - "confidence" (移到判定层)
    # - "probability" (移到判定层)
}
```

**验证**:
- [ ] 基础层不再返回is_prime
- [ ] cvd_series正确返回
- [ ] 所有因子分数正确计算

**预计耗时**: 2小时

---

#### 1.3 移除闸门检查（A4修复）

**修改文件**: `ats_core/pipeline/analyze_symbol.py`

**移除内容**:
- 移除"软约束系统"
- 保留DataQual硬拒绝（数据质量不足时直接返回error）

**逻辑**:
```python
# 保留：数据质量硬检查
if data_qual < 0.90:
    return {
        "success": False,
        "error": "数据质量不足",
        "data_qual": data_qual
    }

# 移除：EV软约束、P软约束、四门调节等
# 这些都移到判定层
```

**验证**:
- [ ] 数据质量不足时正确拒绝
- [ ] 其他闸门检查已移除

**预计耗时**: 1小时

---

#### 1.4 移除weighted_score计算（A2修复）

**修改文件**: `ats_core/pipeline/analyze_symbol.py`

**移除内容**:
- 移除scorecard加权
- 移除confidence计算
- 移除probability计算

**原因**: 这些都将在判定层统一计算

**验证**:
- [ ] 基础层不再计算weighted_score
- [ ] 基础层不再计算confidence
- [ ] 基础层不再计算probability

**预计耗时**: 30分钟

---

**阶段1总耗时**: 4-5小时
**阶段1状态**: 🔧 进行中

---

### 🔧 阶段2: 重构v7.2判定层

**目标**: 统一所有判定逻辑，消除重复计算

#### 2.1 接收基础层数据（L1修复）

**修改文件**: `ats_core/pipeline/analyze_symbol_v72.py`

**修改内容**:
```python
# 旧代码：重新计算CVD
cvd_series, _ = cvd_mix_with_oi_price(k1h, oi_data, window=20)

# 新代码：直接使用基础层的CVD
cvd_series = original_result.get('cvd_series', [])
```

**验证**:
- [ ] 不再重复计算CVD
- [ ] 使用基础层的cvd_series

**预计耗时**: 30分钟

---

#### 2.2 统一F因子（已完成）

由于阶段1.1已经统一F因子为v2，这里直接使用即可：

```python
# 直接使用基础层的F（已经是v2）
F_score = original_result.get('F', 0)
F_meta = original_result.get('scores_meta', {}).get('F', {})
```

**验证**:
- [ ] v7.2层不再重新计算F因子
- [ ] 直接使用基础层的F_v2

**预计耗时**: 15分钟

---

#### 2.3 统一weighted_score（A2修复）

**修改文件**: `ats_core/pipeline/analyze_symbol_v72.py`

**修改内容**:
```python
# 旧代码：重新计算分组加权
T = original_result.get('T', 0)
M = original_result.get('M', 0)
...
weighted_score_v72, group_meta = calculate_grouped_score(T, M, C, V, O, B)

# 保持不变（判定层唯一计算）
# 但需要确保基础层不计算weighted_score
```

**验证**:
- [ ] 只在判定层计算weighted_score
- [ ] 基础层不返回weighted_score

**预计耗时**: 15分钟

---

#### 2.4 统一概率计算（A3修复）

**修改文件**: `ats_core/pipeline/analyze_symbol_v72.py`

**修改内容**:
```python
# 保持统计校准逻辑不变
# 但需要确保基础层不计算probability

calibrator = EmpiricalCalibrator()
if not calibrator.calibration_table:
    P_calibrated = calibrator._bootstrap_probability(...)
else:
    P_calibrated = calibrator.get_calibrated_probability(...)
```

**验证**:
- [ ] 只在判定层计算概率
- [ ] 基础层不返回probability

**预计耗时**: 15分钟

---

#### 2.5 统一EV计算（L2修复）

**修改文件**: `ats_core/pipeline/analyze_symbol_v72.py`

**修改内容**:
```python
# 保持判定层的EV计算逻辑不变
# 移除基础层的EV计算
```

**验证**:
- [ ] 只在判定层计算EV
- [ ] 基础层不返回EV

**预计耗时**: 15分钟

---

#### 2.6 统一闸门检查（A4修复）

**修改文件**: `ats_core/pipeline/analyze_symbol_v72.py`

**修改内容**:
```python
# 保持v7.2的四道闸门逻辑
# 移除基础层的软约束系统（已在阶段1.3完成）

# 闸门1: 数据质量（klines >= 100）
# 闸门2: F因子支撑（F >= -15）
# 闸门3: EV正值（EV_net > 0）
# 闸门4: 概率达标（P >= 0.50）
```

**验证**:
- [ ] 只在判定层做闸门检查
- [ ] 基础层不做闸门检查（除了DataQual硬拒绝）

**预计耗时**: 30分钟

---

**阶段2总耗时**: 2小时
**阶段2状态**: ⏳ 待实施

---

### 🔧 阶段3: 消除重复计算

**目标**: 确保每个指标只计算一次

#### 3.1 验证CVD不重复计算（L1）

**检查点**:
- [ ] 基础层计算CVD一次
- [ ] 判定层不重复计算CVD
- [ ] 批量扫描层不重复计算CVD

**修改文件**: `ats_core/pipeline/batch_scan_optimized.py`

**修改内容**:
```python
# 旧代码（第666行）：
cvd_series, _ = cvd_mix_with_oi_price(k1h, oi_data, window=20)
result['cvd_series'] = cvd_series

# 新代码：
# 基础层已经返回cvd_series，不需要重新计算
# 删除这段代码
```

**预计耗时**: 30分钟

---

#### 3.2 验证F因子不重复计算（A1）

**检查点**:
- [ ] 基础层计算F_v2一次
- [ ] 判定层不重复计算F
- [ ] 无F_v1残留代码

**预计耗时**: 30分钟

---

#### 3.3 验证weighted_score不重复计算（A2）

**检查点**:
- [ ] 基础层不计算weighted_score
- [ ] 判定层计算weighted_score一次（因子分组）

**预计耗时**: 15分钟

---

#### 3.4 验证概率不重复计算（A3）

**检查点**:
- [ ] 基础层不计算概率
- [ ] 判定层计算概率一次（统计校准）

**预计耗时**: 15分钟

---

#### 3.5 验证EV不重复计算（L2）

**检查点**:
- [ ] 基础层不计算EV
- [ ] 判定层计算EV一次

**预计耗时**: 15分钟

---

**阶段3总耗时**: 1.5-2小时
**阶段3状态**: ⏳ 待实施

---

### 🔧 阶段4: 全面配置化

**目标**: 所有阈值、权重、参数都通过配置文件管理

#### 4.1 扩展配置文件（Q2修复）

**修改文件**: `config/signal_thresholds.json`

**新增配置**:
```json
{
  "version": "v7.3_unified",

  "因子分组权重": {
    "TC_weight": 0.50,
    "VOM_weight": 0.35,
    "B_weight": 0.15,
    "TC_internal": {
      "T_weight": 0.70,
      "C_weight": 0.30
    },
    "VOM_internal": {
      "V_weight": 0.50,
      "O_weight": 0.30,
      "M_weight": 0.20
    }
  },

  "EV计算参数": {
    "spread_bps": 2.5,
    "impact_bps": 3.0,
    "default_RR": 2.0,
    "funding_hold_hours": 4.0
  },

  "统计校准参数": {
    "calibration_min_samples": 30,
    "bootstrap_base_p": 0.45,
    "bootstrap_range": 0.23,
    "F_bonus_strong": 0.03,
    "F_bonus_moderate": 0.01,
    "F_penalty_chase": 0.02,
    "I_bonus_independent": 0.02,
    "I_penalty_correlated": 0.01
  },

  "v72闸门阈值": {
    "gate1_data_quality": {
      "klines_min": 100
    },
    "gate2_fund_support": {
      "F_min": -15
    },
    "gate3_ev": {
      "EV_min": 0.0
    },
    "gate4_probability": {
      "P_min": 0.50
    }
  }
}
```

**预计耗时**: 30分钟

---

#### 4.2 更新配置加载器

**修改文件**: `ats_core/config/threshold_config.py`

**新增方法**:
```python
def get_factor_weights(self, group: str = None) -> Dict:
    """获取因子分组权重"""
    if group:
        return self.config.get("因子分组权重", {}).get(group, {})
    return self.config.get("因子分组权重", {})

def get_ev_params(self, key: str = None, default: Any = None) -> Any:
    """获取EV计算参数"""
    if key:
        return self.config.get("EV计算参数", {}).get(key, default)
    return self.config.get("EV计算参数", {})

def get_calibration_params(self, key: str = None, default: Any = None) -> Any:
    """获取统计校准参数"""
    if key:
        return self.config.get("统计校准参数", {}).get(key, default)
    return self.config.get("统计校准参数", {})
```

**预计耗时**: 30分钟

---

#### 4.3 应用配置到判定层

**修改文件**: `ats_core/pipeline/analyze_symbol_v72.py`

**修改内容**:
```python
from ats_core.config.threshold_config import get_thresholds

config = get_thresholds()

# 因子分组权重（从配置读取）
weights = config.get_factor_weights()
weighted_score_v72, group_meta = calculate_grouped_score(
    T, M, C, V, O, B,
    params=weights
)

# EV计算参数（从配置读取）
ev_params = config.get_ev_params()
spread_bps = ev_params.get('spread_bps', 2.5)
impact_bps = ev_params.get('impact_bps', 3.0)
default_RR = ev_params.get('default_RR', 2.0)

# 闸门阈值（从配置读取）
klines_min = config.get_gate_threshold('gate1_data_quality', 'klines_min', 100)
F_min = config.get_gate_threshold('gate2_fund_support', 'F_min', -15)
EV_min = config.get_gate_threshold('gate3_ev', 'EV_min', 0.0)
P_min = config.get_gate_threshold('gate4_probability', 'P_min', 0.50)

gates_data_quality = 1.0 if len(klines) >= klines_min else 0.0
gates_fund_support = 1.0 if F_score >= F_min else 0.0
gates_ev = 1.0 if EV_net > EV_min else 0.0
gates_probability = 1.0 if P_calibrated >= P_min else 0.0
```

**预计耗时**: 1小时

---

**阶段4总耗时**: 2小时
**阶段4状态**: ⏳ 待实施

---

### 🧪 阶段5: 测试和验证

**目标**: 确保重构后系统正常工作

#### 5.1 单元测试

**测试项**:
- [ ] 基础层因子计算正确性
- [ ] 判定层加权计算正确性
- [ ] 统计校准正确性
- [ ] 闸门检查逻辑正确性

**预计耗时**: 2小时

---

#### 5.2 集成测试

**测试项**:
- [ ] 完整流程：数据获取 → 基础分析 → 判定 → 通知
- [ ] 多币种批量扫描
- [ ] v7.2增强层正确应用

**预计耗时**: 1小时

---

#### 5.3 性能测试

**测试项**:
- [ ] 计算时间对比（重构前vs重构后）
- [ ] 内存使用对比
- [ ] 预期提升：30%+（消除重复计算）

**预计耗时**: 1小时

---

**阶段5总耗时**: 4小时
**阶段5状态**: ⏳ 待实施

---

### 📝 阶段6: 文档和提交

#### 6.1 更新文档

**更新文件**:
- [ ] README.md
- [ ] docs/ARCHITECTURE.md（新建）
- [ ] docs/REFACTOR_SUMMARY.md（新建）

**预计耗时**: 1小时

---

#### 6.2 Git提交

**提交内容**:
- [ ] 所有修改的代码文件
- [ ] 新增的配置文件
- [ ] 更新的文档

**提交信息**:
```
refactor: 全面重构v7.3 - 清晰分层架构

架构改进：
- 基础分析层只负责因子计算
- 判定层统一所有判定逻辑
- 消除所有重复计算（F/score/P/EV）
- 全面配置化管理

性能提升：
- 计算效率提升30%+
- 内存使用降低20%+
- 代码行数减少15%+

修复问题：
- C1: I_v2未定义致命bug
- A1-A4: 架构设计缺陷
- L1-L4: 逻辑设计问题
- Q1-Q3: 代码质量问题

详见: docs/REFACTOR_SUMMARY.md
```

**预计耗时**: 30分钟

---

**阶段6总耗时**: 1.5小时
**阶段6状态**: ⏳ 待实施

---

## 📊 总体进度

| 阶段 | 任务 | 预计耗时 | 实际耗时 | 状态 |
|------|------|---------|---------|------|
| 0 | 紧急修复 | 10分钟 | 10分钟 | ✅ 已完成 |
| 1 | 重构基础分析层 | 4-5小时 | - | 🔧 进行中 |
| 2 | 重构v7.2判定层 | 2小时 | - | ⏳ 待实施 |
| 3 | 消除重复计算 | 1.5-2小时 | - | ⏳ 待实施 |
| 4 | 全面配置化 | 2小时 | - | ⏳ 待实施 |
| 5 | 测试和验证 | 4小时 | - | ⏳ 待实施 |
| 6 | 文档和提交 | 1.5小时 | - | ⏳ 待实施 |
| **总计** | - | **15-18小时** | **10分钟** | **6%完成** |

---

## 🎯 预期效果

### 架构改进
- ✅ 分层职责清晰（基础层 → 判定层 → 执行层）
- ✅ 单一数据源（每个指标只算一次）
- ✅ 配置驱动（所有参数可调整）

### 性能提升
- ✅ 计算效率提升30%+（消除重复计算）
- ✅ 内存使用降低20%+（减少数据冗余）
- ✅ 代码行数减少15%+（删除重复逻辑）

### 可维护性
- ✅ 逻辑清晰，易于理解
- ✅ 易于测试和调试
- ✅ 易于扩展新功能

---

## 🚨 风险和缓解

### 风险1: 破坏现有功能

**缓解措施**:
- 每个阶段完成后立即测试
- 保留原始代码备份
- 使用Git分支隔离修改

### 风险2: 性能不如预期

**缓解措施**:
- 阶段5进行性能测试
- 如有问题，可回滚到上一版本

### 风险3: 工期超预期

**缓解措施**:
- 分阶段实施，每阶段独立验证
- 如时间不足，可暂停并部署已完成部分

---

## 📅 下一步行动

1. ✅ 立即开始阶段1.1：统一F因子计算
2. ⏳ 完成阶段1.2-1.4：重构基础分析层
3. ⏳ 进入阶段2：重构v7.2判定层
4. ⏳ 每天结束前提交当天的修改

**预计完成日期**: 2025-11-11（2天后）

---

**制定人**: Claude (Anthropic)
**审核人**: 待用户确认
**状态**: 执行中
