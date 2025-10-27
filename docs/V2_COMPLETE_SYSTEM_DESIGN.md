# V2完整版系统设计方案

## 📐 设计理念

### 核心原则
1. **数据驱动** - 所有因子基于高质量、可获取的数据
2. **因子正交** - 减少冗余，相关性<0.5
3. **自适应性** - 根据市场体制动态调整
4. **可解释性** - 每个信号可追溯原因
5. **鲁棒性** - 对噪音和缺失数据有抵抗力

### 借鉴V1优秀做法
✅ **统一±100评分系统** - 保持标准化
✅ **分层架构** - 清晰的因子分组
✅ **F调节器机制** - 资金领先性调节
✅ **WebSocket实时优化** - 17倍性能提升
✅ **优雅降级** - 数据缺失时合理默认

---

## 🏗️ 系统架构：12+1维因子体系

### 总体架构（200点权重系统）

```
V2完整版 = 5层因子 + 1个调节器 + 1个质量评估

Layer 1: Price Discovery（价格发现）    - 45点
Layer 2: Order Flow（订单流）           - 60点
Layer 3: Positioning（持仓分析）        - 40点
Layer 4: Structure（结构质量）          - 35点
Layer 5: Context（市场环境）            - 20点
--------------------------------
总计：200点 → 归一化到±100（除以2.0）

Regulator: F（资金领先性调节器）
Quality: Q*（信号质量评分）0-100
```

---

## 📊 Layer 1: Price Discovery（价格发现层）- 45点

### **T (Multi-Timeframe Trend)** - 多周期趋势一致性 [25点]

**理论基础**：
趋势是最强的Alpha来源，多周期一致性能过滤假突破

**计算方法**：
```python
# 3个周期：15m / 1h / 4h
trend_15m = calculate_trend_score(k15m)  # EMA斜率+MACD
trend_1h = calculate_trend_score(k1h)
trend_4h = calculate_trend_score(k4h)

# 加权聚合（长周期权重更高）
T_score = (
    trend_15m * 0.2 +  # 短期：20%
    trend_1h * 0.35 +   # 中期：35%
    trend_4h * 0.45     # 长期：45%
)

# 一致性加权
if sign(trend_15m) == sign(trend_1h) == sign(trend_4h):
    T_score *= 1.3  # 同向强化30%
elif sign(trend_1h) != sign(trend_4h):
    T_score *= 0.7  # 冲突减弱30%
```

**数据需求**：K线（15m/1h/4h）✅ 已有

**V1改进**：
- V1只用1个周期 → V2用3个周期
- V1简单EMA → V2多维度（EMA+MACD+斜率+波动率）

---

### **M (Momentum Acceleration)** - 动量加速度 [20点]

**理论基础**：
价格动量的二阶导数（加速度）能提前捕捉趋势转折

**计算方法**：
```python
# ROC (Rate of Change)
roc_14 = (price[-1] - price[-14]) / price[-14] * 100

# 动量加速度（ROC的变化率）
roc_delta = roc_14 - roc_7
acceleration = roc_delta / 7  # 归一化

# RSI动量
rsi_14 = calculate_rsi(price, 14)
rsi_momentum = (rsi_14 - 50) * 2  # -100 to +100

# 综合评分
M_score = (
    acceleration * 50 +    # 50%加速度
    rsi_momentum * 0.3 +   # 30%RSI
    roc_14 * 0.2           # 20%ROC
)
```

**数据需求**：K线 ✅ 已有

**V1改进**：
- V1只用RSI+ROC → V2增加加速度检测
- V1静态 → V2动态调整敏感度

---

## 📈 Layer 2: Order Flow（订单流层）- 60点

### **C+ (Enhanced CVD)** - 增强资金流 [25点]

**理论基础**：
CVD（Cumulative Volume Delta）是机构资金流向的直接体现

**计算方法**：
```python
# 期货CVD（主力）
perp_cvd = sum([
    volume * sign(close - open)  # 主动买入为正，主动卖出为负
    for each kline
])

# 现货CVD（验证）
spot_cvd = sum([
    volume * sign(close - open)
    for each spot kline
])

# 动态权重（根据期现成交量比例）
perp_ratio = perp_volume / (perp_volume + spot_volume)
spot_ratio = 1 - perp_ratio

# 加权融合
cvd_combined = perp_cvd * perp_ratio + spot_cvd * spot_ratio

# EMA平滑（12周期）
cvd_smooth = ema(cvd_combined, 12)

# Z-score归一化
cvd_zscore = (cvd_smooth - mean(cvd_60)) / std(cvd_60)

C_plus_score = tanh(cvd_zscore) * 100  # -100 to +100
```

