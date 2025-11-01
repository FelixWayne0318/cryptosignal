# SPEC_DIGEST.md
**规范摘要：newstandards/ v2.0 可执行口径**

> **Source**: newstandards/ (7 files: STANDARDS.md, MODULATORS.md, PUBLISHING.md, DATA_LAYER.md, NEWCOIN_SPEC.md, SCHEMAS.md, PROJECT_INDEX.md)
> **Generated**: 2025-11-01
> **Purpose**: Executable specification for compliance audit & shadow run implementation
> **Status**: Complete extraction of all formulas, parameters, thresholds, and data contracts

---

## 0. 总体原则（10条）

1. **多空对称**: 无方向性偏好，long/short 对称设计
2. **层级解耦**: A→B→C→D 单向依赖，F/I 不回传修改方向分
3. **斜率优先**: 趋势/动量优先用斜率，禁用裸价格
4. **稳健统计**: EW-中位数/MAD 抗肥尾
5. **软温莎**: soft_winsor 替代硬截断
6. **统一压缩**: tanh 统一映射到 ±100
7. **发布平滑**: 含滞后的发布滤波器
8. **EV硬闸**: EV > 0 是 Prime 发布的必要条件
9. **四道闸门**: DataQual ≥ 0.90, impact ≤ 7bps, spread ≤ 35bps, |OBI| ≤ 0.30
10. **防抖动**: 滞回 + K/N持久 + 冷却期三重防护

---

## 1. A层：方向因子（输出 s_k ∈ [-100,100]）

### 1.1 统一标准化链（所有因子共用）

**步骤1: 输入预平滑**
```
x̃_t = α·x_t + (1-α)·x̃_{t-1}
```
- 标准通道 (1h/4h): α = 0.3
- 新币通道 (1m/5m): α = 0.4

**步骤2: 稳健缩放（抗肥尾）**
```
μ_ew = EWMedian(x̃, span=168)   # 1周窗口
MAD_ew = EW_MAD(x̃, span=168)
z = (x̃ - μ_ew) / (1.4826 · MAD_ew)
```

**步骤3: 软温莎化（抗极端值）**
```python
def soft_winsor(z, z0=2.5, zmax=6, λ=1.5):
    if |z| ≤ z0:
        return z
    elif z0 < |z| < zmax:
        return sign(z) · (z0 + λ·log(1 + |z| - z0))
    else:
        return sign(z) · (z0 + λ·log(1 + zmax - z0))
```
参数: z0=2.5, zmax=6, λ=1.5

**步骤4: tanh压缩到 ±100**
```
s_k = 100 · tanh(z_soft / τ_k)
```
τ_k 因子相关: T=1.8, M=1.8, S=2.0, V=2.2, C=1.6, O=1.6, Q=2.5

**步骤5: 发布平滑（含滞回）**
```python
def publish_filter(s_k, s_prev, α_s=0.4, Δmax=15):
    s_ema = α_s·s_k + (1-α_s)·s_prev
    if |s_ema - s_prev| > Δmax:
        s_ema = s_prev + sign(s_ema - s_prev)·Δmax
    return s_ema
```
参数: α_s = 0.4, Δmax = 15

---

### 1.2 各因子定义

#### T (趋势, weight 标准18 / 新币22)

**T1: ZLEMA多周期斜率**
```
ZLEMA(price, span) = EMA(price + (price - price.shift(lag)), span)
lag = (span - 1) / 2
T1 = 0.4·slope(ZLEMA_20) + 0.3·slope(ZLEMA_50) + 0.3·slope(ZLEMA_100)
```
Intervals: 1h 主力 (标准) / 5m 主力 (新币)

**T2: 距30日高低点位置**
```
d30_high = (price - low30) / (high30 - low30) - 0.5  # [-0.5, +0.5]
d30_low = (high30 - price) / (high30 - low30) - 0.5
T2 = (d30_high - d30_low) / 2
```

**聚合**:
```
T_raw = 0.6·T1 + 0.4·T2
T_score = standardization_chain(T_raw)  # 输出 ±100
```

---

#### M (动量, weight 标准12 / 新币15)

**M1: ROC多周期斜率**
```
ROC(n) = (price / price.shift(n) - 1) · 100
M1 = 0.5·slope(ROC_14) + 0.3·slope(ROC_28) + 0.2·slope(ROC_50)
```

**M2: RSI斜率**
```
RSI = 100 - 100/(1 + RS), RS = EMA(gain)/EMA(loss)
M2 = slope(RSI_14, lookback=5)
```

**M3: MACD斜率**
```
MACD = EMA_12 - EMA_26
signal = EMA(MACD, 9)
M3 = slope(MACD - signal, lookback=5)
```

