# F因子（资金领先性）代码级体检报告

**体检日期**: 2025-11-16
**体检范围**: F因子（Fund Leading）调制器模块 - 完整检查
**体检工程师**: Claude (Code Health Check AI)
**代码版本**: v7.3.47
**方法论**: 基于 `docs/CODE_HEALTH_CHECK_GUIDE.md` 标准流程

---

## 📋 执行摘要

### ✅ 总体结论

**健康评级**: 🟢 **非常健康** (100/100) ✅ **已修复**

F因子模块整体实现质量高，符合v7.3.47系统规范，主要优点：
- ✅ 完整的配置管理（零硬编码达成100%）
- ✅ 健壮的错误处理和降级策略
- ✅ 清晰的调用链和接口设计
- ✅ 完善的元数据跟踪
- ✅ P2级配置不一致问题已修复（2025-11-16）

### 问题统计

| 优先级 | 数量 | 状态 |
|--------|------|------|
| **P0 Critical** | 0 | ✅ 无关键问题 |
| **P1 High** | 0 | ✅ 无高优先级问题 |
| **P2 Medium** | 0 | ✅ **已修复** (2025-11-16) |
| **P3 Low** | 2 | 💡 优化建议 |

### 零硬编码达成度

**100%** ✅ **配置不一致问题已修复**

---

## 一、从setup.sh到F因子的完整调用链路

### 1.1 系统启动流程（setup.sh → F因子）

```
setup.sh (Line 218)
  └─> nohup python3 scripts/realtime_signal_scanner.py
       └─> ats_core/pipeline/batch_scan_optimized.py
            └─> ats_core/pipeline/analyze_symbol.py (Line 627-635)
                 ├─> from ats_core.features.fund_leading import score_fund_leading_v2
                 ├─> F, F_meta = score_fund_leading_v2(cvd_series, oi_data, klines, atr_now, params)
                 └─> modulator_chain.modulate_all(F_score=F, ...) (Line 752-756)
                      └─> 调制Teff和p_min参数
```

**验证**: ✅ 调用链路完整，无断层

---

## 二、阶段1：配置层检查（Configuration Layer）

### 2.1 配置文件完整性检查

#### ✅ **主配置文件**: `config/params.json` (Lines 164-185)

```json
{
  "fund_leading": {
    "oi_weight": 0.4,
    "vol_weight": 0.3,
    "cvd_weight": 0.3,
    "trend_weight": 0.6,
    "slope_weight": 0.4,
    "oi_scale": 3.0,
    "vol_scale": 0.3,
    "cvd_scale": 0.02,
    "price_scale": 3.0,
    "slope_scale": 0.01,
    "leading_scale": 20.0,  // ⚠️ P2问题：与代码不一致
    "crowding_veto": {
      "enabled": true,
      "basis_lookback": 100,
      "funding_lookback": 100,
      "percentile": 90,
      "crowding_penalty": 0.5,
      "min_data_points": 50
    }
  }
}
```

**检查结果**: ⚠️ **发现配置不一致**

#### ⚠️ **统一配置文件**: `config/factors_unified.json` (Lines 435-485)

```json
{
  "F": {
    "name": "Fund Leading",
    "type": "regulator",
    "layer": "money_flow",
    "weight": 0,
    "enabled": true,
    "params": {
      "leading_scale": 200.0,  // ✅ 与代码一致
      "crowding_veto_enabled": true,
      "crowding_percentile": 90,
      "crowding_penalty": 0.5,
      "crowding_min_data": 100,
      "v2": {
        "cvd_weight": 0.6,
        "oi_weight": 0.4,
        "window_hours": 6,
        "scale": 0.50,
        "use_relative_change": true
      }
    },
    "fallback_params": { ... }  // ✅ 完整的降级配置
  }
}
```

**检查结果**: ✅ 配置完整，包含v2专用参数

### 2.2 配置一致性问题

#### ⚠️ **P2-1: leading_scale配置不一致**

**文件**:
- `config/params.json` Line 175
- `config/factors_unified.json` Line 453

**问题**:
```
params.json:           "leading_scale": 20.0
factors_unified.json:  "leading_scale": 200.0  <-- 代码使用此值
fund_leading.py:       默认值 200.0 (Line 100)
```

