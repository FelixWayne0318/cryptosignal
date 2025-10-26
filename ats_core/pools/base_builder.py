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
    # 修复：从 overlay 配置读取参数
    overlay_params = CFG.get("overlay", default={})
    base_params = CFG.get("base", default={})

    # 安全地获取黑名单
    blacklist = getattr(CFG, 'blacklist', []) or []

    # 获取参数
    min_quote = base_params.get("min_quote_volume", 5000000)
    min_z24 = base_params.get("min_z24_abs", 0.5)
    min_pool_size = base_params.get("min_pool_size", 20)  # 保底数量

    t = all_24h()
    base=[]
    top_liquid = []  # 记录流动性Top币种（用于保底）

    for x in t:
        try:
            sym=x["symbol"]
            q=float(x["quoteVolume"])
            if not sym.endswith("USDT"): continue
            if q < min_quote: continue
            if sym in blacklist: continue

            # 记录高流动性币种（用于保底）
            if q > min_quote:
                top_liquid.append({"symbol":sym,"quote":q})

            z24=_robust_z24(sym)
            if z24 is None: continue

            # 放宽：z24绝对值>=0.5（原来1.0）
            if abs(z24) >= min_z24:
                base.append({"symbol":sym,"z24":z24,"quote":q})
        except: pass

    # 保底机制：如果base太少，添加Top流动性币种
    if len(base) < min_pool_size:
        top_liquid = sorted(top_liquid, key=lambda x: -x["quote"])
        for item in top_liquid:
            if len(base) >= min_pool_size:
                break
            if item["symbol"] not in [b["symbol"] for b in base]:
                # 添加流动性币种，z24设为0（中性）
                base.append({"symbol":item["symbol"],"z24":0.0,"quote":item["quote"]})

    base = sorted(base, key=lambda x: -x["quote"])
    with open(os.path.join(DATA,"base_pool.json"),"w",encoding="utf-8") as f:
        json.dump(base,f,ensure_ascii=False,indent=2)
    return [x["symbol"] for x in base]