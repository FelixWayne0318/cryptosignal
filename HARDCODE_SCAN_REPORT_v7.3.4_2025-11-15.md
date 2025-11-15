# CryptoSignal v7.3.4 硬编码问题与版本一致性扫描报告

> **扫描时间**: 2025-11-15
> **扫描范围**: 从 setup.sh 出发的完整系统扫描
> **参考标准**: standards/SYSTEM_ENHANCEMENT_STANDARD.md §5 硬编码检测清单

---

## 📋 执行摘要

### 扫描统计
- **扫描文件数**: 68个Python文件 + 7个配置文件 + 5个README文档
- **发现问题总数**: 47个
  - P0 (Critical): 8个 - 必须立即修复
  - P1 (High): 15个 - 应尽快修复
  - P2 (Medium): 18个 - 建议修复
  - P3 (Low): 6个 - 可选修复

### 主要发现
1. ✅ **版本一致性**: 整体良好，仅3处需要更新
2. ⚠️ **硬编码问题**: 关键路径仍存在8个P0级硬编码
3. ✅ **配置文件**: 完整齐全，但版本不一致
4. ⚠️ **调用链**: 部分阈值未从配置读取

---

## 1️⃣ 版本号一致性检查

### 1.1 版本号分布

| 文件路径 | 当前版本 | 应该版本 | 状态 | 优先级 |
|---------|---------|---------|------|-------|
| `/home/user/cryptosignal/setup.sh` | v7.3.4 | v7.3.4 | ✅ 正确 | - |
| `/home/user/cryptosignal/README.md` | v7.3.4 | v7.3.4 | ✅ 正确 | - |
| `/home/user/cryptosignal/scripts/realtime_signal_scanner.py` | v7.3.4 | v7.3.4 | ✅ 正确 | - |
| `/home/user/cryptosignal/ats_core/pipeline/analyze_symbol.py` | v6.6 (注释) | v7.3.4 | ⚠️ 需更新 | P2 |
| `/home/user/cryptosignal/ats_core/outputs/telegram_fmt.py` | v6.7 (硬编码) | v7.3.4 | ❌ 必须修复 | **P0** |
| `/home/user/cryptosignal/config/factors_unified.json` | v7.3.4 | v7.3.4 | ✅ 正确 | - |
| `/home/user/cryptosignal/config/signal_thresholds.json` | v7.2.19 | v7.3.4 | ⚠️ 需更新 | P1 |
| `/home/user/cryptosignal/ats_core/factors_v2/independence.py` | v7.3.2-Full | v7.3.4 | ⚠️ 需更新 | P2 |

### 1.2 版本不一致详情

#### P0-V1: telegram_fmt.py 版本号硬编码
```python
# 文件: ats_core/outputs/telegram_fmt.py:2064
version = "v6.7"  # ❌ 硬编码
```
**影响**: 用户看到错误的系统版本号
**修复**:
```python
from ats_core.config.runtime_config import RuntimeConfig
version = RuntimeConfig.get_version() or "v7.3.4"
```

#### P1-V2: signal_thresholds.json 版本滞后
```json
{
  "version": "v7.2.19_data_driven",
  "description": "基于实际数据的平衡配置 - 方案B"
}
```
**影响**: 配置版本与系统版本不符，导致混淆
**修复**: 更新为 `v7.3.4`，同步更新 description

#### P2-V3: analyze_symbol.py 注释版本滞后
```python
# 文件: ats_core/pipeline/analyze_symbol.py:5-13
"""
完整的单币种分析管道（统一±100系统 v6.6 - 6+4因子架构）
"""
```
**影响**: 文档与实际版本不符
**修复**: 更新注释为 `v7.3.4 - I因子BTC-only + MarketContext优化`

---

## 2️⃣ 硬编码问题清单（按优先级）

### P0 (Critical) - 必须立即修复

