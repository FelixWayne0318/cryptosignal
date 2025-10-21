from statistics import median
from ats_core.sources.binance import get_open_interest_hist

def fetch_oi_hourly(symbol, limit=200):
    rows = get_open_interest_hist(symbol, period="1h", limit=limit)
    oi=[]
    for x in rows:
        v = x.get("sumOpenInterest") or x.get("openInterest")
        if v is None: continue
        try: oi.append(float(v))
        except: pass
    return oi

def pct(a,b,den): return (a-b)/den if den>1e-12 else 0.0

def pct_series(oi, look=24):
    n=len(oi); 
    if n<=look: return []
    den = median(oi[max(0,n-168):])
    out=[]
    for i in range(look,n): out.append(pct(oi[i],oi[i-look],den))
    return out