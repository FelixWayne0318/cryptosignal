# NEWCOIN_SPEC.md
USDT-M 新币通道（分钟级快反），与标准通道彻底隔离

## 1. 进入与回切
- 进入：`since_listing < 14d` 或 `bars_1h < 400` 或 `!has_OI/funding`
- 回切：`bars_1h ≥ 400 且 OI/funding 连续 ≥3d`，或 `since_listing ≥ 14d`
- 渐变切换：newcoin → standard **48h 线性混合**（权重/温度/门槛/TTL 同步过渡）

## 2. 数据流（Binance USDT-M）
REST：exchangeInfo、klines(1m/5m/15m/1h)、premiumIndex、fundingRate、openInterest  
WS：kline_1m/5m/15m、aggTrade、depth@100ms、markPrice@1s  
锚点：`AVWAP_from_listing = Σ(P·V)/ΣV`（起点=上线第一分钟）

## 3. 新币版 A 层因子（统一标准化链 → ±100）
斜率链：`ZLEMA_1m(HL=5)`、`ZLEMA_5m(HL=8)`、`EWMA_15m(HL=20)`；`ATR_1m(HL=20)`  
因子集合：`{T_new, M_new, S_new, V_new, C_new, O_new, Q_sig_new}`（无 OI→O 值0权重0）  
权重：`T22/M15/S15/V16/C20/O8/Q4`（无 OI 时按比例归一）

## 4. 点火 → 成势 → 衰竭（非线性联立）
- 点火（≥3 条成立）  
  `(P-AVWAP)/ATR_1m ≥ 0.8`；`speed ≥ 0.25 ATR/min (≥2min)`；`agg_buy ≥ 0.62`（空用 agg_sell）  
  `OBI10 ≥ 0.05`（空 ≤ -0.05）；`RVOL_10m ≥ 3.0`（不足则 `RVOL_5m ≥ 2.0`）；`slope_CVD > 0`（空 < 0）
- 成势确认：1m/5m 斜率同向，15m ≥ 0  
- 衰竭/反转：失锚 + CVD 翻转；`speed<0` 连续 2–3 根 1m；OBI 反号且对侧 agg≥0.60；或 `qvol/ATR > 0.6`

## 5. 调节器参数（新币特例）
F 初期常失真 → **置 0.5（中性）**，稳定 ≥3d 再启用  
I 用 15m–1h 与 BTC/ETH 粗相关，降权  
温度：`T0=60, βF=0.20, βI=0.15, Tmin=40, Tmax=95`  
成本/门槛：`λF=0.40, λI_pen=0.35, λI_rew=0.20`；`p0=0.60, dp0=0.06`  
`θF=0.03, θI_pen=0.02, θI_rew=0.008`；`φF=0.02, φI_pen=0.01, φI_rew=0.004`  
概率收缩：`P̃ = 0.5 + w_eff*(P-0.5)`，`w_eff = min(1, bars_1h/400)`

## 6. 执行与闸门（更严）
硬闸（开仓/维持滞回）：`impact ≤ 7/8 bps`、`spread ≤ 35/38 bps`、`|OBI| ≤ 0.30/0.33`、`DataQual ≥ 0.90/0.88`、`Room ≥ R*·ATR_1m`  
入场：回撤接力（anchor=AVWAP/ZLEMA_5m，带宽 ±0.05·ATR_1m）或突破带 δ_in（同标准口径）  
SL/TP：1m/5m 颗粒；追踪 `k_long=1.6, k_short=1.4`；TTL 2–4h；并发=1  
Prime 窗口：0–3m 冷启动仅 Watch；3–8m 可能首批 Prime；8–15m 主力窗口；不过闸只发 Watch

## 7. WS 与稳定性
使用**组合流**合并订阅：建议 **3–5 个连接**（kline/aggTrade/depth/可选 markPrice）；指数回退+抖动重连；定时 REST 深度快照对账；心跳缺失升高 → DataQual 下降 → 自动降级