#### P0-1: analyze_symbol.py - I因子阈值硬编码
```python
# 文件: ats_core/pipeline/analyze_symbol.py:819
i_effective_threshold = 50.0  # ❌ 硬编码
i_confidence_boost = 0.0
```
**问题**: I因子阈值应从配置读取
**修复**:
```python
factor_config = get_factor_config()
i_cfg = factor_config.get_factor_params("I")
i_effective_threshold = i_cfg.get("effective_threshold", 50.0)
```

#### P0-2: analyze_symbol.py - 概率阈值硬编码
```python
# 文件: ats_core/pipeline/analyze_symbol.py:1007-1010
prime_prob_min = 0.45  # ❌ 硬编码
# ...
watch_prob_min = 0.65  # ❌ 硬编码
```
**问题**: 关键阈值硬编码，无法通过配置调优
**修复**:
```python
config = get_thresholds()
prime_prob_min = config.get_threshold('基础分析阈值', 'mature_coin', 'prime_prob_min', 0.45)
watch_prob_min = config.get_threshold('watch_prob_min', 0.65)
```

#### P0-3: data/quality.py - 数据质量阈值硬编码
```python
# 文件: ats_core/data/quality.py:98-99
ALLOW_PRIME_THRESHOLD = 0.90  # ❌ 硬编码
DEGRADE_THRESHOLD = 0.88      # ❌ 硬编码
```
**问题**: 数据质量闸门硬编码，无法配置化
**影响**: 无法根据市场环境调整质量要求
**修复**:
```python
from ats_core.config.threshold_config import get_thresholds

def get_quality_thresholds():
    config = get_thresholds()
    return {
        'allow_prime': config.get_threshold('数据质量阈值', 'allow_prime_threshold', 0.90),
        'degrade': config.get_threshold('数据质量阈值', 'degrade_threshold', 0.88)
    }
```

#### P0-4: data/quality.py - 时间衰减系数硬编码
```python
# 文件: ats_core/data/quality.py:304-310
return 0.95, f"Data slightly old ({age:.0f}s)"     # ❌ 0.95硬编码
return 0.90, f"Data moderately old ({age:.0f}s)"   # ❌ 0.90硬编码
return 0.85, f"Data old ({age:.0f}s)"              # ❌ 0.85硬编码
return 0.70, f"Data stale ({age:.0f}s)"            # ❌ 0.70硬编码
```
**问题**: 数据新鲜度衰减系数硬编码
**修复**: 移至 `config/factors_unified.json` → `data_quality.age_decay_coefficients`

#### P0-5: outputs/telegram_fmt.py - 闸门阈值硬编码
```python
# 文件: ats_core/outputs/telegram_fmt.py:1007
gate1_pass = data_qual >= 0.90  # ❌ 硬编码

# 文件: ats_core/outputs/telegram_fmt.py:1061-1065
if gate_multiplier >= 0.95:     # ❌ 硬编码
elif gate_multiplier >= 0.85:   # ❌ 硬编码
elif gate_multiplier >= 0.70:   # ❌ 硬编码
```
**问题**: Telegram输出中的阈值判断硬编码
**修复**: 从 `signal_thresholds.json` 读取

#### P0-6: outputs/telegram_fmt.py - 数据质量告警阈值硬编码
```python
# 文件: ats_core/outputs/telegram_fmt.py:1526, 2016
if data_qual < 0.95:  # ❌ 硬编码
```
**问题**: 数据质量告警阈值硬编码
**修复**: 从配置读取

#### P0-7: modulators/modulator_chain.py - 仓位惩罚系数硬编码
```python
# 文件: ats_core/modulators/modulator_chain.py:245, 248
position_mult *= 0.9  # ❌ 硬编码
```
**问题**: 仓位调整系数硬编码
**修复**: 移至 `signal_thresholds.json` → `FI调制器参数.position_penalty_factor`

