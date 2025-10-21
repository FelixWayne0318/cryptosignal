# -*- coding: utf-8 -*-
"""
ATS Analyzer · v1.5 one-off tester (Prime/Watch) — strictly per v1.5
- Stdlib only. No external deps.
- Usage:
    python -m app.oneoff_v15 EVAAUSDT --send
    python -m app.oneoff_v15 COAIUSDT --send
- Env (.env in CWD or ~/ats-analyzer/.env):
    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_CHAT_ID=...
    TZ=UTC
    BIGCAP_OVERRIDE=big|small   # optional, override big/small cap
Notes:
- "Big/Small cap" fallback: if no daily list, rank by current 24h notional (Top30=big).
- Funding extreme = the ONLY strategy-level hard veto.
"""

import os, sys, json, math, time, datetime, statistics
import urllib.request, urllib.parse

# -------------------- ENV --------------------
def load_env():
    for path in (os.path.join(os.getcwd(), ".env"),
                 os.path.expanduser("~/ats-analyzer/.env")):
        if not os.path.isfile(path): continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    s=line.strip()
                    if not s or s.startswith("#") or "=" not in s: continue
                    k,v = s.split("=",1)
                    k=k.strip(); v=v.strip()
                    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                        v=v[1:-1]
                    os.environ[k]=v
        except Exception:
            pass

def env(k, d=None): return os.environ.get(k, d)

# -------------------- HTTP --------------------
def http_json(url, params=None, timeout=15):
    if params: url += ("?" + urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())

# -------------------- TA helpers --------------------
def ema(arr, n):
    k = 2.0/(n+1.0); s = None; out = []
    for x in arr:
        s = x if s is None else (x*k + s*(1-k))
        out.append(s)
    return out

def atr_ema(h,l,c,n=14):
    trs=[h[0]-l[0]]
    for i in range(1,len(c)):
        trs.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    # EMA ATR
    k=2.0/(n+1.0); s=None; out=[]
    for tr in trs:
        s = tr if s is None else (tr*k + s*(1-k))
        out.append(s)
    return out

def tr_median(h,l,c,n=14):
    trs=[]
    for i in range(0,len(c)):
        if i==0: trs.append(h[i]-l[i])
        else: trs.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    from statistics import median
    out=[]
    win=[]
    for i,tr in enumerate(trs):
        win.append(tr)
        if len(win)>n: win.pop(0)
        out.append(median(win))
    return out

def rsq(y, window):
    if len(y)<window: return 0.0
    ys=y[-window:]; xs=list(range(window))
    xm=sum(xs)/window; ym=sum(ys)/window
    num=sum((xs[i]-xm)*(ys[i]-ym) for i in range(window))
    denx=sum((x-xm)**2 for x in xs); deny=sum((v-ym)**2 for v in ys)
    if denx<=0 or deny<=0: return 0.0
    r=num/((denx*deny)**0.5)
    return r*r

def chop14(h,l,c):
    if len(c)<15: return 100.0
    tr=[]
    for i in range(1,len(c)):
        tr.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    tr14=sum(tr[-14:])
    hh=max(h[-14:]); ll=min(l[-14:])
    rng=max(1e-12, hh-ll)
    return 100.0*math.log10(tr14/rng)/math.log10(14.0)

def vboost_last123_over_sma20(vol):
    if len(vol)<20: return 1.0
    sma20=sum(vol[-20:])/20.0
    best=0.0
    for k in (1,2,3):
        best=max(best, sum(vol[-k:])/max(1e-12,sma20))
    return min(best, 3.0)

def vroc_abs(vol):
    if len(vol)<21: return 0.0
    sma20=sum(vol[-21:-1])/20.0
    prev=math.log(max(1e-12, sma20))
    cur=math.log(max(1e-12, sum(vol[-20:])/20.0))
    return abs(cur-prev)

def s_curve(x, lo, hi):
    if lo<hi:
        if x<=lo: return 0.0
        if x>=hi: return 1.0
        return (x-lo)/(hi-lo)
    else:
        # descending
        if x>=lo: return 0.0
        if x<=hi: return 1.0
        return (lo-x)/max(1e-12,(lo-hi))

def pct(x, a, b):
    # map x in [a,b] to [0,1]
    if b==a: return 0.0
    t=(x-a)/(b-a)
    return 0.0 if t<0 else (1.0 if t>1 else t)

