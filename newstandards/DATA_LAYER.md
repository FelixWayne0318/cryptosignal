# DATA_LAYER.md
版本: v2.0 · 角色：**稳定、可验证、可回退**的数据底座  
范围：Binance USDT-M（合约）全量**实时/准实时**数据采集、清洗、对账、质量评估、缓存与持久化，服务于 `A层(方向因子)`、`B层(调节器F/I)`、`C层(执行/流动性)`、`D层(概率→EV→发布)`。

---

## 0. 设计目标（SLO/SLI）
- **可用性** ≥ 99.5%（核心流：kline_1m / aggTrade / depth@100ms）
- **端到端延迟**：WS事件落地至本地入库 **p95 ≤ 250ms**（新币通道）；标准通道 **p95 ≤ 500ms**
- **对账完整度**（簿面快照+增量一致性） ≥ 99.9%
- **DataQual** ≥ 0.90 方可发布 Prime（详见 §5）
- **回放可重现**：同一原始事件序列→同一特征/信号（确定性）

---

## 1. 数据源与用途（Binance USDT-M 映射）
> **说明**：能拿到的都从币安拿；拿不到的（行业指数、未来清算密度热力图）用自建/代理并**低权重**。

| 模块 | 端点 | 频率/流式 | 关键字段 | 用途（示例） |
|---|---|---|---|---|
| **K 线** | `/fapi/v1/klines` | 回补/批量 | `open, high, low, close, volume, takerBuyBase/Quote` | T/M/S/V 基础；新币冷启动；1m/5m/15m/1h |
| **K 线(WS)** | `@kline_{1m/5m/15m/1h}` | 实时 | 同上 + `isFinal` | 低延迟更新；`isFinal=true` 才固化到训练面 |
| **成交明细** | `@aggTrade` | 实时 | `p, q, m(isBuyerMaker)` | CVD/OFI、RVOL、买卖额差 |
| **订单簿** | `@depth@100ms` + REST 快照 | 实时+周期快照 | `bids, asks, lastUpdateId` | OBI、冲击(impact)、厚区(shelves)、resilience |
| **Mark/指数/资金费率** | `/fapi/v1/premiumIndex` + `@markPrice@1s`、`/fapi/v1/fundingRate` | 1s/8h/历史 | `markPrice, indexPrice, lastFundingRate, nextFundingTime` | F（拥挤度）、basis |
| **持仓量 OI** | `/fapi/v1/openInterest`、`/futures/data/openInterestHist` | 1–5min/历史 | `openInterest` | O 因子（价格×ΔOI 协同） |
| **强平事件** | `@forceOrder` | 实时 | `side, order.price, order.qty` | 清算脉冲（已实现），Q_sig 参考 |
| **元数据** | `/fapi/v1/exchangeInfo` | 启动/每日 | `onboardDate, filters, status` | 新币上市时间、交易规则 |
| **BTC/ETH 指标** | 同上 | 同步 | — | I（独立性，相关/回归） |

> **组合流使用建议**：用 **组合流（multiplex）** 把多符号合并到少数连接（见 §2），连接总数 **3–5** 路即可撑满需求。

---

## 2. 连接拓扑（3–5 路 WS + 按需挂载）
- **固定连接（常驻 2–3 路）**  
  1) `kline 合并流`：新币 `1m/5m/15m` + 常规 `1h`（必要时）；  
  2) `aggTrade 合并流`：仅对“候选池/在播符号”；  
  3) `markPrice 合并流`（可选）：为 F/basis 提供 1s 级 Mark。
- **按需连接（1–2 路）**  
  4) `depth@100ms 合并流`：**仅在 Watch/Prime 候选时挂载**，离场即卸载；如子流>200，纵向分裂为第二路。  
- **策略**  
  - **指数回退 + 抖动重连**（100ms → 200ms → 400ms … ≤ 5s 上限，随机 ±15% 抖动）  
  - **心跳**：若 `p95 inter-arrival` 超阈（如 2s）或 `pong` 超时，判**软失联**；记录 `miss` 并触发对账/重连  
  - **REST 对账节流**：每 30–60s 深度快照（符号自适应），避免风暴

