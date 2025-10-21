import os, json, math
from statistics import median
from ats_core.cfg import CFG
from ats_core.sources.tickers import all_24h
from ats_core.sources.klines import klines_1h, split_ohlcv

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
os.makedirs(DATA, exist_ok=True)

def _robust_z24(symbol):
    rows = klines_1h(symbol, 800)  # ~33d
    _,_,_,c,_,_,_ = split_ohlcv(rows)
    if len(c)<25: return None
    # build r24 series
    r=[]
    for i in range(24,len(c)):
        r.append(math.log(c[i]/c[i-24]))
    if len(r)<30: return None
    med = median(r)
    mad = median([abs(x-med) for x in r]) or 1e-9
    z = (r[-1]-med)/(1.4826*mad)
    return z

def build_base_universe():
    params = CFG.get("universe", default={})
    t = all_24h()
    base=[]
    for x in t:
        try:
            sym=x["symbol"]
            q=float(x["quoteVolume"])
            if not sym.endswith("USDT"): continue
            if q < params.get("min_24h_quote_usdt", 1e7): continue
            if sym in CFG.blacklist: continue
            z24=_robust_z24(sym)
            if z24 is None: continue
            if abs(z24) >= params.get("robust_z24_abs_threshold",1.0):
                base.append({"symbol":sym,"z24":z24,"quote":q})
        except: pass
    base = sorted(base, key=lambda x: -x["quote"])
    with open(os.path.join(DATA,"base_pool.json"),"w",encoding="utf-8") as f:
        json.dump(base,f,ensure_ascii=False,indent=2)
    return [x["symbol"] for x in base]
if __name__=="__main__":
    build_base_universe()
