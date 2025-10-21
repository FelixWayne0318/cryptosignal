# app/oneoff.py —— 单币快照 v2（Prime / Watch）
# - 对齐“非专业可读”模板
# - 新增：ZigZag 结构评分(SQ)、θ/ICR/回撤/不过度、15m微确认、BTC/ETH环境
# - 仅标准库，无外部依赖
import os, sys, json, math, datetime, urllib.request, urllib.parse

# ------------ 环境与HTTP ------------
def load_env():
    for path in (os.path.join(os.getcwd(), ".env"),
                 os.path.expanduser("~/ats-analyzer/.env")):
        if not os.path.isfile(path): 
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    s=line.strip()
                    if not s or s.startswith("#") or "=" not in s: 
                        continue
                    k,v=s.split("=",1); k=k.strip(); v=v.strip()
                    if (v[:1]==v[-1:] and v[:1] in "\"'"): v=v[1:-1]
                    os.environ[k]=v
        except Exception:
            pass

def env(k, d=None): 
    return os.environ.get(k, d)

def http_json(url, params=None, timeout=15):
    if params: url += ("?" + urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())

# ------------ 指标 ------------
def ema(arr, n):
    k=2.0/(n+1.0); s=None; out=[]
    for x in arr:
        s = x if s is None else (x*k + s*(1-k))
        out.append(s)
    return out

def atr(h,l,c,n=14):
    trs=[h[0]-l[0]]
    for i in range(1,len(c)):
        trs.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    k=2.0/(n+1.0); s=None; out=[]
    for tr in trs:
        s = tr if s is None else (tr*k + s*(1-k))
        out.append(s)
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

def vboost(vol):
    if len(vol)<20: return 1.0
    sma20=sum(vol[-20:])/20.0
    best=0.0
    for k in (1,2,3):
        best=max(best, sum(vol[-k:])/max(1e-9, sma20))
    return min(best, 3.0)

def cvd_slope(base_vol, taker_buy_base, quote_vol, hours=6):
    cvd=[0.0]
    for b,t in zip(base_vol, taker_buy_base):
        cvd.append(cvd[-1] + (2*t - b))
    if len(cvd)<=hours: return 0.0
    dn=sum(quote_vol[-hours:])
    return (cvd[-1]-cvd[-hours-1]) / max(1e-9, dn)

def chop14(h,l,c):
    if len(c)<15: return 100.0
    tr=[]
    for i in range(1,len(c)):
        tr.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))
    tr14=sum(tr[-14:])
    hh=max(h[-14:]); ll=min(l[-14:])
    rng=max(1e-9, hh-ll)
    return 100.0*math.log10(tr14/rng)/math.log10(14)

def clip(x,a,b): 
    return max(a, min(b, x))

# ------------ 结构：ZigZag & SQ ------------
def zigzag_pivots(close, theta):
    """最简 ZigZag：价格相对最后枢轴偏离 ≥ theta 即确认新枢轴。"""
    piv_idx=[0]; piv_px=[close[0]]
    last_dir=0  # 1 up, -1 down, 0 flat
    last_p=close[0]
    for i,px in enumerate(close[1:],1):
        move=px - last_p
        if abs(move) >= theta:
            dirn=1 if move>0 else -1
            # 防止连向同一方向：若同向则替换最后枢轴
            if last_dir==dirn and piv_idx:
                piv_idx[-1]=i; piv_px[-1]=px
            else:
                piv_idx.append(i); piv_px.append(px); last_dir=dirn
            last_p=px
        else:
            # 更新极值（提高最后枢轴质量）
            if last_dir>=0 and px>piv_px[-1]:
                piv_idx[-1]=i; piv_px[-1]=px
                last_p=px
            if last_dir<=0 and px<piv_px[-1]:
                piv_idx[-1]=i; piv_px[-1]=px
                last_p=px
    return list(zip(piv_idx, piv_px))

