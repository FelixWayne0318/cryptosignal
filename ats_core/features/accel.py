from ats_core.features.ta_core import ema

def score_accel(c, cvd_series, params):
    ema30=ema(c,30)
    slope_now=(ema30[-1]-ema30[-7])/6.0
    slope_prev=(ema30[-7]-ema30[-13])/6.0
    ds = slope_now - slope_prev
    cvd6 = (cvd_series[-1]-cvd_series[-7]) / max(1e-12, abs(c[-1])*0.0+1.0)  # scale neutral
    # smooth map
    part1 = max(0.0, min(1.0, ( (slope_now/max(1e-9, (sum([abs(x) for x in c[-30:]])/30.0)/1000.0)) - 0.10 )/0.30 ))
    part2 = max(0.0, min(1.0, ( (cvd6 - 0.01)/0.04 )))
    A = int(100*max(0.0, min(1.0, 0.6*part1 + 0.4*part2 )))
    weak_gate = (ds>=0.02) or (cvd6>=0.02)
    return A, {"dslope30":ds, "cvd6":cvd6, "weak_ok":weak_gate}