from statistics import mean
from ats_core.features.ta_core import ema
from ats_core.sources.tickers import all_24h

def compute_prior_up(c_btc, c_eth, params):
    # simple mapping of slopes + breadth + median funding (proxy via 24h % change breadth)
    def slope_ema30(c):
        e=ema(c,30); return (e[-1]-e[-7])/6.0
    sbtc=slope_ema30(c_btc); seth=slope_ema30(c_eth)
    breadth=0.5
    try:
        t=all_24h()
        chg=[float(x["priceChangePercent"]) for x in t]
        pos=len([x for x in chg if x>0]); tot=len(chg) or 1
        breadth = pos/tot
    except: pass
    raw = 0.5 + 0.10*max(-1.0,min(1.0, (sbtc+seth))) + 0.10*(breadth-0.5)
    lo,hi = params["prior_up_lo"], params["prior_up_hi"]
    return max(lo, min(hi, raw))

def compute_quality_factor(evidence, ctx_symbol, params):
    # evidence: dict{ "pass_dims":int, "over_ok":bool, "samples_ok":bool, "crowding":bool }
    q=1.0
    if evidence.get("pass_dims",0) < 6: q -= 0.1*(6 - evidence["pass_dims"])
    if not evidence.get("over_ok",True): q -= 0.1
    if not evidence.get("samples_ok",True): q -= 0.05
    if evidence.get("crowding",False): q -= 0.05
    return max(0.6, min(1.0, q))