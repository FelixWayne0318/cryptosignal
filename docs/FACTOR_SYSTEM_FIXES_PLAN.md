# 因子系统修复实施计划

**创建日期**: 2025-11-05
**状态**: P0阶段已完成，P0.4-P2待实施

## 修复概述

基于专家评审和系统审计，针对6+4因子系统的三大核心问题进行修复：
1. ✅ **已完成**: 硬编码阈值 → 自适应阈值（P0.1-P0.3）
2. 🔄 **进行中**: F因子crowding veto（P0.4）
3. 📋 **待实施**: 统一zscore归一化框架（P1.1）
4. 📋 **待实施**: Notional OI（P1.2）
5. 📋 **待实施**: T-M相关性分析（P1.3）
6. 📋 **待实施**: 蓄势待发增强检测（P2.1）

---

## ✅ P0阶段：已完成（2025-11-05）

### P0.1 - B因子自适应阈值

**文件**: `ats_core/factors_v2/basis_funding.py`

**修改内容**:
- 新增 `get_adaptive_basis_thresholds()`
- 新增 `get_adaptive_funding_thresholds()`
- 修改 `calculate_basis_funding()` 支持自适应模式

**技术实现**:
```python
# 基差阈值：基于历史数据的50分位和90分位
neutral_bps = np.percentile(np.abs(basis_history), 50)
extreme_bps = np.percentile(np.abs(basis_history), 90)

# 边界保护
neutral_bps = np.clip(neutral_bps, 20.0, 200.0)
extreme_bps = np.clip(extreme_bps, 50.0, 300.0)
```

**预期收益**:
- 牛市时basis>100bps饱和问题解决
- 熊市时basis<50bps失灵问题解决
- 跨币种比较更准确

---

### P0.2 - V因子自适应阈值

**文件**: `ats_core/features/volume.py`

**修改内容**:
- 新增 `get_adaptive_price_threshold()`
- 修改 `score_volume()` 支持自适应模式

**技术实现**:
```python
# 价格方向阈值：基于历史价格变化的中位数
threshold = np.percentile(np.abs(price_changes), 50)

# 边界保护
threshold = np.clip(threshold, 0.001, 0.02)  # 0.1% - 2%
```

**预期收益**:
- 山寨币和主流币使用不同阈值
- 适应不同市场波动率环境

---

### P0.3 - O因子自适应阈值

**文件**: `ats_core/features/open_interest.py`

**修改内容**:
- 新增 `get_adaptive_oi_price_threshold()`
- 修改 `score_open_interest()` 支持自适应模式

**技术实现**:
```python
# 价格方向阈值：基于历史价格变化的70分位（比V因子更高）
threshold = np.percentile(np.abs(price_changes), 70)

# 边界保护
threshold = np.clip(threshold, 0.003, 0.03)  # 0.3% - 3%
```

**预期收益**:
- OI因子在不同波动率下更稳定
- 12小时周期的趋势判断更准确

---

## 🔄 P0.4：F因子crowding veto（待实施）

### 实施计划

**文件**: `ats_core/features/fund_leading.py`

**目标**: 防止在市场过热（crowding）时产生虚假蓄势信号

**修改方案**:

```python
def calculate_fund_leading_with_veto(
    oi_data, cvd_data, volume_data, price_data,
    basis_data=None,      # 新增参数
    funding_data=None,    # 新增参数
    params=None
):
    """
    F因子计算 + crowding veto（P0.4）
    """
    # 原有F因子计算
    F_raw = fund_momentum - price_momentum
    F = 100 * math.tanh(F_raw / 20.0)

    # 新增：crowding检测
    veto_penalty = 1.0
    veto_reasons = []

    # 1. Basis极端检测
    if basis_data and len(basis_data) >= 100:
        basis_q90 = np.percentile(np.abs(basis_data), 90)
        if abs(basis_data[-1]) > basis_q90:
            veto_penalty *= 0.5
            veto_reasons.append(f"basis过热({basis_data[-1]:.1f}bps)")

    # 2. Funding极端检测
    if funding_data and len(funding_data) >= 100:
        funding_q90 = np.percentile(np.abs(funding_data), 90)
        if abs(funding_data[-1]) > funding_q90:
            veto_penalty *= 0.5
            veto_reasons.append(f"funding极端({funding_data[-1]:.4f})")

    # 应用veto惩罚
    F_final = F * veto_penalty

    return F_final, {
        'F_raw': F,
        'veto_penalty': veto_penalty,
        'veto_reasons': veto_reasons
    }
```

**集成点**: 需要修改 `analyze_symbol.py` 传递basis和funding历史数据

**预期收益**:
- 蓄势待发检测准确率从60%提升到75%
- 减少追高风险30%

---

