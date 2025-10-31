# 合规性盘点报告 (COMPLIANCE_REPORT)

> **生成时间**: 2025-10-31
> **对照基准**: newstandards/ v2.0 (6份规范)
> **扫描范围**: ats_core/ 全模块 + scripts/
> **评级标准**: ✅已满足 | ⚠️部分满足 | ❌缺失

---

## 📊 执行摘要 (Executive Summary)

### 总体合规率

| 模块 | 合规度 | 状态 | 优先级 |
|------|--------|------|--------|
| **A层：方向因子** | 55% | ⚠️部分满足 | P1-高 |
| **B层：调节器F/I** | 20% | ❌重大差距 | P0-最高 |
| **C层：执行/流动性** | 5% | ❌几乎缺失 | P0-最高 |
| **D层：概率/EV/发布** | 40% | ⚠️部分满足 | P1-高 |
| **数据层** | 45% | ⚠️部分满足 | P1-高 |
| **新币通道** | 15% | ❌重大差距 | P1-高 |

### 关键风险

| # | 风险项 | 影响 | 现状 |
|---|--------|------|------|
| 1 | **F/I调节器误用** | 🔴严重 | F/I直接参与评分，违反"只改温度/成本/门槛"原则 |
| 2 | **无EV硬闸** | 🔴严重 | 缺少EV>0判断，可能发布负期望信号 |
| 3 | **无DataQual控制** | 🔴严重 | 无数据质量评分，可能在坏数据下发布Prime |
| 4 | **无执行层闸门** | 🟡中等 | 缺少impact/OBI/厚区/spread控制 |
| 5 | **标准化链不统一** | 🟡中等 | 各因子标准化方法不一致，无EW-Median/MAD |

---

## 1. A层：方向因子（合规度：55%）

### 1.1 统一标准化链

#### ❌ 缺失：EW-Median/MAD 稳健缩放

**规范要求**：
```python
# Step 2: 稳健缩放（抗肥尾）
z = (x̃ - μ) / (1.4826·MAD)
μ, MAD: EW-Median/EW-MAD，更新率η=0.03-0.08
```

**现状**：
- 文件：`ats_core/features/trend.py`
- 方法：直接使用原始值或简单EMA，无Median/MAD处理
- 代码片段（trend.py:38-49）：
  ```python
  def _ema(xs: List[float], period: int) -> List[float]:
      # 仅使用简单EMA，无Median/MAD
      alpha = 2.0 / (n + 1.0)
      ema = xs[0]
      # ...
  ```

**影响**：肥尾分布（极值）未被稳健处理，可能导致因子分数过度波动。

**修复难度**：⭐⭐⭐中（需新增EW-Median/EW-MAD模块）

---

#### ❌ 缺失：软winsor连续化

**规范要求**：
```python
# Step 3: 软winsor（连续无台阶）
z_soft = sign(z)·[z0+(zmax-z0)·(1-exp(-(|z|-z0)/λ))] for |z|>z0
参数：z0=2.5, zmax=6, λ=1.5
```

**现状**：
- 各因子文件均无软winsor处理
- 直接使用硬阈值或线性映射

**影响**：极值处理不平滑，可能产生阶跃变化。

**修复难度**：⭐⭐⭐中（需在标准化链中实现）

---

#### ⚠️ 部分满足：tanh压缩到±100

**规范要求**：
```python
# Step 4: tanh压缩到±100
s_k = 100·tanh(z_soft/τ_k)
τ_T=2.2, τ_M=2.4, τ_S=2.2, τ_V=2.3, τ_C=2.2, τ_O=2.3, τ_Q=2.8
```

**现状**：
- 文件：`ats_core/features/scoring_utils.py`
- 存在`directional_score()`函数（可能使用tanh），但未统一应用
- 部分因子直接返回±100硬边界

**位置**：各因子文件（trend.py, momentum.py等）

**影响**：部分因子可能未正确饱和，输出分布不一致。

**修复难度**：⭐⭐低（需统一调用，参数化τ值）

---

#### ❌ 缺失：发布端平滑 + 限斜率 + 过零滞回

**规范要求**：
```python
# Step 5: 发布端再平滑
s_pub = (1-αs)·s_pub_prev + αs·s_raw
标准：αs=0.30, Δmax=15, 过零滞回=10分
新币：αs=0.50, Δmax=25
```

