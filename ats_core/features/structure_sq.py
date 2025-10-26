# coding: utf-8
"""
S（结构）维度 - Zigzag结构分析（v2.0 ±100对称设计）

改进v2.0：
- ✅ 分数范围：-100 到 +100（0为中性）
- ✅ 方向判断：根据zigzag形成上升/下降结构
- ✅ 对称设计：正值=上升结构（HH+HL），负值=下降结构（LL+LH）
"""
from ats_core.features.ta_core import ema
import math

def _theta(base_big, base_small, overlay_add, phaseA_add, strong_sub, is_big, is_overlay, is_phaseA, strong_regime):
    th = (base_big if is_big else base_small)
    if is_overlay: th += overlay_add
    if is_phaseA: th += phaseA_add
    if strong_regime: th -= strong_sub
    return max(0.25, min(0.60, th))

def _zigzag_last(h,l, c, theta_atr):
    # simple ATR-normalized swings; allow last leg early reverse at 0.5θ
    pts=[("H", h[0], 0),("L", l[0], 0)]
    state="init"; lastp = c[0]
    for i in range(1,len(c)):
        if state in ("init","down"):
            if h[i]-lastp >= theta_atr:
                pts.append(("H",h[i],i)); lastp=h[i]; state="down"
            if lastp - l[i] >= theta_atr:
                pts.append(("L",l[i],i)); lastp=l[i]; state="up"
        elif state=="up":
            if h[i]-lastp >= theta_atr:
                pts.append(("H",h[i],i)); lastp=h[i]; state="down"
            if lastp - l[i] >= theta_atr:
                pts.append(("L",l[i],i)); lastp=l[i]; state="up"
    return pts[-6:] if len(pts)>6 else pts

def score_structure(h,l,c, ema30_last, atr_now, params, ctx):
    # theta
    th = _theta(
        params["theta"]["big"], params["theta"]["small"],
        params["theta"]["overlay_add"], params["theta"]["new_phaseA_add"],
        params["theta"]["strong_regime_sub"],
        ctx.get("bigcap",False), ctx.get("overlay",False), ctx.get("phaseA",False), ctx.get("strong",False)
    )
    theta_abs = th*atr_now
    zz = _zigzag_last(h,l,c, theta_abs)
    # sub-scores (proxy but follows v1.5 semantics)
    # consistency HH/HL or LL/LH from last three pivots
    cons=0.5
    if len(zz)>=4:
        kinds=[k for k,_,_ in zz[-4:]]
        if kinds.count("H")>=2 or kinds.count("L")>=2: cons=0.8
    # ICR: last leg length vs prior leg
    icr=0.5
    if len(zz)>=3:
        a=abs(zz[-1][1]-zz[-2][1]); b=abs(zz[-2][1]-zz[-3][1])
        if b>1e-12: icr = max(0.0, min(1.0, a/b))
    # retracement depth (opt 0.38~0.62 of prior)
    retr=0.5
    if len(zz)>=3:
        rng=abs(zz[-2][1]-zz[-3][1]); ret=abs(zz[-1][1]-zz[-2][1])
        d = abs((ret/max(1e-12,rng))-0.5)
        retr = max(0.0, 1.0 - d/0.12)  # 0.38~0.62 within ≈1σ
    # timing: bars between pivots prefer moderate (4~12)
    timing=0.5
    if len(zz)>=3:
        dt = zz[-1][2]-zz[-2][2]
        if dt<=0: timing=0.3
        elif dt<4: timing = 0.6
        elif dt<=12: timing = 1.0
        else: timing = max(0.3, 1.2 - dt/12.0)
    # not over-extended
    over = abs(c[-1]-ema30_last)/max(1e-12, atr_now)
    not_over = 1.0 if over<=0.8 else 0.5
    # 15m confirmation from ctx
    m15_ok = 1.0 if ctx.get("m15_ok", False) else 0.0
    # penalties (explosive bar etc) approximated by over
    penalty = 0.0 if over<=0.8 else 0.1
    # 计算结构质量（0-100）
    quality = 100 * max(0.0, min(1.0, 0.22*cons + 0.18*icr + 0.18*retr + 0.14*timing + 0.20*not_over + 0.08*m15_ok - penalty))

    # ========== 判断结构方向（v2.0新增） ==========
    direction = 0  # 默认中性

    if len(zz) >= 4:
        # 提取最近的高点和低点
        highs = [(p[1], p[2]) for p in zz if p[0] == "H"]
        lows = [(p[1], p[2]) for p in zz if p[0] == "L"]

        if len(highs) >= 2 and len(lows) >= 2:
            # 取最近两个高点和两个低点
            h1, h2 = highs[-2][0], highs[-1][0]
            l1, l2 = lows[-2][0], lows[-1][0]

            # 上升结构：高点更高 AND 低点更高（HH + HL）
            if h2 > h1 and l2 > l1:
                direction = +1  # 上升结构 → 正分
            # 下降结构：高点更低 AND 低点更低（LH + LL）
            elif h2 < h1 and l2 < l1:
                direction = -1  # 下降结构 → 负分
            # 混乱结构：高低点不一致
            else:
                direction = 0   # 混乱 → 中性（质量打折）
                quality *= 0.5  # 混乱结构，质量减半

    # 对称评分：质量 × 方向
    S = int(round(quality * direction))
    S = max(-100, min(100, S))

    return S, {
        "theta": th,
        "icr": icr,
        "retr": retr,
        "timing": timing,
        "not_over": (over<=0.8),
        "m15_ok": bool(ctx.get("m15_ok", False)),
        "penalty": penalty,
        "quality": int(round(quality)),
        "direction": direction,
        "interpretation": "上升结构" if direction == 1 else ("下降结构" if direction == -1 else "混乱结构")
    }