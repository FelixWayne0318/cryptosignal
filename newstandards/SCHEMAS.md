# SCHEMAS.md
版本：v2.0 · 作用：**数据/表结构契约（字段、单位、键、分区）**  
范围：Binance USDT-M（公开 REST/WS）→ 原始层（Raw）→ 特征层（Feat）→ 决策层（Decision）  
时间戳：**ts_exch**=交易所事件时间（毫秒），**ts_srv**=本机接收时间（毫秒）；所有排序/重放以 **ts_exch** 为准。

---

## 0. 统一约定（Naming & Units）
- 价格：`float64`，单位 **USDT**；量：`float64`，单位 **Base(币)**；成交额：`float64`，单位 **USDT**  
- 百分比：以 **小数**表述（如 0.01=1%）；bps：`float32`（1=1bps）  
- 方向：买/卖分别用 `+1/-1`；布尔：`bool`；枚举：小写字符串  
- 主键（PK）统一包含：`symbol, ts_exch`（必要时再加 `interval`/`seq`/`bucket`）  
- 分区（Parquet）：`dt=YYYY-MM-DD/symbol=SYMBOL/(interval=...)`

---

## 1. 原始层（Raw Layer）
### 1.1 K 线表（多张）
**表名**：`klines_1m` / `klines_5m` / `klines_15m` / `klines_1h`  
**PK**：`symbol, open_time`（毫秒）  
**分区**：`dt=UTC(open_time).date, symbol, interval`  
**字段**
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | 交易对（如 BTCUSDT） |
| interval | string | `1m/5m/15m/1h` |
| open_time | int64 | K线开盘时间（ms, exch） |
| close_time | int64 | K线收盘时间（ms, exch） |
| open, high, low, close | float64 | OHLC（USDT） |
| volume_base | float64 | 成交量（Base） |
| volume_quote | float64 | 成交额（USDT） |
| taker_buy_base | float64 | taker 买量（Base） |
| taker_buy_quote | float64 | taker 买额（USDT） |
| trades | int32 | 成交笔数 |
| is_final | bool | 仅 `true` 的行用于训练/打分固化 |
| ts_srv | int64 | 本机接收时刻（ms） |

---

### 1.2 成交聚合表（逐秒）
**表名**：`aggtrade_1s`  
**PK**：`symbol, bucket_ts`（向下取整到秒的 ts_exch）  
**分区**：`dt, symbol`  
**字段**
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| bucket_ts | int64 | 秒桶（ms） |
| buy_quote | float64 | 该秒内买额（USDT, taker 买） |
| sell_quote | float64 | 该秒内卖额（USDT, taker 卖） |
| buy_base | float64 | 该秒内买量（Base） |
| sell_base | float64 | 该秒内卖量（Base） |
| trades_cnt | int32 | 成交条数 |
| avg_price | float64 | 该秒成交均价（USDT） |
| ts_first/ts_last | int64 | 该秒首/末条事件 ts_exch |
| ts_srv | int64 | — |

> 需要原始逐笔时，可另存 `aggtrade_raw(symbol, ts_exch, price, qty, is_buyer_maker, ts_srv)`。

---

### 1.3 订单簿增量表（Depth Events）
**表名**：`depth_events`  
**PK**：`symbol, ts_exch, seq`（同毫秒内多条用 `seq` 递增）  
**分区**：`dt, symbol`  
**字段**
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| ts_exch | int64 | 事件时间（ms） |
| U | int64 | 首次更新 ID（Binance 字段） |
| u | int64 | 末次更新 ID（Binance 字段） |
| side | enum | `bids` / `asks` |
| price | float64 | 变更价位 |
| qty | float64 | 该价位最新数量（0 表示移除） |
| mid | float64 | 事件时刻中价（可选缓存） |
| ts_srv | int64 | — |
| snapshot_id | int64 | 最近对账快照的 `lastUpdateId` |

> 对账快照单独存：`depth_snapshot(symbol, ts_exch, lastUpdateId, bids[], asks[], ts_srv)`（分区同上）。

---

### 1.4 Mark / Funding / OI
**表名**：`mark_funding`（1s/8h 混合采样）  
**PK**：`symbol, ts_exch`（1s 级）  
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| ts_exch | int64 | — |
| mark_price | float64 | 标记价格 |
| index_price | float64 | 指数价格 |
| last_funding_rate | float64 | 上一/当前资金费率 |
| next_funding_time | int64 | 下次结算时间（ms） |
| basis | float64 | `mark_price - index_price` |
| ts_srv | int64 | — |