**聚合**:
```
M_raw = 0.5·M1 + 0.25·M2 + 0.25·M3
M_score = standardization_chain(M_raw)
```

---

#### S (结构, weight 标准10 / 新币15)

**S1: 高低点序列**
```
higher_high = (high > high.shift(1)) & (high.shift(1) > high.shift(2))
lower_low = (low < low.shift(1)) & (low.shift(1) < low.shift(2))
S1 = frac(higher_high) - frac(lower_low)  # 20 bar窗口
```

**S2: 布林带位置**
```
BB_mid = SMA(close, 20)
BB_std = rolling_std(close, 20)
S2 = (close - BB_mid) / (2 · BB_std)  # 归一化到 ±1
```

**聚合**:
```
S_raw = 0.6·S1 + 0.4·S2
S_score = standardization_chain(S_raw)
```

---

#### V (成交量, weight 标准10 / 新币16)

**V1: RVOL (相对成交量)**
```
RVOL = volume / SMA(volume, 20)
V1 = (RVOL - 1) · 100
```

**V2: OBV斜率**
```
OBV_t = OBV_{t-1} + sign(close - close.shift(1)) · volume
V2 = slope(OBV, lookback=10) / ATR
```

**聚合**:
```
V_raw = 0.5·V1 + 0.5·V2
V_score = standardization_chain(V_raw)
```

---

#### C (CVD, weight 标准18 / 新币20)

**C1: CVD斜率 (多周期)**
```
CVD_t = CVD_{t-1} + (buy_volume - sell_volume)
C1 = 0.5·slope(CVD_1m, 10) + 0.3·slope(CVD_5m, 6) + 0.2·slope(CVD_15m, 4)
归一化: C1 / ATR
```

**C2: 买卖压比例**
```
aggBuy_ratio = Σ(buy_volume) / Σ(total_volume)  # 20 bar窗口
C2 = (aggBuy_ratio - 0.5) · 200  # 映射到 ±100
```

**聚合**:
```
C_raw = 0.7·C1 + 0.3·C2
C_score = standardization_chain(C_raw)
```

---

#### O (持仓量, weight 标准18 / 新币8)

**O1: ΔOI 归一化**
```
ΔOI = (OI - OI.shift(1)) / OI.shift(1) · 100
O1 = ΔOI / rolling_std(ΔOI, 20)
```

**O2: OI与价格背离**
```
corr_OI_price = rolling_corr(OI, close, window=20)
O2 = -corr_OI_price  # 背离为正信号
```

**聚合**:
```
O_raw = 0.7·O1 + 0.3·O2
O_score = standardization_chain(O_raw)
```

**新币降权**: 新币通道 weight=8 (vs 标准18)

---

#### Q (强平, weight 标准4 / 新币4)

```
Q_long = Σ(liquidation_qty where side=SELL) / total_liq  # 多头被强平
Q_short = Σ(liquidation_qty where side=BUY) / total_liq
Q_raw = (Q_long - Q_short) · 100
Q_score = standardization_chain(Q_raw)
```
窗口: 1h (标准) / 15m (新币)

---

### 1.3 因子聚合

**线性聚合**:
```
S_lin = Σ w_k · s_k
```

**权重基线** (标准通道):
```
T: 18, M: 12, S: 10, V: 10, C: 18, O: 18, Q: 4
总和: 90
```

**权重新币**:
```
T: 22, M: 15, S: 15, V: 16, C: 20, O: 8, Q: 4
总和: 100
```

**最终压缩**:
```
S_score = 100 · tanh(S_lin / T_agg)
T_agg = 50 (标准), 60 (新币)
输出: S_score ∈ [-100, 100]
```

---

## 2. B层：调节器F/I（影响Teff/cost/thresholds，不修改方向分）

### 2.1 归一化函数

```
g(x) = tanh(γ · (x - 0.5))
γ = 3
输入: x ∈ [0, 1]
输出: g(x) ∈ [-0.46, +0.46]
```

---

### 2.2 F (拥挤度调节器)

**原始计算** (输入 ∈ [0,1]):
```
F_funding = clip(|funding_rate| / 0.0005, 0, 1)
F_basis = clip(|basis_bps| / 30, 0, 1)
F_oi = clip(ΔOI_normalized, 0, 1)

F_raw = 0.5·F_funding + 0.3·F_basis + 0.2·F_oi
```

**归一化**:
```
gF = g(F_raw) = tanh(3 · (F_raw - 0.5))
```

**应用通道**:
1. **温度调节**: Teff = T0·(1+βF·gF) / (1+βI·gI)
2. **成本惩罚**: cost_eff += pen_F, pen_F = λF·max(0, gF)
3. **阈值提升**: p*_min += θF·max(0, gF)