**数据需求**：
- 期货K线 ✅ 已有
- 现货K线 ✅ 已有

**V1改进**：
- V1简单CVD → V2动态权重+现货验证
- V1无平滑 → V2 EMA平滑减少噪音
- V1固定阈值 → V2 Z-score自适应

---

### **V+ (Volume Profile)** - 成交量分布分析 [20点]

**理论基础**：
成交量在价格区间的分布反映支撑阻力和突破概率

**计算方法**：
```python
# 计算成交量分布（过去50根K线）
volume_profile = {}
for kline in last_50:
    price_level = round(kline.close, price_precision)
    volume_profile[price_level] = volume_profile.get(price_level, 0) + kline.volume

# 寻找POC（Point of Control，成交量最大价位）
poc_price = max(volume_profile, key=volume_profile.get)

# 寻找VAH/VAL（Value Area High/Low，70%成交量区间）
sorted_levels = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
cumulative_volume = 0
total_volume = sum(volume_profile.values())
value_area = []

for price, vol in sorted_levels:
    cumulative_volume += vol
    value_area.append(price)
    if cumulative_volume >= total_volume * 0.7:
        break

vah = max(value_area)
val = min(value_area)
current_price = klines[-1].close

# 位置评分
if current_price > vah:
    position_score = 100  # 突破高价值区，看涨
elif current_price < val:
    position_score = -100  # 跌破低价值区，看跌
else:
    position_score = ((current_price - val) / (vah - val) - 0.5) * 200  # -100 to +100

# 触发K检测
if is_trigger_candle(klines[-1], volume_mult=1.5, body_ratio=0.6):
    trigger_score = 100 if klines[-1].close > klines[-1].open else -100
else:
    trigger_score = 0

# 综合评分
V_plus_score = position_score * 0.6 + trigger_score * 0.4
```

**数据需求**：K线 ✅ 已有

**V1改进**：
- V1简单成交量比较 → V2成交量分布分析
- V1无POC/VAH/VAL → V2完整Volume Profile
- V1无触发K → V2触发K模式检测

---

### **L (Liquidity Depth)** - 流动性深度 [15点]

**理论基础**：
订单簿深度反映市场承载能力和价格稳定性

**计算方法**：
```python
# 获取订单簿（20档）
orderbook = fetch_orderbook(symbol, depth=20)

# 1. 价差评分
spread_bps = (ask1 - bid1) / mid_price * 10000
spread_score = 100 if spread_bps < 2 else max(0, 100 - (spread_bps - 2) * 10)

# 2. 深度评分
bid_depth_5 = sum([level.quantity for level in orderbook.bids[:5]])
ask_depth_5 = sum([level.quantity for level in orderbook.asks[:5]])
total_depth_usdt = (bid_depth_5 + ask_depth_5) * mid_price

depth_score = min(100, total_depth_usdt / 1_000_000 * 100)  # 100万USDT为满分

# 3. 失衡度（OBI - Order Book Imbalance）
obi = (bid_depth_5 - ask_depth_5) / (bid_depth_5 + ask_depth_5)
obi_score = obi * 100  # -100 to +100

# 4. 冲击成本
impact_cost_100k = calculate_impact_cost(orderbook, notional=100000)
impact_score = max(0, 100 - impact_cost_100k * 10000)  # 1%冲击为0分

# 综合评分（质量+方向）
quality_score = (spread_score * 0.3 + depth_score * 0.3 + impact_score * 0.4)
L_score = quality_score * 0.7 + obi_score * 0.3
```

**数据需求**：
- ❌ 订单簿API（20档深度）- **需要实现**

**实施方案**：
```python
# Binance Futures API
GET /fapi/v1/depth?symbol=BTCUSDT&limit=20

# WebSocket订阅
ws://fstream.binance.com/ws/btcusdt@depth20@100ms
```

---

## 💼 Layer 3: Positioning（持仓分析层）- 40点

### **O+ (OI Regime Analysis)** - OI四象限体制分析 [20点]

**理论基础**：
持仓量+价格的联合变化识别市场真实力量方向

