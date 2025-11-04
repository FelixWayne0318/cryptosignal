from ats_core.features.ta_core import ema
from ats_core.scoring.scoring_utils import StandardizationChain
import math

# 模块级StandardizationChain实例（持久化EW状态）
# 参数: alpha=0.15, tau=2.0 (wider range for structure scores)
_structure_chain = StandardizationChain(alpha=0.15, tau=2.0, z0=2.5, zmax=6.0, lam=1.5)

def _theta(base_big, base_small, overlay_add, phaseA_add, strong_sub, is_big, is_overlay, is_phaseA, strong_regime):
    th = (base_big if is_big else base_small)
    if is_overlay: th += overlay_add
    if is_phaseA: th += phaseA_add
    if strong_regime: th -= strong_sub
    return max(0.25, min(0.60, th))

def _zigzag_last(h,l, c, theta_atr):
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
    """
    S（结构）评分 - 统一±100系统

    返回：
    - 正分：结构质量好（技术形态完整）
    - 负分：结构质量差（形态混乱）
    - 0：中性
    """
    # theta
    th = _theta(
        params["theta"]["big"], params["theta"]["small"],
        params["theta"]["overlay_add"], params["theta"]["new_phaseA_add"],
        params["theta"]["strong_regime_sub"],
        ctx.get("bigcap",False), ctx.get("overlay",False), ctx.get("phaseA",False), ctx.get("strong",False)
    )
    theta_abs = th*atr_now
    zz = _zigzag_last(h,l,c, theta_abs)

    # sub-scores
    cons=0.5
    if len(zz)>=4:
        kinds=[k for k,_,_ in zz[-4:]]
        if kinds.count("H")>=2 or kinds.count("L")>=2: cons=0.8

    icr=0.5
    if len(zz)>=3:
        a=abs(zz[-1][1]-zz[-2][1]); b=abs(zz[-2][1]-zz[-3][1])
        if b>1e-12: icr = max(0.0, min(1.0, a/b))

    retr=0.5
    if len(zz)>=3:
        rng=abs(zz[-2][1]-zz[-3][1]); ret=abs(zz[-1][1]-zz[-2][1])
        d = abs((ret/max(1e-12,rng))-0.5)
        retr = max(0.0, 1.0 - d/0.12)

    timing=0.5
    if len(zz)>=3:
        dt = zz[-1][2]-zz[-2][2]
        if dt<=0: timing=0.3
        elif dt<4: timing = 0.6
        elif dt<=12: timing = 1.0
        else: timing = max(0.3, 1.2 - dt/12.0)

    over = abs(c[-1]-ema30_last)/max(1e-12, atr_now)
    not_over = 1.0 if over<=0.8 else 0.5

    m15_ok = 1.0 if ctx.get("m15_ok", False) else 0.0

    penalty = 0.0 if over<=0.8 else 0.1

    # 聚合得分（0-1）
    score_raw = max(0.0, min(1.0, 0.22*cons + 0.18*icr + 0.18*retr + 0.14*timing + 0.20*not_over + 0.08*m15_ok - penalty))

    # 转换为中心化值（0.5=中性 → 0，1.0=完美 → +100，0.0=极差 → -100）
    S_raw = (score_raw - 0.5) * 200

    # v2.0合规：应用StandardizationChain（5步稳健化）
    # 输入S_raw，输出标准化后的S_pub（稳健压缩到±100）
    # ⚠️ 2025-11-04紧急修复：禁用StandardizationChain，过度压缩导致信号丢失
    # S_pub, diagnostics = _structure_chain.standardize(S_raw)
    S_pub = max(-100, min(100, S_raw))  # 直接使用原始值

    # 转换为整数
    S = int(round(S_pub))

    # 解释
    if S >= 40:
        interpretation = "结构完整"
    elif S >= 10:
        interpretation = "结构良好"
    elif S >= -10:
        interpretation = "结构一般"
    elif S >= -40:
        interpretation = "结构较差"
    else:
        interpretation = "结构混乱"

    return S, {
        "theta":th,
        "icr":icr,
        "retr":retr,
        "timing":timing,
        "not_over":(over<=0.8),
        "m15_ok":bool(ctx.get("m15_ok",False)),
        "penalty":penalty,
        "interpretation": interpretation
    }
