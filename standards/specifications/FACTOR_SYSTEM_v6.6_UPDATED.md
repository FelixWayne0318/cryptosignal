# 6+4因子系统规范

**规范版本**: v6.6
**生效日期**: 2025-11-03
**状态**: 生效中
**更新说明**: 从v6.4的9+2架构升级到v6.6的6+4架构

> ⚠️ **重要**: 本文档为因子系统核心规范。
> - **A层**: 6个方向因子（T/M/C/V/O/B），权重总和100%
> - **B层**: 4个调制器（L/S/F/I），权重0%，仅调节执行参数
>
> 完整的技术细节参见：[../CORE_STANDARDS.md § 2](../CORE_STANDARDS.md)

---

## 快速导航

- [A层：方向因子（6维）](#a层方向因子)
- [B层：调制器（4维）](#b层调制器)
- [统一标准化链](#统一标准化链)
- [权重配置](#权重配置)
- [v6.6架构变更](#v66架构变更)

---

## A层：方向因子

### 因子列表

| 因子 | 名称 | 权重 | 数据源 | 输出范围 |
|------|------|------|--------|---------|
| **T** | 趋势 | 24.0% | 1h K线 | ±100 |
| **M** | 动量 | 17.0% | 1h K线 | ±100 |
| **C** | CVD | 24.0% | 1h K线 + 成交 | ±100 |
| **V** | 量能 | 12.0% | 1h K线 | ±100 |
| **O** | OI | 17.0% | OI数据 | ±100 |
| **B** | 基差/资金 | 6.0% | 现货+期货 | ±100 |

**总计**: 100.0% ✅

**架构分层** (v6.6优化配置):
- **Layer 1** (价格行为 53%): T(24%) + M(17%) + V(12%)
- **Layer 2** (资金流 41%): C(24%) + O(17%)
- **Layer 3** (微观结构 6%): B(6%)

### 因子详细说明

#### T - 趋势因子 (24%)
**计算方法**: 基于ZLEMA的价格趋势识别
- **输入**: 1h K线数据
- **输出**: -100（强下跌）到 +100（强上涨）
- **实现**: `_calc_trend(h, l, c, c4, params)`
- **文件**: `ats_core/pipeline/analyze_symbol.py:309`

#### M - 动量因子 (17%)
**计算方法**: ROC/RSI/MACD综合动量
- **输入**: 1h K线数据
- **输出**: -100（减速下跌）到 +100（加速上涨）
- **实现**: `_calc_momentum(h, l, c, params)`
- **文件**: `ats_core/pipeline/analyze_symbol.py:314`
- **v6.6修复**: scale=1.00，消除tanh饱和

#### C - CVD资金流因子 (24%)
**计算方法**: 累计成交量差分析
- **输入**: 1h K线 + 成交量数据
- **输出**: -100（资金流出）到 +100（资金流入）
- **实现**: `_calc_cvd_flow(cvd_series, c, params)`
- **文件**: `ats_core/pipeline/analyze_symbol.py:319`

#### V - 量能因子 (12%)
**计算方法**: 相对成交量和买卖差
- **输入**: 1h K线成交量
- **输出**: -100（缩量）到 +100（放量）
- **实现**: `_calc_volume(q, closes=c)`
- **文件**: `ats_core/pipeline/analyze_symbol.py:331`
- **v2.0修复**: 传入closes以修复多空对称性

#### O - 持仓因子 (17%)
**计算方法**: 持仓量变化分析
- **输入**: OI数据
- **输出**: -100（持仓减少）到 +100（持仓增加）
- **实现**: `_calc_oi(symbol, c, params, cvd6, oi_data)`
- **文件**: `ats_core/pipeline/analyze_symbol.py:337`

#### B - 基差+资金费因子 (6%)
**计算方法**: 现货-期货基差和资金费率
- **输入**: 标记价格 + 现货价格 + 资金费率
- **输出**: -100（看跌）到 +100（看涨）
- **实现**: `calculate_basis_funding(perp_price, spot_price, funding_rate, params)`
- **文件**: `ats_core/factors_v2/basis_funding.py`
- **位置**: `ats_core/pipeline/analyze_symbol.py:344`

---

## B层：调制器

### 调制器列表

| 因子 | 名称 | 权重 | 调制目标 | 作用 |
|------|------|------|---------|------|
| **L** | 流动性 | 0.0% | position | 流动性差时降低仓位 |
| **S** | 结构 | 0.0% | confidence | 结构差时降低置信度 |
| **F** | 资金领先 | 0.0% | Teff | 资金领先时提升温度 |
| **I** | 独立性 | 0.0% | cost | 独立性高时降低成本 |

详见：[MODULATORS.md](MODULATORS.md)

### 调制器详细说明

#### L - 流动性调制器
**功能**: 根据流动性质量调节仓位大小
- **输入范围**: 0（极差）到 100（极好）
- **调制目标**: position_size
- **调制公式**: `position = base_position × L_modulation`
- **实现**: `calculate_liquidity(orderbook, params)`
- **文件**: `ats_core/factors_v2/liquidity.py`
- **位置**: `ats_core/pipeline/analyze_symbol.py:370`

#### S - 结构调制器
**功能**: 根据价格结构调节置信度
- **输入范围**: -100（差）到 +100（好）
- **调制目标**: confidence
- **调制公式**: `confidence_final = confidence_base × S_modulation`
- **实现**: `_calc_structure(h, l, c, ema30, atr_now, params, ctx)`
- **文件**: `ats_core/pipeline/analyze_symbol.py:324`

#### F - 资金领先调制器
**功能**: 根据资金价格领先关系调节有效温度
- **输入范围**: -100（价格领先）到 +100（资金领先）
- **调制目标**: Teff (有效温度)
- **调制公式**: `Teff = T0 × F_modulation`
- **实现**: `_calc_fund_leading(...)`
- **文件**: `ats_core/pipeline/analyze_symbol.py:435`
- **v6.6修复**: 移除double-tanh bug

#### I - 独立性调制器
**功能**: 根据与BTC/ETH相关性调节执行成本
- **输入范围**: -100（完全相关）到 +100（完全独立）
- **调制目标**: cost
- **调制公式**: `cost_final = cost_base × I_modulation`
- **实现**: `calculate_independence(alt_prices, btc_prices, eth_prices, params)`
- **文件**: `ats_core/factors_v2/independence.py`
- **位置**: `ats_core/pipeline/analyze_symbol.py:402`
- **v6.6修复**: 移除double-tanh bug

---

## 统一标准化链

所有因子统一使用以下标准化流程：

1. **预平滑**: `x̃_t = α·x_t + (1-α)·x̃_{t-1}`
2. **稳健缩放**: `z = (x̃ - μ) / (1.4826·MAD)`
3. **软winsor**: `z_soft = sign(z)[z0 + (zmax-z0)(1-exp(-(|z|-z0)/λ))]`
4. **压缩到±100**: `s_k = 100 · tanh(z_soft/τ_k)`

详见：`ats_core/features/standardization_chain.py`

---

## 权重配置

**配置文件**: `config/params.json`

**实际生效权重** (v6.6 - 6+4因子架构):
```json
{
  "weights": {
    "_comment": "v6.6 - A层6因子权重（总和=100.0%），B层4调制器（L/S/F/I权重=0），Q因子完全移除",
    "T": 24.0,
    "M": 17.0,
    "C": 24.0,
    "V": 12.0,
    "O": 17.0,
    "B": 6.0,
    "_b_layer": "以下为B层调制器，不参与评分",
    "L": 0.0,
    "S": 0.0,
    "F": 0.0,
    "I": 0.0,
    "E": 0.0
  },
  "weights_comment": {
    "_version": "v6.6 - 统一调制器架构（6因子A层 + 4调制器B层）",
    "_total_weight": "100%（A层6因子权重百分比系统）",
    "_layer1_price_action": "Layer 1 价格行为层（53%）: T(24%) + M(17%) + V(12%)",
    "_layer2_capital_flow": "Layer 2 资金流层（41%）: C(24%) + O(17%)",
    "_layer3_microstructure": "Layer 3 微观结构层（6%）: B(6%)",
    "_layer_b_modulators": "B层调制器（不评分）: L(流动性) + S(结构) + F(资金领先) + I(独立性)",
    "_modulator_role": "L/S/F/I仅调制position/Teff/cost/confidence，不修改方向分数",
    "_deprecated": "E(0) - 环境因子已废弃",
    "_removed_v6.6": "Q因子完全移除（数据不可靠收益低），L/S移至B层调制器",
    "_change_log_v6.6": "权重再分配（S的11% + Q的4%）: T+4%, M+3%, C+4%, V+1%, O+3%",
    "_rationale": "L/S是质量指标非方向指标，整合为调制器实现连续仓位调整，消除硬拒绝门槛",
    "_soft_constraints": "仅DataQual≥0.90为硬门槛，EV和P改为软约束（不拒绝信号，仅不发布）"
  }
}
```

**要求**: A层6因子总和必须=100.0%，B层调制器(L/S/F/I)权重=0%

---

## v6.6架构变更

### 从v6.4到v6.6的主要变化

#### 1. 因子架构调整
**v6.4架构** (9+2):
- A层: T/M/C/S/V/O/L/B/Q (9因子)
- B层: F/I (2调制器)

**v6.6架构** (6+4):
- A层: T/M/C/V/O/B (6因子)
- B层: L/S/F/I (4调制器)

#### 2. 移除的因子
- **Q (清算密度)**: 完全移除
  - **原因**: 清算数据不可靠，收益低
  - **原权重**: 4.0%
  - **状态**: 已删除，代码中无遗留

- **E (环境)**: 已废弃
  - **原因**: 收益低
  - **原权重**: 0.0%
  - **状态**: 标记废弃，不再计算

#### 3. 移至B层的因子
- **L (流动性)**: A层 → B层调制器
  - **原因**: 流动性是质量指标，非方向指标
  - **原权重**: 12.0% → 0.0%
  - **新功能**: 调节仓位大小 (position)

- **S (结构)**: A层 → B层调制器
  - **原因**: 结构是质量指标，非方向指标
  - **原权重**: 10.0% → 0.0%
  - **新功能**: 调节置信度 (confidence)

#### 4. 权重重新分配
释放的权重: L(12%) + S(10%) + Q(4%) = 26%

重新分配到A层6因子:
- T: 18% → 24% (+6%)
- M: 12% → 17% (+5%)
- C: 18% → 24% (+6%)
- V: 10% → 12% (+2%)
- O: 12% → 17% (+5%)
- B: 4% → 6% (+2%)

**总计**: +26% = 26% ✅

#### 5. Bug修复
- **M因子修复**: scale=1.00，消除tanh饱和
- **I因子修复**: 移除double-tanh bug
- **F因子修复**: 移除double-tanh bug
- **V因子修复**: 修复多空对称性

---

## 实现模块

- `ats_core/factors_v2/*.py` - 各因子计算
- `ats_core/scoring/scorecard.py` - 加权聚合
- `ats_core/pipeline/analyze_symbol.py` - 主分析流水线
- `ats_core/modulators/modulator_chain.py` - 调制器链

---

## 验证方法

### 验证权重配置
```bash
python3 -c "
import json
with open('config/params.json') as f:
    weights = json.load(f)['weights']
    factor_weights = {k: v for k, v in weights.items() if not k.startswith('_')}

    # A层6因子
    a_layer = ['T', 'M', 'C', 'V', 'O', 'B']
    a_total = sum(factor_weights.get(k, 0) for k in a_layer)

    # B层4调制器
    b_layer = ['L', 'S', 'F', 'I']
    b_total = sum(factor_weights.get(k, 0) for k in b_layer)

    print(f'A层6因子总和: {a_total}% (应为100%)')
    print(f'B层4调制器总和: {b_total}% (应为0%)')

    assert abs(a_total - 100.0) < 0.01, 'A层权重错误'
    assert abs(b_total) < 0.01, 'B层权重错误'
    print('✅ 权重配置验证通过')
"
```

### 验证因子范围
```bash
python3 -c "
# 所有因子必须在±100范围内
from ats_core.pipeline.analyze_symbol import analyze_symbol
import asyncio

async def test():
    result = await analyze_symbol('BTCUSDT', params={})
    scores = result.get('scores', {})
    for factor, score in scores.items():
        assert -100 <= score <= 100, f'{factor}={score}超出范围'
    print('✅ 因子范围验证通过')

asyncio.run(test())
"
```

---

## 相关文档

- **调制器规范**: [MODULATORS.md](MODULATORS.md)
- **数据层规范**: [DATA_LAYER.md](DATA_LAYER.md) (如果存在)
- **发布规范**: [PUBLISHING.md](PUBLISHING.md) (如果存在)
- **核心标准**: [../CORE_STANDARDS.md](../CORE_STANDARDS.md) (如果存在)

---

**维护**: 量化研究团队
**审核**: 系统架构师
**版本**: v6.6
**生效日期**: 2025-11-03