**计算方法**：
```python
# 计算OI和价格的12小时变化
delta_oi = (oi_now - oi_12h_ago) / oi_12h_ago
delta_price = (price_now - price_12h_ago) / price_12h_ago

# 四象限识别
if delta_oi > 0.05 and delta_price > 0.02:
    regime = "LONG_DOMINANT"  # OI↑ Price↑ 多头主导
    score = 100
elif delta_oi > 0.05 and delta_price < -0.02:
    regime = "SHORT_SQUEEZE"  # OI↑ Price↓ 空头止损
    score = 30
elif delta_oi < -0.05 and delta_price > 0.02:
    regime = "LONG_UNWIND"    # OI↓ Price↑ 多头止损
    score = -30
elif delta_oi < -0.05 and delta_price < -0.02:
    regime = "SHORT_DOMINANT" # OI↓ Price↓ 空头主导
    score = -100
else:
    regime = "NEUTRAL"
    score = 0

# OI水平调整（相对历史）
oi_percentile = percentile_rank(oi_now, oi_history_7d)
if oi_percentile > 80:
    score *= 1.2  # 高持仓强化
elif oi_percentile < 20:
    score *= 0.8  # 低持仓减弱

O_plus_score = clip(score, -100, 100)
```

**数据需求**：
- 持仓量历史 ✅ 已有
- K线 ✅ 已有

**V1改进**：
- V1简单OI变化率 → V2四象限体制识别
- V1无价格联动 → V2 OI+Price联合分析
- V1无历史对比 → V2相对历史百分位调整

---

### **Q (Liquidation Heat Map)** - 清算热力图 [10点]

**理论基础**：
清算密度聚集区是价格磁铁，触及后引发级联反应

**计算方法**：
```python
# 获取清算数据（过去24小时）
liquidations = fetch_liquidations(symbol, hours=24)

# 计算清算密度（按价格区间分桶）
price_buckets = defaultdict(float)
for liq in liquidations:
    bucket = round(liq.price / price_now, 2)  # 相对当前价格的百分比
    price_buckets[bucket] += liq.quantity_usdt

# 寻找清算墙（密度>100万USDT的区域）
liquidation_walls = [
    (bucket, qty) for bucket, qty in price_buckets.items()
    if qty > 1_000_000
]

# 计算LTI（Liquidation Tilt Index）
long_liquidations = sum([liq.qty for liq in liquidations if liq.side == "LONG"])
short_liquidations = sum([liq.qty for liq in liquidations if liq.side == "SHORT"])
total_liquidations = long_liquidations + short_liquidations

if total_liquidations > 0:
    lti = (long_liquidations - short_liquidations) / total_liquidations
    # 多头清算多 → 超跌反弹 → 看涨
    # 空头清算多 → 超涨回调 → 看跌
    lti_score = -lti * 100  # 反向指标
else:
    lti_score = 0

# 清算墙距离评分
nearest_long_wall = min([
    abs(bucket - 1.0) for bucket, _ in liquidation_walls if bucket < 1.0
], default=0.1)

nearest_short_wall = min([
    abs(bucket - 1.0) for bucket, _ in liquidation_walls if bucket > 1.0
], default=0.1)

if nearest_long_wall < 0.02:  # 下方2%有多头清算墙
    wall_score = -50  # 下跌风险
elif nearest_short_wall < 0.02:  # 上方2%有空头清算墙
    wall_score = 50  # 上涨机会
else:
    wall_score = 0

Q_score = lti_score * 0.6 + wall_score * 0.4
```

**数据需求**：
- ❌ 清算数据API - **需要实现**

**实施方案**：
```python
# Binance API
GET /fapi/v1/forceOrders?symbol=BTCUSDT

# 或使用第三方数据源
# Coinglass API、CoinGecko Pro等
```

---

### **B (Basis + Funding Sentiment)** - 基差+资金费情绪 [10点]

**理论基础**：
基差和资金费率反映市场情绪和资金成本