**参数**:
- βF = 0.35 (标准), 0.20 (新币)
- λF = 0.0002 (成本惩罚系数)
- θF = 0.03 (阈值提升系数)

---

### 2.3 I (独立性调节器)

**原始计算**:
```
corr_BTC = rolling_corr(returns, BTC_returns, window=24)
corr_ETH = rolling_corr(returns, ETH_returns, window=24)
I_raw = max(|corr_BTC|, |corr_ETH|)  # ∈ [0, 1], 1表示高度相关
```

**归一化**:
```
gI = g(I_raw) = tanh(3 · (I_raw - 0.5))
```

**应用通道**:
1. **温度调节**: Teff 分母增大 → 概率收缩
2. **成本惩罚**: cost_eff += pen_I, pen_I = λI·max(0, gI)
3. **成本奖励**: cost_eff -= rew_I, rew_I = λI_rew·max(0, -gI)  # 独立时奖励
4. **阈值提升**: Δp_min += φI·max(0, gI)

**参数**:
- βI = 0.25 (标准), 0.15 (新币)
- λI = 0.0001, λI_rew = 0.00005
- φI = 0.01

---

### 2.4 有效温度 Teff

```python
Teff = clip(
    T0 · (1 + βF·gF) / (1 + βI·gI),
    Tmin,
    Tmax
)
```

**参数** (标准通道):
- T0 = 50
- Tmin = 35
- Tmax = 80
- βF = 0.35
- βI = 0.25

**参数** (新币通道):
- T0 = 60
- Tmin = 40
- Tmax = 95
- βF = 0.20
- βI = 0.15

**在线断言**:
- 高拥挤/高相关 → Teff ↑ → 概率 ↓
- 低拥挤/高独立 → Teff ↓ → 概率 ↑

---

### 2.5 有效成本 cost_eff

```
cost_eff = fee + impact_bps/1e4 + pen_F + pen_I - rew_I

pen_F = λF · max(0, gF)
pen_I = λI · max(0, gI)
rew_I = λI_rew · max(0, -gI)
```

**固定成本**:
- fee = 0.0004 (Maker) 或 0.0006 (Taker)
- impact_bps: 从 C层计算 (详见3.2)

---

### 2.6 发布阈值调整

**最小概率阈值**:
```
p*_min = p0 + θF·max(0, gF) + θI·max(0, gI)
```
- p0 = 0.55 (标准), 0.58 (新币)
- θF = 0.03
- θI = 0.02

**最小概率增量** (相对上一发布):
```
Δp_min = Δp0 + φF·max(0, gF) + φI·max(0, gI)
```
- Δp0 = 0.02 (标准), 0.03 (新币)
- φF = 0.01
- φI = 0.01

---

## 3. C层：执行/流动性（硬闸门）

### 3.1 流动性指标

**价差 (basis points)**:
```
spread_bps = (ask1 - bid1) / mid · 1e4
mid = (ask1 + bid1) / 2
```

**冲击成本** (Q为目标仓位USDT价值):
```python
def impact_bps(Q, shelves):
    """
    shelves: [(price_i, cumQty_i), ...] 从最优价开始
    """
    remaining = Q
    avg_price = 0
    for price, cumQty in shelves:
        if remaining <= 0:
            break
        fill = min(remaining, cumQty)
        avg_price += price * fill
        remaining -= fill

    if remaining > 0:  # 流动性不足
        return 999  # 标记为不可交易

    avg_price /= Q
    impact = |avg_price - mid| / mid · 1e4
    return impact
```

**OBI (Orderbook Imbalance)**:
```
OBI10 = (Σ bid_qty_top10 - Σ ask_qty_top10) / (Σ bid_qty_top10 + Σ ask_qty_top10)
输出: ∈ [-1, +1]
```

---

### 3.2 四道硬闸（必须全部通过才能发Prime）

```python
# Gate 1: 冲击成本
impact_bps(Q) <= 7  # 标准
impact_bps(Q) <= 7 or 8  # 新币 (根据阶段)

# Gate 2: 价差
spread_bps <= 35  # 标准
spread_bps <= 35 or 38  # 新币

# Gate 3: 盘口失衡
|OBI10| <= 0.30

# Gate 4: 数据质量 (关键!)
DataQual >= 0.90
```

**逻辑**:
```python
if not (gate1 and gate2 and gate3 and gate4):
    return Signal(level="WATCH", reason="failed_gate_X")
```

**新币特殊规则**:
- 0-3分钟: 强制 WATCH (冷启动)
- 3-8分钟: 可发Prime，但gates更严格
- 8-15分钟: 主窗口，gates稍宽松

