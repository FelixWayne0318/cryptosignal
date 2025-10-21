import math

def ema(arr, n):
    k=2.0/(n+1.0); s=None; out=[]
    for x in arr:
        s = x if s is None else (x*k + s*(1-k))
        out.append(s)
    return out

def atr(h,l,c,n=14):
    trs=[abs(h[0]-l[0])]
    for i in range(1,len(c)):
        trs.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    # EMA-ATR
    k=2.0/(n+1.0); s=None; out=[]
    for tr in trs:
        s = tr if s is None else (tr*k + s*(1-k))
        out.append(s)
    return out

def chop14(h,l,c):
    if len(c)<15: return 100.0
    tr=[]
    for i in range(1,len(c)):
        tr.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    tr14=sum(tr[-14:])
    hh=max(h[-14:]); ll=min(l[-14:])
    rng=max(1e-12,hh-ll)
    return 100.0*math.log10(tr14/rng)/math.log10(14)

def rsq(y, window):
    if len(y)<window: return 0.0
    ys=y[-window:]; xs=list(range(window))
    xm=sum(xs)/window; ym=sum(ys)/window
    num=sum((xs[i]-xm)*(ys[i]-ym) for i in range(window))
    denx=sum((x-xm)**2 for x in xs); deny=sum((v-ym)**2 for v in ys)
    if denx<=0 or deny<=0: return 0.0
    r=num/(denx*deny)**0.5
    return r*r

def cvd(base_vol, taker_buy_base):
    out=[0.0]
    for b,t in zip(base_vol, taker_buy_base):
        out.append(out[-1]+(2.0*t-b))
    return out

def donchian(h,l,look):
    return max(h[-look:]), min(l[-look:])