---

## 3. 时序与对账（防“偷看未来”与乱序）
- **双时戳**：保存 `ts_exch`（交易所事件时间）与 `ts_srv`（本机接收时间）；指标计算**只用 `ts_exch` 排序**  
- **固化规则**：`@kline_*` 仅当 `isFinal=true` 才把该 K 固化进训练/打分面；盘中流用于**观察与执行**  
- **乱序修复**：若 `ts_exch` 倒序到达，按 `ts_exch` 插入缓冲队列，**限时重排**（如 2s 窗）  
- **重放一致性**：所有派生量（如 CVD/OBI/impact）由**按时间排序的原始事件**计算，确保回放可重现

---

## 4. 订单簿一致性（快照 + 增量串联）
- **流程**  
  1) 定时拉 **REST 快照**（得到 `lastUpdateId`）；  
  2) 从 WS 缓冲中找到 `u`（更新序号）**大于** `lastUpdateId` 的第一条增量，按顺序应用；  
  3) 若出现缺口或 `U`/`u` 不连续 → 标记 `mismatch`，重新快照；  
  4) 维护 **多级深度**（1、5、10、20 档）与**完整簿（上限 N 档）**供 impact/OBI/厚区计算。
- **impact（bps）**  
  \[
  \mathrm{impact}_{bps}(Q)=\frac{\overline{P}^{\pm}(Q)-mid}{mid}\cdot10^4
  \]  
  以**报价额 Q（USDT）**穿簿，计算成交均价与中价差；多空镜像。
- **OBI\_k**（k=10 默认）  
  \[
  \mathrm{OBI}_k=\frac{\sum_{i=1}^{k}bid_i-\sum_{i=1}^{k}ask_i}{\sum_{i=1}^{k}bid_i+\sum_{i=1}^{k}ask_i}\in[-1,1]
  \]
- **厚区(shelves)**：以 **±B bps** 桶化（如 B=20bps），在滚动窗口 W（如 5–10min）上，若某价桶深度 \(D(p)\ge\mu+2\sigma\) → 记为**厚区峰**，供 TP 选择  
- **resilience**：簿被吃穿后，恢复到事前 80% 深度的时间（秒）

---

## 5. 数据质量评分（DataQual ∈ [0,1]）
> DataQual 低会**直接挡住 Prime**（Watch-only），并触发降级/告警。

\[
\mathrm{DataQual}=1-\big(w_h\cdot\mathrm{miss}+w_o\cdot\mathrm{ooOrder}+w_d\cdot\mathrm{drift}+w_m\cdot\mathrm{mismatch}\big)
\]

- **miss**：心跳/消息缺失率（按流/按符号）  
- **ooOrder**：乱序事件率（重排窗口外）  
- **drift**：\(|ts_{exch}-ts_{srv}|>T_d\) 比率（如 \(T_d=300ms\)）  
- **mismatch**：簿面对账失败/重建事件率  
- **推荐权重**：`w_h=0.35, w_o=0.15, w_d=0.20, w_m=0.30`  
- **阈值**：`DataQual ≥ 0.90` 才允许 Prime；`<0.88` 立即降级并**冷却 60–120s**

---

## 6. 关键派生量（统一口径，供上层直接消费）
- **AVWAP_from_listing**：起点= `exchangeInfo.onboardDate`（无则用最早 1m K 线），\(\text{AVWAP}=\frac{\sum P_iV_i}{\sum V_i}\)  
- **CVD（quote 口径）**：`CVD_t = Σ (taker_side_i ∈ {+1,−1}) * quoteVol_i`，方向由 `aggTrade.m` 判定  
- **RVOL**：`RVOL = Σ_{近m根} vol / EMA(vol)`（m=10/20）；并输出 `slope_RVOL`  
- **买卖额差 D**：`D = (AggBuyQuote − AggSellQuote)/(AggBuyQuote + AggSellQuote)`  
- **OI 斜率**：`slope_OI = ΔOI/Δt / EMA(|ΔOI|)`（缺失→置 0 且因子权重 0）  
- **F（拥挤度）底料**：`lastFundingRate`、`basis = mark - index`、`ΔOI` 的稳健 z 合成到 [0,1]  
- **I（独立性）底料**：1h/4h 级与 BTC/ETH/板块组合的 `ρ, R²`，合成到 [0,1]  
- **清算脉冲**：`@forceOrder` 聚合为单位时间净强平量；无“未来密度”时仅作 **Q_sig 参考**，低权重

