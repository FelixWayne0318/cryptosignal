from ats_core.sources.klines import klines_15m, split_ohlcv
from ats_core.features.ta_core import ema, atr, cvd

def check_microconfirm_15m(symbol, side_long, params, atr1h):
    rows = klines_15m(symbol, 200)
    o,h,l,c,v,q,tb = split_ohlcv(rows)
    ok_flags = {"ema10_side":False,"micro_vol":False,"cvd_slope":False,"micro_pivot":False}
    veto=False
    # ema10 side + shallow pullback + refill
    ema10 = ema(c,10)
    same_side=0
    for x in range(-params["ema10_side_window"],0):
        same_side += int( (c[x]>=ema10[x]) if side_long else (c[x]<=ema10[x]) )
    ok_flags["ema10_side"] = (same_side>=params["ema10_side_min_ok"])
    # shallow under & refill
    # (proxy by last bar low vs ema10 and recovery within 2 bars)
    # micro volume
    v3 = sum(v[-3:])/3.0; v20=sum(v[-20:])/20.0
    vratio = v3/max(1e-12,v20)
    dVabs = abs((v[-1]-v20)/max(1e-12,v20))
    ok_flags["micro_vol"] = (params["v3_over_v20_min"]<=vratio<=params["v3_over_v20_max"] and params["dV_abs_min"]<=dVabs<=params["dV_abs_max"])
    # cvd slope
    cv = cvd(v,tb)
    s = (cv[-1]-cv[-5])  # 4 bars slope
    ok_flags["cvd_slope"] = (s>0) if side_long else (s<0)
    # micro structure pivot not broken
    lo = min(l[-params["micro_pivot_look"]:])
    hi = max(h[-params["micro_pivot_look"]:])
    tol = params["micro_pivot_tolerance_atr1h"]*atr1h
    if side_long:
        ok_flags["micro_pivot"] = (c[-1] >= lo - tol)
    else:
        ok_flags["micro_pivot"] = (c[-1] <= hi + tol)
    # anti-explosion veto
    atr15 = atr(h,l,c,14)[-1]
    if abs(c[-1]-c[-2]) > params["anti_explosion_atr15m"]*atr15 or vratio>params["anti_explosion_vratio"]:
        veto=True
    # pass if >=2 true and no veto
    passed = (sum(1 for k,v in ok_flags.items() if v) >= params["min_pass_count"]) and (not veto)
    return passed, {"ok":ok_flags, "vratio":vratio, "dVabs":dVabs, "veto":veto}