**计算方法**：
```python
# 1. 基差计算
perp_price = fetch_perp_price(symbol)
spot_price = fetch_spot_price(symbol)
basis_bps = (perp_price - spot_price) / spot_price * 10000

# 基差评分（正基差=看涨情绪，负基差=看跌情绪）
if abs(basis_bps) < 50:
    basis_score = basis_bps / 50 * 50  # -50 to +50（中性）
else:
    basis_score = 50 if basis_bps > 0 else -50  # 极端基差打折

# 2. 资金费率
funding_rate = fetch_funding_rate(symbol)
funding_bps = funding_rate * 10000

# 资金费率评分（正费率=多头过热，负费率=空头过热）
if abs(funding_bps) < 10:
    funding_score = -funding_bps / 10 * 30  # 反向指标
else:
    funding_score = -30 if funding_bps > 0 else 30  # 极端反转

# 3. 资金费率趋势
funding_history_8h = fetch_funding_history(hours=8)
funding_trend = (funding_rate - mean(funding_history_8h)) / std(funding_history_8h)
trend_score = -tanh(funding_trend) * 20  # 反向指标

# 综合评分
B_score = basis_score * 0.4 + funding_score * 0.4 + trend_score * 0.2
```

**数据需求**：
- 现货价格 ✅ 已有
- 期货价格 ✅ 已有
- ⚠️ 资金费率 - **需要稳定化**

**实施方案**：
```python
# Binance API
GET /fapi/v1/premiumIndex?symbol=BTCUSDT  # 实时资金费率
GET /fapi/v1/fundingRate?symbol=BTCUSDT  # 历史资金费率

# WebSocket订阅
ws://fstream.binance.com/ws/btcusdt@markPrice
```

---

## 🏛️ Layer 4: Structure（结构质量层）- 35点

### **S (Support/Resistance Quality)** - 支撑阻力质量 [20点]

**理论基础**：
高质量的支撑阻力是价格反转和突破的关键位置

**计算方法**：
```python
# 1. Pivot点识别（过去50根K线）
pivots_high = find_pivots(highs, type="high", window=5)
pivots_low = find_pivots(lows, type="low", window=5)

# 2. 支撑阻力聚类（相近的pivot合并）
support_clusters = cluster_pivots(pivots_low, tolerance_atr=0.5)
resistance_clusters = cluster_pivots(pivots_high, tolerance_atr=0.5)

# 3. 强度评分（触碰次数+成交量）
support_strength = [
    len(cluster) * sum([volume_at_pivot(p) for p in cluster])
    for cluster in support_clusters
]

resistance_strength = [
    len(cluster) * sum([volume_at_pivot(p) for p in cluster])
    for cluster in resistance_clusters
]

# 4. 当前价格位置
current_price = klines[-1].close
nearest_support = find_nearest(current_price, support_clusters, direction="below")
nearest_resistance = find_nearest(current_price, resistance_clusters, direction="above")

# 距离评分（以ATR为单位）
support_distance_atr = (current_price - nearest_support) / atr_14
resistance_distance_atr = (nearest_resistance - current_price) / atr_14

# 结构质量评分
if 1 <= support_distance_atr <= 3 and 2 <= resistance_distance_atr <= 4:
    structure_quality = 100  # 理想结构
else:
    structure_quality = max(0, 100 - abs(support_distance_atr - 2) * 15 - abs(resistance_distance_atr - 3) * 10)

# 方向倾向
if support_distance_atr < resistance_distance_atr:
    direction_bias = 50  # 离支撑近，看涨
else:
    direction_bias = -50  # 离阻力近，看跌

S_score = structure_quality * 0.6 + direction_bias * 0.4
```

**数据需求**：K线 ✅ 已有

**V1改进**：
- V1简单pivot → V2聚类+强度评分
- V1无成交量 → V2成交量加权
- V1静态距离 → V2动态ATR归一化

---

### **P (Pattern Recognition)** - 形态识别 [15点]

**理论基础**：
经典技术形态（头肩顶底、双顶底、三角形等）统计上有预测能力