def calc_sq(close, ema30_now, atr_now, side_long:bool):
    # θ：基线 0.40×ATR（若价格离 EMA30 很近，降低一点以提早识别；离得远则抬高）
    ext = min(abs(close[-1]-ema30_now)/max(1e-9,atr_now), 0.8)
    theta = (0.35 if ext<0.2 else 0.40 if ext<0.6 else 0.45) * atr_now
    piv = zigzag_pivots(close[-120:], theta)
    if len(piv)<3:
        return dict(theta=theta, sq=0.50, icr=1.0, retr=0.0, over=abs(close[-1]-ema30_now)/max(1e-9,atr_now))
    # 计算最近 6 段 swing
    sw=[piv[i+1][1]-piv[i][1] for i in range(len(piv)-1)][-6:]
    if not sw: 
        return dict(theta=theta, sq=0.50, icr=1.0, retr=0.0, over=abs(close[-1]-ema30_now)/max(1e-9,atr_now))
    # 定义冲击/回撤
    if side_long:
        impulses=[x for x in sw if x>0]; corrections=[-x for x in sw if x<0]
    else:
        impulses=[-x for x in sw if x<0]; corrections=[x for x in sw if x>0]
    imp = sum(abs(x) for x in impulses)/max(1,len(impulses))
    cor = (sum(abs(x) for x in corrections)/max(1,len(corrections))) if corrections else 0.0
    icr = imp/max(1e-9, cor if cor>0 else imp*0.6)  # 无回撤时给个温和分母
    icr_score = clip((icr-1.0)/1.5, 0, 1)  # 1.0~2.5 映射到 0~1

    # 最近一次回撤深度（相对 ATR）
    # 找最后一个 correction 段
    last_cor = 0.0
    for x in reversed(sw):
        if (x<0 and side_long) or (x>0 and not side_long):
            last_cor = abs(x); break
    retr = last_cor / max(1e-9, atr_now)
    # 0.38~0.62 最优，外侧衰减
    retr_score = 1.0 - min(abs(retr-0.5)/0.5, 1.0)

    # 方向一致性（最近 4 段中与当前方向一致的比例）
    sign = (1 if side_long else -1)
    last4 = sw[-4:]
    cons = sum(1 for x in last4 if x*sign>0)/max(1,len(last4))
    cons_score = cons  # 0~1

    # 不过度：|close-EMA30|/ATR ≤ 0.8 最优
    over = abs(close[-1]-ema30_now)/max(1e-9,atr_now)
    over_score = 1.0 if over<=0.8 else max(0.0, 1.0 - (over-0.8)/0.8)

    # 合成 SQ
    sq = 0.28*cons_score + 0.28*icr_score + 0.24*retr_score + 0.20*over_score
    return dict(theta=theta, sq=sq, icr=icr, retr=retr, over=over)

# ------------ 15m 微确认 ------------
def micro_15m(sym, side_long:bool):
    k15 = http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":sym,"interval":"15m","limit":80})
    c15=[float(x[4]) for x in k15]; v15=[float(x[5]) for x in k15]
    if len(c15)<30: 
        return dict(ok=False, vheat=1.0, ema_ok=False)
    ema10=ema(c15,10)
    # 6 根里 ≥4 根在 EMA10 同侧
    sig=0
    for x,ma in zip(c15[-6:], ema10[-6:]):
        sig += 1 if (x>=ma and side_long) or (x<=ma and not side_long) else 0
    ema_ok = (sig>=4)
    # v3/v20 热度
    v3=sum(v15[-3:]); v20=sum(v15[-20:])
    vheat = (v3/max(1e-9,v20/20.0))
    ok = ema_ok and (1.1<=vheat<=1.8)
    return dict(ok=ok, vheat=vheat, ema_ok=ema_ok)

# ------------ BTC/ETH 环境 ------------
def env_btc_eth():
    out=[]
    for sym in ("BTCUSDT","ETHUSDT"):
        k1=http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":sym,"interval":"1h","limit":120})
        k4=http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":sym,"interval":"4h","limit":120})
        c1=[float(x[4]) for x in k1]; c4=[float(x[4]) for x in k4]
        e1=ema(c1,30); e4=ema(c4,30)
        s1=(e1[-1]-e1[-7]); s4=(e4[-1]-e4[-7])
        d1="↗︎" if s1>0 else "↘︎" if s1<0 else "→"
        d4="↗︎" if s4>0 else "↘︎" if s4<0 else "→"
        out.append((sym, d1, d4))
    # 标签：同向/分歧
    same = (out[0][1]==out[1][1] and out[0][2]==out[1][2])
    tag = "同向" if same else "分歧"
    return out, tag

