# 四步分层决策系统 - 关键修正方案
# Critical Corrections for Four-Step Layered Decision System

**版本**: v1.1 (修正版)
**日期**: 2025-11-16
**状态**: 🔴 修正中 - 基于专家review

---

## 📋 专家Review总结

### ✅ 总体评价

> **"这是一个可以直接拿来做 v7.4 的工程版实现方案，只要在3个点做校正，就可以和顶层设计95%对齐。"**

**优点**:
- 实现细节非常丰富，可直接编码
- Step1-4职责边界清晰
- 保留了旧系统回退开关

### 🔴 三个致命缺陷（必须修正）

#### 1. **Enhanced F 因子重复使用价格** ⚠️⚠️⚠️

**问题**:
```python
# 错误的设计
signal_momentum = A层综合得分动量  # A层包含T(23%) + M(10%) = 33%价格维度！
price_momentum = 价格动量
Enhanced_F = signal_momentum - price_momentum

# 实际等于
Enhanced_F = (价格×33% + 非价格×67%) - 价格
            = 价格 vs 价格 的自相关！
```

**后果**:
- 回测效果虚高（价格自相关导致解释力虚高）
- 实盘会严重漂移
- t-test会失效

**正确做法**:
```python
# 只用非价格因子
flow_score = C×w_C + O×w_O + V×w_V + B×w_B  # CVD + 持仓 + 量能 + 基差
flow_momentum = (flow_score_now - flow_score_6h_ago) / ...
price_momentum = (price_now - price_6h_ago) / ...
Enhanced_F = flow_momentum - price_momentum
```

这才是真正的：**资金/仓位/结构 增强速度 vs 价格涨跌速度**

---

#### 2. **I因子语义和实现严重偏差** ⚠️⚠️

**我的错误假设**:
```python
# 设计里假设
I ∈ [-100, 100]
I > 0: 独立行情 (逆风)
I < 0: 跟随行情 (顺风)
```

**实际实现** (independence.py:19-24):
```python
# 实际是
I ∈ [0, 100] (质量因子)
|β| ≤ 0.6: I ∈ [85, 100] (高度独立)
|β| ≥ 1.5: I ∈ [0, 15] (高度相关)

# 语义
I高 (85-100) = 低Beta = 高独立性 ✅
I低 (0-15)   = 高Beta = 高相关性 (严重跟随BTC)
```

**后果**:
- 我设计的所有I因子相关逻辑都是错的
- `calculate_direction_confidence()` 完全反了
- `calculate_btc_alignment()` 完全反了

**正确做法**:
```python
def calculate_direction_confidence(direction_score, I_score, params):
    """
    I_score ∈ [0, 100]
    I_score越高 → 越独立 → 置信度越高
    I_score越低 → 越跟随 → 置信度越低
    """
    # 严重跟随 (高Beta)
    if I_score < 15:
        confidence = 0.60 + (I_score / 15.0) * 0.10  # 0.60-0.70
    # 中度跟随
    elif I_score < 30:
        confidence = 0.70 + ((I_score - 15) / 15.0) * 0.15  # 0.70-0.85
    # 轻度跟随
    elif I_score < 50:
        confidence = 0.85 + ((I_score - 30) / 20.0) * 0.10  # 0.85-0.95
    # 独立行情
    else:
        confidence = 0.95 + ((I_score - 50) / 50.0) * 0.05  # 0.95-1.00

    return confidence
```

---

#### 3. **缺少高Beta币的硬veto** ⚠️

**问题**:
- 我的设计全是"软系数相乘"
- 没有"防作死底线"
- 高Beta币在强BTC趋势下反向操作 → 必死