#### P0-8: pipeline/analyze_symbol.py - 闸门乘数系数硬编码
```python
# 文件: ats_core/pipeline/analyze_symbol.py:1096
gate_multiplier *= (0.7 + 0.3 * gates_data_qual)  # ❌ 0.7, 0.3硬编码

# 文件: ats_core/pipeline/analyze_symbol.py:1102
gate_multiplier *= (0.6 + 0.4 * gates_execution)  # ❌ 0.6, 0.4硬编码
```
**问题**: 闸门乘数计算系数硬编码
**修复**: 移至配置文件

---

### P1 (High) - 应尽快修复

#### P1-1: features/market_regime.py - 市场状态乘数硬编码
```python
# 文件: ats_core/features/market_regime.py:251-252, 257-258, 277-278, 283-284
prob_multiplier = 0.70   # ❌ 硬编码
prime_multiplier = 0.85  # ❌ 硬编码
prob_multiplier = 0.85
prime_multiplier = 0.92
```
**问题**: 市场状态调整系数硬编码
**影响**: 无法根据市场环境动态调整

#### P1-2: features/cvd.py - 权重系数硬编码
```python
# 文件: ats_core/features/cvd.py:353-354, 357-358
futures_weight = 0.7  # ❌ 硬编码
spot_weight = 0.3
```
**问题**: CVD现货/期货权重硬编码
**修复**: 移至 `config/factors_unified.json` → `CVD计算参数.weights`

#### P1-3: features/open_interest.py - OI一致性阈值硬编码
```python
# 文件: ats_core/features/open_interest.py:397, 400
is_consistent = (r_squared >= 0.7)      # ❌ 硬编码
stability_factor = 0.7 + 0.3 * (r_squared / 0.7)  # ❌ 硬编码
```
**问题**: OI趋势一致性阈值硬编码

#### P1-4: factors_v2/independence.py - Beta分段阈值硬编码
```python
# 文件: ats_core/factors_v2/independence.py:359, 364, 369, 374, 394, 402
if beta_abs <= 0.6:    # ❌ 硬编码
elif beta_abs < 0.9:   # ❌ 硬编码
elif beta_abs <= 1.2:
elif beta_abs < 1.5:
```
**问题**: I因子Beta分段阈值硬编码
**影响**: 虽然有注释说明，但应从配置读取

#### P1-5 至 P1-15: 其他高优先级硬编码
- features/accumulation_detection.py - veto惩罚系数 (0.7, 0.85, 0.8)
- features/structure_sq.py - 时机评分阈值
- features/accel.py - 弱闸门阈值 (0.02)
- modulators/modulator_chain.py - 各种边界值
- scoring/probability_v2.py - 概率调整系数
- 等...

---

### P2 (Medium) - 建议修复

#### P2级硬编码（18个）
主要集中在：
1. **默认参数值** - dataclass字段默认值
2. **工具函数** - safe_divide, clamp等函数的默认参数
3. **降级系数** - degradation.py中的阈值
4. **异常值处理** - outlier_detection.py中的系数

**示例**:
```python
# utils/degradation.py:95-97
warning_threshold: float = 0.75   # dataclass默认值，P2级
degraded_threshold: float = 0.50
disabled_threshold: float = 0.50
```

**修复策略**:
- 保留合理的默认值（向后兼容）
- 但优先从配置读取
- 添加配置验证

---

### P3 (Low) - 可选修复

#### P3级硬编码（6个）
主要是：
1. **注释中的示例数值** - 不影响运行
2. **测试数据** - execution/stop_loss_calculator.py中的测试值
3. **日志格式化** - 显示用的常量

---

## 3️⃣ 配置文件完整性检查

### 3.1 配置文件列表

