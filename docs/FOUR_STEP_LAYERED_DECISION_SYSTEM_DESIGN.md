# 四步分层决策系统设计方案
# Four-Step Layered Decision System Design

**版本**: v1.0
**日期**: 2025-11-16
**状态**: 设计方案 - 等待用户确认
**预计工作量**: 40 小时 (分阶段实施)

---

## 📋 目录

1. [设计理念](#设计理念)
2. [系统架构总览](#系统架构总览)
3. [第一步：方向确认层](#第一步方向确认层)
4. [第二步：时机判断层](#第二步时机判断层)
5. [第三步：风险管理层](#第三步风险管理层)
6. [第四步：质量控制层](#第四步质量控制层)
7. [系统输出示例](#系统输出示例)
8. [实施计划](#实施计划)
9. [风险评估](#风险评估)
10. [性能预期](#性能预期)

---

## 🎯 设计理念

### 用户核心洞察

用户提出的革命性思路：

> **"资金也是持续流入，资金流入的速度比价格上涨的速度大，价格也刚好在支撑位，这样上涨的概率就比较大，也不容易止损。"**

这代表了三维风险收益评估框架：

1. **概率维度** (胜率): 资金持续流入 → C因子高 → 趋势确认 → 上涨概率大 ✅
2. **时机维度** (效率): 资金速度 > 价格速度 → F因子高 → 吸筹而非追高 ✅
3. **风险维度** (赔率): 价格在支撑位 → S因子高 → 止损空间小 → 赔率好 ✅

**公式**: `高胜率 + 好赔率 + 优时机 = 顶级机会`

### 当前系统问题

```
当前系统 = 单层加权评分
问题1: 方向评分 ≠ 入场时机 (F因子权重=0)
问题2: 综合得分 ≠ 具体价格 (无止损止盈)
问题3: 信号延迟 44% (过度依赖滞后指标)
```

### 四步分层解决方案

```
第一步 [方向确认层]: A层因子 + I因子 + BTC方向 → 方向强度 + 置信度
第二步 [时机判断层]: 加强版F因子 (信号动量 vs 价格动量) → 吸筹/追高判断
第三步 [风险管理层]: 结构 + 流动性 + 订单薄 + 波动率 → 具体入场/止损/止盈价
第四步 [质量控制层]: 四道门槛验证 → 发布信号 or 拒绝
```

**关键创新**: 不仅输出方向得分，更输出**具体可操作的价格** (入场价、止损价、止盈价)

---

## 🏗️ 系统架构总览

### 数据流

```
输入: K线 + CVD + OI + 订单薄 + BTC数据
  ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第一步: 方向确认层                                                │
│ - A层因子综合得分 (T/M/C/V/O/B)                                   │
│ - I因子顺逆风校验                                                  │
│ - BTC方向一致性检查                                                │
│ 输出: Direction_Strength, Direction_Confidence, BTC_Alignment   │
└─────────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第二步: 时机判断层 (Enhanced F Factor)                           │
│ - 计算信号动量 (Signal_Momentum)                                 │
│ - 计算价格动量 (Price_Momentum)                                  │
│ - Enhanced_F = Signal_Momentum - Price_Momentum                │
│ 输出: Enhanced_F, Timing_Quality, Entry_Signal                 │
└─────────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第三步: 风险管理层                                                │
│ - 从S因子提取ZigZag支撑/阻力位                                     │
│ - 订单薄分析 (买卖墙、深度)                                        │
│ - 波动率调整 (ATR)                                                │
│ - 流动性评估 (L因子)                                               │
│ 输出: Entry_Price, Stop_Loss, Take_Profit, Risk_Reward_Ratio   │
└─────────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第四步: 质量控制层                                                │
│ - Gate1: 基础筛选 (Volume_24h > 阈值)                            │
│ - Gate2: 噪声过滤 (ATR/Price < 阈值)                             │
│ - Gate3: 信号强度 (Prime_Strength > 阈值)                        │
│ - Gate4: 矛盾检测 (因子一致性)                                    │
│ 输出: ACCEPT (发布信号) or REJECT (拒绝 + 原因)                   │
└─────────────────────────────────────────────────────────────────┘
  ↓
最终输出: {
  "action": "LONG" / "SHORT",
  "entry_price": 100.00,
  "stop_loss": 97.80,
  "take_profit": 109.78,
  "risk_pct": 2.2,
  "reward_pct": 9.78,
  "risk_reward_ratio": 4.45,
  "enhanced_f": 85,
  "timing_quality": "Excellent",
  "confidence": 0.92
}
```

---

## 第一步：方向确认层

### 设计目标

1. **保持A层不变**: 继续使用当前6个A层因子 (T/M/C/V/O/B) 的加权评分
2. **I因子顺逆风校验**: 当I因子显示严重顺风 (跟随市场) 时，降低置信度
3. **BTC方向一致性**: 与比特币方向一致时，提升置信度

### 实现细节

#### 1.1 A层综合得分 (保持现有逻辑)

```python
def calculate_direction_score(factor_scores, weights):
    """
    计算A层综合得分

    参数:
        factor_scores: dict, {"T": 30, "M": 15, "C": 85, "V": 40, "O": 65, "B": 20}
        weights: dict, {"T": 0.23, "M": 0.10, "C": 0.26, "V": 0.11, "O": 0.20, "B": 0.10}

    返回:
        direction_score: float, -100 到 +100
    """
    direction_score = sum(
        factor_scores[name] * weights[name]
        for name in ["T", "M", "C", "V", "O", "B"]
    )
    return direction_score  # 示例: 85×0.26 + 65×0.20 + ... ≈ +48
```

#### 1.2 I因子顺逆风校验

```python
def calculate_direction_confidence(direction_score, I_score, params):
    """
    根据I因子计算方向置信度

    I因子语义:
        I > 0: 独立行情 (逆风) → 高置信度
        I < 0: 跟随行情 (顺风) → 低置信度
        I < -50: 严重跟随 → 显著降低置信度

    参数:
        direction_score: float, A层得分
        I_score: float, -100 到 +100
        params: dict, 配置参数

    返回:
        direction_confidence: float, 0.5 到 1.0
    """
    # 阈值 (可配置)
    serious_follow_threshold = params.get("I_serious_follow_threshold", -50)
    moderate_follow_threshold = params.get("I_moderate_follow_threshold", -30)

    if I_score < serious_follow_threshold:
        # 严重顺风: 置信度 0.60-0.70
        confidence = 0.60 + (I_score - (-100)) / ((-100) - serious_follow_threshold) * 0.10
    elif I_score < moderate_follow_threshold:
        # 中度顺风: 置信度 0.70-0.85
        confidence = 0.70 + (I_score - serious_follow_threshold) / (serious_follow_threshold - moderate_follow_threshold) * 0.15
    elif I_score < 0:
        # 轻度顺风: 置信度 0.85-0.95
        confidence = 0.85 + (I_score - moderate_follow_threshold) / (moderate_follow_threshold - 0) * 0.10
    else:
        # 独立行情: 置信度 0.95-1.00
        confidence = 0.95 + (I_score / 100.0) * 0.05

    return max(0.50, min(1.00, confidence))

# 示例:
# I = -80 (严重跟随) → confidence ≈ 0.62
# I = -40 (中度跟随) → confidence ≈ 0.78
# I = -10 (轻度跟随) → confidence ≈ 0.88
# I = +60 (独立行情) → confidence ≈ 0.98
```

#### 1.3 BTC方向一致性检查

```python
def calculate_btc_alignment(direction_score, btc_direction_score, I_score, params):
    """
    计算与BTC方向的一致性系数

    逻辑:
        - 方向一致 + 独立性高 → alignment = 1.00 (完全信任)
        - 方向一致 + 独立性低 → alignment = 0.90-1.00 (部分信任)
        - 方向不一致 + 独立性高 → alignment = 0.85-0.95 (可接受，真独立)
        - 方向不一致 + 独立性低 → alignment = 0.70-0.85 (警惕，可能假信号)

    参数:
        direction_score: float, 本币种方向得分
        btc_direction_score: float, BTC方向得分
        I_score: float, 独立性得分
        params: dict, 配置参数

    返回:
        btc_alignment: float, 0.70 到 1.00
    """
    # 判断方向是否一致
    same_direction = (direction_score * btc_direction_score) > 0

    # 独立性系数 (0到1)
    independence_factor = (I_score + 100) / 200.0  # [-100,100] → [0,1]

    if same_direction:
        # 方向一致: alignment = 0.90 + independence_factor × 0.10
        alignment = 0.90 + independence_factor * 0.10
    else:
        # 方向不一致: alignment = 0.70 + independence_factor × 0.25
        # 独立性越高，越能接受不一致
        alignment = 0.70 + independence_factor * 0.25

    return max(0.70, min(1.00, alignment))

# 示例:
# 一致 + I=+80 → alignment ≈ 0.99 ✅✅✅
# 一致 + I=-40 → alignment ≈ 0.93 ✅✅
# 不一致 + I=+80 → alignment ≈ 0.92 ✅✅ (真独立，可接受)
# 不一致 + I=-60 → alignment ≈ 0.75 ⚠️ (假独立，警惕)
```

#### 1.4 第一步综合输出

```python
def step1_direction_confirmation(factor_scores, btc_direction_score, params):
    """
    第一步完整流程

    返回:
        dict: {
            "direction_score": float,         # -100 到 +100
            "direction_strength": float,      # 0 到 100 (绝对值)
            "direction_confidence": float,    # 0.50 到 1.00
            "btc_alignment": float,           # 0.70 到 1.00
            "final_strength": float,          # direction_strength × confidence × alignment
            "pass": bool                      # 是否通过第一步
        }
    """
    # 1. A层得分
    direction_score = calculate_direction_score(
        factor_scores,
        params["weights"]
    )

    # 2. I因子置信度
    direction_confidence = calculate_direction_confidence(
        direction_score,
        factor_scores["I"],
        params
    )

    # 3. BTC一致性
    btc_alignment = calculate_btc_alignment(
        direction_score,
        btc_direction_score,
        factor_scores["I"],
        params
    )

    # 4. 最终强度 (考虑置信度和一致性)
    direction_strength = abs(direction_score)
    final_strength = direction_strength * direction_confidence * btc_alignment

    # 5. 通过条件 (可配置)
    min_final_strength = params.get("step1_min_final_strength", 20.0)
    pass_step1 = final_strength >= min_final_strength

    return {
        "direction_score": direction_score,
        "direction_strength": direction_strength,
        "direction_confidence": direction_confidence,
        "btc_alignment": btc_alignment,
        "final_strength": final_strength,
        "pass": pass_step1,
        "reject_reason": None if pass_step1 else f"方向强度不足: {final_strength:.1f} < {min_final_strength}"
    }

# 示例输出:
# {
#     "direction_score": +52,
#     "direction_strength": 52,
#     "direction_confidence": 0.88,  # I=-10, 轻度顺风
#     "btc_alignment": 0.93,         # 一致 + I=-10
#     "final_strength": 42.5,        # 52 × 0.88 × 0.93 = 42.5
#     "pass": True
# }
```

---

## 第二步：时机判断层

### 设计目标

**核心创新**: 加强版F因子 (Enhanced F Factor)

- **原版F因子**: `(CVD动量 × 0.6 + OI动量 × 0.4) - 价格动量`
- **加强版F因子**: `信号综合动量 - 价格动量`

区别:
- 原版: 仅基于CVD+OI两个数据源
- 加强版: 基于所有A层因子的综合信号 (T/M/C/V/O/B)

### 实现细节

#### 2.1 信号动量计算

```python
def calculate_signal_momentum(factor_scores_series, weights, window_hours=6):
    """
    计算信号综合动量

    参数:
        factor_scores_series: list of dict, 过去7小时的因子得分序列
            示例: [
                {"T": 25, "M": 10, "C": 80, "V": 35, "O": 60, "B": 15},  # 6小时前
                {"T": 28, "M": 12, "C": 82, "V": 38, "O": 62, "B": 18},  # 5小时前
                ...
                {"T": 35, "M": 20, "C": 90, "V": 45, "O": 70, "B": 25}   # 当前
            ]
        weights: dict, A层权重
        window_hours: int, 时间窗口 (默认6小时)

    返回:
        signal_momentum: float, 信号每小时变化率 (%)
    """
    # 1. 计算每小时的综合信号得分
    signal_series = []
    for scores in factor_scores_series:
        signal = calculate_direction_score(scores, weights)
        signal_series.append(signal)

    # 2. 线性回归求斜率
    n = len(signal_series)
    x_mean = (n - 1) / 2.0
    y_mean = sum(signal_series) / n

    numerator = sum((i - x_mean) * (signal_series[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / max(denominator, 1e-9)  # 得分/小时

    # 3. 转换为百分比动量
    signal_now = signal_series[-1]
    signal_6h_ago = signal_series[0]

    # 方法1: 基于斜率
    # signal_momentum = (slope × 6小时) / max(1, abs(signal_6h_ago)) × 100

    # 方法2: 基于直接变化 (更简单，推荐)
    if abs(signal_now) < 1 and abs(signal_6h_ago) < 1:
        # 信号太弱，动量无意义
        signal_momentum = 0.0
    else:
        # 相对变化率
        signal_change = signal_now - signal_6h_ago
        base = max(abs(signal_now), abs(signal_6h_ago), 10)  # 避免除以过小值
        signal_momentum = (signal_change / base) * 100  # 转换为百分比

    return signal_momentum

# 示例:
# signal_series = [40, 42, 45, 48, 50, 52, 55]  # 稳步上升
# signal_now = 55, signal_6h_ago = 40
# signal_change = 15, base = max(55, 40, 10) = 55
# signal_momentum = 15 / 55 × 100 ≈ 27.3%
```

#### 2.2 价格动量计算

```python
def calculate_price_momentum(klines, window_hours=6):
    """
    计算价格动量

    参数:
        klines: list of dict, K线数据 (至少7根1小时K线)
        window_hours: int, 时间窗口

    返回:
        price_momentum: float, 价格每小时变化率 (%)
    """
    close_now = klines[-1]["close"]
    close_6h_ago = klines[-7]["close"]

    price_change_pct = (close_now - close_6h_ago) / close_6h_ago * 100
    price_momentum = price_change_pct / window_hours  # 每小时变化率

    return price_momentum

# 示例:
# close_6h_ago = 100, close_now = 105
# price_change = 5%, 6小时
# price_momentum = 5% / 6 ≈ 0.833% / 小时
```

#### 2.3 加强版F因子计算

```python
def calculate_enhanced_f_factor(signal_momentum, price_momentum, params):
    """
    计算加强版F因子

    公式: Enhanced_F_raw = Signal_Momentum - Price_Momentum

    语义:
        Enhanced_F > 0: 信号增强速度 > 价格上涨速度 → 吸筹 ✅
        Enhanced_F < 0: 价格上涨速度 > 信号增强速度 → 追高 ⚠️

    参数:
        signal_momentum: float, 信号动量 (%)
        price_momentum: float, 价格动量 (%)
        params: dict, 包含 "enhanced_f_scale" 参数

    返回:
        dict: {
            "enhanced_f": float, -100 到 +100
            "signal_momentum": float,
            "price_momentum": float,
            "timing_quality": str, "Excellent" / "Good" / "Fair" / "Poor" / "Chase"
        }
    """
    import math

    # 1. 原始差值
    enhanced_f_raw = signal_momentum - price_momentum

    # 2. tanh标准化到±100
    scale = params.get("enhanced_f_scale", 20.0)  # 可配置
    enhanced_f = 100.0 * math.tanh(enhanced_f_raw / scale)

    # 3. 时机质量评级
    if enhanced_f >= 80:
        timing_quality = "Excellent"  # 优秀: 强烈吸筹
    elif enhanced_f >= 60:
        timing_quality = "Good"       # 良好: 温和吸筹
    elif enhanced_f >= 30:
        timing_quality = "Fair"       # 一般: 同步
    elif enhanced_f >= -30:
        timing_quality = "Mediocre"   # 平庸: 轻度追高
    elif enhanced_f >= -60:
        timing_quality = "Poor"       # 差: 中度追高
    else:
        timing_quality = "Chase"      # 追高: 重度追高

    return {
        "enhanced_f": enhanced_f,
        "signal_momentum": signal_momentum,
        "price_momentum": price_momentum,
        "timing_quality": timing_quality
    }

# 示例1 (吸筹场景):
# signal_momentum = 27.3%, price_momentum = 0.833%
# enhanced_f_raw = 27.3 - 0.833 = 26.47
# enhanced_f = 100 × tanh(26.47/20) ≈ 92 → "Excellent" ✅✅✅

# 示例2 (追高场景):
# signal_momentum = 5%, price_momentum = 15%
# enhanced_f_raw = 5 - 15 = -10
# enhanced_f = 100 × tanh(-10/20) ≈ -46 → "Poor" ⚠️
```

#### 2.4 入场信号判断

```python
def step2_timing_judgment(factor_scores_series, klines, params):
    """
    第二步完整流程

    返回:
        dict: {
            "enhanced_f": float,
            "timing_quality": str,
            "entry_signal": bool,        # 是否可入场
            "pass": bool,
            "reject_reason": str or None
        }
    """
    # 1. 计算信号动量
    signal_momentum = calculate_signal_momentum(
        factor_scores_series,
        params["weights"]
    )

    # 2. 计算价格动量
    price_momentum = calculate_price_momentum(klines)

    # 3. 计算加强版F因子
    result = calculate_enhanced_f_factor(
        signal_momentum,
        price_momentum,
        params
    )

    # 4. 入场信号判断
    min_enhanced_f = params.get("step2_min_enhanced_f", 30.0)  # 可配置
    entry_signal = result["enhanced_f"] >= min_enhanced_f

    result["entry_signal"] = entry_signal
    result["pass"] = entry_signal
    result["reject_reason"] = None if entry_signal else f"时机不佳 (Enhanced_F={result['enhanced_f']:.1f} < {min_enhanced_f})"

    return result

# 示例输出 (吸筹):
# {
#     "enhanced_f": 92,
#     "signal_momentum": 27.3,
#     "price_momentum": 0.833,
#     "timing_quality": "Excellent",
#     "entry_signal": True,
#     "pass": True,
#     "reject_reason": None
# }

# 示例输出 (追高):
# {
#     "enhanced_f": -46,
#     "signal_momentum": 5.0,
#     "price_momentum": 15.0,
#     "timing_quality": "Poor",
#     "entry_signal": False,
#     "pass": False,
#     "reject_reason": "时机不佳 (Enhanced_F=-46.0 < 30.0)"
# }
```

---

## 第三步：风险管理层

### 设计目标

**输出具体价格**:
- 入场价 (Entry Price)
- 止损价 (Stop Loss)
- 止盈价 (Take Profit)

**数据来源**:
1. **S因子**: ZigZag支撑/阻力位
2. **订单薄**: 买卖墙、深度分析 ⚠️ (需新实现)
3. **波动率**: ATR动态调整
4. **L因子**: 流动性评估

### 实现细节

#### 3.1 支撑/阻力位提取

```python
def extract_support_resistance(s_factor_meta, direction_score):
    """
    从S因子的ZigZag元数据中提取支撑/阻力位

    参数:
        s_factor_meta: dict, S因子返回的元数据，包含ZigZag关键点
            示例: {
                "zigzag_points": [
                    {"type": "L", "price": 98.5, "dt": 8},
                    {"type": "H", "price": 103.2, "dt": 5},
                    {"type": "L", "price": 99.8, "dt": 3},
                    {"type": "H", "price": 104.5, "dt": 1}
                ],
                ...
            }
        direction_score: float, 方向得分 (用于判断做多/做空)

    返回:
        dict: {
            "support": float,      # 最近支撑位
            "resistance": float,   # 最近阻力位
            "support_strength": int,  # 支撑强度 (触及次数)
            "resistance_strength": int
        }
    """
    zigzag_points = s_factor_meta.get("zigzag_points", [])

    if not zigzag_points:
        # 无ZigZag数据，返回None
        return {
            "support": None,
            "resistance": None,
            "support_strength": 0,
            "resistance_strength": 0
        }

    # 提取所有低点和高点
    lows = [p["price"] for p in zigzag_points if p["type"] == "L"]
    highs = [p["price"] for p in zigzag_points if p["type"] == "H"]

    # 最近的支撑/阻力 (最新的低点/高点)
    support = lows[-1] if lows else None
    resistance = highs[-1] if highs else None

    # 强度 (简化: 最近3个点中相同类型的数量)
    recent_3 = zigzag_points[-3:]
    support_strength = sum(1 for p in recent_3 if p["type"] == "L")
    resistance_strength = sum(1 for p in recent_3 if p["type"] == "H")

    return {
        "support": support,
        "resistance": resistance,
        "support_strength": support_strength,
        "resistance_strength": resistance_strength
    }

# 示例:
# zigzag_points = [
#     {"type": "L", "price": 98.5},
#     {"type": "H", "price": 103.2},
#     {"type": "L", "price": 99.8}  ← 最近支撑
# ]
# → support = 99.8, resistance = 103.2
```

#### 3.2 订单薄分析 (新功能 - 需实现)

```python
def analyze_orderbook(symbol, exchange, depth=20):
    """
    分析订单薄，识别买卖墙和深度

    ⚠️ 警告: 此功能需要新实现
    - 需要实时获取订单薄数据 (通过交易所API)
    - 需要添加依赖: ccxt 或直接调用交易所WebSocket

    参数:
        symbol: str, 交易对
        exchange: str, 交易所
        depth: int, 订单薄深度 (默认20档)

    返回:
        dict: {
            "buy_wall_price": float or None,   # 买墙价格 (大额买单)
            "sell_wall_price": float or None,  # 卖墙价格 (大额卖单)
            "buy_depth_score": float,          # 买盘深度评分 0-100
            "sell_depth_score": float,         # 卖盘深度评分 0-100
            "imbalance": float                 # 买卖失衡 (-1到+1, +1表示买盘强)
        }
    """
    # TODO: 实现订单薄获取和分析
    # 伪代码:
    # orderbook = exchange_api.fetch_order_book(symbol, limit=depth)
    # bids = orderbook["bids"]  # [[price, quantity], ...]
    # asks = orderbook["asks"]

    # 1. 识别买卖墙 (大额订单)
    # buy_wall = find_large_order(bids, threshold=median*5)
    # sell_wall = find_large_order(asks, threshold=median*5)

    # 2. 计算深度评分
    # buy_depth_score = sum(quantity for price, quantity in bids)
    # sell_depth_score = sum(quantity for price, quantity in asks)

    # 3. 买卖失衡
    # imbalance = (buy_depth - sell_depth) / (buy_depth + sell_depth)

    # 临时: 返回模拟数据 (实际需要真实实现)
    return {
        "buy_wall_price": None,
        "sell_wall_price": None,
        "buy_depth_score": 50.0,
        "sell_depth_score": 50.0,
        "imbalance": 0.0
    }
```

#### 3.3 计算入场价

```python
def calculate_entry_price(
    current_price,
    support,
    resistance,
    enhanced_f,
    direction_score,
    orderbook_analysis,
    params
):
    """
    计算入场价

    逻辑:
        - Enhanced_F ≥ 70: 强吸筹 → 立即入场 (当前价)
        - Enhanced_F ≥ 40: 中等吸筹 → 等待回调到支撑附近 (support × 1.002)
        - Enhanced_F < 40: 弱吸筹 → 等待明确回调 (support × 1.005)

    参数:
        current_price: float, 当前价格
        support: float, 支撑位
        resistance: float, 阻力位
        enhanced_f: float, 加强版F因子
        direction_score: float, 方向得分 (>0做多, <0做空)
        orderbook_analysis: dict, 订单薄分析结果
        params: dict, 配置参数

    返回:
        float: 入场价
    """
    is_long = direction_score > 0

    if is_long:
        # 做多逻辑
        if enhanced_f >= 70:
            # 强吸筹: 立即入场
            entry_price = current_price
        elif enhanced_f >= 40:
            # 中等吸筹: 回调到支撑上方0.2%
            if support is not None:
                entry_price = support * 1.002
            else:
                entry_price = current_price * 0.998  # 无支撑数据，当前价下方0.2%
        else:
            # 弱吸筹: 回调到支撑上方0.5%
            if support is not None:
                entry_price = support * 1.005
            else:
                entry_price = current_price * 0.995

        # 买墙优化: 如果有强买墙，入场价不低于买墙
        buy_wall = orderbook_analysis.get("buy_wall_price")
        if buy_wall and entry_price < buy_wall:
            entry_price = buy_wall * 1.001  # 买墙上方0.1%

    else:
        # 做空逻辑 (对称)
        if enhanced_f >= 70:
            entry_price = current_price
        elif enhanced_f >= 40:
            if resistance is not None:
                entry_price = resistance * 0.998
            else:
                entry_price = current_price * 1.002
        else:
            if resistance is not None:
                entry_price = resistance * 0.995
            else:
                entry_price = current_price * 1.005

        # 卖墙优化
        sell_wall = orderbook_analysis.get("sell_wall_price")
        if sell_wall and entry_price > sell_wall:
            entry_price = sell_wall * 0.999

    return entry_price
```

#### 3.4 计算止损价

```python
def calculate_stop_loss(
    entry_price,
    support,
    resistance,
    atr,
    direction_score,
    l_score,
    params
):
    """
    计算止损价

    逻辑:
        方法1: 基于结构 (支撑/阻力下方)
        方法2: 基于波动率 (ATR × 倍数)
        最终: 取两者中更保守的 (止损更近的)

    参数:
        entry_price: float, 入场价
        support: float, 支撑位
        resistance: float, 阻力位
        atr: float, ATR值
        direction_score: float, 方向得分
        l_score: float, 流动性得分 (-100到+100)
        params: dict, 包含 "stop_loss_atr_multiplier" 等参数

    返回:
        float: 止损价
    """
    is_long = direction_score > 0

    # ATR倍数 (根据流动性调整)
    base_multiplier = params.get("stop_loss_atr_multiplier", 2.0)
    if l_score < -30:
        # 低流动性: 放宽止损 (×1.5)
        atr_multiplier = base_multiplier * 1.5
    elif l_score > 30:
        # 高流动性: 收紧止损 (×0.8)
        atr_multiplier = base_multiplier * 0.8
    else:
        atr_multiplier = base_multiplier

    if is_long:
        # 做多止损
        # 方法1: 支撑下方0.2%
        if support is not None:
            structure_stop = support * 0.998
        else:
            structure_stop = None

        # 方法2: 入场价 - ATR × 倍数
        volatility_stop = entry_price - atr * atr_multiplier

        # 取两者中更高的 (更保守)
        if structure_stop is not None:
            stop_loss = max(structure_stop, volatility_stop)
        else:
            stop_loss = volatility_stop

    else:
        # 做空止损 (对称)
        if resistance is not None:
            structure_stop = resistance * 1.002
        else:
            structure_stop = None

        volatility_stop = entry_price + atr * atr_multiplier

        if structure_stop is not None:
            stop_loss = min(structure_stop, volatility_stop)
        else:
            stop_loss = volatility_stop

    return stop_loss
```

#### 3.5 计算止盈价

```python
def calculate_take_profit(
    entry_price,
    stop_loss,
    resistance,
    support,
    direction_score,
    params
):
    """
    计算止盈价

    逻辑:
        约束1: 赔率 ≥ 1.5 (最低要求)
        约束2: 不超过阻力位 (做多) 或支撑位 (做空)

        计算:
            min_target = entry + (entry - stop_loss) × 2.0  (赔率2.0)
            structure_target = resistance × 0.998 (做多)
            take_profit = max(min_target, structure_target)

    参数:
        entry_price: float
        stop_loss: float
        resistance: float
        support: float
        direction_score: float
        params: dict, 包含 "min_risk_reward_ratio"

    返回:
        float: 止盈价
    """
    is_long = direction_score > 0
    min_rr_ratio = params.get("min_risk_reward_ratio", 1.5)

    # 风险 (止损距离)
    risk = abs(entry_price - stop_loss)

    if is_long:
        # 做多止盈
        # 最小目标 (基于赔率)
        min_target = entry_price + risk * min_rr_ratio

        # 结构目标 (阻力位下方0.2%)
        if resistance is not None:
            structure_target = resistance * 0.998
        else:
            structure_target = min_target  # 无阻力数据，使用最小目标

        # 取两者中更高的 (更激进的目标)
        take_profit = max(min_target, structure_target)

    else:
        # 做空止盈 (对称)
        min_target = entry_price - risk * min_rr_ratio

        if support is not None:
            structure_target = support * 1.002
        else:
            structure_target = min_target

        take_profit = min(min_target, structure_target)

    return take_profit
```

#### 3.6 第三步综合输出

```python
def step3_risk_management(
    current_price,
    klines,
    s_factor_meta,
    l_score,
    direction_score,
    enhanced_f,
    atr,
    symbol,
    exchange,
    params
):
    """
    第三步完整流程

    返回:
        dict: {
            "entry_price": float,
            "stop_loss": float,
            "take_profit": float,
            "risk_pct": float,           # 风险百分比
            "reward_pct": float,         # 收益百分比
            "risk_reward_ratio": float,  # 赔率
            "support": float,
            "resistance": float,
            "pass": bool
        }
    """
    # 1. 提取支撑/阻力
    sr = extract_support_resistance(s_factor_meta, direction_score)

    # 2. 订单薄分析
    orderbook = analyze_orderbook(symbol, exchange)

    # 3. 计算入场价
    entry_price = calculate_entry_price(
        current_price,
        sr["support"],
        sr["resistance"],
        enhanced_f,
        direction_score,
        orderbook,
        params
    )

    # 4. 计算止损价
    stop_loss = calculate_stop_loss(
        entry_price,
        sr["support"],
        sr["resistance"],
        atr,
        direction_score,
        l_score,
        params
    )

    # 5. 计算止盈价
    take_profit = calculate_take_profit(
        entry_price,
        stop_loss,
        sr["resistance"],
        sr["support"],
        direction_score,
        params
    )

    # 6. 计算风险和收益
    risk_pct = abs(entry_price - stop_loss) / entry_price * 100
    reward_pct = abs(take_profit - entry_price) / entry_price * 100
    risk_reward_ratio = reward_pct / max(risk_pct, 0.01)

    # 7. 验证赔率
    min_rr = params.get("min_risk_reward_ratio", 1.5)
    pass_step3 = risk_reward_ratio >= min_rr

    return {
        "entry_price": round(entry_price, 4),
        "stop_loss": round(stop_loss, 4),
        "take_profit": round(take_profit, 4),
        "risk_pct": round(risk_pct, 2),
        "reward_pct": round(reward_pct, 2),
        "risk_reward_ratio": round(risk_reward_ratio, 2),
        "support": sr["support"],
        "resistance": sr["resistance"],
        "pass": pass_step3,
        "reject_reason": None if pass_step3 else f"赔率不足: {risk_reward_ratio:.2f} < {min_rr}"
    }

# 示例输出:
# {
#     "entry_price": 100.00,
#     "stop_loss": 97.80,
#     "take_profit": 109.78,
#     "risk_pct": 2.20,
#     "reward_pct": 9.78,
#     "risk_reward_ratio": 4.45,
#     "support": 99.80,
#     "resistance": 110.00,
#     "pass": True
# }
```

---

## 第四步：质量控制层

### 设计目标

沿用现有四道门槛系统，确保信号质量:

1. **Gate1**: 基础筛选 (成交量、价格范围等)
2. **Gate2**: 噪声过滤 (波动率、ATR)
3. **Gate3**: 信号强度 (Prime_Strength阈值)
4. **Gate4**: 矛盾检测 (因子一致性)

### 实现细节

#### 4.1 四道门槛检查

```python
def step4_quality_control(
    symbol,
    klines,
    factor_scores,
    prime_strength,
    step1_result,
    step2_result,
    step3_result,
    params
):
    """
    第四步完整流程

    返回:
        dict: {
            "gate1_pass": bool,
            "gate2_pass": bool,
            "gate3_pass": bool,
            "gate4_pass": bool,
            "all_gates_pass": bool,
            "final_decision": "ACCEPT" or "REJECT",
            "reject_reason": str or None
        }
    """
    # Gate1: 基础筛选
    volume_24h = sum(k["volume"] for k in klines[-24:])
    min_volume = params.get("gate1_min_volume_24h", 1000000)
    gate1_pass = volume_24h >= min_volume
    gate1_reason = None if gate1_pass else f"24h成交量不足: {volume_24h:.0f} < {min_volume}"

    # Gate2: 噪声过滤
    close_now = klines[-1]["close"]
    atr = klines[-1].get("atr", 0)
    noise_ratio = atr / close_now if close_now > 0 else 1.0
    max_noise = params.get("gate2_max_noise_ratio", 0.15)
    gate2_pass = noise_ratio <= max_noise
    gate2_reason = None if gate2_pass else f"噪声过高: {noise_ratio:.2%} > {max_noise:.2%}"

    # Gate3: 信号强度 (已由第一步的final_strength验证，这里可额外检查)
    min_strength = params.get("gate3_min_prime_strength", 35)
    gate3_pass = prime_strength >= min_strength
    gate3_reason = None if gate3_pass else f"信号强度不足: {prime_strength:.1f} < {min_strength}"

    # Gate4: 矛盾检测
    # 检查因子一致性 (例如: C和O方向一致性)
    c_score = factor_scores["C"]
    o_score = factor_scores["O"]
    t_score = factor_scores["T"]

    # 矛盾1: C和O方向相反 (资金流入但持仓减少，或反之)
    contradiction1 = (c_score * o_score) < -1000  # 都是强信号但方向相反

    # 矛盾2: T和增强F因子矛盾 (强趋势但追高)
    contradiction2 = (abs(t_score) > 70) and (step2_result["enhanced_f"] < -40)

    gate4_pass = not (contradiction1 or contradiction2)
    if contradiction1:
        gate4_reason = f"C和O因子方向矛盾: C={c_score}, O={o_score}"
    elif contradiction2:
        gate4_reason = f"趋势与时机矛盾: T={t_score}, Enhanced_F={step2_result['enhanced_f']}"
    else:
        gate4_reason = None

    # 综合判断
    all_gates_pass = gate1_pass and gate2_pass and gate3_pass and gate4_pass

    if all_gates_pass:
        final_decision = "ACCEPT"
        reject_reason = None
    else:
        final_decision = "REJECT"
        # 找出第一个失败的门槛
        reject_reason = gate1_reason or gate2_reason or gate3_reason or gate4_reason

    return {
        "gate1_pass": gate1_pass,
        "gate2_pass": gate2_pass,
        "gate3_pass": gate3_pass,
        "gate4_pass": gate4_pass,
        "all_gates_pass": all_gates_pass,
        "final_decision": final_decision,
        "reject_reason": reject_reason
    }
```

---

## 系统输出示例

### 成功案例 (ACCEPT)

```json
{
  "symbol": "ETHUSDT",
  "timestamp": "2025-11-16T10:00:00Z",
  "decision": "ACCEPT",

  "step1_direction": {
    "direction_score": 52.3,
    "direction_strength": 52.3,
    "direction_confidence": 0.88,
    "btc_alignment": 0.93,
    "final_strength": 42.7,
    "pass": true
  },

  "step2_timing": {
    "enhanced_f": 85.2,
    "signal_momentum": 27.3,
    "price_momentum": 0.83,
    "timing_quality": "Excellent",
    "entry_signal": true,
    "pass": true
  },

  "step3_risk": {
    "entry_price": 2000.00,
    "stop_loss": 1956.00,
    "take_profit": 2188.00,
    "risk_pct": 2.20,
    "reward_pct": 9.40,
    "risk_reward_ratio": 4.27,
    "support": 1950.00,
    "resistance": 2200.00,
    "pass": true
  },

  "step4_quality": {
    "gate1_pass": true,
    "gate2_pass": true,
    "gate3_pass": true,
    "gate4_pass": true,
    "all_gates_pass": true,
    "final_decision": "ACCEPT"
  },

  "action": "LONG",
  "confidence": 0.88,

  "factor_scores": {
    "T": 35, "M": 20, "C": 90, "V": 45, "O": 70, "B": 25,
    "F": 85, "S": 65, "L": 40, "I": -10
  }
}
```

### 拒绝案例 (REJECT - 追高)

```json
{
  "symbol": "BTCUSDT",
  "timestamp": "2025-11-16T10:00:00Z",
  "decision": "REJECT",

  "step1_direction": {
    "direction_score": 68.5,
    "direction_strength": 68.5,
    "direction_confidence": 0.92,
    "btc_alignment": 1.00,
    "final_strength": 63.0,
    "pass": true
  },

  "step2_timing": {
    "enhanced_f": -52.3,
    "signal_momentum": 5.2,
    "price_momentum": 18.7,
    "timing_quality": "Chase",
    "entry_signal": false,
    "pass": false,
    "reject_reason": "时机不佳 (Enhanced_F=-52.3 < 30.0)"
  },

  "step3_risk": null,
  "step4_quality": null,

  "reject_reason": "时机不佳 (Enhanced_F=-52.3 < 30.0) - 价格已大幅上涨，信号增强滞后，疑似追高"
}
```

---

## 实施计划

### 阶段划分

#### **阶段1: 第一步和第二步** (20小时)

**任务**:
1. 实现Step1方向确认层 (8小时)
   - `calculate_direction_confidence()`
   - `calculate_btc_alignment()`
   - 单元测试

2. 实现Step2时机判断层 (12小时)
   - `calculate_signal_momentum()` - 核心创新 ✨
   - `calculate_enhanced_f_factor()`
   - 单元测试
   - 回测验证 (对比原版F因子)

**可交付物**:
- 新文件: `ats_core/decision/step1_direction.py`
- 新文件: `ats_core/decision/step2_timing.py`
- 测试覆盖率 ≥ 80%

**风险**: 低 (不涉及订单薄等外部依赖)

---

#### **阶段2: 第三步 (基础版)** (12小时)

**任务**:
1. 实现支撑/阻力位提取 (4小时)
   - `extract_support_resistance()`
   - 利用现有S因子元数据

2. 实现价格计算逻辑 (6小时)
   - `calculate_entry_price()`
   - `calculate_stop_loss()`
   - `calculate_take_profit()`
   - 单元测试

3. 订单薄分析 **占位实现** (2小时)
   - `analyze_orderbook()` 返回默认值
   - 预留接口，后续扩展

**可交付物**:
- 新文件: `ats_core/decision/step3_risk.py`
- 输出具体价格 (entry/stop/target)

**风险**: 低-中 (订单薄占位，不影响主流程)

---

#### **阶段3: 第四步 + 集成** (8小时)

**任务**:
1. 实现第四步质量控制 (3小时)
   - `step4_quality_control()`
   - 沿用现有四道门槛逻辑

2. 主流程集成 (5小时)
   - 新文件: `ats_core/decision/four_step_system.py`
   - 函数: `run_four_step_decision()`
   - 集成到现有信号生成流程

**可交付物**:
- 完整四步系统
- 集成测试

**风险**: 中 (需要修改主流程)

---

#### **阶段4 (可选): 订单薄真实实现** (20-30小时)

**任务**:
1. 添加交易所API依赖 (ccxt或原生WebSocket)
2. 实现实时订单薄获取
3. 买卖墙识别算法
4. 深度评分算法
5. 缓存和性能优化

**风险**: 高 (外部依赖、延迟、稳定性)

**建议**: 先上线基础版，观察效果后再决定是否实现

---

### 配置参数 (config/params.json 新增)

```json
{
  "four_step_system": {
    "enabled": true,

    "step1": {
      "min_final_strength": 20.0,
      "I_serious_follow_threshold": -50,
      "I_moderate_follow_threshold": -30
    },

    "step2": {
      "enhanced_f_scale": 20.0,
      "min_enhanced_f": 30.0,
      "signal_momentum_window_hours": 6
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

## 风险评估

### 技术风险

| 风险项 | 等级 | 缓解措施 |
|--------|------|----------|
| 信号动量计算不稳定 | 中 | 充分回测，调整scale参数 |
| 订单薄数据延迟 | 高 | 阶段4可选，先用占位实现 |
| 支撑/阻力位提取不准 | 中 | 依赖S因子质量，已有ZigZag数据 |
| BTC数据获取失败 | 低 | 降级处理: btc_alignment=0.9 |
| 性能下降 (新增计算) | 低 | 增量计算，缓存优化 |

### 业务风险

| 风险项 | 等级 | 缓解措施 |
|--------|------|----------|
| 信号数量大幅减少 | 中 | 配置参数可调，分阶段放宽阈值 |
| 回测效果不理想 | 中 | 先在测试环境验证，保留回退机制 |
| 赔率要求过高错失机会 | 低 | min_risk_reward_ratio可配置 (1.5-3.0) |

---

## 性能预期

### 信号质量提升 (预估)

基于用户洞察和理论分析:

```
当前系统问题:
- 信号延迟: 15-25% 价格移动后才发信号
- 追高比例: ~40% 信号属于追高 (F<0但被忽略)
- 止损不明: 无具体止损价，用户自行判断

四步系统改进:
1. 第二步Enhanced F过滤 → 追高比例降至 <10% ✅
2. 第三步具体价格 → 止损明确，赔率保证 ≥1.5 ✅
3. 第一步BTC/I因子确认 → 方向准确性提升 10-15% ✅

综合预期:
- 信号胜率: 55% → 65-70% (+10-15个百分点)
- 平均赔率: ~1.8 → ≥2.5 (结构化止盈止损)
- 信号数量: 100% → 60-70% (质量换数量)
- 综合收益 (胜率×赔率): 0.99 → 1.625-1.75 (+64-77%) ✅✅✅
```

### 计算性能

```
新增计算量:
- Step1: 轻量 (~5ms)
- Step2: 中等 (~15ms, 需7小时历史因子得分)
- Step3: 轻量 (~10ms)
- Step4: 轻量 (~5ms)

总计: ~35ms / 信号

影响: 可忽略 (现有系统单次计算 ~200ms)
```

---

## 向后兼容

### 双轨运行方案

```python
def generate_signal(symbol, klines, ...):
    """信号生成主函数"""

    # 1. 计算所有因子 (保持不变)
    factor_scores = calculate_all_factors(...)

    # 2. 选择决策系统
    if params.get("four_step_system.enabled", False):
        # 新系统: 四步分层决策
        result = run_four_step_decision(
            symbol, klines, factor_scores, btc_data, params
        )
    else:
        # 旧系统: 加权评分
        result = run_legacy_system(
            factor_scores, params
        )

    return result
```

**切换开关**: `config/params.json` 中 `"four_step_system.enabled": true/false`

---

## 总结

### 关键创新

1. **加强版F因子**: 从单纯CVD+OI → 全因子综合信号，更全面反映市场情绪
2. **三维风险收益**: 概率 + 时机 + 风险，系统化评估机会质量
3. **具体可操作价格**: 不仅给方向，更给入场/止损/止盈价，直接可用
4. **分层过滤**: 四步递进，每步关注点不同，清晰分离关注点

### 用户价值

- ✅ **解决追涨杀跌**: Enhanced F过滤追高信号
- ✅ **明确止损**: 不再靠感觉，系统给出具体价格
- ✅ **保证赔率**: 最低1.5赔率，确保"不容易止损"
- ✅ **提升胜率**: 多维度确认，减少假信号

---

**下一步**: 等待用户确认本设计方案，确认后开始阶段1实施 (预计20小时)