def clip(x,a,b): return a if x<a else (b if x>b else x)

# -------------------- ZigZag & SQ --------------------
def zigzag_swings(h,l,c, atr_now, theta, allow_last_half=True):
    """
    threshold theta in absolute price (theta * ATR reference passed in)
    Return list of swings: [(idx, price, 'H'/'L')]
    """
    n=len(c)
    if n<5: return []
    # start from last pivot candidates
    swings=[]
    # decide initial direction by last few bars
    i=0
    # We'll build on closes but guard by highs/lows
    last_pivot_idx=0
    last_pivot_price=c[0]
    dirn=0  # 1 up, -1 down, 0 unknown
    T=theta
    for i in range(1,n):
        diff=c[i]-last_pivot_price
        if dirn>=0 and diff>=T:
            # up swing confirmed
            swings.append((last_pivot_idx,last_pivot_price,'L'))
            last_pivot_idx=i; last_pivot_price=c[i]; dirn=-1
        elif dirn<=0 and diff<=-T:
            swings.append((last_pivot_idx,last_pivot_price,'H'))
            last_pivot_idx=i; last_pivot_price=c[i]; dirn=1
        else:
            # extend pivot extreme
            if dirn>=0:
                if c[i]<last_pivot_price: last_pivot_idx=i; last_pivot_price=c[i]
            if dirn<=0:
                if c[i]>last_pivot_price: last_pivot_idx=i; last_pivot_price=c[i]
    # close last
    if swings:
        last_type='H' if swings[-1][2]=='L' else 'L'
        swings.append((last_pivot_idx,last_pivot_price,last_type))
    else:
        # no swings found, just create a tiny one based on range
        swings=[(0,c[0],'L'), (n-1,c[-1],'H' if c[-1]>c[0] else 'L')]

    # Allow early reversal for the last leg at 0.5*theta
    if allow_last_half and len(swings)>=2:
        i0,p0,t0=swings[-2]
        i1,p1,t1=swings[-1]
        # If last leg magnitude < theta but > 0.5 theta, keep it; else compress
        if abs(p1-p0) < 0.5*T:
            swings.pop()

    return swings[-12:]  # last up to 12 pivots sufficient

def sq_score(h,l,c, ema30, atr_now, theta, side_long, fifteen_ctx):
    """
    Compute SQ (0-100) per v1.5: consistency, ICR, retracement depth, tempo, not-overextended, 15m micro confirm
    fifteen_ctx: dict with keys 'micro_ok' (bool), 'micro_boom_veto' (bool)
    """
    swings=zigzag_swings(h,l,c, atr_now, theta, allow_last_half=True)
    if len(swings)<3:
        base=50.0
        micro=5.0 if fifteen_ctx.get("micro_ok", False) else 0.0
        over = abs(c[-1]-ema30[-1])/max(1e-12,atr_now)
        pos = 1.0 if over<=0.8 else 0.5
        return clip(base*pos + micro, 0, 100)

    # Build HH/HL or LL/LH consistency
    # Take last 6 swings
    seq=swings[-6:]
    highs=[p for i,p,t in seq if t=='H']
    lows =[p for i,p,t in seq if t=='L']
    cons=0.0
    if side_long:
        # want HH or HL
        for k in range(1,len(highs)):
            if highs[k]>highs[k-1]: cons+=1
        for k in range(1,len(lows)):
            if lows[k]>lows[k-1]: cons+=1
        denom=max(1, (len(highs)-1)+(len(lows)-1))
    else:
        for k in range(1,len(highs)):
            if highs[k]<highs[k-1]: cons+=1
        for k in range(1,len(lows)):
            if lows[k]<lows[k-1]: cons+=1
        denom=max(1, (len(highs)-1)+(len(lows)-1))
    cons_score = 100.0 * cons/denom

    # Impulse vs Correction ratio (ICR): magnitude of trend legs / pullbacks
    legs=[]
    for k in range(1,len(seq)):
        legs.append(abs(seq[k][1]-seq[k-1][1]))
    if not legs: legs=[0.0]
    # classify legs alternately; trend legs approx = ones aligned with side
    trend_legs = legs[::2] if ((side_long and seq[0][2]=='L') or ((not side_long) and seq[0][2]=='H')) else legs[1::2]
    corr_legs  = legs[1::2] if trend_legs is legs[::2] else legs[::2]
    tavg = sum(trend_legs)/max(1,len(trend_legs))
    cavg = sum(corr_legs )/max(1,len(corr_legs))
    icr = tavg/max(1e-12,cavg)
    icr_score = pct(icr, 1.0, 2.0)*100.0  # 1.0→0分，≥2.0→100分

    # Retracement depth of last pullback (Fib sweet spot 0.38–0.62)
    if len(seq)>=3:
        a=abs(seq[-1][1]-seq[-2][1]); b=abs(seq[-2][1]-seq[-3][1])
        depth = min(a,b)/max(a,b) if max(a,b)>0 else 0.0
    else:
        depth=0.5
    depth_score = (1.0 - (abs(depth-0.5)/0.12))  # 0.38~0.62 best
    depth_score = clip(depth_score,0.0,1.0)*100.0

    # Tempo (uniform swing lengths)
    idx=[i for i,p,t in seq]
    seg=[idx[k]-idx[k-1] for k in range(1,len(idx))]
    if len(seg)>=2:
        mean=sum(seg)/len(seg); var=sum((x-mean)**2 for x in seg)/len(seg)
        tempo = 1.0/(1.0+math.sqrt(var)/max(1e-6,mean))
    else:
        tempo=0.6
    tempo_score = clip(tempo,0.0,1.0)*100.0

    # Position not over-extended
    over = abs(c[-1]-ema30[-1])/max(1e-12,atr_now)
    pos_score = 100.0 if over<=0.8 else 50.0

    micro_score = 100.0 if fifteen_ctx.get("micro_ok", False) else 0.0

    # weights per v1.5 narrative
    score = (0.35*cons_score + 0.25*icr_score + 0.15*depth_score +
             0.10*tempo_score + 0.10*pos_score + 0.05*micro_score)
    return clip(score, 0.0, 100.0)