**计算方法**：
```python
# 识别经典形态（过去100根K线）
patterns = {
    "double_top": detect_double_top(klines),
    "double_bottom": detect_double_bottom(klines),
    "head_shoulders": detect_head_shoulders(klines),
    "inverse_head_shoulders": detect_inverse_head_shoulders(klines),
    "ascending_triangle": detect_ascending_triangle(klines),
    "descending_triangle": detect_descending_triangle(klines),
    "bull_flag": detect_bull_flag(klines),
    "bear_flag": detect_bear_flag(klines)
}

# 形态评分
pattern_scores = {
    "double_top": -80,
    "double_bottom": 80,
    "head_shoulders": -80,
    "inverse_head_shoulders": 80,
    "ascending_triangle": 60,
    "descending_triangle": -60,
    "bull_flag": 70,
    "bear_flag": -70
}

# 寻找最强信号
detected_patterns = [
    (name, confidence) for name, confidence in patterns.items()
    if confidence > 0.7  # 置信度>70%
]

if detected_patterns:
    # 选择置信度最高的形态
    best_pattern, confidence = max(detected_patterns, key=lambda x: x[1])
    P_score = pattern_scores[best_pattern] * confidence
else:
    P_score = 0

# 突破确认
if P_score != 0:
    if is_breakout_confirmed(klines, pattern=best_pattern):
        P_score *= 1.3  # 突破确认强化30%
```

**数据需求**：K线 ✅ 已有

**V1改进**：
- V1无形态识别 → V2完整形态库
- V1无置信度 → V2置信度加权
- V1无突破确认 → V2突破确认机制

---

## 🌍 Layer 5: Context（市场环境层）- 20点

### **I (Independence Beta)** - 独立性分析 [10点]

**理论基础**：
Beta独立性低的币种有更高的Alpha潜力

**计算方法**：
```python
# 计算24小时收益率
alt_returns = calculate_returns(alt_prices, window=24)
btc_returns = calculate_returns(btc_prices, window=24)
eth_returns = calculate_returns(eth_prices, window=24)

# OLS回归
beta_btc = regression(alt_returns, btc_returns).beta
beta_eth = regression(alt_returns, eth_returns).beta

# Beta加权（BTC权重更高）
beta_weighted = beta_btc * 0.6 + beta_eth * 0.4

# 独立性评分
if beta_weighted < 0.5:
    independence_score = 100  # 高独立性
elif beta_weighted < 1.0:
    independence_score = 100 - (beta_weighted - 0.5) * 100
elif beta_weighted < 1.5:
    independence_score = 50 - (beta_weighted - 1.0) * 100
else:
    independence_score = max(0, 50 - (beta_weighted - 1.5) * 50)

# R²调整（拟合度越高，独立性越低）
r_squared = regression(alt_returns, btc_returns).r_squared
independence_adjusted = independence_score * (1 - r_squared * 0.3)

I_score = independence_adjusted
```

**数据需求**：
- 币种K线 ✅ 已有
- BTC K线 ✅ 已有
- ETH K线 ✅ 已有

**V2 Lite改进**：
- 增加R²调整
- 增加动态窗口（24h/7d切换）

---

### **R (Market Regime Detection)** - 市场体制识别 [10点]

**理论基础**：
不同市场体制下，最优策略不同

**计算方法**：
```python
# 1. 波动率体制
volatility_20d = std(btc_returns_20d) * sqrt(365)  # 年化波动率

if volatility_20d > 0.08:
    volatility_regime = "HIGH_VOL"  # 高波动
elif volatility_20d > 0.04:
    volatility_regime = "NORMAL"    # 正常
else:
    volatility_regime = "LOW_VOL"   # 低波动

# 2. 趋势体制
btc_trend = calculate_trend_score(btc_klines)

if abs(btc_trend) > 60:
    trend_regime = "TRENDING"       # 趋势市
elif abs(btc_trend) < 30:
    trend_regime = "RANGING"        # 震荡市
else:
    trend_regime = "TRANSITIONING"  # 过渡期

# 3. 流动性体制
btc_volume_ratio = btc_volume_24h / btc_volume_avg_30d

if btc_volume_ratio > 1.5:
    liquidity_regime = "HIGH_LIQUIDITY"
elif btc_volume_ratio > 0.8:
    liquidity_regime = "NORMAL"
else:
    liquidity_regime = "LOW_LIQUIDITY"

# 综合体制评分
regime_scores = {
    ("HIGH_VOL", "TRENDING", "HIGH_LIQUIDITY"): 80,      # 最佳交易环境
    ("NORMAL", "TRENDING", "NORMAL"): 60,
    ("LOW_VOL", "RANGING", "LOW_LIQUIDITY"): -60,       # 最差交易环境
    ("HIGH_VOL", "RANGING", "NORMAL"): -40,             # 高波动震荡（危险）
}

# 查找匹配体制
regime_key = (volatility_regime, trend_regime, liquidity_regime)
R_score = regime_scores.get(regime_key, 0)  # 默认中性
```