**正确做法** - 在Step1增加硬规则:
```python
def step1_direction_confirmation(factor_scores, btc_direction_score, btc_trend_strength, params):
    # ... 原有逻辑 ...

    # 🔴 硬veto规则 (防作死底线)
    I_score = factor_scores["I"]
    high_beta_threshold = params.get("step1_high_beta_threshold", 30)  # I<30表示高Beta
    strong_btc_threshold = params.get("step1_strong_btc_threshold", 70)  # BTC趋势很强

    is_high_beta = I_score < high_beta_threshold
    is_strong_btc_trend = abs(btc_trend_strength) > strong_btc_threshold
    is_opposite_direction = (direction_score * btc_direction_score) < 0

    if is_high_beta and is_strong_btc_trend and is_opposite_direction:
        # 高Beta币 + 强BTC趋势 + 反向 → 直接SKIP
        return {
            ...
            "pass": False,
            "reject_reason": "High Beta coin vs strong BTC trend (hard veto - 防作死)"
        }

    # ... 继续原有逻辑 ...
```

**示例场景**:
```
I_score = 12  (高Beta币，β≈1.8)
BTC: T_BTC = -85 (强烈下跌)
本币方向: direction_score = +52 (想做多)

→ 硬veto → SKIP → 避免"逆大盘送钱"
```

---

## 🔧 完整修正方案

### 修正1: 重写Step2 - Enhanced F Factor

#### 新设计思路

**核心理念**:
> Enhanced_F 必须回答："资金/仓位/结构增强速度 vs 价格涨跌速度，谁更快？"

**数据来源**:
- **Flow Score**: 仅使用非价格因子 (C/O/V/B)
- **Price**: 价格动量

#### 实现细节

```python
def calculate_flow_score(factor_scores, weights):
    """
    计算资金流动综合得分 (仅非价格因子)

    参数:
        factor_scores: dict, {"C": 85, "O": 65, "V": 40, "B": 20, ...}
        weights: dict, 流动因子权重 (总和=1.0)

    返回:
        flow_score: float, -100 到 +100
    """
    # 默认权重 (可配置)
    default_weights = {
        "C": 0.40,  # CVD流动 (最重要)
        "O": 0.30,  # 持仓量
        "V": 0.20,  # 量能
        "B": 0.10   # 基差/资金费
    }

    w = weights if weights else default_weights

    flow_score = (
        factor_scores["C"] * w["C"] +
        factor_scores["O"] * w["O"] +
        factor_scores["V"] * w["V"] +
        factor_scores["B"] * w["B"]
    )

    return flow_score

def calculate_flow_momentum(factor_scores_series, weights, window_hours=6):
    """
    计算资金流动动量

    参数:
        factor_scores_series: list of dict, 过去7小时的因子得分序列
        weights: dict, 流动因子权重
        window_hours: int, 时间窗口

    返回:
        flow_momentum: float, 百分比 (%)
    """
    # 计算每小时的flow_score
    flow_series = [
        calculate_flow_score(scores, weights)
        for scores in factor_scores_series
    ]

    flow_now = flow_series[-1]
    flow_6h_ago = flow_series[0]

    # 相对变化率
    if abs(flow_now) < 1 and abs(flow_6h_ago) < 1:
        # 信号太弱，动量无意义
        flow_momentum = 0.0
    else:
        flow_change = flow_now - flow_6h_ago
        base = max(abs(flow_now), abs(flow_6h_ago), 10)  # 避免除以过小值
        flow_momentum = (flow_change / base) * 100

    return flow_momentum

def calculate_enhanced_f_factor_v2(
    factor_scores_series,
    klines,
    params
):
    """
    加强版F因子 v2 (修正版)

    核心修正:
        - signal_momentum → flow_momentum (仅C/O/V/B)
        - 避免价格自相关

    公式: Enhanced_F = flow_momentum - price_momentum

    语义:
        Enhanced_F > 0: 资金增强速度 > 价格上涨速度 → 吸筹 ✅
        Enhanced_F < 0: 价格上涨速度 > 资金增强速度 → 追高 ⚠️

    参数:
        factor_scores_series: list of dict, 过去7小时因子得分
        klines: list of dict, K线数据
        params: dict, 配置参数

    返回:
        dict: {
            "enhanced_f": float, -100 到 +100
            "flow_momentum": float,
            "price_momentum": float,
            "timing_quality": str,
            "flow_weights": dict  # 使用的权重
        }
    """
    import math

    # 1. 获取流动因子权重 (可配置)
    flow_weights = params.get("enhanced_f_flow_weights", {
        "C": 0.40,
        "O": 0.30,
        "V": 0.20,
        "B": 0.10
    })

    # 2. 计算资金流动动量
    flow_momentum = calculate_flow_momentum(
        factor_scores_series,
        flow_weights
    )

    # 3. 计算价格动量
    close_now = klines[-1]["close"]
    close_6h_ago = klines[-7]["close"]
    price_change_pct = (close_now - close_6h_ago) / close_6h_ago * 100
    price_momentum = price_change_pct / 6.0  # 每小时变化率

    # 4. Enhanced_F = 资金动量 - 价格动量
    enhanced_f_raw = flow_momentum - price_momentum

    # 5. tanh标准化到±100
    scale = params.get("enhanced_f_scale", 20.0)
    enhanced_f = 100.0 * math.tanh(enhanced_f_raw / scale)

    # 6. 时机质量评级
    if enhanced_f >= 80:
        timing_quality = "Excellent"
    elif enhanced_f >= 60:
        timing_quality = "Good"
    elif enhanced_f >= 30:
        timing_quality = "Fair"
    elif enhanced_f >= -30:
        timing_quality = "Mediocre"
    elif enhanced_f >= -60:
        timing_quality = "Poor"
    else:
        timing_quality = "Chase"

    return {
        "enhanced_f": enhanced_f,
        "flow_momentum": flow_momentum,
        "price_momentum": price_momentum,
        "timing_quality": timing_quality,
        "flow_weights": flow_weights
    }

# 示例1 (吸筹场景):
# C: 80→90 (+12.5%), O: 60→70 (+16.7%), V: 35→45 (+28.6%), B: 15→20 (+33.3%)
# flow_score: 60→75
# flow_momentum ≈ +25%
# price_momentum ≈ +0.8%
# enhanced_f ≈ +95 → "Excellent" ✅✅✅

# 示例2 (追高场景):
# C: 70→75 (+7%), O: 60→62 (+3%), V: 40→42 (+5%), B: 20→22 (+10%)
# flow_score: 60→63
# flow_momentum ≈ +5%
# price_momentum ≈ +15%
# enhanced_f ≈ -48 → "Poor" ⚠️
```

