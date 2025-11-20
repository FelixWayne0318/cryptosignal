# 四步系统实施最终准备状态报告
# Final Preparation Status for Four-Step System Implementation

**检查日期**: 2025-11-16
**检查范围**: 配置非硬编码验证 + 剩余准备工作确认

---

## ✅ 核心结论

### 配置状态: 完全非硬编码 ✅

**所有10个因子的参数都已外部化到 `config/params.json`**

### 剩余准备工作: 4小时 (4项任务)

**订单簿分析已完成** (L因子已实现，节省20-30小时) ✅

---

## 📋 配置非硬编码验证

### ✅ A层因子配置 (全部外部化)

| 因子 | 配置位置 | 关键参数 | 状态 |
|------|---------|---------|------|
| **T** (趋势) | `params.trend` (L2-8) | ema_order_min_bars, slope_atr_min, atr_period | ✅ |
| **M** (动量) | `params.momentum` (L12-22) | ema_fast(3), ema_slow(5), slope_lookback(6) | ✅ |
| **C** (CVD流) | `params.cvd_flow` (L24-27) | lookback_hours(6), cvd_scale(0.02) | ✅ |
| **V** (量能) | `params.volume_adaptive` (L212-219) | lookback(20), percentile(50), adaptive thresholds | ✅ |
| **O** (持仓) | `params.open_interest` (L39-51) | long_oi24 thresholds, upup12/dnup12, w_change(0.7) | ✅ |
| **B** (基差) | `params.basis_funding` (L89-100) | basis_neutral_bps(50), funding weights | ✅ |

### ✅ B层调制器配置 (全部外部化)

| 因子 | 配置位置 | 关键参数 | 状态 |
|------|---------|---------|------|
| **F** (资金领先) | `params.fund_leading` (L164-185) | oi/vol/cvd weights, leading_scale(200), crowding_veto | ✅ |
| **S** (结构) | `params.structure` (L29-37) | theta.big(0.35), small(0.40), overlay_add, etc. | ✅ |
| **L** (流动性) | `params.liquidity` (L76-87) | band_bps(40), impact_threshold_bps(10), obi_threshold(0.3) | ✅ |
| **I** (独立性) | 无需额外配置 | Beta计算内置，输出[0,100]质量因子 | ✅ |

### ✅ 因子权重配置 (L131-162)

```json
{
  "weights": {
    "T": 23.0,  // A层价格行为
    "M": 10.0,  // A层价格行为
    "C": 26.0,  // A层资金流
    "V": 11.0,  // A层价格行为
    "O": 20.0,  // A层资金流
    "B": 10.0,  // A层微观结构
    "L": 0.0,   // B层调制器 (不参与加权)
    "S": 0.0,   // B层调制器 (不参与加权)
    "F": 0.0,   // B层调制器 (不参与加权)
    "I": 0.0    // B层调制器 (不参与加权)
  }
}
```

**分层设计** (L147-153):
- Layer 1 价格行为: T(23%) + M(10%) + V(11%) = 44%
- Layer 2 资金流: C(26%) + O(20%) = 46%
- Layer 3 微观结构: B(10%) = 10%
- B层调制器: L/S/F/I 调制仓位/置信度，不修改方向分数 ✅

### ⚠️ 缺失配置块

**需要添加**: `params.four_step_system` (准备工作第4项)

```json
{
  "four_step_system": {
    "enabled": false,  // ← 初始关闭，先测试
    "step1": {
      "min_final_strength": 20.0,
      "weights": {
        "T": 0.23, "M": 0.10, "C": 0.26,
        "V": 0.11, "O": 0.20, "B": 0.10
      },
      "I_high_beta_threshold": 30,
      "I_mid_threshold": 50,
      "I_independent_threshold": 85,
      "btc_strong_trend_threshold": 70.0,
      "confidence_floor": 0.50,
      "confidence_ceiling": 1.00
    },
    "step2": {
      "enhanced_f_scale": 20.0,
      "enhanced_f_flow_weights": {
        "C": 0.40, "O": 0.30, "V": 0.20, "B": 0.10
      },
      "factor_scores_lookback_hours": 6,
      "S_theta_threshold": 0.65,
      "L_liquidity_min": 30,
      "timing_score_scale": 100.0
    },
    "step3": {
      "volatility_atr_period": 14,
      "max_loss_fraction": 0.02,
      "entry_buffer_multiplier": 1.001,
      "stop_buffer_multiplier": 0.998,
      "tp_incremental_multiplier": 1.2
    },
    "step4": {
      "min_ev": 0.8,
      "min_risk_reward": 1.0,
      "min_final_score": 50.0,
      "oi_crowding_percentile": 95,
      "basis_extreme_percentile": 95,
      "funding_extreme_percentile": 95
    }
  }
}
```