---

### 3.3 止损/止盈 (SL/TP)

**ATR计算**:
```
ATR = EMA(TrueRange, span=14)
TrueRange = max(high-low, |high-close_prev|, |low-close_prev|)
```

**SL/TP设置**:
```
SL0 = entry ± 1.2·ATR  # ± 取决于方向
TP1 = entry ± 1.8·ATR  # 首目标 (50%仓位)
TP2 = entry ± 3.0·ATR  # 次目标 (剩余50%)

concurrency设置:
- 标准通道: 允许1-2个同向信号
- 新币通道: 严格1个
```

---

## 4. D层：发布层（概率→EV→离散发布）

### 4.1 概率计算

**Logistic变换**:
```
P_long = σ(S_score / Teff) = 1 / (1 + exp(-S_score / Teff))
P_short = σ(-S_score / Teff) = 1 / (1 + exp(S_score / Teff))
```

**短样本收缩** (新币特有):
```
P̃ = 0.5 + w_eff · (P - 0.5)
w_eff = min(1, bars_1h / 400)
```
bars_1h < 400 时，概率向0.5收缩

---

### 4.2 期望值计算 (EV)

```
μ_win = TP1 / entry - 1  # 盈利率
μ_loss = |SL0 / entry - 1|  # 亏损率

EV_long = P_long · μ_win - (1 - P_long) · μ_loss - cost_eff
EV_short = P_short · μ_win - (1 - P_short) · μ_loss - cost_eff
```

**硬闸**:
```
if EV <= 0:
    return Signal(level="WATCH", reason="EV_negative")
```

---

### 4.3 发布规则（三重防抖动）

#### 4.3.1 滞回 (Hysteresis)

**入场阈值**:
```
p_entry = p*_min  # 从B层调整后
```

**维持阈值** (低于入场):
```
p_maintain = p_entry - Δhys
Δhys = 0.01~0.02
```

**状态机**:
```python
if state == "NONE":
    if p >= p_entry:
        state = "PRIME"
elif state == "PRIME":
    if p < p_maintain:
        state = "NONE"
```

---

#### 4.3.2 K/N持久性

```
需要连续K/N个bar满足条件才发布
K = 2, N = 3  # 即3个bar中至少2个满足
```

**实现**:
```python
buffer = deque(maxlen=N)
buffer.append(condition_met)
if sum(buffer) >= K:
    publish()
```

---

#### 4.3.3 冷却期

```
降级后必须等待τ_cool秒才能重新评估
τ_cool = 60~120s
```

**实现**:
```python
if downgrade_event:
    cooldown_until = now + τ_cool
if now < cooldown_until:
    return "WATCH"  # 冷却中
```

---

### 4.4 强度展示

```
prime_strength = 0.6·|S_score| + 40·clip((p* - 0.60)/0.15, 0, 1)
输出: ∈ [0, 100]
```
用于前端展示信号强度

---

### 4.5 TTL (信号有效期)

```
TTL_standard = 8h
TTL_newcoin = 2~4h  # 根据阶段

过期后信号自动失效，需重新计算
```

---

## 5. 数据层（WS拓扑 + DataQual）

### 5.1 SLO目标

**可用性**: ≥ 99.5% (月度)
**延迟** (p95):
- 新币: ≤ 250ms
- 标准: ≤ 500ms

---

### 5.2 Binance数据源映射

#### REST端点:
```
https://fapi.binance.com/fapi/v1/klines?symbol={}&interval={}&limit={}
https://fapi.binance.com/fapi/v1/depth?symbol={}&limit={}
https://fapi.binance.com/fapi/v1/openInterest?symbol={}
https://fapi.binance.com/fapi/v1/fundingRate?symbol={}
https://fapi.binance.com/fapi/v1/allForceOrders?symbol={}
```

#### WS流:
```
wss://fstream.binance.com/stream?streams=
  {symbol}@kline_{interval}
  /{symbol}@aggTrade
  /{symbol}@depth@100ms
  /{symbol}@markPrice@1s
```

---

### 5.3 WS拓扑（硬约束：3-5条流）

**固定连接** (2-3条):
```
1. kline: {symbol}@kline_1m + kline_5m + ...  # 多周期合并
2. aggTrade: {symbol}@aggTrade  # 逐笔成交
3. markPrice (可选): {symbol}@markPrice@1s  # 标记价格+资金费率
```

**按需连接** (1-2条):
```
4. depth: {symbol}@depth@100ms  # 仅Watch/Prime时订阅
5. (备用): 其他流，总数不超过5
```

**重连策略**:
```python
backoff = min(100ms * 2^retry, 5s)
jitter = backoff * (1 ± 0.15)  # ±15%抖动
```

