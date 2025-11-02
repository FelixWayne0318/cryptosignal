# MODULATORS.md
F/I 调节器：只改“温度/成本/门槛”，不碰方向分

## 1. 归一与平滑
`g(x)=tanh(γ(x-0.5)) ∈ [-1,1]，γ=3`；对 `g(F), g(I)` 先做 EMA(α=0.2)

## 2. 拥挤度 F ∈ [0,1]
由 funding、basis、ΔOI 的稳健 z 合成后 sigmoid → [0,1]；F 高→拥挤/挤兑风险高→更保守

## 3. 独立性 I ∈ [0,1]
与 BTC/ETH/板块组合做 1h/4h 相关与回归 R²  
`I = σ( a1*(1- R²̄) + a2*(1- |ρ|̄ ) )`

## 4. 概率温度（置信度）
`Teff = clip( T0 * (1 + βF*gF) / (1 + βI*gI), Tmin, Tmax )`  
`P_long=σ(S/Teff)`；`P_short=σ(-S/Teff)`  
护栏：`1 + βI*gI ≥ 0.6`；`Tmin ≤ Teff ≤ Tmax`

## 5. EV 成本（分段惩罚/奖励，互不抵消）
`pen_F = λF*max(0,gF)*ATR_bps`  
`pen_I = λI_pen*max(0,-gI)*ATR_bps`  
`rew_I = λI_rew*max(0,gI)*ATR_bps`  
`cost_eff = fee + impact_bps*mid/1e4 + pen_F + pen_I - rew_I`  
约束：`λI_pen ≥ λI_rew`（坏环境惩罚 ≥ 好环境回扣）

## 6. 发布门槛（软调）
`p*_min = p0 + θF*max(0,gF) + θI_pen*max(0,-gI) - θI_rew*max(0,gI)`  
`Δp_min = dp0 + φF*max(0,gF) + φI_pen*max(0,-gI) - φI_rew*max(0,gI)`

## 7. 默认参数（标准通道）
`T0=50, βF=0.35, βI=0.25, Tmin=35, Tmax=90`  
`λF=0.60, λI_pen=0.50, λI_rew=0.30`  
`p0=0.62, dp0=0.08`  
`θF=0.03, θI_pen=0.02, θI_rew=0.01`  
`φF=0.02, φI_pen=0.01, φI_rew=0.005`

## 8. 断言（在线）
坏环境（F↑或 I↓）→ 必须观察到：`Teff↑、cost_eff↑、门槛↑`；否则回退中性并告警

## 9. 回退
将 `β*, λ*, θ*, φ*` 全置 0 → 全中性（便于灰度/回滚）