**表名**：`oi_1m`  
**PK**：`symbol, ts_exch`（分钟对齐）  
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| ts_exch | int64 | 分钟时刻（ms） |
| open_interest | float64 | OI 张数（按交易所口径） |
| ts_srv | int64 | — |

---

### 1.5 强平事件
**表名**：`force_order`  
**PK**：`symbol, ts_exch, seq`  
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| ts_exch | int64 | — |
| side | enum | `BUY` / `SELL`（被强平方向） |
| price | float64 | 强平价 |
| qty | float64 | 数量 |
| ts_srv | int64 | — |

---

## 2. 质量与对账状态
**表名**：`qos_state_1m`  
**PK**：`symbol, ts_exch`（分钟对齐）  
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| ts_exch | int64 | — |
| miss | float32 | 心跳/消息缺失率 |
| oo_order | float32 | 乱序超窗比率 |
| drift | float32 | |ts_exch − ts_srv| 超阈比率 |
| mismatch | float32 | 簿面对账失败率 |
| dataqual | float32 | `1 - (0.35*miss + 0.15*oo + 0.20*drift + 0.30*mismatch)` |
| notes | string | 附加诊断 |

---

## 3. 特征层（Feat Layer）
### 3.1 方向因子（A 层）
**表名**：`features_a_1h`（主 1h；新币另存 `features_a_newcoin_1m/5m`）  
**PK**：`symbol, ts_exch`（bar close）  
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| ts_exch | int64 | 对应 K 线收盘时刻 |
| T,M,S,V,C,O,Q | float32 | **标准化后**的因子得分（±100） |
| S_lin | float32 | 加权线性分（未tanh） |
| S_score | float32 | `100*tanh(S_lin/T_agg)` |
| meta_* | json | 各因子原始量/斜率/参数摘要 |
| ts_srv | int64 | — |

### 3.2 调节器（B 层）
**表名**：`features_b_modulators`  
**PK**：`symbol, ts_exch`  
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| ts_exch | int64 | — |
| F_raw | float32 | 拥挤度原始 0–1 |
| I_raw | float32 | 独立性原始 0–1 |
| gF, gI | float32 | `tanh(γ(x-0.5))` ∈[−1,1] |
| Teff | float32 | 概率温度 |
| cost_fee | float32 | 手续费（USDT 等价） |
| cost_impact_bps | float32 | 冲击成本（bps） |
| cost_penF, cost_penI, cost_rewI | float32 | 惩罚/回扣分量 |
| cost_eff | float32 | 总成本 |
| pmin, dpmin | float32 | 动态发布门槛 |
| ts_srv | int64 | — |

### 3.3 执行与簿面（C 层）
**表名**：`features_c_exec_1m`（1 分钟颗粒）  
**PK**：`symbol, ts_exch`  
| 字段 | 类型 | 说明 |
|---|---|---|
| spread_bps | float32 | (ask1−bid1)/mid*1e4 |
| obi10 | float32 | L10 OBI |
| impact_bps_q | float32 | 指定 Q(USDT) 的冲击 |
| shelves_cnt | int16 | 厚区峰计数 |
| resilience_s | float32 | 恢复到80%深度的秒数 |
| room_atr | float32 | 价格到结构位/ATR |
| ts_srv | int64 | — |

---

## 4. 决策层（Decision Layer）
**表名**：`decision_d_prob_ev`  
**PK**：`symbol, ts_exch`  
| 字段 | 类型 | 说明 |
|---|---|---|
| S_score | float32 | ±100 方向分 |
| P_long, P_short | float32 | σ(S/Teff), σ(−S/Teff) |
| P_long_cal | float32 | 校准后概率 |
| EV_long, EV_short | float32 | 期望值（含成本） |
| edge | float32 | `S_score/100` |
| ts_srv | int64 | — |

**表名**：`publish_events`  
**PK**：`symbol, publish_ts`  
| 字段 | 类型 | 说明 |
|---|---|---|
| publish_ts | int64 | 发布时间（ms, exch） |
| side | enum | `long/short/watch/revoke` |
| prime | bool | 是否 Prime |
| prime_strength | int16 | 0–100（展示口径） |
| prime_signed | int16 | −100..100 |
| entry_lo/entry_hi | float64 | 入场带 |
| sl0 | float64 | 初始止损 |
| tp1/tp2 | float64 | 止盈参考 |
| ttl_h | float32 | 有效期（小时） |
| reasons | json | 触发条件/闸门/阈值说明 |
| ts_srv | int64 | — |