---

### 5.4 订单簿对账

**快照获取**:
```
GET /fapi/v1/depth?symbol={}&limit=1000
返回: {lastUpdateId, bids[], asks[]}
```

**增量更新**:
```
WS depth event: {U, u, b[], a[]}
U = first_update_id
u = final_update_id
```

**对账逻辑**:
```python
if u <= lastUpdateId:
    discard  # 旧数据
elif U <= lastUpdateId + 1 <= u:
    apply_update(b, a)
    lastUpdateId = u
else:
    fetch_new_snapshot()  # 断层
```

**reconcile_success_rate** 应 ≥ 99%

---

### 5.5 DataQual计算

```
DataQual = 1 - (0.35·miss + 0.15·ooOrder + 0.20·drift + 0.30·mismatch)
```

**四个分量**:

1. **miss** (缺失率):
```
miss = (expected_events - received_events) / expected_events
例: 1分钟应收60个aggTrade，实收55个 → miss=5/60=0.083
```

2. **ooOrder** (乱序率):
```
ooOrder = count(ts_exch[i] < ts_exch[i-1]) / total_events
```

3. **drift** (时钟漂移):
```
drift = |ts_srv - ts_exch - offset| / threshold
threshold = 500ms (标准), 250ms (新币)
offset = 已知的平均网络延迟
```

4. **mismatch** (快照不一致):
```
mismatch = reconcile_fail_count / reconcile_total
```

**硬闸**:
```python
if DataQual < 0.90:
    return "WATCH"  # 不允许Prime
if DataQual < 0.88:
    immediate_downgrade()  # 立即降级
    cooldown = 60~120s
```

**记录频率**: 每分钟计算一次，写入 `qos_state_1m` 表

---

### 5.6 时间戳规范

- **ts_exch**: 交易所时间戳 (ms), 用于排序和逻辑
- **ts_srv**: 服务器接收时间戳 (ms), 用于诊断
- **优先级**: ts_exch > ts_srv

---

### 5.7 衍生量计算

**AVWAP** (逐笔成交加权均价):
```
AVWAP = Σ(price · qty) / Σ(qty)  # 窗口内
```

**CVD** (累积成交量差):
```
CVD_t = CVD_{t-1} + (buy_qty - sell_qty)
买卖判断: is_buyer_maker == False → 买单
```

**RVOL** (相对成交量):
```
RVOL = volume_current / SMA(volume, 20)
```

**OBI** (盘口失衡):
```
OBI10 = (bid_qty_sum - ask_qty_sum) / (bid_qty_sum + ask_qty_sum)
范围: [-1, +1]
```

**impact, shelves, resilience**: 详见3.1节

---

### 5.8 缓存分层

**Hot** (内存):
- 保留: 48-72小时
- 数据: 原始kline, aggTrade, depth, features

**Warm** (Parquet):
- 保留: 90天
- 格式: 列式存储，分区 by dt/symbol

**Cold** (S3/OSS):
- 保留: 长期归档
- 压缩: gzip/snappy

---

### 5.9 订阅分级

**Cold** (仅1h K线):
- 适用: 长期不活跃币种
- 连接: 1条WS (kline_1h)

**Warm** (Watch级别):
- 适用: 有兴趣但未达Prime
- 连接: 2-3条 (kline + aggTrade + markPrice)

**Hot** (Prime级别):
- 适用: 已发布Prime信号
- 连接: 4-5条 (Warm + depth@100ms)

**动态切换**:
```python
if signal_level == "PRIME":
    subscribe("depth@100ms")
elif signal_level == "WATCH":
    unsubscribe("depth@100ms")
```

---

## 6. 新币通道专项

### 6.1 入场/退出条件

**入场** (任一满足):
```
since_listing < 14d
OR bars_1h < 400
OR !has_OI OR !has_funding  # OI/资金费率数据不足3天
```

**退出** (全部满足):
```
bars_1h >= 400
AND (has_OI AND has_funding >= 3d)
AND since_listing >= 14d
```

**过渡期**:
```
48小时线性混合: w = (hours_in_transition) / 48
final_score = (1-w)·newcoin_score + w·standard_score
```

---

### 6.2 因子权重差异

```
标准通道: T:18, M:12, S:10, V:10, C:18, O:18, Q:4
新币通道: T:22, M:15, S:15, V:16, C:20, O: 8, Q:4

差异:
- T/M/S/V/C 提升 (快速动量优先)
- O 降低 (OI数据不稳定)
```

---

### 6.3 点燃条件 (Ignition, ≥3/6)