# -------------------- OI / Funding --------------------
def oi_series(symbol, limit=200):  # hourly
    # https://www.binance.com/en/binance-api/post/futures/data/openInterestHist
    # For USDT perpetuals:
    url="https://fapi.binance.com/futures/data/openInterestHist"
    js=http_json(url, {"symbol":symbol, "period":"1h", "limit":limit})
    # returns list newest first? On futures: usually oldest first. Normalize by ts.
    js=sorted(js, key=lambda x:int(x.get("timestamp",0)))
    oi=[float(x["sumOpenInterest"]) for x in js]
    ts=[int(x["timestamp"]) for x in js]
    return ts, oi

def funding_series(symbol, limit=60):
    url="https://fapi.binance.com/fapi/v1/fundingRate"
    js=http_json(url, {"symbol":symbol, "limit":limit})
    js=sorted(js, key=lambda x:int(x.get("fundingTime",0)))
    rates=[float(x["fundingRate"]) for x in js]
    ts=[int(x["fundingTime"]) for x in js]
    return ts, rates

def robust_z(arr):
    if not arr: return 0.0
    med=statistics.median(arr)
    mad=statistics.median([abs(x-med) for x in arr]) if len(arr)>1 else 0.0
    if mad<=1e-12: return 0.0
    return (arr[-1]-med)/(1.4826*mad+1e-12)

# -------------------- CVD (simple synthetic) --------------------
def cvd_slope_per_h(base_vol, taker_buy_base, notional, hours=6):
    cvd=[0.0]
    for b,t in zip(base_vol, taker_buy_base):
        cvd.append(cvd[-1] + (2.0*t - b))
    if len(cvd)<=hours: return 0.0
    dn=sum(notional[-hours:])
    return (cvd[-1]-cvd[-hours-1]) / max(1e-12, dn)

# -------------------- Big/Small cap --------------------
def is_bigcap(symbol):
    override=env("BIGCAP_OVERRIDE","").lower().strip()
    if override=="big": return True
    if override=="small": return False
    # fallback: rank current 24h notional Top30
    tickers=http_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    vals=[]
    for t in tickers:
        s=t.get("symbol","")
        if not s.endswith("USDT"): continue
        try:
            qv=float(t.get("quoteVolume","0"))
        except:
            qv=0.0
        vals.append((qv,s))
    vals.sort(reverse=True)
    top=set([s for _,s in vals[:30]])
    return symbol in top