---

### 修正2: 重写Step1 - I因子对齐

#### 新设计思路

**I因子实际语义** (基于independence.py):
```
I ∈ [0, 100]
I_score 高 (85-100) → 低Beta (≤0.6) → 高独立性 → 高置信度 ✅
I_score 低 (0-15)   → 高Beta (≥1.5) → 高相关性 → 低置信度 ⚠️
```

#### 实现细节

```python
def calculate_direction_confidence_v2(direction_score, I_score, params):
    """
    根据I因子计算方向置信度 (修正版)

    I因子语义 (实际实现):
        I ∈ [0, 100]
        I高 (85-100): 低Beta, 高独立性 → 高置信度
        I低 (0-15): 高Beta, 高相关性 → 低置信度

    参数:
        direction_score: float, A层得分
        I_score: float, 0 到 100
        params: dict, 配置参数

    返回:
        direction_confidence: float, 0.5 到 1.0
    """
    # 阈值 (可配置)
    high_beta_threshold = params.get("I_high_beta_threshold", 15)      # 严重跟随
    moderate_beta_threshold = params.get("I_moderate_beta_threshold", 30)  # 中度跟随
    low_beta_threshold = params.get("I_low_beta_threshold", 50)        # 轻度跟随

    if I_score < high_beta_threshold:
        # 严重跟随BTC (高Beta): 置信度 0.60-0.70
        confidence = 0.60 + (I_score / high_beta_threshold) * 0.10
    elif I_score < moderate_beta_threshold:
        # 中度跟随: 置信度 0.70-0.85
        range_size = moderate_beta_threshold - high_beta_threshold
        confidence = 0.70 + ((I_score - high_beta_threshold) / range_size) * 0.15
    elif I_score < low_beta_threshold:
        # 轻度跟随: 置信度 0.85-0.95
        range_size = low_beta_threshold - moderate_beta_threshold
        confidence = 0.85 + ((I_score - moderate_beta_threshold) / range_size) * 0.10
    else:
        # 独立行情 (低Beta): 置信度 0.95-1.00
        range_size = 100 - low_beta_threshold
        confidence = 0.95 + ((I_score - low_beta_threshold) / range_size) * 0.05

    return max(0.50, min(1.00, confidence))

# 示例:
# I = 12 (严重跟随, β≈1.8) → confidence ≈ 0.68 ⚠️
# I = 25 (中度跟随, β≈1.3) → confidence ≈ 0.80 ⚠️
# I = 45 (轻度跟随, β≈1.0) → confidence ≈ 0.93 ✅
# I = 90 (高度独立, β≈0.3) → confidence ≈ 0.99 ✅✅✅


def calculate_btc_alignment_v2(direction_score, btc_direction_score, I_score, params):
    """
    计算与BTC方向的一致性系数 (修正版)

    逻辑:
        - 方向一致 + 独立性高 → alignment = 1.00 (完全信任)
        - 方向一致 + 独立性低 → alignment = 0.90-1.00 (部分信任)
        - 方向不一致 + 独立性高 → alignment = 0.85-0.95 (可接受，真独立)
        - 方向不一致 + 独立性低 → alignment = 0.70-0.85 (警惕，可能假信号)

    参数:
        direction_score: float, 本币种方向得分
        btc_direction_score: float, BTC方向得分
        I_score: float, 独立性得分 (0-100, 高=独立)
        params: dict, 配置参数

    返回:
        btc_alignment: float, 0.70 到 1.00
    """
    # 判断方向是否一致
    same_direction = (direction_score * btc_direction_score) > 0

    # 独立性系数 (0到1)
    independence_factor = I_score / 100.0  # [0,100] → [0,1]

    if same_direction:
        # 方向一致: alignment = 0.90 + independence_factor × 0.10
        alignment = 0.90 + independence_factor * 0.10
    else:
        # 方向不一致: alignment = 0.70 + independence_factor × 0.25
        # 独立性越高，越能接受不一致
        alignment = 0.70 + independence_factor * 0.25

    return max(0.70, min(1.00, alignment))

# 示例:
# 一致 + I=90 → alignment ≈ 0.99 ✅✅✅
# 一致 + I=20 → alignment ≈ 0.92 ✅✅
# 不一致 + I=90 → alignment ≈ 0.93 ✅✅ (真独立，可接受)
# 不一致 + I=20 → alignment ≈ 0.75 ⚠️ (假独立，警惕)
```