**数据需求**：
- BTC K线 ✅ 已有
- BTC成交量 ✅ 已有

**创新点**：
- V1/V2 Lite都无此维度
- 市场体制识别影响权重分配

---

## ⚙️ Regulator: F (Fund Leading)** - 资金领先性调节器

**保持V1设计**，但增强计算：

```python
# OI增长
oi_change_pct = (oi_now - oi_24h_ago) / oi_24h_ago

# 成交量比
volume_ratio = volume_24h / volume_avg_30d

# CVD趋势
cvd_delta_pct = (cvd_now - cvd_24h_ago) / price_now

# 价格趋势
price_slope = (ema30[-1] - ema30[-7]) / (6 * atr)

# 领先性判断
if oi_change_pct > 0.1 and cvd_delta_pct > 0.005 and price_slope < 0.5:
    fund_leading = 100  # 资金先行，价格滞后（强看涨）
elif oi_change_pct < -0.1 and cvd_delta_pct < -0.005 and price_slope > -0.5:
    fund_leading = -100  # 资金撤退，价格滞后（强看跌）
else:
    fund_leading = (oi_change_pct * 50 + volume_ratio * 25 + cvd_delta_pct * 2500) / 3

F_score = clip(fund_leading, -100, 100)
```

**作用**：
- 调节最终概率的温度参数
- F > 50: 降低温度（增强信号）
- F < -50: 提高温度（减弱信号）

---

## 🎯 Quality Assessment: Q* (Signal Quality Score)** - 信号质量评分

**创新模块**：评估信号的可靠性

```python
# 1. 因子一致性（多个因子同向）
bullish_factors = sum([1 for score in scores.values() if score > 30])
bearish_factors = sum([1 for score in scores.values() if score < -30])
consistency = abs(bullish_factors - bearish_factors) / 12 * 100

# 2. 数据质量
data_quality = (
    (1 if orderbook_available else 0) * 20 +
    (1 if liquidation_available else 0) * 15 +
    (1 if funding_available else 0) * 15 +
    (kline_completeness) * 30 +
    (spot_kline_available) * 20
)

# 3. 市场体制适配
if regime_score > 50 and abs(weighted_score) > 70:
    regime_bonus = 20  # 好体制+强信号
elif regime_score < -40 and abs(weighted_score) < 50:
    regime_penalty = -30  # 差体制+弱信号
else:
    regime_bonus = 0

# 4. 历史准确率（滑动窗口）
historical_accuracy = fetch_factor_ic(symbol, window=30d)

# 综合质量评分
Q_star = (
    consistency * 0.3 +
    data_quality * 0.3 +
    (regime_score + 100) / 2 * 0.2 +
    historical_accuracy * 0.2 +
    regime_bonus
)

Q_star = clip(Q_star, 0, 100)
```

**用途**：
- Q* > 80: Prime信号（高质量）
- Q* > 60: Watch信号（中质量）
- Q* < 60: 过滤掉（低质量）

---

## 🔄 自适应权重系统

### 根据市场体制动态调整权重

```python
def get_adaptive_weights(regime_score, volatility_regime):
    base_weights = {
        "T": 25, "M": 20, "C+": 25, "V+": 20, "L": 15,
        "O+": 20, "Q": 10, "B": 10, "S": 20, "P": 15,
        "I": 10, "R": 10
    }

    # 趋势市：强化T/M/C+
    if regime_score > 60:
        return {
            "T": 30, "M": 25, "C+": 30, "V+": 20, "L": 10,
            "O+": 25, "Q": 10, "B": 10, "S": 15, "P": 10,
            "I": 10, "R": 5
        }

    # 震荡市：强化S/P/L
    elif regime_score < -40:
        return {
            "T": 15, "M": 10, "C+": 15, "V+": 15, "L": 25,
            "O+": 15, "Q": 15, "B": 15, "S": 30, "P": 25,
            "I": 10, "R": 10
        }

    # 高波动：强化Q/R/L
    elif volatility_regime == "HIGH_VOL":
        return {
            "T": 20, "M": 15, "C+": 20, "V+": 15, "L": 25,
            "O+": 20, "Q": 20, "B": 15, "S": 15, "P": 10,
            "I": 10, "R": 15
        }

    # 默认权重
    return base_weights
```

---

## 📉 最终评分计算