# -------------------- Prior (BTC/ETH) --------------------
def prior_up_from_btc_eth():
    def slope_atr(sym, interval):
        k = http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":sym,"interval":interval,"limit":200})
        c=[float(x[4]) for x in k]
        h=[float(x[2]) for x in k]; l=[float(x[3]) for x in k]
        atr=atr_ema(h,l,c,14)[-1]
        ema30=ema(c,30); s=(ema30[-1]-ema30[-7])/6.0
        return s/max(1e-12,atr)
    try:
        s1=(slope_atr("BTCUSDT","1h")+slope_atr("ETHUSDT","1h"))/2.0
        s4=(slope_atr("BTCUSDT","4h")+slope_atr("ETHUSDT","4h"))/2.0
        x=0.5*s1+0.5*s4  # overall tilt
        # map to [0.42,0.58]:
        shift = clip(0.08*math.tanh(x/0.6), -0.08, 0.08)
        return clip(0.5+shift, 0.42, 0.58)
    except Exception:
        return 0.5

# -------------------- Entry/SL/TP per v1.5 --------------------
def price_plan(side_long, price, ema10, ema30, atr_now, h, l):
    ext = min(abs(price-ema30)/max(1e-12,atr_now), 0.6)
    delta = (0.02 + 0.10*ext)*atr_now
    if side_long:
        entry_lo = ema10 - delta
        entry_hi = ema10 + 0.01*atr_now
        # last pivot low approx
        piv = min(l[-12:])
        sl = max(piv - 0.10*atr_now, ((entry_lo+entry_hi)/2.0) - 1.8*atr_now)
        hh = max(h[-72:])
        R = ((entry_lo+entry_hi)/2.0) - sl
        tp1 = (entry_lo+entry_hi)/2.0 + 1.0*R
        room = (hh - (entry_lo+entry_hi)/2.0)/max(1e-12,atr_now)
        tp2 = (entry_lo+entry_hi)/2.0 + min(2.5*R, max(0.0, hh*0.998 - (entry_lo+entry_hi)/2.0))
    else:
        entry_lo = ema10 - 0.01*atr_now
        entry_hi = ema10 + delta
        piv = max(h[-12:])
        sl = min(piv + 0.10*atr_now, ((entry_lo+entry_hi)/2.0) + 1.8*atr_now)
        ll = min(l[-72:])
        R = sl - ((entry_lo+entry_hi)/2.0)
        tp1 = (entry_lo+entry_hi)/2.0 - 1.0*R
        room = (((entry_lo+entry_hi)/2.0) - ll)/max(1e-12,atr_now)
        tp2 = (entry_lo+entry_hi)/2.0 - min(2.5*R, max(0.0, (entry_lo+entry_hi)/2.0 - ll*1.002))
    return entry_lo, entry_hi, sl, tp1, tp2, room