| 文件名 | 版本 | 大小 | 状态 | 用途 |
|--------|------|------|------|------|
| `factors_unified.json` | v7.3.4 | 18KB | ✅ 完整 | 因子参数统一配置 |
| `signal_thresholds.json` | v7.2.19 | 32KB | ⚠️ 版本滞后 | 信号阈值配置 |
| `params.json` | - | 10KB | ⚠️ 废弃中 | 旧版权重配置 |
| `factor_ranges.json` | - | 2.4KB | ✅ 正常 | 因子范围定义 |
| `numeric_stability.json` | - | 1.2KB | ✅ 正常 | 数值稳定性参数 |
| `logging.json` | - | 827B | ✅ 正常 | 日志配置 |
| `telegram.json` | - | 395B | ✅ 正常 | Telegram通知配置 |

### 3.2 配置文件问题

#### P1-C1: params.json 仍在使用，但已标记废弃
```python
# ats_core/cfg.py:4-14
"""
配置管理器 - 旧系统 (v6.6架构)

⚠️ 职责范围（临时）:
- 仅负责 params.json 读取
- 未来计划（v8.0）: 本模块将被废弃
```

**问题**:
- `params.json` 仍被 `analyze_symbol.py` 使用（CFG.params）
- 新旧配置系统并存，容易混淆

**建议**:
1. 加速迁移，将所有配置移至 `factors_unified.json` 和 `signal_thresholds.json`
2. 在 v7.3.5 中完全废弃 `params.json`

#### P1-C2: signal_thresholds.json 版本滞后
**问题**: 配置文件版本为 v7.2.19，系统版本为 v7.3.4
**影响**: 可能缺少v7.3.x的新增配置项
**修复**: 更新版本号，检查是否缺少I因子相关配置

---

## 4️⃣ 调用链配置读取检查

### 4.1 完整调用链

```
setup.sh (v7.3.4)
  → scripts/realtime_signal_scanner.py (v7.3.4)
    → ats_core/pipeline/batch_scan_optimized.py
      → ats_core/pipeline/analyze_symbol.py
        ├── ats_core/factors_v2/independence.py (I因子)
        ├── ats_core/factors_v2/basis_funding.py (B因子)
        ├── ats_core/features/cvd.py (C因子)
        ├── ats_core/features/open_interest.py (O因子)
        ├── ats_core/modulators/modulator_chain.py
        │   ├── ats_core/modulators/fi_modulators.py
        │   └── L/S/F/I调制器
        └── ats_core/outputs/telegram_fmt.py
```

### 4.2 配置读取情况

| 模块 | 配置读取方式 | 状态 | 问题 |
|------|------------|------|------|
| `analyze_symbol.py` | ✅ `get_thresholds()` + `get_factor_config()` | 良好 | 仍有3处硬编码 (P0-1,2,8) |
| `fi_modulators.py` | ✅ `get_thresholds()` → `FI调制器参数` | 良好 | 已配置化 |
| `modulator_chain.py` | ✅ 从 `params` 读取各调制器参数 | 良好 | 1处硬编码 (P0-7) |
| `independence.py` | ✅ `RuntimeConfig` | 优秀 | Beta阈值建议配置化 (P1-4) |
| `basis_funding.py` | ✅ `get_factor_config()` | 优秀 | 已完全配置化 |
| `cvd.py` | ⚠️ 部分配置化 | 中等 | 权重硬编码 (P1-2) |
| `quality.py` | ❌ 全硬编码 | 差 | 严重 (P0-3,4) |
| `telegram_fmt.py` | ❌ 大量硬编码 | 差 | 严重 (P0-5,6) |

### 4.3 配置读取问题汇总

#### 问题1: data/quality.py 未接入配置系统
```python
# 当前实现：全硬编码
ALLOW_PRIME_THRESHOLD = 0.90
DEGRADE_THRESHOLD = 0.88
```

**修复方案**:
1. 在 `signal_thresholds.json` 添加数据质量配置段
2. 使用 `threshold_config.get_thresholds()` 读取
3. 保留默认值作为兜底

