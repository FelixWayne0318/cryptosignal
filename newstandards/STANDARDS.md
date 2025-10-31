# STANDARDS.md
版本: v2.0 · 目标：方向证据连续稳健、执行可落地、发布稀缺可靠

## 0. 总体原则（Principles）
1) 多空对称：不预设方向，所有口径镜像适用  
2) 分层解耦：A=方向因子(±100)｜B=调节器F/I(仅温度/成本/门槛)｜C=执行/流动性｜D=概率→EV→发布  
3) 斜率优先：以变化率/斜率为主，水平值为辅，避免伪相关  
4) 非线性可控：边际饱和用 tanh/σ/soft-ops；阈值用滞回+时间持久+冷却  
5) 软封顶不过载：统一 EW-Median/MAD → 软 winsor → tanh；极值(|score|=100)出现率 < 5%  
6) EV 为王：EV>0 是发布硬闸；概率/强度用于门槛与排序  
7) 执行可成交优先：TP 厚区 maker；SL 必须可成交（stop-market/分片）  
8) 统一单位：执行侧一律 bps / 秒 / ATR 标准化  
9) 可灰度可回退：调节强度(β,λ,θ,φ)置 0 即回到中性；新模块先影子运行  
10) 在线自检：DataQual<0.90 → Watch-only；F/I 生效需通过断言（坏环境只能更保守）

## 1. 数据与质量 (Data & QoS)
- 时钟同步：对齐交易所，漂移 <100ms  
- Binance USDT-M 数据：
  - REST：`/fapi/v1/exchangeInfo`、`/fapi/v1/klines`、`/fapi/v1/openInterest`（当前）、`/futures/data/openInterestHist`（历史）、`/fapi/v1/premiumIndex`（mark/funding 即时报价）、`/fapi/v1/fundingRate`
  - WS：`@kline_{1m/5m/15m/1h/4h}`、`@aggTrade`、`@depth@100ms`、`@markPrice@1s`
- 质量分（用于闸门与降级）  
  `DataQual = 1 - (w_h*miss + w_o*oo_order + w_d*drift + w_m*mismatch) ∈ [0,1]`  
  约束：`DataQual ≥ 0.90` 才允许 Prime（否则 Watch-only）
- **WS 稳定性建议**：使用**组合流**合并订阅，连接数控制 **3–5 路**（kline/aggTrade/depth/可选 markPrice）；指数回退+抖动重连；定时 REST 深度快照对账（按 lastUpdateId 串联增量）。

## 2. A 层：方向因子（输出 s_k∈[-100,100]）

### 2.0 统一标准化链（所有因子共用）
- 输入预平滑：`x̃_t=αx_t+(1-α)x̃_{t-1}`（1h/4h α=0.3；新币 1m/5m α=0.4）  
- 稳健缩放（抗肥尾）：`z=(x̃-μ)/ (1.4826*MAD)`，`μ,MAD` 用 EW-Median/EW-MAD（η=0.03~0.08）  
- 软 winsor（连续）：`z_soft = sign(z)[ z0+(zmax-z0)(1-exp(-( |z|-z0 )/λ)) ]`（|z|>z0；z0=2.5,zmax=6,λ=1.5）  
- 压缩到 ±100：`s_k = 100 * tanh(z_soft/τ_k)`（τ_k 取该特征 |z| 的 p99≈2~3）  
- 发布端再平滑 + 限斜率 + 过零滞回：  
  `s_pub=(1-αs)s_pub_prev+αs*s_raw`；标准 αs=0.30, Δmax=15；新币 αs=0.50, Δmax=25；仅当 |s_pub|≥10 允许翻符号

### 2.1 趋势 T（1h）
- ZLEMA：`ZLEMA_t=α(2P_t-P_{t-L})+(1-α)ZLEMA_{t-1}`  
- 斜率（单位 ATR）：`slope_ZL=(ZLEMA_t-ZLEMA_{t-h})/h / ATR_1h`  
- 乖离（单位 ATR）：`d30=(P_t-EWMA_30)/ATR_1h`  
- 组合：`T = StdChain(w1*slope_ZL + w2*slope_EW30 + w3*d30)`