---

## 🎯 剩余准备工作清单

### Task 1: S因子ZigZag导出 (0.5小时) ⚠️

**文件**: `ats_core/features/structure_sq.py`

**问题**: ZigZag已计算但未在metadata中导出

**当前代码** (line 248-257):
```python
return S, {
    "theta": th,
    "icr": icr,
    "retr": retr,
    "timing": timing,
    "not_over": (over<=0.8),
    "m15_ok": bool(ctx.get("m15_ok",False)),
    "penalty": penalty,
    "interpretation": interpretation
    # ⚠️ 缺少: "zigzag_points"
}
```

**需要修复**:
```python
# 在返回语句前添加
zigzag_points = []
for i, (kind, price, dt) in enumerate(zz):
    zigzag_points.append({
        "type": kind,           # "H" or "L"
        "price": float(price),
        "dt": len(c) - dt       # 距当前的K线数
    })

return S, {
    "theta": th,
    "icr": icr,
    "retr": retr,
    "timing": timing,
    "not_over": (over<=0.8),
    "m15_ok": bool(ctx.get("m15_ok",False)),
    "penalty": penalty,
    "interpretation": interpretation,
    "zigzag_points": zigzag_points  # ✅ 新增
}
```

**用途**: Step3风险管理需要ZigZag点来识别关键支撑阻力位

**预计工作量**: 0.5小时

---

### Task 2: factor_scores_series实现 (2小时) ⚠️

**需要创建**: `ats_core/utils/factor_history.py`

**功能**: 计算过去7小时的因子得分序列

**用途**: Step2计算Enhanced F Factor需要

```python
def get_factor_scores_series(
    symbol: str,
    klines_1h: list,
    window_hours: int = 7
) -> list:
    """
    计算历史因子得分序列

    参数:
        symbol: 交易对
        klines_1h: 1小时K线数据 (至少24根)
        window_hours: 回溯小时数 (默认7)

    返回:
        factor_scores_series: [
            {"T": 25, "M": 10, "C": 80, ...},  # 6小时前
            {"T": 28, "M": 12, "C": 82, ...},  # 5小时前
            ...
            {"T": 35, "M": 20, "C": 90, ...}   # 当前
        ]
    """
    series = []

    # 对过去window_hours小时，每小时计算一次
    for i in range(-window_hours, 0):
        # 取该时刻之前的K线窗口
        klines_window = klines_1h[:i] if i < -1 else klines_1h

        # 计算该时刻的六个因子
        # (复用analyze_symbol中的因子计算逻辑)
        T_score, _ = calculate_T(klines_window)
        M_score, _ = calculate_M(klines_window)
        C_score, _ = calculate_C(klines_window)
        V_score, _ = calculate_V(klines_window)
        O_score, _ = calculate_O(klines_window)
        B_score, _ = calculate_B(klines_window)

        series.append({
            "T": T_score,
            "M": M_score,
            "C": C_score,
            "V": V_score,
            "O": O_score,
            "B": B_score
        })

    return series
```

**实施方案**:
1. 创建新文件 `ats_core/utils/factor_history.py`
2. 从 `analyze_symbol.py` 中提取因子计算逻辑为独立函数
3. 在 `get_factor_scores_series()` 中循环调用
4. 在主流程中集成（四步系统调用时）