# -------------------- 15m micro confirmation --------------------
def micro_15m(side_long, symbol, atr1h):
    k15=http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":symbol,"interval":"15m","limit":100})
    c=[float(x[4]) for x in k15]; h=[float(x[2]) for x in k15]; l=[float(x[3]) for x in k15]; v=[float(x[5]) for x in k15]
    ema10=ema(c,10); # 15m EMA10
    last6=c[-6:]
    last6_ema=[v for v in ema10[-6:]]
    # 回踩稳：近6根≥4根在 EMA10 同侧；下穿≤0.15×ATR(1h) 且 ≤2 根收复
    on_side=0
    for px,em in zip(last6,last6_ema):
        if side_long and px>=em: on_side+=1
        if (not side_long) and px<=em: on_side+=1
    cond1 = on_side>=4
    # 下穿幅度估计
    under = 0
    for px,em in zip(last6,last6_ema):
        if side_long and px<em and (em-px)>(0.15*atr1h): under+=1
        if (not side_long) and px>em and (px-em)>(0.15*atr1h): under+=1
    cond1 = cond1 and (under<=2)

    # 微量能：v3/v20 in [1.1,1.6] 且 |ΔV|_15m in [0.12,0.45]
    if len(v)<21:
        cond2=False
    else:
        v3=sum(v[-3:]); v20=sum(v[-20:])
        v3v20 = v3/max(1e-12, v20/20.0)
        v_sma_prev = sum(v[-21:-1])/20.0
        dV = abs(math.log(max(1e-12,v20/20.0)) - math.log(max(1e-12,v_sma_prev)))
        cond2 = (1.1<=v3v20<=1.6) and (0.12<=dV<=0.45)

    # 主动性斜率：近4根 15m CVD斜率与方向同号
    tb=[float(x[9]) for x in k15]; base=[float(x[5]) for x in k15]
    cvd=[0.0]
    for b,t in zip(base,tb):
        cvd.append(cvd[-1]+(2.0*t-b))
    ok_cnt=0
    for k in range(-4,0):
        sl=cvd[k]-cvd[k-1]
        if side_long and sl>=0: ok_cnt+=1
        if (not side_long) and sl<=0: ok_cnt+=1
    cond3 = ok_cnt>=3

    # 微结构：近10根 HL/LH≥1，未破最近微枢轴（允许 ≤0.05×ATR(1h)）
    last10=h[-10:]; last10l=l[-10:]; micro_ok=False
    # 简化近端枢轴：最近高/低
    ph=max(last10); pl=min(last10l)
    broke=False
    if side_long:
        # 不能破 pl 太多
        broke = (pl < (min(last10l)+0.0)) and ((min(last10l)-pl) > 0.05*atr1h)
    else:
        broke = (ph > (max(last10)+0.0)) and ((ph-max(last10)) > 0.05*atr1h)
    # HL/LH 检测
    hl_lh=False
    for i in range(2,10):
        if side_long and last10l[i]>last10l[i-1]>=last10l[i-2]: hl_lh=True; break
        if (not side_long) and last10[i-2]>=last10[i-1]>last10[i]: hl_lh=True; break
    cond4 = (not broke) and hl_lh

    # 反爆发否决：单根15m |ΔP| > 0.8×ATR(15m) 或 v3/v20 > 2.0
    atr15 = atr_ema(h,l,c,14)[-1]
    boom=False
    for k in range(-6,0):
        if abs(c[k]-c[k-1])>0.8*atr15: boom=True; break
    if len(v)>=20:
        boom = boom or ((sum(v[-3:]) / max(1e-12, sum(v[-20:])/20.0)) > 2.0)

    micro_ok = sum([cond1,cond2,cond3,cond4])>=2
    return {"micro_ok":micro_ok, "micro_boom_veto":boom,
            "v3v20": (sum(v[-3:])/max(1e-12,sum(v[-20:])/20.0)) if len(v)>=20 else 0.0}

# -------------------- Telegram --------------------
def tg_send(html):
    token=env("TELEGRAM_BOT_TOKEN"); chat=env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[WARN] TELEGRAM env missing; skip send"); return
    data=urllib.parse.urlencode({"chat_id":chat,"text":html,
                                 "parse_mode":"HTML","disable_web_page_preview":"true"}).encode()
    req=urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    urllib.request.urlopen(req, timeout=12).read()

# -------------------- Main Scoring (v1.5 exact) --------------------
def trend_score(side_long, slopeATR, R2, ema_order_ok, bg_same):
    sc=0
    # slope block up to 60
    if side_long:
        sc += 60 if slopeATR>=0.30 else (40 if slopeATR>=0.15 else (20 if slopeATR>=0.05 else 0))
    else:
        sc += 60 if slopeATR<=-0.30 else (40 if slopeATR<=-0.15 else (20 if slopeATR<=-0.05 else 0))
    # R2 up to 30
    sc += int(30*clip((R2-0.45)/0.50, 0, 1))
    # ema order + bg same small bonus
    if ema_order_ok: sc+=5
    if bg_same: sc+=5
    return clip(sc,0,100)

def accel_score(side_long, dslope, dcvd):
    # weak gate already in s_curve
    if side_long:
        s1=s_curve(dslope, 0.02, 0.08)
        s2=s_curve(dcvd , 0.02, 0.06)
    else:
        s1=s_curve(-dslope, 0.02, 0.08)
        s2=s_curve(-dcvd , 0.02, 0.06)
    return int(100*clip(0.6*s1+0.4*s2,0,1))

def volume_score(side_long, vboost, vrocabs, vol_hist):
    if side_long:
        # 1.2~1.7 best; cap at 3.0
        return int(100*clip((vboost-1.2)/(1.7-1.2),0,1))
    else:
        # prefer ≤1.15 or "peak>2.0 then low"
        low = 1.0 if vboost<=1.15 else 0.0
        peak = 0.0
        if len(vol_hist)>=30:
            sma20=sum(vol_hist[-21:-1])/20.0
            recent_peak=max(sum(vol_hist[k:k+3])/max(1e-12,sma20) for k in range(len(vol_hist)-25,len(vol_hist)-2))
            if recent_peak>2.0 and vboost<1.4: peak=0.8
        sc = max(low, peak)
        return int(100*sc)