---

### 修正3: 增加高Beta币硬veto

#### 新设计思路

**防作死底线**:
> 高Beta币 + 强BTC趋势 + 反向 → 直接SKIP，不进入Step2

#### 实现细节

```python
def step1_direction_confirmation_v2(
    factor_scores,
    btc_direction_score,
    btc_trend_strength,
    params
):
    """
    第一步完整流程 (修正版)

    新增:
        - 使用修正后的I因子置信度
        - 增加高Beta币硬veto规则

    返回:
        dict: {
            "direction_score": float,
            "direction_strength": float,
            "direction_confidence": float,
            "btc_alignment": float,
            "final_strength": float,
            "pass": bool,
            "reject_reason": str or None,
            "hard_veto": bool  # 是否被硬veto拒绝
        }
    """
    # 1. A层得分
    direction_score = calculate_direction_score(
        factor_scores,
        params["weights"]
    )

    # 2. I因子置信度 (修正版)
    direction_confidence = calculate_direction_confidence_v2(
        direction_score,
        factor_scores["I"],
        params
    )

    # 3. BTC一致性 (修正版)
    btc_alignment = calculate_btc_alignment_v2(
        direction_score,
        btc_direction_score,
        factor_scores["I"],
        params
    )

    # 4. 🔴 硬veto规则 (防作死底线)
    I_score = factor_scores["I"]
    high_beta_threshold = params.get("step1_high_beta_threshold", 30)
    strong_btc_threshold = params.get("step1_strong_btc_threshold", 70)

    is_high_beta = I_score < high_beta_threshold
    is_strong_btc_trend = abs(btc_trend_strength) > strong_btc_threshold
    is_opposite_direction = (direction_score * btc_direction_score) < 0

    hard_veto_triggered = is_high_beta and is_strong_btc_trend and is_opposite_direction

    if hard_veto_triggered:
        # 高Beta币逆强BTC趋势 → 直接拒绝
        return {
            "direction_score": direction_score,
            "direction_strength": abs(direction_score),
            "direction_confidence": direction_confidence,
            "btc_alignment": btc_alignment,
            "final_strength": 0.0,
            "pass": False,
            "reject_reason": (
                f"High Beta coin (I={I_score}) vs strong BTC trend "
                f"(|T_BTC|={abs(btc_trend_strength):.1f}) - Hard Veto (防作死)"
            ),
            "hard_veto": True
        }

    # 5. 最终强度 (考虑置信度和一致性)
    direction_strength = abs(direction_score)
    final_strength = direction_strength * direction_confidence * btc_alignment

    # 6. 通过条件 (可配置)
    min_final_strength = params.get("step1_min_final_strength", 20.0)
    pass_step1 = final_strength >= min_final_strength

    return {
        "direction_score": direction_score,
        "direction_strength": direction_strength,
        "direction_confidence": direction_confidence,
        "btc_alignment": btc_alignment,
        "final_strength": final_strength,
        "pass": pass_step1,
        "reject_reason": None if pass_step1 else f"方向强度不足: {final_strength:.1f} < {min_final_strength}",
        "hard_veto": False
    }

# 示例1 (硬veto触发):
# I = 12 (高Beta, β≈1.8)
# BTC: T_BTC = -85 (强烈下跌)
# 本币: direction_score = +52 (想做多)
# → hard_veto=True → SKIP → "防作死" ✅

# 示例2 (通过):
# I = 88 (低Beta, β≈0.4)
# BTC: T_BTC = -85 (强烈下跌)
# 本币: direction_score = +52 (想做多)
# → confidence=0.99, alignment=0.93 → final_strength=47.8 → PASS ✅
```