# ------------ 主流程：评分+概率+给价 ------------
def score_and_price_plan(sym):
    k1 = http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":sym,"interval":"1h","limit":300})
    if len(k1)<120: 
        raise RuntimeError("样本不足(1h)")
    o=[float(x[1]) for x in k1]
    h=[float(x[2]) for x in k1]
    l=[float(x[3]) for x in k1]
    c=[float(x[4]) for x in k1]
    v=[float(x[5]) for x in k1]
    q=[float(x[7]) for x in k1]
    tb=[float(x[9]) for x in k1]
    k4=http_json("https://fapi.binance.com/fapi/v1/klines", {"symbol":sym,"interval":"4h","limit":200})
    c4=[float(x[4]) for x in k4]

    atr1=atr(h,l,c,14); atr_now=atr1[-1]
    ema10=ema(c,10); ema30=ema(c,30)
    slope30=(ema30[-1]-ema30[-7])/6.0
    slope_ratio=slope30/max(1e-9,atr_now)
    r2=rsq(ema30,21)
    vb=vboost(v)
    cvd6=cvd_slope(v,tb,q,6)
    ch=chop14(h,l,c)
    ema30_4h=ema(c4,30)
    bg_same = ((ema30_4h[-1]-ema30_4h[-7])>0 and slope_ratio>0) or ((ema30_4h[-1]-ema30_4h[-7])<0 and slope_ratio<0)

    # 方向初判（用于 SQ & 给价）
    side_long = (slope_ratio>=0)  # 以 1h EMA30 斜率为先
    # 结构SQ
    sq_dict = calc_sq(c, ema30[-1], atr_now, side_long)
    SQ = sq_dict["sq"]

    # 六组打分（S 用 SQ）
    T=0
    if slope_ratio>=0.30: T+=60
    elif slope_ratio>=0.15: T+=40
    elif slope_ratio>=0.05: T+=20
    T+=int(40*clip((r2-0.45)/0.25,0,1))
    if bg_same: T+=10
    T=min(T,100)

    A=int(100*clip(0.6*clip((slope_ratio-0.10)/0.30,0,1) + 0.4*clip((cvd6-0.01)/0.04,0,1),0,1))
    S=int(100*clip(SQ,0,1))
    V=int(100*clip((vb-1.2)/(1.7-1.2),0,1))
    O=int(100*clip((cvd6 if slope_ratio>0 else -cvd6)*50,0,1))
    E=int(100*clip((52-ch)/12,0,1))

    Up = 0.25*T+0.15*A+0.15*S+0.20*V+0.15*O+0.10*E
    Up = clip(Up/100.0,0,1)
    Edge = Up-(1-Up)
    Q = 0.8
    p_up = clip(0.5 + 0.35*Edge*Q, 0.35, 0.85)
    p_dn = 1-p_up
    side = "多" if p_up>=p_dn else "空"
    # 若方向与 slope 矛盾，则取概率更大的一侧作为最终方向
    side_long = (side=="多")
    prob=int(round(100*max(p_up,p_dn)))
    price=c[-1]

    # 给价（Prime）
    ext=min(abs(price-ema30[-1])/max(1e-9,atr_now),0.6)
    delta=(0.02+0.10*ext)*atr_now
    if side_long:
        entry_lo=ema10[-1]-delta; entry_hi=ema10[-1]+0.01*atr_now
        # 枢轴低点
        piv_low=min(l[-12:])
        sl=max(piv_low-0.10*atr_now, ((entry_lo+entry_hi)/2)-1.8*atr_now)
        hh=max(h[-72:]); R=((entry_lo+entry_hi)/2)-sl
        tp1=(entry_lo+entry_hi)/2 + 1.0*R
        tp2=(entry_lo+entry_hi)/2 + min(2.5*R, max(0.0, hh*0.998 - (entry_lo+entry_hi)/2))
        room=(hh-(entry_lo+entry_hi)/2)/max(1e-9,atr_now)
    else:
        entry_lo=ema10[-1]-0.01*atr_now; entry_hi=ema10[-1]+delta
        piv_high=max(h[-12:])
        sl=min(piv_high+0.10*atr_now, ((entry_lo+entry_hi)/2)+1.8*atr_now)
        ll=min(l[-72:]); R=sl-((entry_lo+entry_hi)/2)
        tp1=(entry_lo+entry_hi)/2 - 1.0*R
        tp2=(entry_lo+entry_hi)/2 - min(2.5*R, max(0.0, (entry_lo+entry_hi)/2 - ll*1.002))
        room=(((entry_lo+entry_hi)/2)-ll)/max(1e-9,atr_now)

    # 15m 微确认
    m15 = micro_15m(sym, side_long)
    # BTC/ETH 环境
    be, be_tag = env_btc_eth()
    btc_label=f"BTC {be[0][1]}/{be[0][2]}"
    eth_label=f"ETH {be[1][1]}/{be[1][2]}"

    # 近端 SR 带（Watch 用）
    sr_hi=max(h[-20:]); sr_lo=min(l[-20:])
    ref_band=f"{min(entry_lo,entry_hi):.6g}–{max(entry_lo,entry_hi):.6g}"

    return {
        "symbol":sym,"side":side,"prob":prob,"price":price,
        "T":int(T),"S":int(S),"V":int(V),"A":int(A),"O":int(O),"E":int(E),
        "vb":round(vb,2),"r2":round(r2,2),"slopeATR":round(slope_ratio,2),"cvd6":round(cvd6,4),
        "chop":round(ch,1),"room":round(room,2),"Q":Q,
        "entry_lo":entry_lo,"entry_hi":entry_hi,"sl":sl,"tp1":tp1,"tp2":tp2,
        "theta_atr":round(sq_dict["theta"]/max(1e-9,atr_now),2),
        "SQ":round(SQ,2),"ICR":round(sq_dict["icr"],2),"retrATR":round(sq_dict["retr"],2),
        "overATR":round(sq_dict["over"],2),"micro_ok":m15["ok"],
        "vheat":round(m15.get("vheat",1.0),2),"btc_env":btc_label,"eth_env":eth_label,"env_tag":be_tag,
        "ref_band":ref_band,"sr_lo":sr_lo,"sr_hi":sr_hi
    }