```python
def calculate_final_score(scores, weights, F_score, Q_star):
    # 1. 加权求和
    weighted_sum = sum([scores[f] * weights[f] for f in scores.keys()])

    # 2. 归一化到±100（200点系统）
    normalized_score = weighted_sum / 2.0

    # 3. F调节器调整温度
    temperature = 35.0 * (1.0 - F_score / 100.0 * 0.3)  # 30%调节幅度

    # 4. Sigmoid概率映射
    probability = 1 / (1 + exp(-normalized_score / temperature))

    # 5. 质量调整
    if Q_star < 60:
        probability *= 0.85  # 低质量打折
    elif Q_star > 80:
        probability *= 1.1   # 高质量加强

    probability = clip(probability, 0, 1)

    return {
        "weighted_score": normalized_score,
        "probability": probability,
        "confidence": abs(normalized_score),
        "quality": Q_star,
        "direction": "LONG" if normalized_score > 10 else ("SHORT" if normalized_score < -10 else "NEUTRAL")
    }
```

---

## 🎨 信号分级系统

```python
def classify_signal(result):
    score = result["weighted_score"]
    prob = result["probability"]
    quality = result["quality"]

    # Prime信号（高质量+强信号）
    if quality >= 80 and abs(score) >= 75 and (prob >= 0.68 or prob <= 0.32):
        return "PRIME"

    # Watch信号（中质量+中强信号）
    elif quality >= 65 and abs(score) >= 60 and (prob >= 0.60 or prob <= 0.40):
        return "WATCH"

    # Trash（低质量或弱信号）
    else:
        return "TRASH"
```

---

## 📊 性能预期

| 指标 | V1生产 | V2 Lite | **V2完整版** |
|------|--------|---------|-------------|
| **因子数量** | 7+1维 | 8+1维 | **12+1维** |
| **数据源** | K线+OI | K线+OI | K线+OI+订单簿+清算 |
| **准确率** | 62% | 68-72% | **75-80%** |
| **假信号率** | 25% | 15-18% | **8-12%** |
| **夏普率** | 1.2 | 1.5-1.8 | **2.0-2.5** |
| **最大回撤** | -18% | -12-15% | **-8-10%** |
| **信息比率** | 0.8 | 1.2-1.5 | **1.8-2.2** |
| **Alpha** | 低 | 中高 | **高** |

---

## 🛠️ 实施路线图

### Phase 1: 数据源集成（4-6周）

**Week 1-2: 订单簿数据**
```python
# WebSocket订阅
ws://fstream.binance.com/ws/<symbol>@depth20@100ms

# 缓存管理
class OrderbookCache:
    def __init__(self, max_symbols=200):
        self.cache = {}  # {symbol: deque(orderbooks)}
        self.ws_connections = {}

    def subscribe(self, symbol):
        # 订阅实时订单簿
        pass

    def get_latest(self, symbol):
        # 返回最新订单簿
        pass
```

**Week 3-4: 清算数据**
```python
# Binance API
GET /fapi/v1/forceOrders

# 或第三方数据源
# Coinglass API: https://open-api.coinglass.com/
# 每5分钟拉取一次，缓存24小时
```

**Week 5-6: 资金费率稳定化**
```python
# 实时订阅 + 历史缓存
ws://fstream.binance.com/ws/!markPrice@arr@1s

# 缓存7天历史
class FundingRateCache:
    def __init__(self):
        self.cache = {}  # {symbol: [(timestamp, rate), ...]}

    def get_current(self, symbol):
        pass

    def get_history(self, symbol, hours=24):
        pass
```

---

### Phase 2: 因子实现（4-6周）

**Week 1: Layer 1-2（价格发现+订单流）**
- 实现T多周期趋势
- 实现M动量加速度
- 实现C+增强CVD
- 实现V+成交量分布
- 实现L流动性深度

**Week 2-3: Layer 3（持仓分析）**
- 实现O+ OI四象限
- 实现Q清算热力图
- 实现B基差+资金费

**Week 4: Layer 4（结构质量）**
- 实现S支撑阻力质量
- 实现P形态识别

**Week 5: Layer 5（市场环境）**
- 实现I独立性Beta
- 实现R市场体制识别

**Week 6: 调节器+质量评估**
- 实现F资金领先性
- 实现Q*信号质量评分

---

### Phase 3: 自适应系统（2-3周）