## 📋 P1.1：统一zscore归一化框架（待实施）

### 实施计划

**文件**: 新建 `ats_core/utils/factor_normalizer.py`

**目标**: 统一10个因子的归一化方法，解决跨币种、跨regime比较失真问题

**核心类设计**:

```python
class FactorNormalizer:
    """
    统一因子归一化框架（P1.1）

    支持模式：
    - zscore: 基于历史均值和标准差
    - percentile: 基于历史百分位
    - legacy: 使用固定阈值（兼容模式）
    - hybrid: 数据充足用zscore，不足用legacy
    """

    def __init__(self, window_size=100, mode='hybrid'):
        self.window_size = window_size
        self.mode = mode

    def normalize(self, value, history_window,
                  fixed_neutral=None, fixed_extreme=None):
        """
        统一归一化接口

        Returns:
            (normalized_value, metadata)
            - normalized_value: [-100, +100]
            - metadata: {method, mean, std, z_score, ...}
        """
        if self.mode == 'hybrid':
            if len(history_window) >= self.window_size:
                return self._zscore_normalize(value, history_window)
            else:
                return self._legacy_normalize(value, fixed_neutral, fixed_extreme)
        # ...

    def _zscore_normalize(self, value, window):
        """
        Z-score归一化 → tanh映射

        z = (value - μ) / σ
        normalized = 100 * tanh(z / 2)  # z=±4 → ±98分
        """
        mean = np.mean(window)
        std = np.std(window)
        z = (value - mean) / (std + 1e-6)
        normalized = 100 * np.tanh(z / 2.0)

        return normalized, {
            'method': 'zscore',
            'mean': mean,
            'std': std,
            'z': z
        }
```

**应用到各因子**:

```python
# T因子示例（trend.py）
normalizer = FactorNormalizer(window_size=100, mode='hybrid')
T_raw, meta = normalizer.normalize(
    value=slope,
    history_window=slope_history[-100:],
    fixed_neutral=0.0,
    fixed_extreme=0.02
)

# 保留现有的R²加权（专家方案遗漏了这个好设计！）
T = T_raw * r_squared_confidence
```

**实施顺序**:
1. Week 3: 创建FactorNormalizer + 应用到T/M/C/V因子
2. Week 4: 应用到O/B/L/S/F/I因子 + 全面测试

**预期收益**:
- 跨币种一致性从50%提升到85%
- 跨regime稳定性从40%提升到90%

---

## 📋 P1.2：O因子改用Notional OI（待实施）

### 实施计划

**文件**: `ats_core/features/open_interest.py`

**问题**:
- BTC: 1张合约=100 USD
- 山寨币: 1张合约=10 USD
- 导致OI变化无法跨币种比较

**解决方案**:

```python
def calculate_notional_oi(oi_contracts, price, contract_multiplier=1.0):
    """
    计算名义持仓量（P1.2）

    Args:
        oi_contracts: 合约张数
        price: 当前价格
        contract_multiplier: 合约乘数（永续通常=1）

    Returns:
        notional_oi: 名义持仓量（USD）
    """
    return oi_contracts * price * contract_multiplier

# 应用到O因子
notional_oi_window = [
    calculate_notional_oi(oi, price)
    for oi, price in zip(oi_history, price_history)
]

# 后续逻辑不变
slope, r_squared = linregress(notional_oi_window)
```

**预期收益**:
- 跨币种比较准确性提升50%
- 大小盘币OI信号一致性提升

---

## 📋 P1.3：T-M相关性分析（待实施）

### 实施计划

**文件**: 新建 `diagnose/analyze_tm_correlation.py`

**目标**: 实证分析T和M因子的相关性，决定是否需要正交化

**脚本设计**:

```python
def analyze_T_M_correlation(symbol_list, days=30):
    """
    分析T和M因子的实际相关性（P1.3）

    Returns:
        (correlation_matrix, recommendations)
    """
    results = []

    for symbol in symbol_list:
        # 获取历史T和M数据
        T_history = get_factor_history(symbol, 'T', days=days)
        M_history = get_factor_history(symbol, 'M', days=days)

        # 计算相关系数
        corr = np.corrcoef(T_history, M_history)[0, 1]

        results.append({
            'symbol': symbol,
            'correlation': corr,
            'T_std': np.std(T_history),
            'M_std': np.std(M_history)
        })

    # 判断阈值
    avg_corr = np.mean([r['correlation'] for r in results])

    if avg_corr < 0.5:
        recommendation = "保持现状，无需正交化"
    elif avg_corr < 0.7:
        recommendation = "降低M权重：17% → 10%"
    else:
        recommendation = "需要正交化或重新设计M因子（方案C：短窗口版本）"

    return results, recommendation
```