---

## 5. 新币状态
**表名**：`newcoin_state`  
**PK**：`symbol`  
| 字段 | 类型 | 说明 |
|---|---|---|
| symbol | string | — |
| onboard_ts | int64 | 上线时间（ms） |
| bars_1h | int32 | 已积累的 1h 根数 |
| in_newcoin | bool | 是否处于新币通道 |
| stage | enum | `coldstart/watch/prime/standard` |
| last_switch_ts | int64 | 最近通道切换时刻 |

---

## 6. 校验规则（强约束）
- **时间一致性**：同一 `symbol, interval` 的 `open_time`/`close_time` 不能重叠；`ts_exch` 单调非降  
- **价格/量非负**；`bid1 ≤ ask1`；簿面应用增量时 `u` 必须连续  
- **DataQual 约束**：当 `dataqual < 0.90` 时，不得写入 `publish_events.prime=true` 记录  
- **单位一致性**：所有 bps 字段不得>2000（保护异常）；概率在 `[0,1]`

---

## 7. 示例（片段）
```json
// features_a_1h
{
  "symbol":"BTCUSDT","ts_exch":1730265600000,
  "T":64.2,"M":31.0,"S":18.5,"V":22.4,"C":41.3,"O":33.7,"Q":3.1,
  "S_lin":52.8,"S_score":88.3,"ts_srv":1730265600123
}
// features_b_modulators
{
  "symbol":"BTCUSDT","ts_exch":1730265600000,
  "F_raw":0.72,"I_raw":0.41,"gF":0.50,"gI":-0.26,
  "Teff":71.0,"cost_fee":0.0004,"cost_impact_bps":6.8,
  "cost_penF":0.9,"cost_penI":0.4,"cost_rewI":0.0,
  "cost_eff":1.3,"pmin":0.66,"dpmin":0.09
}

```markdown
# EVAL_MANUAL.md
版本：v2.0 · 作用：**评测与校准手册（从离线到在线）**  
目标：用**可复现**的指标体系验证 A/B/C/D 层口径的有效性与稳定性，给出上线/回滚的硬性标准。

---

## 0. 数据切分与标签（Labeling）
- **时间切分**：`Train (T1) → Valid (T2) → OOT (T3)`，严格按时间前推；新币与老币分别评测并汇总  
- **符号分组**：Top 流动性、中等、新币，分别统计与加权  
- **标签**（多窗口）：对每个 1h bar（新币用 1m/5m），计算未来收益  
  \[
  r_{+H}=\frac{P_{t+H}-P_t}{P_t},\quad H\in\{1h,4h,8h\}
  \]
  并计算 **成本后**收益：`r_net = r_{+H} - cost_eff_benchmark`  
- **事件标签**：点火/失锚/清算带触碰（按 NEWCOIN_SPEC 与 STANDARDS 的条件重放识别）

---

## 1. 十分位单调性（Decile Monotonicity）
**目的**：验证方向分 `S_score` 与下期收益/胜率/EV 的单调关系  
**做法**：按 `S_score` 绝对值或有符号分成 10 分位，计算  
- `mean(r_net)`、`winrate( r_net>0 )`、`EV = P*μ_win - (1-P)*μ_loss - cost`  
- **指标**：  
  - `Kendall τ`（分位序与均值序的秩相关）≥ **0.75**  
  - `Q10 - Q1` 的 `mean(r_net)` **显著 > 0**（t 检验 p<0.01）  
  - 多空对称：对 `-S_score` 重复，结果镜像

**不通过处理**：调整 `τ_k`（tanh 温度）、权重、或剔除失效因子；记录于 `CHANGELOG.md`

---

## 2. 可靠性曲线（Probability Calibration）
**目的**：概率 `P_long/P_short` 与实际命中率对齐  
**做法**：将预测概率分箱（例如 20 桶），对比实际命中率；计算  
- **Brier Score**、**NLL**；拟合 **Platt** 或 **Isotonic** 校准器（5 折时序 CV）  
- **标准**：  
  - `Brier ≤ 基线×0.9`；`NLL ≤ 基线×0.9`  
  - 过拟合防护：`train` 与 `valid` 的校准曲线 **KS≤0.08**