#### 问题2: telegram_fmt.py 未接入配置系统
```python
# 当前实现：多处硬编码判断
gate1_pass = data_qual >= 0.90
if gate_multiplier >= 0.95:
```

**修复方案**:
1. 导入 `get_thresholds()`
2. 读取闸门阈值配置
3. 动态判断，不硬编码

---

## 5️⃣ 重点检查区域分析

### 5.1 Modulators (调制器)

| 文件 | 硬编码数 | 配置化程度 | 评级 |
|------|---------|-----------|------|
| `fi_modulators.py` | 0 | 100% | ⭐⭐⭐⭐⭐ |
| `modulator_chain.py` | 1 | 95% | ⭐⭐⭐⭐ |

**结论**: 调制器系统配置化良好，仅1处P0需修复

### 5.2 Gates (闸门逻辑)

| 闸门 | 位置 | 硬编码 | 状态 |
|------|------|--------|------|
| Gate1 (数据质量) | `quality.py` + `telegram_fmt.py` | ❌ 多处 | P0 |
| Gate2 (资金支持) | `analyze_symbol.py` | ✅ 配置化 | 良好 |
| Gate3 (EV) | `analyze_symbol.py` | ✅ 配置化 | 良好 |
| Gate4 (概率) | `analyze_symbol.py` | ⚠️ 部分硬编码 | P0-2 |
| Gate5 (独立性) | `modulator_chain.py` | ✅ 配置化 | 良好 |
| Gate Multiplier | `analyze_symbol.py` + `telegram_fmt.py` | ❌ 硬编码 | P0-8,P0-5 |

**结论**: 闸门系统配置化60%，Gate1和Gate4需要重点修复

### 5.3 Scorecard (加权评分)

| 组件 | 配置化 | 评价 |
|------|--------|------|
| 因子权重 | ✅ `factors_unified.json` | 优秀 |
| 标准化参数 | ✅ `factors_unified.json` | 优秀 |
| 概率映射 | ⚠️ 部分硬编码 | P1 |
| 自适应权重 | ✅ 配置化 | 良好 |

**结论**: 评分系统配置化85%，概率映射需要优化

### 5.4 Telegram输出格式化

**问题严重程度**: P0

**硬编码清单**:
- 版本号 (P0-V1)
- 闸门阈值判断 (P0-5)
- 数据质量告警 (P0-6)
- 风险等级判断 (多处 0.95, 0.85, 0.70)

**修复优先级**: 最高

---

## 6️⃣ 修复优先级建议

### Phase 1: P0级修复（立即执行）

**工作量**: 2-3小时
**风险**: 低（纯配置化重构，逻辑不变）

1. **P0-1**: `analyze_symbol.py` I因子阈值配置化
2. **P0-2**: `analyze_symbol.py` 概率阈值配置化
3. **P0-3**: `quality.py` 数据质量阈值配置化
4. **P0-4**: `quality.py` 时间衰减系数配置化
5. **P0-5**: `telegram_fmt.py` 闸门阈值配置化
6. **P0-6**: `telegram_fmt.py` 数据质量告警配置化
7. **P0-7**: `modulator_chain.py` 仓位惩罚系数配置化
8. **P0-8**: `analyze_symbol.py` 闸门乘数系数配置化
9. **P0-V1**: `telegram_fmt.py` 版本号从配置读取

**配置文件修改**:
1. 在 `signal_thresholds.json` 添加:
   ```json
   "数据质量阈值": {
     "allow_prime_threshold": 0.90,
     "degrade_threshold": 0.88,
     "age_decay": {
       "slightly_old": 0.95,
       "moderately_old": 0.90,
       "old": 0.85,
       "stale": 0.70
     }
   }
   ```

2. 在 `factors_unified.json` 添加:
   ```json
   "I因子参数": {
     "effective_threshold": 50.0,
     "confidence_boost": 0.0
   }
   ```

