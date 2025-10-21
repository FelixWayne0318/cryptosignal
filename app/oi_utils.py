import json, urllib.request, urllib.parse
from statistics import median

def _http_json(url, params=None, timeout=15):
    if params: url += ("?" + urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())

def fetch_oi_hourly(symbol, limit=200):
    """
    返回按时间升序的 OI 数列（float list）。
    /futures/data/openInterestHist 可能字段名为 sumOpenInterest 或 openInterest
    """
    rows = _http_json(
        "https://fapi.binance.com/futures/data/openInterestHist",
        {"symbol": symbol, "period": "1h", "limit": str(limit)}
    )
    oi = []
    for x in rows:
        v = x.get("sumOpenInterest") or x.get("openInterest")
        if v is None: continue
        try:
            oi.append(float(v))
        except:
            pass
    if len(oi) < 30:
        raise RuntimeError("OI samples too few")
    return oi

def _pct(a,b,den):
    return (a-b)/den if den>1e-12 else 0.0

def _pct_series(oi, look=24):
    """ 构造 24h OI 变化的归一序列，便于做分位/极端检测 """
    n=len(oi)
    if n<=look: return []
    den = median(oi[max(0,n-168):])  # 近 7 天小时中位
    out=[]
    for i in range(look,n):
        out.append(_pct(oi[i],oi[i-look],den))
    return out

def oi_metrics_and_score(oi, closes, side_long:bool):
    """
    输入：oi（升序）、closes（升序，1h收盘）、side_long
    输出：O分（0..100），以及可展示的标签/度量
    规则（v1.5 要点）：
      多：OI_24h ∈ +5%~+18% 最优；近12h “价涨+OI增”次数越多越好
      空：近12h “价跌+OI增” ≥8 小时 或 OI_24h ∈ [-25%,-8%] 更佳
      拥挤：OI_24h 位于历史（~8天）95分位以上，小幅扣 8 分（非硬否决）
    """
    n=len(oi)
    den = median(oi[max(0,n-168):])  # 7d 中位OI作尺度
    oi1h = _pct(oi[-1], oi[-2], den)
    oi24 = _pct(oi[-1], oi[-25], den) if n>=25 else 0.0

    # 近12小时的价格方向 & OI方向
    k = min(12, len(closes)-1, len(oi)-1)
    up_up = dn_up = 0
    for i in range(1, k+1):
        dp = closes[-i] - closes[-i-1]
        doi = oi[-i] - oi[-i-1]
        if dp>0 and doi>0: up_up += 1         # 价涨 + OI增
        if dp<0 and doi>0: dn_up += 1         # 价跌 + OI增

    # 拥挤度：以 24h 归一变化的历史分布做阈值（~8天）
    hist_24 = _pct_series(oi, 24)
    crowd_warn = False
    if hist_24:
        s = sorted(hist_24)
        p95 = s[int(0.95*(len(s)-1))]
        crowd_warn = (oi24 >= p95)
    else:
        p95 = None

    def _clip(x,a,b): 
        return a if x<a else (b if x>b else x)

    def _map_linear(x, lo, hi):
        """线性 0..1"""
        if hi==lo: return 0.0
        return _clip((x-lo)/(hi-lo), 0.0, 1.0)

    if side_long:
        # 多：主看 OI_24h 在 +5%~+18%；辅以 “价涨+OI增”近12小时的占比
        s1 = _map_linear(oi24, 0.05, 0.18)        # → 0..1
        s2 = _map_linear(up_up, 6, 12)            # 6~12 小时 → 0..1
        O = int(round(80*s1 + 20*s2))
    else:
        # 空：两路取优（max）
        # A 路：近12小时 “价跌+OI增” 8~12 小时最佳
        a = _map_linear(dn_up, 8, 12)
        # B 路：OI_24h 大幅回撤（合约去杠杆）
        b = _map_linear(-oi24, 0.08, 0.25)
        O = int(round(100*max(a, b)))

    if crowd_warn:
        O = max(0, O-8)   # 极端拥挤小惩罚（非一票否决）

    tags = {
        "oi1h_pct": round(oi1h*100,2),
        "oi24h_pct": round(oi24*100,2),
        "pos12_upup": int(up_up),
        "pos12_dnup": int(dn_up),
        "crowding_p95": (round(p95*100,2) if p95 is not None else None),
        "crowding_warn": bool(crowd_warn),
    }
    return O, tags
