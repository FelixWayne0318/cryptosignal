import math

def score_volume(vol):
    if len(vol)<25: return 50, {"v5v20":1.0, "vroc_abs":0.0}
    v5 = sum(vol[-5:])/5.0
    v20= sum(vol[-20:])/20.0
    vlevel = v5/max(1e-12,v20)
    # vroc_abs: |ln(v/sma20) - ln(prev)|
    cur = math.log(max(1e-9,vol[-1]/max(1e-9,v20)))
    prv = math.log(max(1e-9,vol[-2]/max(1e-9, sum(vol[-21:-1])/20.0 )))
    vroc_abs = abs(cur-prv)
    # map to score
    s1 = max(0.0, min(1.0, (vlevel-1.2)/(1.7-1.2)))
    s2 = max(0.0, min(1.0, (vroc_abs-0.15)/(0.60-0.15)))
    V = int(round(60*s1 + 40*s2))
    return V, {"v5v20":vlevel, "vroc_abs":vroc_abs}