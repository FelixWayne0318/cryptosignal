from statistics import median
from ats_core.sources.oi import fetch_oi_hourly, pct, pct_series

def score_open_interest(symbol, closes, side_long, params, cvd6_fallback):
    oi = fetch_oi_hourly(symbol, limit=200)
    if len(oi)<30:
        # fallback to CVD proxy
        O = int(100*max(0.0, min(1.0, ((cvd6_fallback - 0.01)/0.05) )))
        return O, {"oi1h_pct":None,"oi24h_pct":None,"dnup12":None,"upup12":None,"crowding_warn":False}
    den = median(oi[max(0,len(oi)-168):])
    oi1h = pct(oi[-1], oi[-2], den)
    oi24 = pct(oi[-1], oi[-25], den) if len(oi)>=25 else 0.0
    # last 12h price-dir vs OI-dir
    k = min(12, len(closes)-1, len(oi)-1)
    up_up = dn_up = 0
    for i in range(1,k+1):
        dp = closes[-i] - closes[-i-1]
        doi= oi[-i] - oi[-i-1]
        if dp>0 and doi>0: up_up+=1
        if dp<0 and doi>0: dn_up+=1
    # crowding
    hist24 = pct_series(oi, 24)
    crowd_warn = False
    p95=None
    if hist24:
        s=sorted(hist24); p95=s[int(0.95*(len(s)-1))]
        crowd_warn = (oi24 >= p95)
    # scoring maps
    if side_long:
        s1 = max(0.0, min(1.0, (oi24 - params["long_oi24_lo"])/(params["long_oi24_hi"]-params["long_oi24_lo"])))
        s2 = max(0.0, min(1.0, (up_up - 6)/(12-6)))
        O = int(round(80*s1 + 20*s2))
    else:
        a = max(0.0, min(1.0, (dn_up - params["short_dnup12_lo"])/(params["short_dnup12_hi"]-params["short_dnup12_lo"])))
        b = max(0.0, min(1.0, ((-oi24) - (-params["short_oi24_hi"])) / ( (-params["short_oi24_lo"]) - (-params["short_oi24_hi"]) )))
        O = int(round(100*max(a,b)))
    if crowd_warn: O = max(0, O - params["crowding_p95_penalty"])
    return O, {"oi1h_pct":round(oi1h*100,2),"oi24h_pct":round(oi24*100,2),"dnup12":dn_up,"upup12":up_up,"crowding_warn":crowd_warn}