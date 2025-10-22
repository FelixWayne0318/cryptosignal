# coding: utf-8
import math
from ats_core.cfg import CFG
from ats_core.sources.klines import klines_1h, klines_4h, split_ohlcv
from ats_core.features.ta_core import ema, atr, cvd
from ats_core.features.trend import score_trend
from ats_core.features.accel import score_accel
from ats_core.features.structure_sq import score_structure
from ats_core.features.volume import score_volume
from ats_core.features.open_interest import score_open_interest
from ats_core.features.environment import environment_score, funding_hard_veto
from ats_core.features.prior_q import compute_prior_up, compute_quality_factor
from ats_core.features.pricing import price_plan
from ats_core.features.microconfirm_15m import check_microconfirm_15m
from ats_core.scoring.scorecard import scorecard
from ats_core.scoring.probability import map_probability

def is_bigcap(symbol: str):
    return symbol in CFG.get("majors", default=["BTCUSDT", "ETHUSDT"])

def analyze_symbol(symbol: str, ctx_market=None):
    p = CFG.params

    # 1h / 4h 原始数据
    k1 = klines_1h(symbol, 300)
    if len(k1) < 120:
        raise RuntimeError("1h samples insufficient")
    o, h, l, c, v, q, tb = split_ohlcv(k1)

    k4 = klines_4h(symbol, 200)
    _, _, _, c4, _, _, _ = split_ohlcv(k4)

    # 基础特征
    atr1 = atr(h, l, c, 14)
    atr_now = atr1[-1]
    ema30 = ema(c, 30)
    cv = cvd(v, tb)

    # 各维度打分
    # T
    T, Tm = score_trend(h, l, c, c4, p["trend"])
    # A
    A, Am = score_accel(c, cv, p.get("accel", {}))
    # S（score 阶段不依赖 m15；发布阶段再看 m15_ok）
    S, Sm = score_structure(
        h, l, c, ema30[-1], atr_now, p["structure"],
        {"bigcap": is_bigcap(symbol), "overlay": False, "phaseA": False,
         "strong": (Tm["slopeATR"] >= 0.30), "m15_ok": False}
    )
    # V
    V, Vm = score_volume(v)

    # OI 回退输入：把 6 根 CVD 变化做 tanh 归一，稳定在 [-1, 1]
    # 这样配合 open_interest.py 的平滑回退，不会出现“轻微负值→直接 0 分”的误导
    try:
        cvd6_raw = (cv[-1] - cv[-7]) if len(cv) >= 8 else 0.0
        scale = max(1e-6, abs(cv[-7])) if len(cv) >= 8 else 1.0
        cvd6 = math.tanh(cvd6_raw / scale)
    except Exception:
        cvd6 = 0.0

    # O
    O, Om = score_open_interest(symbol, c, (Tm["slopeATR"] > 0), p["open_interest"], cvd6)

    # E + funding veto
    E, Em = environment_score(h, l, c, atr_now, p["environment"])
    veto, Fm = funding_hard_veto(symbol, is_bigcap(symbol), p["environment"]["funding"])

    # prior_up（如无 ctx，给中性）
    if ctx_market and "btc_c" in ctx_market and "eth_c" in ctx_market:
        prior = compute_prior_up(ctx_market["btc_c"], ctx_market["eth_c"], p["prior_q"])
    else:
        prior = 0.5

    # 质量因子 Q（兼容 crowding_warn）
    pass_dims = sum(
        1 for x in (T, A, S, V, O, E)
        if isinstance(x, (int, float)) and x >= 65
    )
    Q = compute_quality_factor(
        {
            "pass_dims": pass_dims,
            "over_ok": Sm["not_over"],
            "samples_ok": (len(k1) >= 120),
            "crowding": Om.get("crowding_warn", False) if isinstance(Om, dict) else False,
        },
        {"bigcap": is_bigcap(symbol)},
        p["prior_q"],
    )

    # 概率（显式提供 prob_up/prob_dn，供模板精确显示）
    Up, Down, edge = scorecard({"T": T, "A": A, "S": S, "V": V, "O": O, "E": E}, p["weights"])
    p_up, p_dn = map_probability(edge, prior, Q)  # 0~1
    prob_pct = int(round(100 * max(p_up, p_dn)))

    # 定价/计划
    pr = price_plan(h, l, c, atr_now, p["pricing"], side_long=(p_up >= p_dn))

    # 15m 微确认（仅影响发布，不回写 S 分）
    m15_ok, m15m = check_microconfirm_15m(
        symbol, side_long=(p_up >= p_dn), params=p["micro_15m"], atr1h=atr_now
    )

    # 发布决策
    prime = False
    reason = []
    if veto:
        prime = False
        reason.append("资金费率极端")
    else:
        if (
            max(p_up, p_dn) >= p["publish"]["prob_threshold"]
            and pass_dims >= p["publish"]["min_pass_dimensions"]
            and m15_ok
        ):
            prime = True
        else:
            if max(p_up, p_dn) < p["publish"]["prob_threshold"]:
                reason.append("概率未达标")
            if pass_dims < p["publish"]["min_pass_dimensions"]:
                reason.append("维度不足")
            if not m15_ok:
                reason.append("15m微确认未通过")

    side = "多" if p_up >= p_dn else "空"

    res = {
        "symbol": symbol,
        "side": side,
        # 概率：同时提供 0~1（prob_up/prob_dn）与百分比整数（prob）
        "prob_up": p_up,
        "prob_dn": p_dn,
        "prob": prob_pct,

        # 现价别名，便于模板自适配：last/price/close 都能匹配
        "last": c[-1],
        "price": c[-1],

        # 六维得分
        "scores": {"T": T, "A": A, "S": S, "V": V, "O": O, "E": E},

        # 元数据
        "meta": {
            "trend": Tm, "accel": Am, "struct": Sm, "volume": Vm,
            "oi": Om, "env": Em, "fund": Fm,
            "prior": prior, "Q": Q, "pass_dims": pass_dims, "m15": m15m
        },

        # 定价/计划
        "pricing": pr,

        # 发布信息
        "publish": {"prime": prime, "reason": reason},
    }
    return res