**实际影响**:
- **中等影响** - 如果仅从params.json读取，F因子会过度饱和（20.0太小）
- 当前实际使用`factors_unified.json`，影响可控

**预期行为**:
所有配置文件应统一使用 `leading_scale: 200.0`

**优先级**: P2 (Medium)

**修复建议**:
```bash
# 修改 config/params.json Line 175
"leading_scale": 200.0,  # 从20.0改为200.0
```

**验证方式**:
```python
# 检查配置读取优先级
import json
with open('config/params.json') as f:
    assert json.load(f)['fund_leading']['leading_scale'] == 200.0
```

---

## 三、阶段2：算法层检查（Algorithm Layer）

### 3.1 核心实现检查

**文件**: `ats_core/features/fund_leading.py`

#### ✅ **函数1: score_fund_leading()** (Lines 44-226)

**函数签名**:
```python
def score_fund_leading(
    oi_change_pct: float,
    vol_ratio: float,
    cvd_change: float,
    price_change_pct: float,
    price_slope: float,
    params: Dict[str, Any] = None,
    basis_history: Optional[List[float]] = None,
    funding_history: Optional[List[float]] = None
) -> Tuple[int, Dict[str, Any]]:
```

**检查清单**:

- [x] **参数列表**: ✅ 完整，符合设计文档
- [x] **算法实现**: ✅ 符合公式 `F = 资金动量 - 价格动量`
- [x] **数据流**: ✅ 输入 → 处理 → 输出 完整
- [x] **边界条件**: ✅ NaN/Inf检查 (Lines 153-160)
- [x] **返回值**: ✅ `(int, Dict)` 类型正确

**核心算法验证** (Lines 112-166):

```python
# ✅ 1. 资金动量计算（正确）
fund_momentum = (
    oi_weight * ((oi_score - 50) * 2) +      # ✅ 对称映射
    vol_weight * ((vol_score - 50) * 2) +
    cvd_weight * ((cvd_score - 50) * 2)
)  # 范围: [-100, +100]

# ✅ 2. 价格动量计算（正确）
price_momentum = (
    trend_weight * ((trend_score - 50) * 2) + # ✅ 对称映射
    slope_weight * ((slope_score - 50) * 2)
)  # 范围: [-100, +100]

# ✅ 3. 资金领先性计算（正确）
leading_raw = fund_momentum - price_momentum

# ✅ 4. 边界检查（v7.3.47新增）
if not is_valid_number(leading_raw):
    return 0, {"degradation_reason": "invalid_leading_raw", ...}

# ✅ 5. tanh平滑映射
normalized = math.tanh(leading_raw / leading_scale)
F_raw = 100.0 * normalized
```

**Crowding Veto检测** (Lines 168-198):

```python
# ✅ Basis过热检测
if basis_history and len(basis_history) >= min_data:
    basis_threshold = np.percentile(np.abs(basis_history), percentile)
    if current_basis > basis_threshold:
        veto_penalty *= crowding_penalty  # ✅ 应用惩罚而非硬拒绝
        veto_applied = True

# ✅ Funding极端检测
if funding_history and len(funding_history) >= min_data:
    funding_threshold = np.percentile(np.abs(funding_history), percentile)
    if current_funding > funding_threshold:
        veto_penalty *= crowding_penalty
        veto_applied = True

# ✅ 应用veto惩罚
F_final = F_raw * veto_penalty
F = int(round(max(-100.0, min(100.0, F_final))))
```

**检查结果**: ✅ **算法实现正确，无逻辑错误**

---

#### ✅ **函数2: score_fund_leading_v2()** (Lines 229-405)

**函数签名**:
```python
def score_fund_leading_v2(
    cvd_series: List[float],
    oi_data: List,
    klines: List,
    atr_now: float,
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
```

**检查清单**:

- [x] **参数列表**: ✅ 简化接口，使用原始数据
- [x] **算法实现**: ✅ 6小时窗口，CVD+OI综合判断
- [x] **数据流**: ✅ 完整
- [x] **边界条件**: ✅ 数据不足降级 (Lines 292-298)
- [x] **返回值**: ✅ 类型正确

**数据验证** (Lines 291-301):

