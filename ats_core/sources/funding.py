from statistics import mean, pstdev
from typing import Dict

from ats_core.sources.binance import get_funding_hist


def funding_stats(symbol: str) -> Dict:
    """
    读取资金费率历史，给出样本数、最新值、均值、标准差、z 分数与分位
    若无法获取数据，返回 {"samples":0, "error": "..."}（不抛异常，便于上层容错）
    """
    try:
        rows = get_funding_hist(symbol, limit=120)
    except Exception as e:
        return {"samples": 0, "error": str(e)}

    vals = []
    for x in rows:
        try:
            vals.append(float(x.get("fundingRate", 0.0)))
        except Exception:
            continue

    vals = vals[-120:]
    n = len(vals)
    if n == 0:
        return {"samples": 0}

    mu = mean(vals)
    sd = pstdev(vals) if n > 1 else 0.0

    srt = sorted(vals)

    def pct(x: float) -> float:
        if len(srt) <= 1:
            return 0.5
        i = 0
        for k, v in enumerate(srt):
            if v <= x:
                i = k
        return i / (len(srt) - 1)

    last = vals[-1]
    z = (last - mu) / sd if sd > 1e-12 else 0.0
    return {"samples": n, "last": last, "mean": mu, "sd": sd, "z": z, "p": pct(last)}