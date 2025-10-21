from ats_core.sources.binance import get_klines

def klines_1h(symbol, limit=300): return get_klines(symbol,"1h",limit)
def klines_4h(symbol, limit=200): return get_klines(symbol,"4h",limit)
def klines_15m(symbol, limit=300): return get_klines(symbol,"15m",limit)

def split_ohlcv(rows):
    o,h,l,c,v, q, tb = [],[],[],[],[],[],[]
    for x in rows:
        o.append(float(x[1])); h.append(float(x[2])); l.append(float(x[3])); c.append(float(x[4]))
        v.append(float(x[5])); q.append(float(x[7])); tb.append(float(x[9]))
    return o,h,l,c,v,q,tb