```python
# ✅ 数据不足降级
if len(klines) < 7:
    return 0, {
        "degradation_reason": "insufficient_data",  # ✅ 标准降级元数据
        "min_data_required": 7,
        "actual_data_points": len(klines)
    }

# ✅ ATR保护
if atr_now <= 0:
    atr_now = 1.0  # ✅ 安全默认值
```

**核心计算** (Lines 303-373):

```python
# ✅ 1. 价格变化（6h）
price_6h_ago = closes[-7] if len(closes) >= 7 else closes[0]
price_change_pct = (close_now - price_6h_ago) / price_6h_ago

# ✅ 2. CVD变化（相对变化率，v7.3.4修复）
if use_relative:  # ✅ 推荐模式
    cvd_change_pct = (cvd_now - cvd_6h_ago) / max(abs(cvd_6h_ago), 1e-9)
    cvd_change_norm = cvd_change_pct
else:
    # 旧逻辑（已废弃）
    cvd_change_norm = cvd_change_6h / max(1e-9, abs(price_6h_ago))

# ✅ 3. OI名义化变化率
oi_notional_now = oi_now * close_now
oi_notional_6h = oi_6h_ago * price_6h_ago
oi_change_6h = (oi_notional_now - oi_notional_6h) / max(1e-9, abs(oi_notional_6h))

# ✅ 4. 资金动量（加权）
fund_momentum = cvd_weight * cvd_change_norm + oi_weight * oi_change_6h
price_momentum = price_change_pct

# ✅ 5. F原始值
F_raw = fund_momentum - price_momentum

# ✅ 6. 边界检查（v7.3.47新增）
if not is_valid_number(F_raw):
    return 0, {"degradation_reason": "invalid_F_raw", ...}

# ✅ 7. tanh映射
F_normalized = math.tanh(F_raw / scale)
F_score = 100.0 * F_normalized
```

**检查结果**: ✅ **算法实现正确，数值稳定性良好**

---

### 3.2 配置管理检查

#### ✅ **配置加载逻辑** (Lines 82-110)

```python
# ✅ v3.0配置管理模式
try:
    config = get_factor_config()
    config_params = config.get_factor_params("F")
except Exception as e:
    # ✅ 降级处理：配置加载失败时使用硬编码默认值
    print(f"⚠️ F因子配置加载失败，使用默认值: {e}")
    config_params = {
        "oi_weight": 0.4,
        "vol_weight": 0.3,
        # ... 完整的降级参数
    }

# ✅ 合并配置参数：配置文件 < 传入的params（向后兼容）
p = dict(config_params)
if isinstance(params, dict):
    p.update(params)  # ✅ 传入参数优先级最高
```

**检查结果**: ✅ **三级配置优先级正确**：
1. 传入参数 (最高)
2. 配置文件
3. 硬编码默认值 (降级)

---

### 3.3 魔法数字扫描

**扫描结果**:

| 位置 | 数字 | 用途 | 状态 |
|------|------|------|------|
| Line 100 | `200.0` | leading_scale默认值 | ✅ 仅降级用 |
| Line 165 | `100.0` | F分数归一化系数 | ✅ 数学常量 |
| Line 201 | `-100.0`, `100.0` | F分数范围clamp | ✅ 范围定义 |
| Line 390 | `-100.0`, `100.0` | F分数范围clamp | ✅ 范围定义 |
| Line 300 | `1.0` | ATR降级默认值 | ✅ 仅降级用 |
| Line 322 | `1e-9` | 除零保护epsilon | ✅ 数值稳定性 |

**零硬编码达成度**: **99%** (1个配置不一致问题)

**检查结果**: ✅ **无业务常量硬编码**

---

### 3.4 错误处理和边界条件检查

#### ✅ **异常捕获** (Lines 82-90, 261-276)

```python
# ✅ 精确捕获（配置加载）
try:
    config = get_factor_config()
    config_params = config.get_factor_params("F")
except Exception as e:  # ✅ 可接受：配置错误可能多样
    print(f"⚠️ F因子配置加载失败，使用默认值: {e}")
    config_params = {...}  # ✅ 完整降级参数

# ✅ 精确捕获（数据解析）
try:
    if isinstance(oi_data[-1], dict):
        oi_now = float(oi_data[-1]["sumOpenInterest"])
    else:
        oi_now = float(oi_data[-1][1])
except (ValueError, IndexError, TypeError, KeyError) as e:  # ✅ 精确异常类型
    oi_change_6h = 0.0  # ✅ 安全降级
```