def oi_score(side_long, oi_ts, oi_vals, c):
    if len(oi_vals)<26: return 50  # neutral if insufficient
    # OI_24h change vs 7d median OI (normalize)
    median_7d = statistics.median(oi_vals[-7*24:]) if len(oi_vals)>=7*24 else statistics.median(oi_vals[-48:])
    change_24 = (oi_vals[-1]-oi_vals[-25])/max(1e-12, median_7d)
    if side_long:
        # 5%~18% best
        if change_24<=0.0: return 40
        return int(100*pct(change_24, 0.05, 0.18))
    else:
        # (price down + OI up) >= 8/12h, or OI_24h in [-25%,-8%]
        # price down + OI up pattern:
        cnt=0
        for k in range(-12,0):
            if c[k]<c[k-1] and oi_vals[k]>oi_vals[k-1]: cnt+=1
        pat = cnt>=8
        drop = (-0.25)<=change_24<=(-0.08)
        if pat or drop: return 80
        return 40

def env_score(chop, room):
    # CHOP↓ ≤52 good; Room ≥0.5 × ATR add
    sc = int(100*clip((52.0-chop)/12.0,0,1))
    if room>=0.5: sc = min(100, sc+10)
    return sc

def funding_extreme_veto(symbol, bigcap):
    ts, fr = funding_series(symbol, limit=60)
    if len(fr)<12:  # insufficient → do not veto
        return False, 0.0
    z = robust_z(fr[-30:] if len(fr)>=30 else fr)
    # extreme rules:
    if bigcap and abs(z)>=2.3: return True, z
    if (not bigcap) and abs(z)>=2.0: return True, z
    return False, z

def format_prime_v15(sym, side_long, prob, price, entry_lo, entry_hi, sl, tp1, tp2,
                     T,S,V,A,O,E, prior, Q, chop, room):
    side_text = "🟩 做多" if side_long else "🟥 做空"
    prob_txt = f"{int(round(prob*100))}%"
    col = lambda x: "🟢" if x>=80 else ("🟨" if x>=65 else ("🟧" if x>=50 else "🟥"))
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")
    return (
f"<b>{side_text} {prob_txt} · 8h · {sym}</b>\n"
f"现价 <code>{price:.6g}</code>\n\n"
f"<b>计划</b>\n"
f"入场 <code>{entry_lo:.6g} – {entry_hi:.6g}</code>\n"
f"止损 <code>{sl:.6g}</code>\n"
f"止盈 <code>TP1=+1R   TP2≤2.5R（靠近对手位）</code>\n\n"
f"<b>六维证据</b>\n"
f"• 趋势 {col(T)} {T} —— 斜率 & 1h/4h 同侧\n"
f"• 结构 {col(S)} {S} —— ZigZag 连贯；不过度\n"
f"• 量能 {col(V)} {V} —— v5/v20 & 变化率\n"
f"• 加速 {col(A)} {A} —— Δ斜率 & ΔCVD\n"
f"• 持仓 {col(O)} {O} —— OI 24h/1h\n"
f"• 环境 {col(E)} {E} —— CHOP/Room\n\n"
f"<b>环境</b> prior={prior:.2f} · Q={Q:.2f} · CHOP={chop:.1f} · Room={room:.2f}×ATR\n"
f"<b>失效</b> ① 回收入场下沿且 v5/v20&lt;1 ② CVD 连续 2h 反向\n"
f"<code>UTC {now} · 有效 8h 或触发失效</code>"
    )

def format_watch_v15(sym, side_long, prob, price, ref_lo, ref_hi, prior, Q, chop):
    side_text = "👀 观察 多" if side_long else "👀 观察 空"
    prob_txt = f"{int(round(prob*100))}%"
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")
    return (
f"<b>{side_text} {prob_txt} · 8h · {sym}</b>\n"
f"现价 <code>{price:.6g}</code>  参考带（非指令）<code>{ref_lo:.6g} – {ref_hi:.6g}</code>\n\n"
f"<b>迹象</b> 趋势/结构/量能/加速/CHOP 组合临界，关注 15m 回踩与微量能\n"
f"<b>环境</b> prior={prior:.2f} · Q={Q:.2f} · CHOP={chop:.1f}\n"
f"<code>UTC {now} · 观察 4h</code>"
    )