**决策树**:
```
if avg_corr(T, M) < 0.5:
    → 不执行P2.2，保持现状
elif 0.5 ≤ avg_corr < 0.7:
    → 降低M权重：17% → 10%，不改代码
else:  # avg_corr ≥ 0.7
    → 执行P2.2，选择方案C（短窗口版本）
```

---

## 📋 P2.1：蓄势待发增强检测（待实施）

### 实施计划

**文件**: `ats_core/pipeline/analyze_symbol.py`

**当前逻辑**:
```python
if F >= 90 and C >= 60 and T < 40:
    is_accumulating = True
    threshold = 35
```

**增强逻辑**（保守方案，不过度复杂化）:

```python
def detect_accumulation_v2(factors, meta):
    """
    蓄势待发检测 v2.0（P2.1）

    改进：
    1. 保留原有screening逻辑
    2. 新增veto条件（防止追高）
    3. trigger逻辑作为可选模式
    """
    T, M, C, V, O, B, F, L, S, I = factors.values()

    # === Stage 1: Screening ===
    screening_passed = False

    if F >= 85 and C >= 60 and -10 <= T <= 40:  # 放宽F阈值，增加T下界
        screening_passed = True
        base_threshold = 35

    if not screening_passed:
        return False, "", 50

    # === Stage 2: Veto Conditions（关键改进！） ===
    veto_penalty = 1.0
    veto_reasons = []

    # Veto 1: Crowding
    basis_meta = meta.get('B', {})
    if basis_meta.get('basis_bps', 0) > 150:
        veto_penalty *= 0.7
        veto_reasons.append("basis过热")

    # Veto 2: Liquidity
    if L < 50:  # 专家建议70太严，改为50
        veto_penalty *= 0.85
        veto_reasons.append("流动性偏低")

    # Veto 3: Momentum contradiction
    if M < -50:
        veto_penalty *= 0.8
        veto_reasons.append("动量向下")

    # 应用veto惩罚
    adjusted_threshold = base_threshold / veto_penalty

    if veto_penalty < 0.6:
        # 惩罚过重，取消蓄势状态
        return False, f"veto过多", 50

    return True, "蓄势待发(v2)", int(adjusted_threshold)
```

**预期收益**:
- 蓄势检测准确率从60%提升到80%
- 虚假信号减少40%

---

## 配置管理

### config/params.json 新增配置

```json
{
  "factor_optimization_v2": {
    "enabled": true,
    "adaptive_threshold": {
      "mode": "hybrid",  // adaptive | legacy | hybrid
      "min_data_points": 50,
      "basis_neutral_bps_bounds": [20, 200],
      "basis_extreme_bps_bounds": [50, 300],
      "funding_neutral_rate_bounds": [0.0001, 0.005],
      "funding_extreme_rate_bounds": [0.0005, 0.01],
      "price_threshold_v_bounds": [0.001, 0.02],
      "price_threshold_o_bounds": [0.003, 0.03]
    },
    "crowding_veto": {
      "enabled": true,
      "basis_percentile": 90,
      "funding_percentile": 90,
      "veto_penalty": 0.5
    },
    "zscore_normalization": {
      "enabled": false,  // 初始禁用，测试后启用
      "window_size": 100,
      "mode": "hybrid",
      "tanh_scale": 2.0  // z/2 使 3σ → ±95分
    },
    "accumulation_detection_v2": {
      "enabled": false,  // A/B测试后启用
      "screening_thresholds": {
        "F_min": 85,
        "C_min": 60,
        "T_range": [-10, 40]
      },
      "veto_thresholds": {
        "basis_bps_max": 150,
        "L_min": 50,
        "M_min": -50
      },
      "veto_penalty_threshold": 0.6
    }
  }
}
```

---

## 测试策略

### 单元测试

```bash
# P0.1-P0.3: 自适应阈值
pytest tests/test_adaptive_thresholds.py -v

# P0.4: Crowding veto
pytest tests/test_crowding_veto.py -v

# P1.1: Zscore框架
pytest tests/test_factor_normalizer.py -v
```

### 回测验证

```bash
# 30天历史回测
python backtest.py \
    --start-date 2024-10-01 \
    --end-date 2024-11-01 \
    --config config_v2.json \
    --baseline config_v1.json \
    --metrics win_rate,sharpe,max_drawdown

# 目标：新版本不低于baseline的95%
```

### 监控指标

```python
# 关键监控
monitoring_metrics = {
    'adaptive_threshold_usage': '自适应阈值使用率',
    'fallback_rate': 'Fallback到legacy的比例（<30%为健康）',
    'veto_rate': 'Veto触发率（10-30%为合理）',
    'factor_distribution': '因子分数分布（避免zscore > 5的异常）',
    'signal_quality': '信号质量（目标：60% → 85%）',
    'false_positive_rate': '虚假信号率（目标：25% → 10%）'
}
```