# ------------ Telegram 输出 ------------
def tg_send(html):
    token=env("TELEGRAM_BOT_TOKEN"); chat=env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[WARN] TELEGRAM env missing; skip send"); return
    data=urllib.parse.urlencode({"chat_id":chat,"text":html,"parse_mode":"HTML","disable_web_page_preview":"true"}).encode()
    req=urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    urllib.request.urlopen(req, timeout=12).read()

def fmt_prime(r):
    arrow = "⬆️" if r['side']=="多" else "⬇️"
    micro = "✅" if r["micro_ok"] else "—"
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")
    return (
f"<b>✅ {r['symbol']} · {arrow} {r['side']}（8h展望）</b>\n"
f"时间(UTC) {now} · 概率 <b>{r['prob']}%</b> · 现价 <code>{r['price']:.6g}</code>\n"
f"入场带 <code>{min(r['entry_lo'],r['entry_hi']):.6g} – {max(r['entry_lo'],r['entry_hi']):.6g}</code> · SL <code>{r['sl']:.6g}</code> · TP1/TP2 <code>{r['tp1']:.6g} / {r['tp2']:.6g}</code>\n"
f"结构：SQ={r['SQ']:.2f} | θ={r['theta_atr']:.2f}×ATR | ICR={r['ICR']:.2f} | 回撤={r['retrATR']:.2f}×ATR | 不过度={r['overATR']:.2f}×ATR | 15m微确认 {micro}\n"
f"趋势/量能/持仓：slope30/ATR={r['slopeATR']:+.2f} · R²={r['r2']:.2f} · Vboost={r['vb']:.2f} · CVD6h={r['cvd6']:+.4f}\n"
f"环境：{r['btc_env']} · {r['eth_env']}（{r['env_tag']}） · CHOP={r['chop']:.1f} · Room={r['room']:.2f}×ATR · Q={r['Q']:.2f}\n"
f"失效：收回入场带下沿且 v5/v20<1；CVD 2h 反向。"
    )

def fmt_watch(r):
    arrow = "⬆️" if r['side']=="多" else "⬇️"
    micro = "✅" if r["micro_ok"] else "—"
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")
    return (
f"<b>👀 {r['symbol']} · {arrow} {r['side']}</b>\n"
f"时间(UTC) {now} · 概率 <b>{r['prob']}%</b> · 现价 <code>{r['price']:.6g}</code>\n"
f"参考区间（非指令）：<code>{r['ref_band']}</code> · 近端SR <code>{r['sr_lo']:.6g} / {r['sr_hi']:.6g}</code>\n"
f"结构：SQ={r['SQ']:.2f} | θ={r['theta_atr']:.2f}×ATR | ICR={r['ICR']:.2f} | 回撤={r['retrATR']:.2f}×ATR | 不过度={r['overATR']:.2f}×ATR | 15m {micro}\n"
f"趋势/量能/持仓：slope30/ATR={r['slopeATR']:+.2f} · R²={r['r2']:.2f} · Vboost={r['vb']:.2f} · CVD6h={r['cvd6']:+.4f}\n"
f"环境：{r['btc_env']} · {r['eth_env']}（{r['env_tag']}） · CHOP={r['chop']:.1f} · Room={r['room']:.2f}×ATR · Q={r['Q']:.2f}"
    )

# ------------ CLI ------------
def main():
    load_env()
    if len(sys.argv)<2:
        print("Usage: python -m app.oneoff SYMBOL [--send] [--type prime|watch]"); sys.exit(1)
    sym=sys.argv[1].upper()
    send=("--send" in sys.argv[2:])
    typ="prime"
    for i,a in enumerate(sys.argv[2:],2):
        if a=="--type" and i+1 < len(sys.argv):
            typ=sys.argv[i+1]
    r=score_and_price_plan(sym)
    msg = fmt_prime(r) if typ.lower()!="watch" else fmt_watch(r)
    print(msg)
    if send: tg_send(msg)

if __name__=="__main__":
    main()