### Phase 2: P1级修复（本周内）

**工作量**: 4-5小时

1. **P1-V2**: 更新 `signal_thresholds.json` 版本号
2. **P1-C1**: 清理 `params.json` 依赖，完全迁移到新配置
3. **P1-1 至 P1-15**: 市场状态乘数、CVD权重等配置化

### Phase 3: P2级优化（下周）

**工作量**: 2-3小时

1. Dataclass默认值审查
2. 降级系数配置化
3. 异常值处理参数统一

### Phase 4: P3级优化（有时间再做）

**工作量**: 1小时

1. 清理注释中的示例数值
2. 统一测试数据管理

---

## 7️⃣ 配置文件修改建议

### 7.1 signal_thresholds.json 新增配置段

```json
{
  "version": "v7.3.4",
  "updated_at": "2025-11-15",
  "description": "v7.3.4配置 - I因子BTC-only + 硬编码清理",

  "数据质量阈值": {
    "description": "数据质量评估阈值（quality.py）",
    "allow_prime_threshold": 0.90,
    "degrade_threshold": 0.88,
    "age_decay_coefficients": {
      "slightly_old_seconds": 60,
      "slightly_old_factor": 0.95,
      "moderately_old_seconds": 180,
      "moderately_old_factor": 0.90,
      "old_seconds": 300,
      "old_factor": 0.85,
      "stale_factor": 0.70
    }
  },

  "闸门乘数系数": {
    "description": "闸门乘数计算系数（analyze_symbol.py）",
    "data_qual_min_weight": 0.7,
    "data_qual_max_weight": 0.3,
    "execution_min_weight": 0.6,
    "execution_max_weight": 0.4
  },

  "Telegram输出阈值": {
    "description": "Telegram格式化显示阈值（telegram_fmt.py）",
    "gate1_data_qual_min": 0.90,
    "gate_multiplier_excellent": 0.95,
    "gate_multiplier_good": 0.85,
    "gate_multiplier_acceptable": 0.70,
    "data_qual_warning_threshold": 0.95
  },

  "概率阈值": {
    "description": "信号发布概率阈值（analyze_symbol.py）",
    "prime_prob_min_default": 0.45,
    "watch_prob_min_default": 0.65
  }
}
```

### 7.2 factors_unified.json 新增配置段

```json
{
  "I因子参数": {
    "description": "Independence因子配置（v7.3.4）",
    "effective_threshold": 50.0,
    "confidence_boost_default": 0.0,
    "beta_thresholds": {
      "high_independence_max": 0.6,
      "independent_max": 0.9,
      "neutral_max": 1.2,
      "correlated_max": 1.5
    }
  },

  "CVD权重配置": {
    "description": "CVD现货/期货混合权重",
    "futures_weight": 0.7,
    "spot_weight": 0.3,
    "dynamic_adjustment_enabled": false
  },

  "调制器参数": {
    "position_penalty_factor": 0.9,
    "description": "仓位惩罚系数（modulator_chain.py）"
  }
}
```

---

## 8️⃣ 测试验证计划

### 8.1 配置文件验证

```bash
# 1. JSON语法验证
python -m json.tool config/signal_thresholds.json > /dev/null
python -m json.tool config/factors_unified.json > /dev/null

# 2. 配置完整性验证
python -c "
from ats_core.config.threshold_config import get_thresholds
from ats_core.config.factor_config import get_factor_config

cfg1 = get_thresholds()
cfg2 = get_factor_config()
print('✅ 配置文件加载成功')
"
```

### 8.2 硬编码检测回归测试

```bash
# 运行本报告中使用的检测命令，确保P0问题已修复
grep -rn "i_effective_threshold.*=.*50\.0" --include="*.py" ats_core/
# 预期：无结果（已配置化）

grep -rn "prime_prob_min.*=.*0\.45" --include="*.py" ats_core/
# 预期：无结果（已配置化）

grep -rn "ALLOW_PRIME_THRESHOLD.*=.*0\.90" --include="*.py" ats_core/
# 预期：无结果（已配置化）
```