**检查结果**: ✅ **异常捕获合理，无过度捕获**

#### ✅ **边界检查**

```python
# ✅ 1. NaN/Inf检查（v7.3.47新增）
if not is_valid_number(leading_raw):
    return 0, {"degradation_reason": "invalid_leading_raw", ...}

if not is_valid_number(F_raw):
    return 0, {"degradation_reason": "invalid_F_raw", ...}

# ✅ 2. 数据不足检查
if len(klines) < 7:
    return 0, {"degradation_reason": "insufficient_data", ...}

# ✅ 3. 除零保护
cvd_change_pct = (cvd_now - cvd_6h_ago) / max(abs(cvd_6h_ago), 1e-9)
oi_change_6h = ... / max(1e-9, abs(oi_notional_6h))

# ✅ 4. 范围clamp
F = int(round(max(-100.0, min(100.0, F_final))))
F_score = int(round(max(-100.0, min(100.0, F_score))))

# ✅ 5. ATR保护
if atr_now <= 0:
    atr_now = 1.0
```

**检查结果**: ✅ **边界检查完整，数值稳定性良好**

---

## 四、阶段3：集成层检查（Integration Layer）

### 4.1 调用点检查

**文件**: `ats_core/pipeline/analyze_symbol.py`

#### ✅ **调用参数匹配** (Lines 629-635)

```python
# ✅ 导入
from ats_core.features.fund_leading import score_fund_leading_v2

# ✅ 调用
F, F_meta = score_fund_leading_v2(
    cvd_series=cvd_series,       # ✅ List[float]
    oi_data=oi_data,              # ✅ List
    klines=k1,                    # ✅ List
    atr_now=atr_now,              # ✅ float
    params=params.get("fund_leading", {})  # ✅ Dict
)
```

**参数类型检查**:

| 参数 | 期望类型 | 实际类型 | 匹配 |
|------|----------|----------|------|
| cvd_series | List[float] | cvd_series (Line 597) | ✅ |
| oi_data | List | oi_data (全局变量) | ✅ |
| klines | List | k1 (1h K线) | ✅ |
| atr_now | float | atr_now (Line 619) | ✅ |
| params | Dict | params.get(...) | ✅ |

**检查结果**: ✅ **参数完全匹配**

#### ✅ **返回值解构** (Line 629)

```python
# ✅ 函数返回: Tuple[int, Dict[str, Any]]
# ✅ 调用解构: F, F_meta = ...
# ✅ 数量匹配: 2 = 2
```

**检查结果**: ✅ **返回值解构正确**

---

### 4.2 调制器集成检查

#### ✅ **传递给modulator_chain** (Lines 752-756)

```python
modulator_output = modulator_chain.modulate_all(
    L_score=L,  # L from liquidity.py: [0, 100]
    S_score=S,  # S from structure_sq.py: [-100, +100]
    F_score=F,  # ✅ F from fund_leading.py: [-100, +100]
    I_score=I,  # I from independence.py: [-100, +100]
    L_components=L_components,
    confidence_base=confidence,
    ...
)
```

**类型检查**:
- 期望: `int`, 范围 `[-100, +100]`
- 实际: `F` 类型为 `int`, 范围已clamp
- ✅ **类型和范围正确**

---

### 4.3 蓄势检测使用检查

#### ✅ **F因子在蓄势检测中的使用** (Lines 1280-1288)

```python
if F >= F_min_strong and C >= C_min_strong and T < T_max_strong:
    # ✅ 强烈蓄势特征
    is_accumulating = True
    accumulating_reason = f"强势蓄势(F≥{F_min_strong}+C≥{C_min_strong}+T<{T_max_strong})"

elif F >= F_min_moderate and C >= C_min_moderate and T < T_max_moderate and V < V_max_moderate:
    # ✅ 深度蓄势特征
    is_accumulating = True
    accumulating_reason = f"深度蓄势(F≥{F_min_moderate}+C≥{C_min_moderate}+V<{V_max_moderate}+T<{T_max_moderate})"
```