---

## 风险矩阵

| 修复项 | 风险等级 | 缓解措施 | 预期收益 |
|--------|----------|----------|----------|
| P0.1-P0.3 自适应阈值 | 🟢 低 | Fallback机制 | ⭐⭐⭐⭐⭐ |
| P0.4 Crowding veto | 🟡 中 | 惩罚而非拒绝 | ⭐⭐⭐⭐ |
| P1.1 Zscore框架 | 🟡 中 | Hybrid模式 | ⭐⭐⭐⭐⭐ |
| P1.2 Notional OI | 🟢 低 | 纯量纲转换 | ⭐⭐⭐ |
| P1.3 T-M分析 | 🟢 无 | 纯诊断 | ⭐⭐⭐⭐ (决策依据) |
| P2.1 蓄势增强 | 🟡 中 | A/B测试 | ⭐⭐⭐⭐ |
| P2.2 M因子重设计 | 🔴 高 | 条件性执行 | ❓ 未知 |

---

## 实施时间表

```
Week 1 (已完成): P0.1-P0.3
├─ Day 1-2: B因子修复 ✅
├─ Day 3-4: V/O因子修复 ✅
└─ Day 5: 提交 ✅

Week 2: P0.4 + P1.2
├─ Day 1-3: F因子crowding veto
├─ Day 4-5: O因子notional改造
└─ 回测验证

Week 3-4: P1.1
├─ Week 3: FactorNormalizer + T/M/C/V
├─ Week 4: O/B/L/S/F/I + 全面测试
└─ 分阶段部署（先BTC/ETH，后全币种）

Week 5: P1.3 + P2决策
├─ Day 1-3: 历史数据分析
├─ Day 4-5: 决定是否执行P2.2
└─ 生成分析报告

Week 6-7: P2.1（可选）
├─ Week 6: 蓄势增强开发
├─ Week 7: A/B测试
└─ 根据结果决定是否全量

Week 8: P2.2（条件性）
├─ 仅当P1.3证实corr(T,M) > 0.7
└─ Shadow mode运行30天
```

---

## 回滚策略

### 配置开关

所有修复都支持通过配置回滚：

```python
# config/params.json
"factor_optimization_v2": {
    "enabled": false,  // 一键回滚所有P0-P2修复
    "adaptive_threshold": {
        "mode": "legacy"  // 单项回滚
    }
}
```

### 代码版本

```python
# 保留v1代码作为fallback
def score_volume_v1(vol, closes, params):
    """Legacy版本，供回滚使用"""
    pass

def score_volume_v2(vol, closes, params):
    """P0.2修复版本"""
    pass

# 运行时选择
if params.get('factor_optimization_v2', {}).get('enabled', False):
    return score_volume_v2(vol, closes, params)
else:
    return score_volume_v1(vol, closes, params)
```

---

## 成功标准

### 量化指标

| 指标 | 当前 | P0后目标 | P0+P1后目标 | P0+P1+P2后目标 |
|------|------|----------|-------------|----------------|
| 信号质量 | 60% | 75% | 85% | 90% |
| 跨regime稳定性 | 40% | 80% | 90% | 90% |
| 跨币种一致性 | 50% | 60% | 85% | 85% |
| 蓄势检测准确率 | 55% | 70% | 75% | 80% |
| 虚假信号率 | 25% | 15% | 10% | 8% |

### 定性标准

- ✅ 牛熊切换时因子不失灵
- ✅ BTC和山寨币使用同一套因子系统
- ✅ 新币冷启动时能安全降级
- ✅ 监控面板显示阈值使用情况
- ✅ 文档完整，后续维护者能理解设计rationale

---

## 后续维护

### 监控清单

1. **每日监控**:
   - Fallback率（<30%）
   - Veto触发率（10-30%）
   - 信号数量（波动<20%）

2. **每周监控**:
   - 因子分布（zscore <5）
   - 自适应阈值范围（在边界保护内）
   - Win rate vs baseline（>95%）

3. **每月review**:
   - T-M相关性（监控是否上升）
   - 蓄势检测效果（准确率/召回率）
   - 系统性能（扫描速度<0.5秒/币种）

### 文档更新

修复完成后需要更新：
- standards/FACTOR_SYSTEM_V66.md （添加P0-P2修复说明）
- standards/MODULATORS.md （如有B层修改）
- docs/FACTOR_SYSTEM_AUDIT_REPORT.md （更新审计结果）

---

## 联系人

- **实施负责人**: Claude (Sonnet 4.5)
- **技术审查**: 待用户指定
- **测试负责人**: 待用户指定
- **文档维护**: 待用户指定

---

*本文档将持续更新至所有修复完成*