```python
conditions = [
    (P - AVWAP) / ATR >= 0.8,         # 价格偏离锚点
    speed >= 0.25 * ATR / min,        # 速度阈值
    agg_buy_ratio >= 0.62,            # 主动买入占比
    OBI10 >= 0.05,                    # 盘口倾斜
    RVOL >= 3.0,                      # 放量
    slope_CVD > 0,                    # CVD斜率为正
]
ignition = sum(conditions) >= 3
```

---

### 6.4 动量确认

```
1m/5m 斜率同向 (同正或同负)
AND 15m 斜率 ≥ 0  # 不能逆向
```

---

### 6.5 衰竭信号 (Exhaustion)

**任一触发**:
```
1. 失去锚点 + CVD翻转: |P - AVWAP| > 1.5·ATR AND CVD slope反向
2. 速度归零: speed < 0 持续 2-3 bar
3. OBI反转: OBI10 从正转负 (多头) 或 从负转正 (空头)
4. 强平放量: qvol / ATR > 0.6
```

---

### 6.6 温度参数

```
T0 = 60      (vs 标准 50)
Tmin = 40    (vs 标准 35)
Tmax = 95    (vs 标准 80)
βF = 0.20    (vs 标准 0.35)
βI = 0.15    (vs 标准 0.25)
```
→ 新币更激进，但调节器权重降低

---

### 6.7 闸门严格化

```
标准: impact≤7bps, spread≤35bps
新币 (阶段相关):
  - 0-3分钟: 强制WATCH (冷启动)
  - 3-8分钟: impact≤7bps, spread≤35bps (严格)
  - 8-15分钟: impact≤8bps, spread≤38bps (稍宽松)
```

---

### 6.8 Prime窗口

```
0-3分钟: WATCH only (冷启动)
3-8分钟: 可发Prime，但条件严格
8-15分钟: 主窗口，条件稍宽松
>15分钟: 衰竭期，谨慎发布
```

---

### 6.9 TTL缩短

```
标准通道: TTL = 8h
新币通道: TTL = 2~4h  # 根据波动率动态调整
```

---

### 6.10 并发限制

```
标准通道: concurrency = 1~2
新币通道: concurrency = 1  # 严格单信号
```

---

## 7. 字段映射表（SCHEMAS对照）

### 7.1 A层因子 → SCHEMAS

| 因子 | 字段名 | 表名 | 类型 | 单位 | 范围 |
|------|--------|------|------|------|------|
| T | T_score | features_a_1h | float32 | dimensionless | ±100 |
| M | M_score | features_a_1h | float32 | dimensionless | ±100 |
| S | S_score | features_a_1h | float32 | dimensionless | ±100 |
| V | V_score | features_a_1h | float32 | dimensionless | ±100 |
| C | C_score | features_a_1h | float32 | dimensionless | ±100 |
| O | O_score | features_a_1h | float32 | dimensionless | ±100 |
| Q | Q_score | features_a_1h | float32 | dimensionless | ±100 |
| S_lin | S_lin | features_a_1h | float32 | dimensionless | - |
| S_final | S_score | features_a_1h | float32 | dimensionless | ±100 |

---

### 7.2 B层调节器 → SCHEMAS

| 模块 | 字段名 | 表名 | 类型 | 单位 | 范围 |
|------|--------|------|------|------|------|
| F_raw | F_raw | features_b_modulators | float32 | dimensionless | [0,1] |
| I_raw | I_raw | features_b_modulators | float32 | dimensionless | [0,1] |
| gF | gF | features_b_modulators | float32 | dimensionless | [-0.46,+0.46] |
| gI | gI | features_b_modulators | float32 | dimensionless | [-0.46,+0.46] |
| Teff | Teff | features_b_modulators | float32 | dimensionless | [Tmin, Tmax] |
| cost_eff | cost_eff | features_b_modulators | float32 | fraction | [0, 0.01+] |
| pmin | pmin | features_b_modulators | float32 | probability | [0.5, 1.0] |
| dpmin | dpmin | features_b_modulators | float32 | probability | [0, 0.1] |

---

### 7.3 C层执行 → SCHEMAS

| 指标 | 字段名 | 表名 | 类型 | 单位 | 范围 |
|------|--------|------|------|------|------|
| spread | spread_bps | features_c_exec_1m | float32 | bps | [0, 500+] |
| OBI | obi10 | features_c_exec_1m | float32 | dimensionless | [-1, +1] |
| impact | impact_bps_q | features_c_exec_1m | float32 | bps | [0, 999] |
| shelves | shelves_cnt | features_c_exec_1m | int16 | count | [0, 100] |
| resilience | resilience_s | features_c_exec_1m | float32 | seconds | [0, 300+] |
| room | room_atr | features_c_exec_1m | float32 | ATR | [0, 10+] |