---

## 7. 缓存与持久化（数据契约）
- **内存缓存（热层）**  
  - `KlineCache[symbol][interval]`：`deque(maxlen=400)`（1h/4h 标准；新币 1m 用 `maxlen=2000`）  
  - `TradeAggBuffer[symbol]`：按秒聚合（quoteVol、买/卖额）  
  - `DepthBook[symbol]`：当前 L1/L10 与 N 档快照  
  - `QoSState[symbol/stream]`：miss/ooOrder/drift/mismatch 的滑窗计数器
- **持久化（温层/冷层）**  
  - **列式（Parquet）**：分区 `dt=YYYY-MM-DD/symbol=`；表：`klines_{1m,5m,15m,1h}`、`aggtrade_1s`、`depth_events`、`mark_funding`、`oi_1m`  
  - **键值（Meta）**：`exchangeInfo`、`onboardDate`、`lastSnapshotId[symbol]`  
  - **回放**：以 `ts_exch` 排序的 `aggtrade_1s` + `depth_events` 可**完整重建**所有派生量
- **保留策略**（建议）  
  - 热：近 48–72h 全量在内存；  
  - 温：近 90d 留 Parquet；  
  - 冷：归档 S3/OSS（压缩）；K 线与 Mark/Funding 长期保留

---

## 8. 订阅策略（冷/温/热 三级）
- **冷**：仅 1h K 线（REST+偶发 WS）；不订 `aggTrade/depth`  
- **温**（Watch 候选）：开启 `aggTrade`；按需挂载 `depth@100ms`；`markPrice` 可选  
- **热**（Prime 候选/持仓中）：`aggTrade+depth` 常驻；impact/OBI/QoS 高频评估；离场降级→卸载 depth  
> **收益**：把“100+ WS”收敛为“**3–5 路组合流 + 动态子流**”，稳定性、带宽、CPU 全面改善。

---

## 9. 速率与容错
- **REST 限频**：集中回补时做**分片与速率阈**（如 ≤ 5 RPS/端点），失败指数回退，**跨端点打散**  
- **WS 消息节流**：对 **depth 增量**做时间窗聚合（如 50–100ms 桶），不影响 OBI/impact 精度  
- **异常矩阵**  
  - `miss↑`：降级到 Watch-only → 触发快照对账 → 继续高则**重连**  
  - `mismatch↑`：立即快照重建；若 5min 内>3 次，暂停该符号 `depth` 并告警  
  - `drift↑`：校时（NTP）/切换时钟源；同时对 `ts_srv` 补偿  
  - `ooOrder↑`：加大乱序重排窗（如 2s→3s），若仍高则降级

---

## 10. 配置面（建议键位，对应 STANDARDS/MODULATORS）
```yaml
sources:
  kline:   { intervals: [1m,5m,15m,1h], warmup_bars: {1m: 2000, 1h: 400} }
  ws:
    max_conns: 5
    streams: { kline: true, aggTrade: true, depth100ms: on_demand, markPrice: optional }
    reconnect: { backoff_ms: [100,200,400,800,1600,5000], jitter: 0.15 }
  depth:
    snapshot_secs: 30
    max_levels: 500
    bucket_bps: 20
quality:
  weights: { miss: 0.35, ooOrder: 0.15, drift: 0.20, mismatch: 0.30 }
  thresholds: { allow_prime: 0.90, degrade: 0.88 }
timing:
  reorder_window_ms: 2000
  drift_warn_ms: 300
storage:
  parquet_root: /data/ts
  retention_days: { hot: 3, warm: 90 }