---

## 📊 修正前后对比

### Enhanced F Factor

| 版本 | Signal成分 | 问题 | 预期效果 |
|------|-----------|------|---------|
| **v1.0 (错误)** | A层总分 (T/M/C/V/O/B) | 价格自相关 | 回测虚高，实盘漂移 ⚠️ |
| **v1.1 (修正)** | Flow得分 (C/O/V/B) | 无 | 真实反映资金vs价格 ✅ |

**修正核心**:
```
v1.0: (价格×33% + 非价格×67%) vs 价格 → 自相关 ⚠️
v1.1: (非价格×100%) vs 价格 → 正交 ✅
```

### I因子置信度

| I_score | v1.0 (错误) | v1.1 (修正) |
|---------|------------|------------|
| 12 (高Beta) | confidence=0.88 ⚠️ | confidence=0.68 ✅ |
| 88 (低Beta) | confidence=0.62 ⚠️ | confidence=0.99 ✅ |

**修正核心**: 完全反转了映射关系

### 硬Veto

| 场景 | v1.0 (错误) | v1.1 (修正) |
|------|------------|------------|
| I=12, T_BTC=-85, 本币做多 | 软系数降权 (可能通过) ⚠️ | 硬veto直接SKIP ✅ |

---

## 🛠️ 配置参数更新