**Week 1: 权重自适应**
```python
class AdaptiveWeightManager:
    def __init__(self):
        self.regime_detector = RegimeDetector()
        self.weight_profiles = load_weight_profiles()

    def get_weights(self, market_state):
        regime = self.regime_detector.detect(market_state)
        return self.weight_profiles[regime]
```

**Week 2: 因子IC监控**
```python
class FactorICMonitor:
    def __init__(self):
        self.ic_history = {}  # {factor: [(date, ic), ...]}

    def update(self, factor_name, predictions, actuals):
        ic = calculate_information_coefficient(predictions, actuals)
        self.ic_history[factor_name].append((datetime.now(), ic))

    def get_factor_quality(self, factor_name, window=30):
        # 计算滑动窗口IC
        pass
```

**Week 3: 在线学习**
```python
# 每日更新因子权重
class OnlineLearner:
    def __init__(self):
        self.optimizer = BayesianOptimizer()

    def daily_update(self):
        # 基于昨日表现微调权重
        performance = fetch_yesterday_performance()
        new_weights = self.optimizer.optimize(performance)
        update_config(new_weights)
```

---

### Phase 4: 回测验证（3-4周）

**Week 1: 历史回测**
```bash
# 3个月历史数据
python tools/backtest_v2_complete.py --start 2025-07-01 --end 2025-10-01

# 对比V1/V2 Lite/V2完整版
python tools/compare_versions.py
```

**Week 2: 样本外测试**
```python
# 训练期：2025-01-01 ~ 2025-07-01
# 测试期：2025-07-01 ~ 2025-10-01

out_of_sample_results = backtest(
    train_start="2025-01-01",
    train_end="2025-07-01",
    test_start="2025-07-01",
    test_end="2025-10-01"
)
```

**Week 3-4: A/B测试**
```python
# 实盘小仓位测试（10%资金）
# V1: 50% | V2 Complete: 50%
ab_test_results = run_ab_test(
    duration_days=30,
    allocation={"v1": 0.5, "v2_complete": 0.5}
)
```

---

### Phase 5: 生产部署（2-3周）

**Week 1: 灰度发布**
- 10%币种使用V2完整版
- 90%币种使用V1/V2 Lite

**Week 2: 扩大范围**
- 50%币种使用V2完整版

**Week 3: 全量上线**
- 100%币种使用V2完整版
- V1/V2 Lite作为备份

---

## 📚 总结

### V2完整版核心优势

1. **更全面的因子覆盖**
   - 12维因子覆盖价格发现、订单流、持仓、结构、环境5个层面
   - 每个因子都有明确的理论基础和实证支持

2. **更强的自适应能力**
   - 市场体制识别（R因子）
   - 动态权重调整
   - 因子IC在线监控

3. **更高的信号质量**
   - 信号质量评估（Q*）
   - 多层过滤机制
   - 预期准确率75-80%

4. **更完善的风险管理**
   - 清算热力图（Q因子）
   - 流动性深度（L因子）
   - 基差情绪（B因子）

5. **更好的可解释性**
   - 每个信号可追溯到具体因子
   - 质量评分透明
   - 体制识别明确

### 与V1/V2 Lite对比

```
V1 (7+1维)
  ├─ 优点：稳定、简单、数据需求低
  └─ 缺点：准确率62%，缺乏微观结构

V2 Lite (8+1维)
  ├─ 优点：准确率68-72%，无需额外数据源
  └─ 缺点：缺乏流动性/清算/基差因子

V2完整版 (12+1维) ✨
  ├─ 优点：准确率75-80%，全方位覆盖，自适应
  └─ 缺点：需要订单簿+清算数据，复杂度高
```

### 实施建议

1. **数据源优先级**
   - P0: 订单簿（L因子）- 最重要
   - P1: 清算数据（Q因子）
   - P2: 资金费率（B因子）

2. **渐进式实施**
   - 先实现V2 Lite（8维）
   - 数据源就绪后逐步开启L/B/Q
   - 最后添加P/R因子

3. **持续优化**
   - 每周监控因子IC
   - 每月微调权重
   - 每季度回测验证

---

**总预计时间**：15-20周（4-5个月）
**预期收益**：准确率+13-18%，夏普率+0.8-1.3

---

**维护者**: CryptoSignal Team
**文档版本**: 3.0.0-design
**更新时间**: 2025-10-27