**现状**：
- 无发布端平滑逻辑
- 无斜率限制
- 无过零滞回

**位置**：缺失（应在`analyze_symbol.py`或`scorecard.py`中）

**影响**：信号可能出现剧烈跳变，缺少防抖机制。

**修复难度**：⭐⭐⭐中（需状态管理，跨周期记录）

---

### 1.2 因子计算逻辑

| 因子 | 规范要求 | 现状 | 合规度 | 文件位置 |
|------|---------|------|--------|---------|
| **T（趋势）** | ZLEMA斜率 + 乖离 | ✅有ZLEMA，⚠️斜率单位未统一到ATR | 70% | `features/trend.py:87-100` |
| **M（动量）** | ROC/RSI/MACD斜率 | ✅有计算，⚠️未标准化到ATR单位 | 65% | `features/momentum.py` |
| **S（结构）** | 速度 + 距关键位 | ⚠️部分实现，缺少关键位距离 | 50% | `features/structure_sq.py` |
| **V（量能）** | RVOL斜率 + 买卖差D | ✅有RVOL，⚠️缺少D斜率 | 60% | `features/volume.py` |
| **C（CVD）** | CVD斜率 + 背离惩罚 | ✅有CVD斜率，⚠️背离惩罚未显式 | 70% | `features/cvd.py` |
| **O（OI）** | OI斜率·sgn(slope_P) | ✅有OI斜率，⚠️未与价格斜率同向性 | 60% | `features/open_interest.py` |
| **Q（清算）** | 清算密度加权 | ⚠️有liquidation，但非密度加权 | 40% | `factors_v2/liquidation.py` |

---

### 1.3 聚合

**规范要求**：
```python
S_lin = Σ w_k·s_k
S = 100·tanh(S_lin/T_agg)
权重基线：T18/M12/S10/V10/C18/O18/Q4（标准）
```

**现状**：
- 文件：`ats_core/scoring/scorecard.py:31-44`
- ✅ 已实现加权平均：`weighted_score = total / weight_sum`
- ⚠️ 但未用tanh压缩，直接clip到[-100,100]：
  ```python
  weighted_score = max(-100.0, min(100.0, weighted_score))  # 硬clip
  ```

**问题**：缺少tanh非线性饱和，边界不平滑。

**修复难度**：⭐低

---

## 2. B层：调节器F/I（合规度：20%）⚠️重大差距

### 2.1 核心问题：F/I参与评分（违反规范）

**规范要求**：
```
F/I 只改三件事：
1) Teff（概率温度）
2) cost_eff（EV成本）
3) 发布门槛（p_min, Δp_min）

❌ 不得直接参与方向分计算
```

**现状**：
- 文件：`ats_core/scoring/adaptive_weights.py`
- 🔴 **F因子权重**=10.0%（参与加权平均）
- 代码片段（adaptive_weights.py:49, 70, 92, 113, 128）：
  ```python
  return {
      "F": 10.0,  # ❌ F直接参与评分！
      # ...
  }
  ```

- 文件：`ats_core/pipeline/analyze_symbol.py:14-16`
- 注释确认：
  ```python
  # F因子双重作用：参与评分（权重10.0%）+ 极端值否决（<-70时×0.7惩罚）⭐
  ```

**影响**：🔴 **严重违反规范**，F因子既调节又评分，导致逻辑混乱。

**修复方案**：
1. 从weights中移除F
2. F/I仅用于计算Teff、cost_eff、发布门槛
3. 重新设计概率计算流程

**修复难度**：⭐⭐⭐⭐高（需重构评分系统）

---

### 2.2 缺失模块

| 模块 | 规范要求 | 现状 | 优先级 |
|------|---------|------|--------|
| **g(x)归一函数** | `g(x)=tanh(γ(x-0.5))` + EMA(α=0.2) | ❌ 缺失 | P0 |
| **Teff温度公式** | `Teff=clip(T0·(1+βF·gF)/(1+βI·gI), Tmin, Tmax)` | ❌ 缺失 | P0 |
| **cost_eff分段成本** | `pen_F + pen_I - rew_I` | ❌ 缺失 | P0 |
| **发布门槛软调** | `p_min = p0 + θF·max(0,gF) + ...` | ❌ 缺失 | P0 |
| **在线断言** | F↑或I↓ → 必须Teff↑、cost↑、门槛↑ | ❌ 缺失 | P1 |