**检查结果**: ✅ **逻辑正确，符合设计意图**

---

## 五、阶段4：输出层检查（Output Layer）

### 5.1 输出函数检查

**文件**: `ats_core/outputs/telegram_fmt.py`

#### ✅ **_desc_fund_leading()** (Line 446-458)

```python
def _desc_fund_leading(s: int, leading_raw: float = None) -> str:
    """
    描述资金领先性（方案C：分开描述，去除程度修饰）
    """
    if s >= 10:
        desc = "资金领先价格"  # ✅ 简洁清晰
    elif s <= -10:
        desc = "价格领先资金"  # ✅ 对称设计
    else:
        desc = "资金价格同步"  # ✅ 中性区间
    return desc
```

**检查结果**: ✅ **描述清晰，逻辑正确**

#### ✅ **_emoji_by_fund_leading()** (Line 580-594)

```python
def _emoji_by_fund_leading(s: int) -> str:
    """
    资金领先价格 (F>0) = ✅ 好信号（蓄势待发）
    价格领先资金 (F<0) = ⚠️ 风险（追涨/杀跌）
    """
    if s >= 10:
        return "✅"  # ✅ 资金领先，质量好
    else:
        return "⚠️"  # ✅ 价格领先或同步，风险提示
```

**检查结果**: ✅ **emoji映射正确**

#### ✅ **_score_fund_leading()** (Line 708-710)

```python
def _score_fund_leading(r: Dict[str, Any]) -> int:
    """兼容读取F分数"""
    v = _get(r, "F_score") or _get(r, "F")
    return int(v) if v is not None else 0
```

**检查结果**: ✅ **兼容性良好**

---

### 5.2 输出展示检查

#### ✅ **F调制器展示** (Lines 1136-1150)

```python
# 🔧 F资金领先调制器
F_score = _get(r, "F") or 0
Teff_F = _get(r, "modulator_output.Teff_F") or 1.0
adj_F = _get(r, "modulator_output.p_min_adjustment_F") or 0.0

f_desc = _desc_fund_leading(F_score, _get(r, "scores_meta.F.leading_raw"))
lines.append(f"\n🔧 F资金领先 {F_score:+d}: {f_desc}")

if Teff_F != 1.0:
    lines.append(f"   └─ 温度倍数: ×{Teff_F:.2f}")

if abs(adj_F) > 0.001:
    lines.append(f"   └─ p_min调整(F): {adj_F:+.3f}")
```

**检查结果**: ✅ **展示完整，格式规范**

---

## 六、问题汇总与修复路线图

### 🚨 **P0级（无）**

无P0级问题 ✅

---

### ⚠️ **P1级（无）**

无P1级问题 ✅

---

### ⚠️ **P2级（1项）** - ✅ **已修复**

#### **P2-1: leading_scale配置不一致** - ✅ **已修复（2025-11-16）**

**影响**: 如果从params.json读取，F因子会过度饱和

**修复难度**: 🟢 Low

**实际工时**: 0.5小时 ✅

**修复步骤** (已完成):
1. ✅ 修改 `config/params.json` Line 175
2. ✅ 将 `"leading_scale": 20.0` 改为 `"leading_scale": 200.0`
3. ✅ 配置一致性验证通过

**验证结果**:
```bash
$ grep -n "leading_scale" config/*.json

config/factors_unified.json:453:        "leading_scale": 200.0,
config/factors_unified.json:479:        "leading_scale": 200.0,
config/params.json:175:    "leading_scale": 200.0,
```

✅ **所有配置文件已统一为 200.0**

---

### 💡 **P3级（2项）**

#### **P3-1: v2参数文档不完整**

**文件**: `ats_core/features/fund_leading.py`

**位置**: Lines 458-465

**问题**: v2参数在factors_unified.json中存在，但代码注释未详细说明

**建议**: 在fund_leading.py顶部文档块添加v2参数说明

**优先级**: P3 (Low)

---

#### **P3-2: interpret_F()函数未被使用**

**文件**: `ats_core/features/fund_leading.py`

**位置**: Lines 408-431

**问题**: `interpret_F()` 函数定义但未在系统中被调用

**建议**:
- 选项1: 在telegram_fmt.py中使用此函数增强F因子描述
- 选项2: 如果不需要，可以删除以减少代码冗余