### 2.2 动量 M（1h）
`slope_ROC=[(P_t-P_{t-20})/P_{t-20} - (P_{t-h}-P_{t-20-h})/P_{t-20-h}]/h`  
`slope_RSI=[RSI14_t - RSI14_{t-h}]/h`  
`slope_MACD=[MACD_hist_t - MACD_hist_{t-h}]/h`  
`M = StdChain(a1*slope_ROC + a2*slope_RSI + a3*slope_MACD)`

### 2.3 结构/速度 S
`v=(P_t-P_{t-h})/h / ATR`；`δ=(P_t-L*)/ATR`（多；空镜像）  
`S = StdChain(b1*v + b2*δ)`

### 2.4 量能 V
`RVOL=Σ Vol_{t-i} / EMA(Vol)`；`slope_RVOL=[RVOL_t-RVOL_{t-h}]/h`  
`D=(AggBuyQuote-AggSellQuote)/(AggBuyQuote+AggSellQuote)`；`slope_D=[D_t-D_{t-h}]/h`  
`V = StdChain(c1*slope_RVOL + c2*slope_D)`

### 2.5 CVD C
`CVD=Σ side_i*quoteVol_i`；`slope_CVD=(CVD_t-CVD_{t-h})/h / EMA(|ΔCVD|)`  
若 `slope_CVD * slope_P < 0` 则背离惩罚；`C = StdChain(slope_CVD + div_penalty)`

### 2.6 OI O
`slope_OI=(OI_t-OI_{t-h})/h / EMA(|ΔOI|)`  
`O = StdChain( sgn(slope_P) * slope_OI )`（无 OI：值 0、权重 0）

### 2.7 清算残差 Q_sig（小权重）
`Q_sig = StdChain( Σ_{p∈N(P)} sgn(P-p) * LD(p) )`（无 LD 用 qvol/ATR proxy，小权重）

### 2.8 聚合
`S_lin = Σ w_k*s_k`；`S = 100*tanh(S_lin/T_agg) ∈ [-100,100]`  
权重基线：`T18/M12/S10/V10/C18/O18/Q4`（可做 regime 自适应）

## 3. C 层：执行/流动性（闸门与触发）
- `spread_bps = (ask1 - bid1)/mid * 1e4`  
- `impact_bps(Q) = (P̄^±(Q) - mid)/mid * 1e4`  
- `OBI10 = (Σ bid1..10 - Σ ask1..10) / (Σ bid + Σ ask)` ∈[-1,1]  
- 厚区(shelves)：±B bps 桶，`D(p) ≥ μ+2σ` 判为厚区峰（TP 目标）
- **硬闸（开仓/维持滞回）**：impact ≤ 7/8 bps；spread ≤ 35/38 bps；|OBI| ≤ 0.30/0.33；DataQual ≥ 0.90/0.88；Room ≥ R*·ATR；关闸冷却 60–120s
- **入场**：回撤接力（AVWAP/ZLEMA10(1h) ±0.1·ATR_1h 被动挂）或突破带 `δ_in=0.05·ATR+min(0.10·ATR,c·impact)`  
- **SL0（可成交优先）**：`d_struct=|entry-结构低/高|`，`d_atr=1.8·ATR`；`SL0=softmax_τ(d_struct,d_atr)`（τ=0.1·ATR）；触发=穿价≥2tick & ≥300ms & Agg/OBI 同向  
- **追踪 SL**：`SL=softmin_τ(Chandelier(HH_N - k·ATR), 结构保护, BE)`；`N:8→14`；`k_long=1.6,k_short=1.4`  
- **止盈**：厚区入口/中段 maker；20s 无成交上移 1–2 tick；无厚区不挂 TP

## 4. 数据源映射（Binance）
K线：`/fapi/v1/klines` + `@kline_*`；成交：`@aggTrade`；簿面：`@depth@100ms` + REST 快照对账；  
Mark/Funding：`@markPrice@1s`、`/fapi/v1/premiumIndex`、`/fapi/v1/fundingRate`；OI：`/fapi/v1/openInterest`（历史可选 `/futures/data/openInterestHist`）