### config/params.json 新增

```json
{
  "four_step_system": {
    "enabled": true,

    "step1": {
      "min_final_strength": 20.0,

      "I_high_beta_threshold": 15,
      "I_moderate_beta_threshold": 30,
      "I_low_beta_threshold": 50,

      "high_beta_threshold": 30,
      "strong_btc_threshold": 70
    },

    "step2": {
      "enhanced_f_scale": 20.0,
      "min_enhanced_f": 30.0,
      "signal_momentum_window_hours": 6,

      "enhanced_f_flow_weights": {
        "C": 0.40,
        "O": 0.30,
        "V": 0.20,
        "B": 0.10
      }
    },

    "step3": {
      "stop_loss_atr_multiplier": 2.0,
      "min_risk_reward_ratio": 1.5
    },

    "step4": {
      "gate1_min_volume_24h": 1000000,
      "gate2_max_noise_ratio": 0.15,
      "gate3_min_prime_strength": 35
    }
  }
}
```

---

## 📝 实施顺序

### 阶段0: 修正设计文档 (1小时) ✅

- [x] 创建本修正文档
- [x] 更新主设计文档 FOUR_STEP_LAYERED_DECISION_SYSTEM_DESIGN.md

### 阶段1: Step1 + Step2修正版 (24小时)

1. **Step1修正** (10小时)
   - 重写 `calculate_direction_confidence_v2()`
   - 重写 `calculate_btc_alignment_v2()`
   - 增加硬veto规则
   - 单元测试

2. **Step2修正** (14小时)
   - 重写 `calculate_flow_score()`
   - 重写 `calculate_flow_momentum()`
   - 重写 `calculate_enhanced_f_factor_v2()`
   - 单元测试
   - **回测验证** (对比v1.0，确认修正有效)

### 阶段2: Step3 + Step4 (16小时)

- 保持原设计不变
- 集成测试

### 阶段3: 主流程集成 (8小时)

- 集成到信号生成流程
- A/B对比测试

**总计**: 48小时 (原40小时 + 8小时修正)

---

## ⚠️ 关键警告

### 1. 不修正的后果

如果不做这三个修正，直接实施v1.0：

- **Enhanced F会失效**: 价格自相关导致误判
- **I因子完全反了**: 高Beta币会被当成独立币
- **没有防作死底线**: 高Beta币逆BTC趋势会被放行

**预计损失**: 实盘收益比预期低50%以上 ⚠️⚠️⚠️

### 2. 必须做回测验证

修正后的Enhanced_F必须做对比回测:
```
v1.0 (A层动量 - 价格动量) vs v1.1 (Flow动量 - 价格动量)

验证指标:
- 吸筹场景识别率 (应该更高)
- 追高场景拦截率 (应该更高)
- 信号数量 (可能减少10-20%)
- 胜率 (应该提升)
```

### 3. 参数必须配置化

所有阈值必须从config读取，禁止硬编码:
- `high_beta_threshold = 30`  # ✅ 配置化
- `if I_score < 30:`  # ⚠️ 硬编码

---

## ✅ 总结

### 专家评价是对的

> **"以 Claude Code 这版为主线实现，以我那版为设计原则+风险check list，在具体实现上做三点修正。"**

### 三点修正确认

1. ✅ **Enhanced F修正**: 只用C/O/V/B，不用T/M
2. ✅ **I因子对齐**: 重写置信度函数，适配[0,100]语义
3. ✅ **硬veto增加**: 高Beta + 强BTC + 反向 → SKIP

### 修正后的系统

```
第一步 [方向确认] → I因子正确对齐 + 硬veto ✅
第二步 [时机判断] → Enhanced F无自相关 ✅
第三步 [风险管理] → 保持原设计 ✅
第四步 [质量控制] → 保持原设计 ✅
```

**现在可以实施了！**

---

**下一步**: 等待用户确认修正方案，确认后开始阶段1实施 (24小时)