**位置**：应在`ats_core/scoring/`或新建`ats_core/modulators/`

**修复难度**：⭐⭐⭐⭐⭐非常高（全新模块）

---

### 2.3 F/I因子本身

| 因子 | 规范要求 | 现状 | 文件 |
|------|---------|------|------|
| **F拥挤度** | funding+basis+ΔOI → [0,1] | ⚠️ 有F计算，但输出±100而非[0,1] | `features/fund_leading.py` |
| **I独立性** | 与BTC/ETH相关R²→[0,1] | ⚠️ 有I计算，但输出±100而非[0,1] | `factors_v2/independence.py` |

**问题**：F/I输出范围错误（应为[0,1]概率，实为±100方向分）。

**修复难度**：⭐⭐中

---

## 3. C层：执行/流动性（合规度：5%）❌几乎缺失

### 3.1 核心度量

| 指标 | 规范要求 | 现状 | 优先级 |
|------|---------|------|--------|
| **spread_bps** | `(ask1-bid1)/mid×1e4` | ❌ 缺失 | P0 |
| **impact_bps** | `(P̄±(Q)-mid)/mid×1e4` | ❌ 缺失 | P0 |
| **OBI_k** | `(Σbid-Σask)/(Σbid+Σask)∈[-1,1]` | ❌ 缺失 | P0 |
| **厚区shelves** | ±B bps桶，D(p)≥μ+2σ | ❌ 缺失 | P1 |
| **resilience** | 簿恢复到80%深度的秒数 | ❌ 缺失 | P2 |

**现状**：
- `ats_core/features/orderbook_depth.py` 存在，但仅做基础计算
- 无impact/OBI/spread的bps单位度量
- 无厚区识别逻辑

**修复难度**：⭐⭐⭐⭐⭐非常高（需订单簿实时数据流）

---

### 3.2 硬闸（开仓/维持滞回）

**规范要求**：
```yaml
开仓阈值:
  impact_bps: ≤7 (新币) / ≤10 (标准)
  spread_bps: ≤35
  |OBI|: ≤0.30
  DataQual: ≥0.90
  Room: ≥R*·ATR

维持阈值: 各放宽3-5单位
冷却: 60-120s
```

**现状**：❌ **完全缺失**

**位置**：应在`ats_core/execution/`或`ats_core/gates/`

**影响**：🔴 可能在流动性极差时发布信号，导致无法成交或巨大滑点。

**修复难度**：⭐⭐⭐⭐⭐非常高（需实时订单簿 + 状态机）

---

### 3.3 入场/SL/TP策略

| 策略 | 规范要求 | 现状 | 优先级 |
|------|---------|------|--------|
| **入场** | 回撤接力/突破带 | ❌ 缺失 | P1 |
| **SL0** | `softmax_τ(d_struct, d_atr)` | ❌ 缺失 | P1 |
| **追踪SL** | `softmin_τ(Chandelier, 结构, BE)` | ❌ 缺失 | P1 |
| **TP** | 厚区maker，20s调整 | ❌ 缺失 | P2 |

**现状**：
- `ats_core/execution/binance_futures_client.py` 存在，但仅基础下单
- 无复杂入场/SL/TP逻辑

**修复难度**：⭐⭐⭐⭐高（需策略引擎）

---

## 4. D层：概率/EV/发布（合规度：40%）

### 4.1 概率计算

#### ⚠️ 部分满足：分边概率

**规范要求**：
```python
P_long = σ(S/Teff)
P_short = σ(-S/Teff)
```

**现状**：
- 文件：`ats_core/scoring/probability_v2.py`
- ✅ 有概率映射：
  ```python
  def map_probability_sigmoid(
      edge: float,
      temperature: float = 50.0,
      ...
  ) -> Dict[str, Any]:
      # ...
      p = 1.0 / (1.0 + math.exp(-edge / temperature))
  ```

- ⚠️ 但Teff未按规范计算（无F/I调节）
- ⚠️ 温度固定=50，未动态调节

**修复难度**：⭐⭐⭐中（需接入B层Teff）

---

#### ⚠️ 部分满足：短样本收缩

**规范要求**：
```python
P̃ = 0.5 + w_eff·(P - 0.5)
w_eff = min(1, bars_1h/400)
```

**现状**：
- `ats_core/scoring/probability_v2.py` 有`calibrate_p()`
- ⚠️ 但收缩逻辑可能不完全匹配

