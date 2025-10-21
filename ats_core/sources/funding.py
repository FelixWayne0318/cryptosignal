from statistics import mean, pstdev
from ats_core.sources.binance import get_funding_hist

def funding_stats(symbol:str):
    rows = get_funding_hist(symbol, limit=120)
    vals = [float(x["fundingRate"]) for x in rows][-120:]
    n = len(vals)
    if n==0: return {"samples":0}
    mu = mean(vals); sd = pstdev(vals) if n>1 else 0.0
    # percentile by rank
    srt = sorted(vals)
    def pct(x):
        i = 0
        for k,v in enumerate(srt):
            if v<=x: i=k
        return (i)/(len(srt)-1) if len(srt)>1 else 0.5
    last = vals[-1]
    return {"samples":n,"last":last,"mean":mu,"sd":sd,"z": (last-mu)/sd if sd>1e-12 else 0.0,"p": pct(last)}