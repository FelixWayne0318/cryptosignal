import os, json, math, time
from statistics import median
from ats_core.cfg import CFG
from ats_core.sources.tickers import all_24h
from ats_core.sources.klines import klines_1h, split_ohlcv
from ats_core.sources.oi import fetch_oi_hourly

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
FN = os.path.join(DATA, "overlay_today.json")

def _robust_z(xlist):
    if len(xlist)<30: return 0.0
    med = median(xlist)
    mad = median([abs(x-med) for x in xlist]) or 1e-9
    return (xlist[-1]-med)/(1.4826*mad)

def _z_volume_1h(sym):
    rows = klines_1h(sym, 200)
    _,_,_,_,v,_,_ = split_ohlcv(rows)
    if len(v)<30: return 0.0, 0.0
    logv=[math.log(max(1e-9,x)) for x in v]
    return _robust_z(logv), v[-1]

def _is_new_contract(sym):
    rows = klines_1h(sym, 48)
    return len(rows)<48  # <2天 视作新

def _oi_1h_pct(sym):
    oi = fetch_oi_hourly(sym, 30)
    if len(oi)<2: return 0.0
    den = median(oi)
    return (oi[-1]-oi[-2])/max(1e-12,den)

def update_overlay_universe(base_syms):
    par = CFG.get("overlay", default={})
    t24 = { x["symbol"]:x for x in all_24h() }
    # load current overlay
    cur={}
    if os.path.isfile(FN):
        try: cur = json.load(open(FN,'r',encoding='utf-8'))
        except: cur={}
    now=int(time.time())
    added={}
    for sym in base_syms:
        if not sym.endswith("USDT"): continue
        x = t24.get(sym); if_not = False
        if x is None: continue
        quote=float(x["quoteVolume"]); chg=float(x["priceChangePercent"])
        conds=[]
        # (1) new contract
        if _is_new_contract(sym): conds.append("new")
        # (2) z_vol_1h and hour quote
        zv, v1h = _z_volume_1h(sym)
        if zv>=par["z_volume_1h_threshold"] and quote>=par["min_hour_quote_usdt"]:
            conds.append("zv1h")
        # or z24>=2 and 24h quote >=20M
        # we approximate z24 by priceChangePercent robust check
        if abs(chg)>=200.0 and quote>=par["z24_and_24h_quote"]["quote"]:
            conds.append("z24x")
        # (3) OI_1h%顺势：大币阈值/小币阈值
        oi1h = _oi_1h_pct(sym)
        big = sym in CFG.get("majors", default=["BTCUSDT","ETHUSDT"])
        if (big and oi1h>=par["oi_1h_pct_big"]) or ((not big) and oi1h>=par["oi_1h_pct_small"]):
            conds.append("oi1h")
        # (4) 三同向快变（近 1h）：简化检查 ΔP、v5/v20、CVD_mix（以 taker-buy 比例近似）
        # 这里用 ΔP 与 v5/v20 快速代理
        if abs(chg)/100.0 >= par["triple_sync"]["dP1h_abs_pct"]:
            conds.append("triple")
        if conds:
            added[sym]={
                "when": now,
                "why": conds,
                "hot": 0.5*max(0.0,zv) + 0.3*abs(chg)/100.0 + 0.2*max(0.0,oi1h)*math.exp(-(0)/ (par["hot_decay_hours"]*3600.0))
            }
    # merge (only grow)
    for k,v in added.items():
        cur[k]=v
    with open(FN,'w',encoding='utf-8') as f:
        json.dump(cur,f,ensure_ascii=False,indent=2)
    # return sorted by hot
    arr=[(k,v["hot"]) for k,v in cur.items()]
    arr.sort(key=lambda x: -x[1])
    return [k for k,_ in arr]