**修复难度**：⭐低

---

### 4.2 EV计算

#### ❌ 缺失：期望收益公式

**规范要求**：
```python
EV = P·μ_win - (1-P)·μ_loss - cost_eff
μ_win, μ_loss: 历史分桶条件均值（多空镜像）
```

**现状**：❌ **完全缺失**

**位置**：应在`ats_core/scoring/expected_value.py`（新建）

**影响**：🔴 无EV>0硬闸，可能发布负期望信号。

**修复难度**：⭐⭐⭐⭐高（需历史数据回测建模）

---

### 4.3 发布规则

#### ❌ 缺失：EV硬闸 + K/N持久 + 冷却

**规范要求**：
```python
Prime发布:
  EV* > 0  AND
  p* ≥ p_min  AND
  ΔP ≥ Δp_min  AND
  K/N持久 (如2/3根确认)

维持滞回: 门槛降低0.01-0.02
冷却: 60-120s
```

**现状**：
- 文件：`scripts/realtime_signal_scanner.py` + `analyze_symbol.py`
- ⚠️ 有概率阈值判断
- ❌ 无EV>0硬闸
- ❌ 无K/N持久机制
- ❌ 无滞回/冷却

**位置**：`scripts/realtime_signal_scanner.py:234-235`（过滤逻辑简陋）

**修复难度**：⭐⭐⭐中（需状态机）

---

## 5. 数据层（合规度：45%）

### 5.1 WS连接拓扑

#### ⚠️ 部分满足：WebSocket缓存

**规范要求**：
```yaml
3-5路组合流:
  - kline合并流 (1m/5m/15m/1h)
  - aggTrade合并流 (候选池)
  - markPrice合并流 (可选)
  - depth@100ms合并流 (按需挂载)

重连: 指数退避 + 抖动
心跳: p95 inter-arrival监控
```

**现状**：
- 文件：`ats_core/data/realtime_kline_cache.py`
- ✅ 有WebSocket K线缓存
- ❌ 未使用组合流（单独订阅每个symbol×interval）
- ❌ 无aggTrade/depth/markPrice流
- ⚠️ 重连策略简单（无指数退避+抖动）

**代码片段**：
```python
# realtime_kline_cache.py:50
self.ws_connected: Dict[str, bool] = {}  # 单独管理连接
```

**影响**：连接数过多（可能>100），稳定性差。

**修复难度**：⭐⭐⭐⭐高（需重构WS管理）

---

### 5.2 DataQual计算

#### ❌ 缺失：数据质量评分

**规范要求**：
```python
DataQual = 1 - (0.35·miss + 0.15·ooOrder + 0.20·drift + 0.30·mismatch)

阈值:
  ≥0.90 → 允许Prime
  <0.90 → Watch-only
  <0.88 → 立即降级 + 冷却60-120s
```

**现状**：❌ **完全缺失**

**位置**：应在`ats_core/data/quality.py`（新建）

**影响**：🔴 可能在坏数据下发布信号（网络延迟、乱序、缺失）。

**修复难度**：⭐⭐⭐⭐高（需实时监控miss/ooOrder/drift/mismatch）

---

### 5.3 时序与对账

| 功能 | 规范要求 | 现状 | 优先级 |
|------|---------|------|--------|
| **双时戳** | ts_exch + ts_srv | ⚠️ 部分，未系统化 | P1 |
| **isFinal固化** | 仅isFinal=true训练 | ❌ 未严格执行 | P2 |
| **乱序修复** | 2s限时重排窗口 | ❌ 缺失 | P1 |
| **簿面对账** | REST快照 + WS增量串联 | ❌ 缺失（无depth流） | P0 |

**修复难度**：⭐⭐⭐⭐高

---

### 5.4 派生量

| 指标 | 规范要求 | 现状 | 文件 |
|------|---------|------|------|
| **AVWAP_from_listing** | Σ(P·V)/ΣV，起点=onboardDate | ❌ 缺失 | - |
| **CVD** | Σ(side·quoteVol) | ✅ 有 | `features/cvd.py` |
| **RVOL** | Σvol/EMA(vol) | ✅ 有 | `features/volume.py` |
| **买卖额差D** | (BuyQ-SellQ)/(BuyQ+SellQ) | ⚠️ 部分 | - |
| **slope_OI** | ΔOI/Δt/EMA(\|ΔOI\|) | ⚠️ 有OI，缺标准化 | `features/open_interest.py` |
| **impact_bps** | (P̄±(Q)-mid)/mid×1e4 | ❌ 缺失 | - |
| **OBI_k** | (Σbid-Σask)/(Σbid+Σask) | ❌ 缺失 | - |
| **shelves** | ±B bps桶，D(p)≥μ+2σ | ❌ 缺失 | - |