---

## 3. 事件研究（Event Study）
**目的**：验证“点火→成势→衰竭”等阶段条件的经济含义  
**做法**：以事件发生时刻为 0，对齐窗口 `[-H_pre, +H_post]`（如 2h/8h），计算  
- **累计异常收益（CAR）**：`CAR = Σ (r − r_bench)`；基准为板块/市值加权指数  
- **成交与簿面响应**：`RVOL, OBI, impact, resilience` 的均值曲线  
- **标准**：  
  - 点火后的 `CAR(+2h)` 显著同向（p<0.01）且超过成本带  
  - 衰竭事件后的 `CAR(+2h)` 反向显著（多/空镜像）

---

## 4. EV 与执行可行性（Execution Viability）
**目的**：在**真实成本模型**下收益为正、可成交  
**做法**：  
- 成本模型：`fee + impact_bps*mid/1e4`（impact 以实际簿面回放）  
- 入场/TP/SL 回放：按 C 层“厚区 maker / stop-market 分片”规则重建  
- **指标**：  
  - `EV>0` 的占比 ≥ **55%**（在 Valid/OOT）  
  - **Fill Rate**（TP/SL/入场）≥ **90%**  
  - **滑点容差**：实测 impact p95 ≤ 规则上限（7–10bps）

---

## 5. 发布阈与滞回调参（Grid & ROC）
**目的**：找到稳定的 `p_min, Δp_min, Teff` 等阈值  
**做法**：网格搜索 + 时序 CV；目标函数：`Sharpe` / `Sortino` / `Hit-rate` / `MaxDD` 约束  
- **标准**：  
  - OOT 期 `Sharpe ≥ 1.2`（或较基线提升 ≥30%）  
  - 多空对称接受区间：多与空的 `Hit-rate` 差距 ≤ 8pp  
  - 产能（触发频率）与执行资源匹配（并发/TTL/冷却）

---

## 6. 漂移监测（Online Drift）
**周期**：滚动 `7d/14d`  
**指标/阈值**：  
- `Brier/NLL` 相对劣化 > **25%** → **收紧门槛**（p_min +0.02, Δp_min +0.01）  
- `DataQual` 下降（均值 < 0.92 或 5 分钟内 <0.90）→ **降级到 Watch-only**  
- 触发次数骤减 > **40%** 或过密 > **50%** → 复核阈值与冷却

---

## 7. A/B 与影子运行（Shadow → Gray → Full）
- **影子期**：新口径全量计算但**不发布**；与线上版本比较 `rank-corr ≥ 0.90` 才进入灰度  
- **灰度**：5–10% 符号；`CAR/EV/FillRate` 不劣于线上 ≥ 10 个交易日  
- **回滚**：若任一在线断言失败（如 F/I 调节未导致 `Teff↑/cost↑/门槛↑`），**立即回退**

---

## 8. 报告模板（自动生成）
**Report.md 必含**：  
- 数据区间/样本量/分组；  
- 十分位图（`S_score` vs `mean(r_net)`/`winrate`）；  
- 可靠性曲线（预测 vs 实际）+ 校准器系数；  
- 事件研究曲线（点火/衰竭，CAR/RVOL/OBI/impact）；  
- EV/Sharpe/MaxDD 表；  
- 执行指标（FillRate、impact p95、spread p95）；  
- 漂移面板（7/14 天）；  
- 结论与改参建议（列出将落 `CONFIG` 的 Key/Value）。

---

## 9. 失败分析与归因（必做）
- **单因子剥离**：移除单个因子，观察十分位与 EV 变化（Ablation）  
- **阶段错配**：点火成立但 CVD/OBI 不协同 → 下调 `V/C` 权重或提高 Δp_min  
- **成本主导**：EV 为负但命中率正常 → 复核 impact/厚区/入场带宽与挂单时机

---

## 10. 复现与版本控制
- 每次评测输出 `RUN_META.json`：代码 hash、参数版本、数据区间、样本过滤规则  
- 任何口径变更必须写入 `CHANGELOG.md`：**变更项/理由/预期影响/回滚条件**

---

### 一句话
先过 **单调性** 与 **可靠性**，再看 **EV 与执行**；线上靠 **漂移监控 + 影子/灰度** 守住稳定。过不了阈，就别上——这不是脾气，是纪律。