from ats_core.features.ta_core import ema, atr, rsq

def score_trend(h,l,c,c4, params):
    ema5=ema(c,5); ema10=ema(c,10); ema30=ema(c,30)
    ema30_4h=ema(c4,30)
    atr1=atr(h,l,c,14); atr_now=atr1[-1]
    slope=(ema30[-1]-ema30[-7])/6.0
    slopeATR = slope/max(1e-12, atr_now)
    bg_same = ((ema30_4h[-1]-ema30_4h[-7])>0 and slopeATR>0) or ((ema30_4h[-1]-ema30_4h[-7])<0 and slopeATR<0)
    # EMA order
    order_ok = 0
    for i in range(1, params["ema_order_min_bars"]+1):
        if (ema5[-i]>ema10[-i]>ema30[-i]) or (ema5[-i]<ema10[-i]<ema30[-i]): order_ok+=1
    r2=rsq(ema30,21)
    # score
    T=0
    if slopeATR>=params["slope_atr_min_long"]: T+=60
    elif slopeATR>=0.15: T+=40
    elif slopeATR>=0.05: T+=20
    T+= int(40*max(0.0, min(1.0,(r2-0.45)/0.25)))
    if bg_same: T+=10
    if order_ok>=params["ema_order_min_bars"]: T+=10
    return min(T,100), {"slopeATR":slopeATR, "r2":r2, "bg_same":bg_same}