---

### 7.4 D层概率/EV → SCHEMAS

| 字段 | 字段名 | 表名 | 类型 | 单位 | 范围 |
|------|--------|------|------|------|------|
| S_score | S_score | decision_d_prob_ev | float32 | dimensionless | ±100 |
| P_long | P_long | decision_d_prob_ev | float32 | probability | [0, 1] |
| P_short | P_short | decision_d_prob_ev | float32 | probability | [0, 1] |
| EV_long | EV_long | decision_d_prob_ev | float32 | fraction | [-0.1, 0.5] |
| EV_short | EV_short | decision_d_prob_ev | float32 | fraction | [-0.1, 0.5] |

---

### 7.5 发布事件 → SCHEMAS

| 字段 | 字段名 | 表名 | 类型 | 单位 | 说明 |
|------|--------|------|------|------|------|
| side | side | publish_events | string | - | "LONG"/"SHORT" |
| prime | prime | publish_events | bool | - | True=Prime, False=Watch |
| strength | prime_strength | publish_events | float32 | [0,100] | 信号强度 |
| entry_lo | entry_lo | publish_events | float64 | USDT | 入场价下限 |
| entry_hi | entry_hi | publish_events | float64 | USDT | 入场价上限 |
| sl0 | sl0 | publish_events | float64 | USDT | 止损价 |
| tp1 | tp1 | publish_events | float64 | USDT | 首目标 |
| tp2 | tp2 | publish_events | float64 | USDT | 次目标 |
| ttl_h | ttl_h | publish_events | float32 | hours | 信号有效期 |

---

### 7.6 数据质量 → SCHEMAS

| 字段 | 字段名 | 表名 | 类型 | 单位 | 范围 |
|------|--------|------|------|------|------|
| miss | miss | qos_state_1m | float32 | fraction | [0, 1] |
| oo_order | oo_order | qos_state_1m | float32 | fraction | [0, 1] |
| drift | drift | qos_state_1m | float32 | fraction | [0, 1] |
| mismatch | mismatch | qos_state_1m | float32 | fraction | [0, 1] |
| dataqual | dataqual | qos_state_1m | float32 | dimensionless | [0, 1] |

---

### 7.7 新币状态 → SCHEMAS

| 字段 | 字段名 | 表名 | 类型 | 单位 | 说明 |
|------|--------|------|------|------|------|
| onboard_ts | onboard_ts | newcoin_state | int64 | ms | 首次发现时间 |
| bars_1h | bars_1h | newcoin_state | int32 | count | 累积1h K线数 |
| in_newcoin | in_newcoin | newcoin_state | bool | - | 是否在新币通道 |
| stage | stage | newcoin_state | string | - | "ignition"/"momentum"/"exhaustion" |

---

### 7.8 原始数据表 (Binance WS/REST)

**klines_{interval}**:
```
PK: (symbol, open_time)
字段: open, high, low, close (float64, USDT)
      volume_base, volume_quote (float64)
      taker_buy_base, taker_buy_quote (float64)
      is_final (bool)
      ts_exch, ts_srv (int64, ms)
```

**aggtrade_1s** (聚合每秒):
```
PK: (symbol, bucket_ts)
字段: price_vwap (float64, USDT)
      qty_sum (float64, base)
      buy_qty, sell_qty (float64, base)
      trade_count (int32)
      ts_srv (int64, ms)
```

**depth_events**:
```
PK: (symbol, ts_exch, seq)
字段: U, u (int64, update_id)
      bids_json, asks_json (text, JSON array)
      ts_srv (int64, ms)
```

**mark_funding**:
```
PK: (symbol, ts_exch)
字段: mark_price, index_price (float64, USDT)
      funding_rate (float64, 8小时费率)
      basis_bps (float32, bps)
      ts_srv (int64, ms)
```

**oi_1m**:
```
PK: (symbol, ts_exch)
字段: open_interest (float64, base quantity)
      oi_value (float64, USDT)
      ts_srv (int64, ms)
```

**force_order**:
```
PK: (symbol, ts_exch, order_id)
字段: side ("BUY"/"SELL")
      qty (float64, base)
      price (float64, USDT)
      ts_srv (int64, ms)
```

---

## 8. Binance数据源映射

### 8.1 REST API

| 数据 | 端点 | 频率 | 用途 |
|------|------|------|------|
| Kline | /fapi/v1/klines | 按需 | 历史K线回填 |
| Depth | /fapi/v1/depth | 按需 | 订单簿快照 (对账) |
| OI | /fapi/v1/openInterest | 1分钟 | 持仓量快照 |
| Funding | /fapi/v1/fundingRate | 按需 | 资金费率历史 |
| Force Orders | /fapi/v1/allForceOrders | 1分钟 | 强平事件 |
| Exchange Info | /fapi/v1/exchangeInfo | 1小时 | 币种元数据 |

