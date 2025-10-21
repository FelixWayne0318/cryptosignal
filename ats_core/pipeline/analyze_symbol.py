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

def is_bigcap(symbol:str):
    return symbol in CFG.get("majors", default=["BTCUSDT","ETHUSDT"])

def analyze_symbol(symbol:str, ctx_market=None):
    p = CFG.params
    # 1h/4h
    k1 = klines_1h(symbol, 300)
    if len(k1)<120: raise RuntimeError("1h samples insufficient")
    o,h,l,c,v,q,tb = split_ohlcv(k1)
    k4 = klines_4h(symbol, 200)
    _,_,_,c4,_,_,_ = split_ohlcv(k4)
    # basics
    atr1 = atr(h,l,c,14); atr_now=atr1[-1]
    ema30 = ema(c,30)
    cv = cvd(v,tb)
    # micro 15m gating is done later (publish)
    # T
    T, Tm = score_trend(h,l,c,c4, p["trend"])
    # A
    A, Am = score_accel(c, cv, p.get("accel", {}))
    # S (needs m15_ok in ctx later; for score use False first; publish阶段再更新)
    S, Sm = score_structure(h,l,c, ema30[-1], atr_now, p["structure"], {"bigcap":is_bigcap(symbol), "overlay":False, "phaseA":False, "strong":(Tm["slopeATR"]>=0.30), "m15_ok":False})
    # V
    V, Vm = score_volume(v)
    # O
    cvd6 = (cv[-1]-cv[-7]) / max(1e-12, 1.0)
    O, Om = score_open_interest(symbol, c, (Tm["slopeATR"]>0), p["open_interest"], cvd6)
    # E + funding veto
    E, Em = environment_score(h,l,c, atr_now, p["environment"])
    veto, Fm = funding_hard_veto(symbol, is_bigcap(symbol), p["environment"]["funding"])
    # prior_up & Q
    # need BTC/ETH 1h for prior (simple: reuse c if symbol is btc/eth; otherwise fetch if ctx not provided)
    if ctx_market and "btc_c" in ctx_market and "eth_c" in ctx_market:
        prior = compute_prior_up(ctx_market["btc_c"], ctx_market["eth_c"], p["prior_q"])
    else:
        prior = 0.5  # fallback neutral
    # quality factor
    pass_dims = sum(1 for x in (T,A,S,V,O,E) if x>=65)
    Q = compute_quality_factor(
        {"pass_dims":pass_dims, "over_ok":Sm["not_over"], "samples_ok":(len(k1)>=120), "crowding":Om.get("crowding_warn",False)},
        {"bigcap":is_bigcap(symbol)}, p["prior_q"])
    # probability
    Up, Down, edge = scorecard({"T":T,"A":A,"S":S,"V":V,"O":O,"E":E}, p["weights"])
    p_up, p_dn = map_probability(edge, prior, Q)
    # pricing
    pr = price_plan(h,l,c, atr_now, p["pricing"], side_long=(p_up>=p_dn))
    # 15m micro confirm before publish
    m15_ok, m15m = check_microconfirm_15m(symbol, side_long=(p_up>=p_dn), params=p["micro_15m"], atr1h=atr_now)
    # re-evaluate S with m15_ok influence (only affects S meta for output; score不回填以避免重复计算复杂度)
    # publish decision
    prime = False
    reason = []
    if veto:
        prime=False; reason.append("资金费率极端")
    else:
        if max(p_up,p_dn) >= p["publish"]["prob_threshold"] and pass_dims >= p["publish"]["min_pass_dimensions"] and m15_ok:
            prime=True
        else:
            if max(p_up,p_dn) < p["publish"]["prob_threshold"]: reason.append("概率未达标")
            if pass_dims < p["publish"]["min_pass_dimensions"]: reason.append("维度不足")
            if not m15_ok: reason.append("15m微确认未通过")
    side = "多" if p_up>=p_dn else "空"
    res = {
        "symbol":symbol, "side":side, "prob":int(round(100*max(p_up,p_dn))),
        "price": c[-1],
        "scores":{"T":T,"A":A,"S":S,"V":V,"O":O,"E":E},
        "meta": {"trend":Tm,"accel":Am,"struct":Sm,"volume":Vm,"oi":Om,"env":Em,"fund":Fm, "prior":prior, "Q":Q, "pass_dims":pass_dims, "m15":m15m},
        "pricing": pr,
        "publish":{"prime":prime,"reason":reason}
    }
    return res