def analyze_symbol(sym):
    # 1) 1h/4h klines
    k1 = http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":sym,"interval":"1h","limit":300})
    if len(k1)<180: raise RuntimeError("样本不足(1h)<180")
    o=[float(x[1]) for x in k1]; h=[float(x[2]) for x in k1]; l=[float(x[3]) for x in k1]
    c=[float(x[4]) for x in k1]; v=[float(x[5]) for x in k1]
    q=[float(x[7]) for x in k1]; tb=[float(x[9]) for x in k1]
    price=c[-1]
    atr1=atr_ema(h,l,c,14); atr_now=atr1[-1]
    if atr_now<=0:
        atr1=tr_median(h,l,c,14); atr_now=atr1[-1]

    ema5=ema(c,5); ema10=ema(c,10); ema30=ema(c,30)
    slope30=(ema30[-1]-ema30[-7])/6.0
    slopeATR=slope30/max(1e-12,atr_now)
    R2=rsq(ema30,21)

    # 4h background
    k4=http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":sym,"interval":"4h","limit":200})
    c4=[float(x[4]) for x in k4]
    ema30_4h=ema(c4,30); slope4=(ema30_4h[-1]-ema30_4h[-7])/6.0
    bg_same = (slope4>0 and slopeATR>0) or (slope4<0 and slopeATR<0)

    # volume features
    vboost=vboost_last123_over_sma20(v)
    vroc=vroc_abs(v)

    # acceleration: Δslope, ΔCVD(6h)
    slope6  = (ema30[-1]-ema30[-7])/6.0
    slope12 = (ema30[-1]-ema30[-13])/12.0
    dslope  = (slope6 - slope12)/max(1e-12, atr_now)
    dcvd = cvd_slope_per_h(v, tb, q, hours=6)

    # OI
    oi_ts, oi_vals = oi_series(sym, limit=200)

    # funding extreme veto
    bigcap = is_bigcap(sym)
    veto, fz = funding_extreme_veto(sym, bigcap)

    # 15m micro context
    micro = micro_15m(side_long=True,  symbol=sym, atr1h=atr_now)  # compute once, reuse for both sides in SQ
    micro_short = micro_15m(side_long=False, symbol=sym, atr1h=atr_now)

    # Entry/SL/TP require side → compute later per side

    # Scoring per side
    def side_pipeline(side_long):
        ema_order_ok = (ema5[-1]>ema10[-1]>ema30[-1]) if side_long else (ema5[-1]<ema10[-1]<ema30[-1])
        T = trend_score(side_long, slopeATR, R2, ema_order_ok, bg_same)
        A = accel_score(side_long, dslope, dcvd)
        # provisional micro ctx for structure
        ctx = micro if side_long else micro_short
        theta = (0.35 if bigcap else 0.40)*atr_now  # Overlay/NewCoin调节在日程流程，这里 one-off使用基准；不简化其他逻辑
        S = int(round(sq_score(h,l,c, ema30[-1], atr_now, theta, side_long, ctx)))
        V = volume_score(side_long, vboost, vroc, v)
        O = oi_score(side_long, oi_ts, oi_vals, c)
        # temp entry for room/env
        e_lo,e_hi,sl,tp1,tp2,room = price_plan(side_long, price, ema10[-1], ema30[-1], atr_now, h, l)
        E = env_score(chop14(h,l,c), room)
        up = 0.25*T + 0.15*A + 0.15*S + 0.20*V + 0.15*O + 0.10*E
        return int(round(T)),int(round(S)),int(round(V)),int(round(A)),int(round(O)),int(round(E)), up/100.0, (e_lo,e_hi,sl,tp1,tp2,room)

    # Calculate both sides
    T_l,S_l,V_l,A_l,O_l,E_l, UpScore, plan_l = side_pipeline(True)
    T_s,S_s,V_s,A_s,O_s,E_s, DnScore, plan_s = side_pipeline(False)

    # Edge
    Edge = UpScore - DnScore  # [-1,1]

    # Prior & Q
    prior = prior_up_from_btc_eth()
    # Q: sample coverage + overextension + non-crowding + micro status
    over = abs(c[-1]-ema30[-1])/max(1e-12,atr_now)
    Q = 1.0
    # samples
    if len(k1)<240: Q-=0.05
    if len(oi_vals)<48: Q-=0.05
    if len(funding_series(sym,limit=20)[1])<12: Q-=0.05
    # over-extended penalty
    if over>0.8: Q-=0.05
    # micro confirm aids when consistent with side later
    # clamp
    Q=clip(Q,0.6,1.0)

    # Probabilities
    P_up = clip(prior + 0.35*Edge*Q, 0.0, 1.0)
    P_dn = 1.0 - P_up

    # Decide side by higher prob
    side_long = (P_up>=P_dn)
    T,S,V,A,O,E   = (T_l,S_l,V_l,A_l,O_l,E_l) if side_long else (T_s,S_s,V_s,A_s,O_s,E_s)
    e_lo,e_hi,sl,tp1,tp2,room = plan_l if side_long else plan_s
    prob = P_up if side_long else P_dn

    # Publish thresholds (strict v1.5)
    dims_ok = sum([x>=65 for x in (T,S,V,A,O,E)])
    # CHOP>55 or structure切换≥2 → 总发布阈+5（此处已体现在 S/E 分中；保持固定发布线）
    publish_prime = (prob>=0.62 and dims_ok>=4)
    publish_watch = (0.58<=prob<0.62)

    # 资金费率极端 → 硬否决
    if veto:
        return {
            "symbol": sym, "veto": True, "funding_z": float(fz),
            "reason": "资金费率极端（唯一一票否决）"
        }

    # 15m 反爆发否决：本轮不发（冷却），但返回可读信息
    micro_ctx = micro if side_long else micro_short
    if micro_ctx.get("micro_boom_veto", False):
        publish_prime=False
        publish_watch=False

    # Decide output template
    result = {
        "symbol": sym, "side_long": side_long, "prob": float(prob),
        "price": price, "entry_lo": e_lo, "entry_hi": e_hi, "sl": sl, "tp1": tp1, "tp2": tp2,
        "T":T, "S":S, "V":V, "A":A, "O":O, "E":E,
        "prior": float(prior), "Q": float(Q),
        "chop": float(chop14(h,l,c)), "room": float(room),
        "publish_prime": publish_prime, "publish_watch": publish_watch,
        "micro_ok": micro_ctx.get("micro_ok", False),
        "micro_boom_veto": micro_ctx.get("micro_boom_veto", False),
        "funding_veto": False,
    }
    return result