---

## 6. 新币通道（合规度：15%）

### 6.1 进入与回切

**规范要求**：
```python
进入: since_listing<14d OR bars_1h<400 OR !has_OI/funding
回切: bars_1h≥400 AND OI/funding连续≥3d OR since_listing≥14d
渐变切换: newcoin→standard 48h线性混合
```

**现状**：
- 文件：`ats_core/pipeline/analyze_symbol.py:148-175`
- ✅ 有新币检测：
  ```python
  coin_age_hours = len(k1)
  is_ultra_new = coin_age_hours <= ultra_new_hours  # 1-24h
  is_phaseA = coin_age_days <= phaseA_days  # 1-7d
  is_phaseB = coin_age_days <= phaseB_days  # 7-30d
  ```

- ⚠️ 但判断条件不完全匹配规范
- ❌ 无回切逻辑（一旦进入新币通道，无法切回）
- ❌ 无48h线性混合

**修复难度**：⭐⭐⭐中

---

### 6.2 点火→成势→衰竭

#### ❌ 缺失：非线性联立条件

**规范要求**：
```python
点火（≥3条成立）:
  1) (P-AVWAP)/ATR_1m ≥ 0.8
  2) speed ≥ 0.25·ATR/min (≥2min)
  3) agg_buy ≥ 0.62 (空用agg_sell)
  4) OBI10 ≥ 0.05 (空≤-0.05)
  5) RVOL_10m ≥ 3.0 (不足用RVOL_5m≥2.0)
  6) slope_CVD > 0 (空<0)

成势确认: 1m/5m斜率同向，15m≥0
衰竭: 失锚+CVD翻转 OR speed<0连续2-3根 OR ...
```

**现状**：❌ **完全缺失**

**位置**：应在`ats_core/newcoin/ignition_detector.py`（新建）

**影响**：🔴 无法捕捉新币快速启动窗口（8-15分钟黄金期）。

**修复难度**：⭐⭐⭐⭐⭐非常高（需分钟级数据流 + 多条件联立）

---

### 6.3 新币版A层因子

**规范要求**：
```python
时间框架: 1m/5m/15m/1h
斜率链: ZLEMA_1m(HL=5), ZLEMA_5m(HL=8), EWMA_15m(HL=20), ATR_1m(HL=20)
权重: T22/M15/S15/V16/C20/O8/Q4
```

**现状**：
- ⚠️ 有1m/5m数据检测，但未用于因子计算
- ❌ 无专门的新币因子计算逻辑
- ❌ 权重未区分新币/标准通道

**修复难度**：⭐⭐⭐⭐高

---

### 6.4 新币执行参数

**规范要求**：
```yaml
硬闸更严: impact≤7/8 bps, spread≤35/38 bps
入场: anchor=AVWAP/ZLEMA_5m, 带宽±0.05·ATR_1m
SL/TP: 1m/5m颗粒
Prime窗口: 0-3m冷启动仅Watch, 3-8m可能Prime, 8-15m主力
TTL: 2-4h, 并发=1
```

**现状**：❌ **全部缺失**（无执行层）

**修复难度**：⭐⭐⭐⭐⭐非常高

---

## 7. 模块级对照矩阵

### 7.1 代码文件映射