**性能考虑**:
- 初版使用实时计算（每次重新计算7小时）
- 后续可优化为缓存机制（保存每小时结果）
- 预计每次调用耗时 < 1秒

**预计工作量**: 2小时

---

### Task 3: BTC因子计算 (1小时) ⚠️

**文件**: `ats_core/pipeline/analyze_symbol.py`

**功能**: 在主流程中添加BTC因子计算

**当前状态**: 未实现BTC因子计算

**需要添加** (在analyze_symbol函数中):
```python
def analyze_symbol(symbol: str, params: dict = None) -> dict:
    # ... 现有逻辑 ...

    # ✅ 新增: BTC因子计算 (用于四步系统Step1)
    btc_factor_scores = None
    if params.get("four_step_system", {}).get("enabled", False):
        try:
            # 获取BTC 1小时K线
            btc_klines = get_klines(
                symbol="BTCUSDT",
                timeframe="1h",
                limit=168  # 7天数据
            )

            # 计算BTC T因子 (至少需要这一个)
            from ats_core.features.trend import score_trend
            btc_T, _ = score_trend(btc_klines, params.get("trend", {}))

            # 可选: 计算更多BTC因子
            # btc_M, _ = score_momentum(btc_klines, params.get("momentum", {}))

            btc_factor_scores = {
                "T": btc_T,
                # "M": btc_M,  # 可选
            }
        except Exception as e:
            warn(f"BTC因子计算失败: {e}")
            # 降级处理: 使用默认值
            btc_factor_scores = {"T": 0.0}

    # ... 后续逻辑 ...
```

**用途**: Step1方向确认需要
```python
# Step1中使用
btc_direction_score = btc_factor_scores.get("T", 0.0)
btc_trend_strength = abs(btc_direction_score)

# 硬veto规则
if I_score < 30 and btc_trend_strength > 70 and opposite_direction:
    return {"pass": False, "hard_veto": True}
```

**降级处理**:
- BTC数据获取失败 → 使用默认值 {"T": 0.0}
- 不影响四步系统运行，只是缺少BTC方向校验

**预计工作量**: 1小时

---

### Task 4: 配置块添加 (0.5小时) ⚠️

**文件**: `config/params.json`

**操作**: 在文件末尾添加 `four_step_system` 配置块

**添加位置**: 在 `"universe"` 数组之后 (L364-369)

```json
{
  "universe": [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT"
  ],

  "four_step_system": {
    "_comment": "v7.4四步分层决策系统 - 基于专家实施方案",
    "_version": "v7.4.2",
    "enabled": false,

    "step1": {
      "_comment": "Step1: 方向确认层 (Enhanced I Factor)",
      "min_final_strength": 20.0,
      "weights": {
        "T": 0.23,
        "M": 0.10,
        "C": 0.26,
        "V": 0.11,
        "O": 0.20,
        "B": 0.10
      },
      "I_high_beta_threshold": 30,
      "I_mid_threshold": 50,
      "I_independent_threshold": 85,
      "btc_strong_trend_threshold": 70.0,
      "confidence_floor": 0.50,
      "confidence_ceiling": 1.00
    },

    "step2": {
      "_comment": "Step2: 时机判断层 (Enhanced F Factor v2)",
      "enhanced_f_scale": 20.0,
      "enhanced_f_flow_weights": {
        "C": 0.40,
        "O": 0.30,
        "V": 0.20,
        "B": 0.10
      },
      "factor_scores_lookback_hours": 6,
      "S_theta_threshold": 0.65,
      "L_liquidity_min": 30,
      "timing_score_scale": 100.0,
      "timing_rejection_threshold": 30.0
    },

    "step3": {
      "_comment": "Step3: 风险管理层 (价格计算)",
      "volatility_atr_period": 14,
      "max_loss_fraction": 0.02,
      "entry_buffer_multiplier": 1.001,
      "stop_buffer_multiplier": 0.998,
      "tp_incremental_multiplier": 1.2,
      "orderbook_placeholder_enabled": true
    },

    "step4": {
      "_comment": "Step4: 质量控制层 (最终审核)",
      "min_ev": 0.8,
      "min_risk_reward": 1.0,
      "min_final_score": 50.0,
      "oi_crowding_percentile": 95,
      "basis_extreme_percentile": 95,
      "funding_extreme_percentile": 95
    }
  }
}
```