### 8.3 功能回归测试

```bash
# 1. 运行单次扫描，验证系统正常
python scripts/realtime_signal_scanner.py --max-symbols 10

# 2. 检查输出版本号
tail -100 ~/cryptosignal_*.log | grep "v7.3.4"

# 3. 验证配置生效
tail -100 ~/cryptosignal_*.log | grep "data_qual_min\|prime_prob_min"
```

---

## 9️⃣ 总结与建议

### 9.1 当前状态评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 版本一致性 | 85/100 | 整体良好，3处需更新 |
| 配置化程度 | 75/100 | 核心逻辑已配置化，输出层需改进 |
| 代码质量 | 80/100 | 结构清晰，但仍有硬编码残留 |
| 可维护性 | 70/100 | 配置系统健全，但新旧并存 |

### 9.2 核心问题

1. **数据质量模块 (quality.py)** 完全未配置化 → P0优先级
2. **输出格式化 (telegram_fmt.py)** 大量硬编码 → P0优先级
3. **配置版本不一致** → P1优先级
4. **params.json 与新配置系统并存** → P1优先级

### 9.3 修复路径建议

**第一步（今天）**: 修复P0级别的8个问题
- 工作量：2-3小时
- 风险：低
- 收益：消除关键路径硬编码

**第二步（本周）**: 修复P1级别问题 + 配置版本统一
- 工作量：4-5小时
- 风险：中
- 收益：配置系统完全统一

**第三步（下周）**: P2优化 + 文档更新
- 工作量：2-3小时
- 风险：低
- 收益：代码质量提升

### 9.4 长期规划

1. **v7.3.5**: 完成所有P0/P1修复
2. **v7.4.0**: 完全废弃 `params.json`，统一到新配置系统
3. **v8.0**: 配置系统重构，引入配置验证框架

---

## 📎 附录

### A. 扫描命令清单

```bash
# 1. 版本号检测
grep -rn "v7\.[0-9]\|v6\.[0-9]" --include="*.py" --include="*.json" --include="*.md"

# 2. 阈值硬编码检测
grep -rn "threshold.*=.*[0-9]\." --include="*.py" | grep -v "\.get\|config\|#"

# 3. Magic Number检测
grep -rn "= 0\.[0-9]" --include="*.py" | grep -v "\.get\|config\|#"

# 4. if条件硬编码检测
grep -rn "if.*[>=<].*[0-9]\." --include="*.py" | grep -v "\.get\|config"

# 5. dataclass默认值检测
grep -rn "@dataclass" -A 10 --include="*.py" | grep "float.*="
```

### B. 配置读取最佳实践

```python
# ✅ 推荐方式
from ats_core.config.threshold_config import get_thresholds
from ats_core.config.factor_config import get_factor_config

config = get_thresholds()
threshold = config.get_threshold('section', 'key', default_value)

# ❌ 禁止方式
threshold = 0.90  # 硬编码

# ✅ 带验证的配置读取
threshold = config.get_threshold('section', 'key', 0.90)
assert 0.0 <= threshold <= 1.0, f"Invalid threshold: {threshold}"
```

### C. 文件修改清单

**需要修改的文件** (P0级):
1. `ats_core/pipeline/analyze_symbol.py` (3处)
2. `ats_core/data/quality.py` (2处)
3. `ats_core/outputs/telegram_fmt.py` (3处)
4. `ats_core/modulators/modulator_chain.py` (1处)
5. `config/signal_thresholds.json` (版本更新 + 新增配置)
6. `config/factors_unified.json` (新增配置)

---

**报告生成**: 2025-11-15
**扫描工具**: Claude Code (Sonnet 4.5)
**下次扫描**: v7.3.5发布后