def main():
    load_env()
    if len(sys.argv)<2:
        print("Usage: python -m app.oneoff_v15 SYMBOL [--send]")
        sys.exit(1)
    sym=sys.argv[1].upper()
    send = ("--send" in sys.argv[2:])
    r = analyze_symbol(sym)

    if r.get("veto", False):
        msg = (f"<b>⚠️ 未发布 · {r['symbol']}</b>\n"
               f"原因：{r['reason']} · z≈{r.get('funding_z',0):+.2f}")
        print(msg)
        if send: tg_send(msg)
        return

    if r["publish_prime"]:
        html = format_prime_v15(r["symbol"], r["side_long"], r["prob"], r["price"],
                                r["entry_lo"], r["entry_hi"], r["sl"], r["tp1"], r["tp2"],
                                r["T"], r["S"], r["V"], r["A"], r["O"], r["E"],
                                r["prior"], r["Q"], r["chop"], r["room"])
    elif r["publish_watch"]:
        # 参考带使用入场区
        html = format_watch_v15(r["symbol"], r["side_long"], r["prob"], r["price"],
                                r["entry_lo"], r["entry_hi"], r["prior"], r["Q"], r["chop"])
    else:
        # 不发布（低于阈值）→ 返回一条可读说明
        side_txt = "多" if r["side_long"] else "空"
        msg=(f"<b>ℹ️ 未发布 · {r['symbol']}</b>\n"
             f"侧：{side_txt} 概率 {int(round(r['prob']*100))}% · 维度≥65 数量 {sum([x>=65 for x in (r['T'],r['S'],r['V'],r['A'],r['O'],r['E'])])}/6")
        print(msg)
        if send: tg_send(msg)
        return

    print(html)
    if send: tg_send(html)

if __name__=="__main__":
    main()