---

### 8.2 WebSocket Streams

| Stream | 格式 | 频率 | 数据 |
|--------|------|------|------|
| kline | {symbol}@kline_{interval} | 实时 | OHLCV, is_final |
| aggTrade | {symbol}@aggTrade | 实时 | 逐笔成交 (聚合) |
| depth | {symbol}@depth@100ms | 100ms | 增量深度更新 |
| markPrice | {symbol}@markPrice@1s | 1秒 | 标记价格+资金费率 |

**连接示例**:
```
wss://fstream.binance.com/stream?streams=btcusdt@kline_1m/btcusdt@aggTrade/btcusdt@depth@100ms
```

---

## 9. 硬约束（护栏，不可违反）

### 9.1 无实际交易
```
shadow_run模式:
- 仅读取公开行情数据
- 禁止调用任何下单API (/fapi/v1/order, /fapi/v1/batchOrders, etc.)
- 禁止读取私钥/API密钥 (仅用testnet密钥做mock测试)
```

### 9.2 WS连接数限制
```
总连接数 ≤ 5
推荐配置: 3条固定 (kline + aggTrade + markPrice)
         + 1条按需 (depth@100ms, 仅Prime时)
         + 1条备用
```

### 9.3 DataQual闸门
```
if DataQual < 0.90:
    block_prime_publish()  # 仅允许WATCH
if DataQual < 0.88:
    immediate_downgrade()
    cooldown = 60~120s
```

### 9.4 F/I三通道隔离
```
F/I 调节器 ONLY 影响:
  1. Teff (温度)
  2. cost_eff (成本)
  3. p*_min, Δp_min (阈值)

严禁修改:
  - S_score (方向分)
  - 任何A层因子 (T/M/S/V/C/O/Q)

在线断言:
assert S_score_after_modulator == S_score_before_modulator
```

---

## 10. 验收标准

### 10.1 SPEC_DIGEST ↔ SCHEMAS字段对齐

**抽查10处**:
1. `T_score` → features_a_1h.T_score (float32, ±100) ✓
2. `Teff` → features_b_modulators.Teff (float32, [Tmin,Tmax]) ✓
3. `spread_bps` → features_c_exec_1m.spread_bps (float32, bps) ✓
4. `P_long` → decision_d_prob_ev.P_long (float32, [0,1]) ✓
5. `prime` → publish_events.prime (bool) ✓
6. `dataqual` → qos_state_1m.dataqual (float32, [0,1]) ✓
7. `bars_1h` → newcoin_state.bars_1h (int32) ✓
8. `open_interest` → oi_1m.open_interest (float64, base) ✓
9. `funding_rate` → mark_funding.funding_rate (float64) ✓
10. `side` → publish_events.side (string, "LONG"/"SHORT") ✓

### 10.2 四道闸门全覆盖

```python
# 代码中必须显式检查:
assert impact_bps <= threshold_impact
assert spread_bps <= threshold_spread
assert abs(OBI10) <= 0.30
assert DataQual >= 0.90
# 全部通过才允许 prime=True
```

### 10.3 WS连接数监控

```python
active_connections = count_websocket_connections()
assert active_connections <= 5
# 记录到监控日志
```

### 10.4 深度对账成功率

```
reconcile_success_rate = successful_reconciles / total_reconciles
assert reconcile_success_rate >= 0.99  # 99%
```

### 10.5 合规报告完整性

**COMPLIANCE_REPORT.md 必须包含**:
- 每个模块 → 规范条款映射
- 合规状态 (✓ / ⚠ / ✗)
- 不合规项: file:line + 修复建议
- 关键检查: 标准化链、F/I隔离、EV>0闸、四道闸、WS拓扑、对账逻辑、防抖动、新币通道

---

## APPENDIX: 单位约定

| 数据类型 | 类型 | 单位 | 说明 |
|----------|------|------|------|
| 价格 | float64 | USDT | 交易对报价货币 |
| 数量 | float64 | Base | 基础货币 (如BTC) |
| bps | float32 | 万分之一 | 1bps = 0.0001 |
| 时间戳 | int64 | ms | Unix毫秒 |
| 概率 | float32 | [0,1] | 无单位 |
| 分数 | float32 | ±100 | A层因子输出 |
| 费率 | float64 | 小数 | 如0.0004 = 0.04% |
| ATR | float64 | USDT | 与价格同单位 |

---

**END OF SPEC_DIGEST.md**