| 规范模块 | 应存在的文件 | 当前状态 | 行号/位置 |
|---------|------------|---------|---------|
| **A层标准化链** | `ats_core/features/standardization.py` | ❌ 不存在 | - |
| **A层：T因子** | `ats_core/features/trend.py` | ✅ 存在 | 全文 |
| **A层：M因子** | `ats_core/features/momentum.py` | ✅ 存在 | 全文 |
| **A层：C因子** | `ats_core/features/cvd.py` | ✅ 存在 | 全文 |
| **A层：S因子** | `ats_core/features/structure_sq.py` | ✅ 存在 | 全文 |
| **A层：V因子** | `ats_core/features/volume.py` | ✅ 存在 | 全文 |
| **A层：O因子** | `ats_core/features/open_interest.py` | ✅ 存在 | 全文 |
| **A层：Q因子** | `ats_core/factors_v2/liquidation.py` | ✅ 存在 | 全文 |
| **A层：聚合** | `ats_core/scoring/scorecard.py` | ✅ 存在 | 1-55 |
| **B层：g(x)归一** | `ats_core/modulators/normalization.py` | ❌ 不存在 | - |
| **B层：F拥挤度** | `ats_core/features/fund_leading.py` | ⚠️ 存在但输出±100 | 全文 |
| **B层：I独立性** | `ats_core/factors_v2/independence.py` | ⚠️ 存在但输出±100 | 全文 |
| **B层：Teff** | `ats_core/modulators/temperature.py` | ❌ 不存在 | - |
| **B层：cost_eff** | `ats_core/modulators/cost.py` | ❌ 不存在 | - |
| **B层：门槛调节** | `ats_core/modulators/threshold.py` | ❌ 不存在 | - |
| **C层：度量** | `ats_core/execution/metrics.py` | ❌ 不存在 | - |
| **C层：硬闸** | `ats_core/execution/gates.py` | ❌ 不存在 | - |
| **C层：入场策略** | `ats_core/execution/entry.py` | ❌ 不存在 | - |
| **C层：SL/TP** | `ats_core/execution/stops.py` | ❌ 不存在 | - |
| **D层：概率** | `ats_core/scoring/probability_v2.py` | ✅ 存在 | 全文 |
| **D层：EV** | `ats_core/scoring/expected_value.py` | ❌ 不存在 | - |
| **D层：发布规则** | `ats_core/publishing/rules.py` | ❌ 不存在 | - |
| **数据层：WS组合流** | `ats_core/data/ws_multiplex.py` | ❌ 不存在 | - |
| **数据层：DataQual** | `ats_core/data/quality.py` | ❌ 不存在 | - |
| **数据层：簿面对账** | `ats_core/data/depth_reconciliation.py` | ❌ 不存在 | - |
| **新币：点火检测** | `ats_core/newcoin/ignition_detector.py` | ❌ 不存在 | - |
| **新币：新币因子** | `ats_core/newcoin/factors_1m.py` | ❌ 不存在 | - |
| **新币：通道管理** | `ats_core/newcoin/channel_manager.py` | ❌ 不存在 | - |

---

### 7.2 关键问题清单（按优先级）

#### P0 - 最高优先级（阻塞性问题）

| # | 问题 | 文件 | 行号 | 影响 | 修复难度 |
|---|------|------|------|------|---------|
| 1 | **F/I直接参与评分** | `adaptive_weights.py` | 49,70,92,113,128 | 🔴严重违反规范 | ⭐⭐⭐⭐高 |
| 2 | **无EV>0硬闸** | - | - | 🔴可能发布负期望信号 | ⭐⭐⭐⭐高 |
| 3 | **无DataQual控制** | - | - | 🔴坏数据下发布Prime | ⭐⭐⭐⭐高 |
| 4 | **无B层Teff计算** | - | - | 🔴概率温度固定，无动态调节 | ⭐⭐⭐⭐⭐非常高 |
| 5 | **无B层cost_eff** | - | - | 🔴EV无法计算 | ⭐⭐⭐⭐高 |
| 6 | **无C层硬闸** | - | - | 🔴流动性差时可能下单 | ⭐⭐⭐⭐⭐非常高 |

#### P1 - 高优先级

| # | 问题 | 文件 | 行号 | 影响 | 修复难度 |
|---|------|------|------|------|---------|
| 7 | **无统一标准化链** | 各因子文件 | - | 🟡因子输出不一致 | ⭐⭐⭐中 |
| 8 | **无发布端平滑+限斜率+过零滞回** | - | - | 🟡信号跳变 | ⭐⭐⭐中 |
| 9 | **无K/N持久+滞回+冷却** | `realtime_signal_scanner.py` | 234-235 | 🟡发布抖动 | ⭐⭐⭐中 |
| 10 | **WS未使用组合流** | `realtime_kline_cache.py` | - | 🟡连接数过多 | ⭐⭐⭐⭐高 |
| 11 | **新币无点火检测** | - | - | 🟡错失新币快速启动 | ⭐⭐⭐⭐⭐非常高 |

#### P2 - 中优先级