**检查清单**:
- [ ] JSON格式正确（逗号、括号）
- [ ] 所有参数都有默认值
- [ ] `enabled: false` 初始关闭
- [ ] 注释说明每个步骤的职责

**预计工作量**: 0.5小时

---

### Task 5: 订单簿分析 (0小时) ✅ 已完成

**状态**: L因子已完整实现订单簿分析

**文件**: `ats_core/features/liquidity_priceband.py` (16KB)

**功能**:
- ✅ 价格带聚合 (`aggregate_within_band`)
- ✅ 买卖墙识别 (`calculate_obi`, OBI ∈ [-1, 1])
- ✅ 价格冲击计算 (`calculate_impact_bps`)
- ✅ 深度覆盖分析 (`calculate_coverage`)
- ✅ 价差计算 (`calculate_spread_bps`)

**L因子元数据提供**:
```python
{
    "obi_value": float,           # -1到+1, >0.3=买墙, <-0.3=卖墙
    "bid_qty_in_band": float,     # 买盘深度
    "ask_qty_in_band": float,     # 卖盘深度
    "buy_impact_bps": float,      # 买入冲击
    "sell_impact_bps": float,     # 卖出冲击
    "best_bid": float,
    "best_ask": float,
    "mid_price": float,
    "spread_bps": float,
    "coverage_score": float,
    "gates_passed": int           # 四道闸通过数
}
```

**Step3使用方法**:
```python
# 从L因子元数据提取订单簿信息
def extract_orderbook_from_L_meta(l_meta: dict) -> dict:
    obi_value = l_meta.get("obi_value", 0.0)
    best_bid = l_meta.get("best_bid", 0.0)
    best_ask = l_meta.get("best_ask", 0.0)

    # OBI阈值: ±0.3表示显著失衡
    buy_wall_price = best_bid if obi_value > 0.3 else None
    sell_wall_price = best_ask if obi_value < -0.3 else None

    return {
        "buy_wall_price": buy_wall_price,
        "sell_wall_price": sell_wall_price,
        "buy_depth_score": l_meta.get("bid_qty_in_band", 50.0),
        "sell_depth_score": l_meta.get("ask_qty_in_band", 50.0),
        "imbalance": obi_value
    }

# 在step3_risk_management中调用
orderbook_info = extract_orderbook_from_L_meta(l_meta)
```

**节省时间**: 原本预计20-30小时，现在0小时 ✅

---

## 📊 准备工作时间估算

| 任务 | 预计时间 | 优先级 | 状态 |
|------|---------|--------|------|
| 1. S因子ZigZag导出 | 0.5h | P0 | ⚠️ 待完成 |
| 2. factor_scores_series实现 | 2.0h | P0 | ⚠️ 待完成 |
| 3. BTC因子计算 | 1.0h | P0 | ⚠️ 待完成 |
| 4. 配置块添加 | 0.5h | P0 | ⚠️ 待完成 |
| 5. 订单簿分析 | 0.0h | P0 | ✅ 已完成 (L因子) |
| **总计** | **4.0小时** | - | - |

---

## 🚀 实施路径

### 阶段0: 准备工作 (4小时) ← **当前阶段**

**执行顺序**:
1. Task 4: 配置块添加 (0.5h) - 最简单，先完成
2. Task 1: S因子ZigZag导出 (0.5h) - 修改单个函数
3. Task 3: BTC因子计算 (1h) - 在主流程中添加
4. Task 2: factor_scores_series实现 (2h) - 最复杂，最后完成

**完成标志**:
- [ ] `params.json` 包含 `four_step_system` 配置
- [ ] S因子meta包含 `zigzag_points` 字段
- [ ] `analyze_symbol` 计算 `btc_factor_scores`
- [ ] `ats_core/utils/factor_history.py` 实现并测试
- [ ] 提交commit: "feat(P0): 四步系统前置条件准备"

---

