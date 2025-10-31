# PUBLISHING.md
概率→EV→发布：证据平滑，决策离散，但防抖

## 1. 分边概率与温度
`Teff = clip( T0 * (1 + βF*gF) / (1 + βI*gI), Tmin, Tmax )`  
`P_long=σ( S/Teff )`；`P_short=σ( -S/Teff )`  
短样本收缩：`P̃ = 0.5 + w_eff*(P-0.5)`，`w_eff = min(1, bars_1h/400)`

## 2. 期望收益 EV（单边）
`EV = P * μ_win - (1-P) * μ_loss - cost_eff`  
`μ_win, μ_loss` 用历史分桶条件均值（多空镜像）

## 3. 发布规则（离散 + 防抖）
- Prime（发布）：`EV*>0  ∧  p*≥p_min  ∧  ΔP≥Δp_min`
- 维持 Prime（滞回）：门槛降低 0.01~0.02
- 时间持久：K/N 连续满足（如 2/3 根确认）才升/降级
- 冷却：降级/撤信后 60–120s 再评估，防锯齿
- Watch：`EV*>0` 但未达 Prime 门槛，或闸门临界

## 4. 强度展示（可选）
`prime_strength = 0.6*|S| + 40*clip((p* - 0.60)/0.15, 0, 1)`  
`prime_signed = 100*(P_long - P_short) ∈ [-100, 100]`

## 5. 断言与监控
- 断言：坏环境（F↑或 I↓）应观测到 `Teff↑、cost_eff↑、门槛↑`；否则回退中性并告警  
- 评测：十分位单调性、可靠性曲线（校准）、事件窗（点火/失锚/清算带）  
- 漂移报警：7/14 天 Brier/NLL 恶化、或流动性闸常红 → 自动降频/收紧门槛

## 6. TTL 与并发
标准通道：TTL 8h；新币通道：TTL 2–4h；新币并发=1