| # | 问题 | 文件 | 行号 | 影响 | 修复难度 |
|---|------|------|------|------|---------|
| 12 | **聚合缺少tanh压缩** | `scorecard.py` | 46 | 🟢边界不平滑 | ⭐低 |
| 13 | **无厚区识别** | - | - | 🟢TP策略缺失 | ⭐⭐⭐⭐高 |
| 14 | **无簿面对账** | - | - | 🟢深度数据可能不一致 | ⭐⭐⭐⭐高 |
| 15 | **无AVWAP_from_listing** | - | - | 🟢新币锚点缺失 | ⭐⭐中 |

---

## 8. 修复路径建议

### 8.1 立即行动（P0）

```yaml
第1步: 重构B层（F/I调节器）
  - 从weights中移除F
  - 新建modulators/目录
  - 实现g(x), Teff, cost_eff, 门槛调节

第2步: 实现DataQual
  - 新建data/quality.py
  - 监控miss/ooOrder/drift/mismatch
  - 添加Prime发布闸门

第3步: 实现EV计算
  - 新建scoring/expected_value.py
  - 回测历史数据建立μ_win/μ_loss
  - 添加EV>0硬闸
```

### 8.2 近期规划（P1）

```yaml
第4步: 统一标准化链
  - 新建features/standardization.py
  - 实现EW-Median/MAD + 软winsor + tanh
  - 所有因子接入

第5步: WS组合流优化
  - 重构realtime_kline_cache.py
  - 实现3-5路组合流
  - 添加aggTrade/depth/markPrice

第6步: 发布端防抖
  - 实现平滑+限斜率+过零滞回
  - 实现K/N持久+滞回+冷却
  - 状态机管理
```

### 8.3 长期改进（P2）

```yaml
第7步: C层执行闸门
  - 实现impact/OBI/spread/厚区
  - 硬闸 + 滞回
  - 入场/SL/TP策略

第8步: 新币通道
  - 点火→成势→衰竭检测
  - 分钟级因子计算
  - 通道切换管理
```

---

## 9. 风险评估

### 9.1 不修复的后果

| 风险 | 概率 | 影响 | 风险等级 |
|------|------|------|---------|
| **发布负EV信号** | 高 | 🔴资金损失 | 🔴严重 |
| **坏数据下发布Prime** | 中 | 🔴错误信号 | 🔴严重 |
| **流动性差时下单** | 中 | 🟡巨大滑点 | 🟡中等 |
| **F/I逻辑混乱** | 高 | 🟡信号质量下降 | 🟡中等 |
| **信号剧烈跳变** | 高 | 🟢用户体验差 | 🟢轻微 |

### 9.2 修复收益

| 收益 | 预期提升 |
|------|---------|
| **信号质量** | +30-50%（EV>0硬闸 + DataQual） |
| **系统稳定性** | +40-60%（WS组合流 + 对账） |
| **新币捕获率** | +200-500%（点火检测 + 分钟级） |
| **执行成功率** | +20-40%（C层闸门 + 厚区TP） |

---

## 10. 总结

### 10.1 合规性总览

```
总体合规度: 35% (加权平均)

分层评分:
  ✅ A层：55% - 因子存在但标准化不统一
  ❌ B层：20% - 严重违反规范（F/I参与评分）
  ❌ C层：5%  - 几乎缺失
  ⚠️ D层：40% - 有概率但无EV
  ⚠️ 数据层：45% - 有缓存但无质量控制
  ❌ 新币：15% - 检测存在但无点火机制
```

### 10.2 关键建议

1. **立即修复B层**：F/I从评分中移除，单独计算Teff/cost/门槛
2. **实现DataQual**：添加数据质量评分，<0.90禁止Prime
3. **实现EV硬闸**：添加期望收益计算，EV≤0禁止发布
4. **统一标准化链**：所有因子接入EW-Median/MAD → 软winsor → tanh
5. **WS组合流优化**：减少连接数从>100到3-5路

### 10.3 预计工作量

| 阶段 | 工作量 | 时间 |
|------|--------|------|
| **P0修复** | 120-150工时 | 3-4周 |
| **P1改进** | 80-100工时 | 2-3周 |
| **P2完善** | 60-80工时 | 1.5-2周 |
| **总计** | 260-330工时 | **6-9周** |

---

**生成时间**: 2025-10-31
**下一步**: 执行 C阶段（实施方案）→ D阶段（影子运行）→ E阶段（变更提案）