### 阶段1: Step1+2实现 (24小时)

**创建文件**:
```
ats_core/decision/
├── step1_direction.py       # 方向确认层
├── step2_timing.py          # 时机判断层
└── four_step_system.py      # 主入口 (部分)
```

**实现内容**:
- Step1: `calculate_direction_confidence_v2()` + 硬veto规则
- Step2: `calculate_enhanced_f_v2()` + 时机评分

**测试方式**: 单元测试 + 回测验证

---

### 阶段2: Step3+4实现 (16小时)

**创建文件**:
```
ats_core/decision/
├── step3_risk.py            # 风险管理层
├── step4_quality.py         # 质量控制层
└── four_step_system.py      # 主入口 (完整)
```

**实现内容**:
- Step3: 入场价/止损/止盈计算 + 订单簿调整
- Step4: EV/RR计算 + 过热检测 + 最终评分

**测试方式**: 集成测试 + 仿真环境

---

### 阶段3: 集成测试 (8小时)

**集成点**: `ats_core/pipeline/analyze_symbol.py`

```python
# 在analyze_symbol中添加
if params.get("four_step_system", {}).get("enabled", False):
    from ats_core.decision.four_step_system import run_four_step_decision

    result = run_four_step_decision(
        symbol=symbol,
        exchange="binance",
        klines=k1h,
        factor_scores=factor_scores,
        factor_scores_series=factor_scores_series,
        btc_factor_scores=btc_factor_scores,
        s_factor_meta=s_meta,
        l_factor_meta=l_meta,
        prime_strength=prime_strength,
        params=params
    )

    if result["decision"] == "ACCEPT":
        # 生成信号
        ...
```

**测试策略**:
1. Dual run (新旧系统并行，对比结果)
2. 回测验证 (历史数据)
3. 仿真环境 (实时数据，不实际交易)
4. 逐步切换 (先5%流量，再20%，最后100%)

---

## ✅ 总结

### 配置状态

**所有因子参数已非硬编码** ✅
- 10个因子的所有参数都在 `config/params.json`
- 因子权重可配置
- 自适应阈值可配置
- 微观结构参数可配置

**缺失配置**: `four_step_system` 配置块 (Task 4，0.5小时)

---

### 剩余准备工作

**P0必须完成** (4小时):
1. ✅ 订单簿分析 (0h) - **L因子已实现**
2. ⚠️ S因子ZigZag导出 (0.5h)
3. ⚠️ factor_scores_series实现 (2h)
4. ⚠️ BTC因子计算 (1h)
5. ⚠️ 配置块添加 (0.5h)

**可选优化** (后续版本):
- factor_scores_series缓存机制 (8h)
- ATR简易计算fallback (1h)
- 订单簿实时更新优化 (4h)

---

### 实施时间估算

- **阶段0**: 准备工作 (4h) ← **下一步**
- **阶段1**: Step1+2实现 (24h)
- **阶段2**: Step3+4实现 (16h)
- **阶段3**: 集成测试 (8h)
- **总计**: 52小时

---

### 下一步行动

**建议**: 立即开始阶段0准备工作

**执行顺序**:
1. Task 4: 配置块添加 (15分钟) ✅ 最简单
2. Task 1: S因子ZigZag导出 (30分钟)
3. Task 3: BTC因子计算 (60分钟)
4. Task 2: factor_scores_series实现 (120分钟)

**完成后**: 提交commit并开始阶段1 (Step1+2实现)

---

## 🎉 重要发现回顾

### 订单簿分析已完整实现 (L因子)

**之前认为**: 需要20-30小时实现订单簿分析
**实际情况**: L因子已提供完整的价格带法订单簿分析
**节省时间**: 20-30小时 ✅✅✅

**优势**:
- ✅ 买卖墙识别 (OBI值)
- ✅ 深度分析 (bid/ask qty in band)
- ✅ 价格冲击计算 (impact_bps)
- ✅ 四道闸验证 (gates_passed)

**Step3可以使用真实订单簿数据而非占位** ✅

---

**文档创建**: 2025-11-16
**下次更新**: 完成阶段0准备工作后