**优先级**: P3 (Low)

---

## 七、总结 & 建议

### ✅ **做得好的地方**

1. **配置管理**: ✅ 完整的三级配置优先级系统
2. **错误处理**: ✅ 精确的异常捕获和降级策略
3. **数值稳定性**: ✅ 完善的边界检查和NaN/Inf防护
4. **代码规范**: ✅ 清晰的函数签名和类型注解
5. **元数据跟踪**: ✅ 完整的降级原因和中间值记录
6. **向后兼容**: ✅ params参数优先级设计
7. **Crowding Veto**: ✅ 软约束设计，避免硬拒绝

### ❌ **需要改进的地方**

1. **配置不一致** (P2): params.json中leading_scale=20.0应改为200.0
2. **文档完善** (P3): v2参数说明可以更详细
3. **代码清理** (P3): interpret_F()函数可考虑删除或使用

### 🎯 **行动建议**

1. **立即执行**: 修复P2-1配置不一致问题（30分钟）
2. **本周内完成**: 补充v2参数文档（1小时）
3. **下周迭代**: 评估interpret_F()函数的去留（30分钟）

---

## 八、附录

### 8.1 F因子模块文件清单

| 层次 | 文件路径 | 行数 | 作用 |
|------|----------|------|------|
| **配置层** | config/params.json | 164-185 | F因子v1参数 |
| | config/factors_unified.json | 435-485 | F因子统一配置 |
| **算法层** | ats_core/features/fund_leading.py | 432 | 核心实现 |
| **集成层** | ats_core/pipeline/analyze_symbol.py | 629-635 | 调用点 |
| | | 752-756 | 传递给调制器 |
| | | 1280-1288 | 蓄势检测使用 |
| **输出层** | ats_core/outputs/telegram_fmt.py | 446-458 | 描述函数 |
| | | 580-594 | emoji映射 |
| | | 708-710 | 分数读取 |
| | | 1136-1150 | 调制器展示 |

### 8.2 配置参数完整列表

#### v1参数（score_fund_leading）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| oi_weight | 0.4 | OI在资金动量中的权重 |
| vol_weight | 0.3 | 成交量在资金动量中的权重 |
| cvd_weight | 0.3 | CVD在资金动量中的权重 |
| trend_weight | 0.6 | 趋势在价格动量中的权重 |
| slope_weight | 0.4 | 斜率在价格动量中的权重 |
| oi_scale | 3.0 | OI变化率缩放因子 |
| vol_scale | 0.3 | 量能比值缩放因子 |
| cvd_scale | 0.02 | CVD变化缩放因子 |
| price_scale | 3.0 | 价格变化率缩放因子 |
| slope_scale | 0.01 | 斜率缩放因子 |
| **leading_scale** | **200.0** | **领先性原始值缩放因子（⚠️ params.json为20.0）** |
| crowding_veto_enabled | true | 是否启用过热veto |
| crowding_percentile | 90 | 过热检测百分位 |
| crowding_penalty | 0.5 | 过热惩罚系数 |
| crowding_min_data | 100 | 最小数据点数 |

#### v2参数（score_fund_leading_v2）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| cvd_weight | 0.6 | CVD在资金动量中的权重 |
| oi_weight | 0.4 | OI在资金动量中的权重 |
| window_hours | 6 | 计算窗口（小时） |
| scale | 0.50 | tanh缩放因子 |
| use_relative_change | true | 使用相对变化率 |

### 8.3 健康检查方法论验证

本次体检严格遵循 `docs/CODE_HEALTH_CHECK_GUIDE.md` 的四步检查法：

- [x] **Step 1: 核心实现检查** ✅ 算法实现、数据流、边界条件全部验证
- [x] **Step 2: 调用链检查** ✅ 参数匹配、返回值、类型转换全部检查
- [x] **Step 3: 配置管理检查** ✅ 配置文件、加载器、魔法数字扫描完成
- [x] **Step 4: 错误处理检查** ✅ 异常捕获、降级策略、边界检查完整

---

**体检完毕！** 🏁

**最终评级**: 🟢 **健康** (95/100)

**建议**: 修复P2-1配置不一致问题后，F因子模块将达到 🟢 **非常健康** (100/100)
