import os, json, time, urllib.request, urllib.parse
from ats_core.logging import warn
from ats_core.cfg import CFG
from ats_core.backoff import sleep_retry

_CACHE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "cache")
os.makedirs(_CACHE, exist_ok=True)

def _cache_path(key:str)->str:
    return os.path.join(_CACHE, key + ".json")

def _get(url, params=None, key=None, ttl=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    key = key or str(abs(hash(url)))
    ttl = ttl if ttl is not None else CFG.get("limits","cache_ttl_sec", default=900)

    p = _cache_path(key)
    now = time.time()
    if os.path.isfile(p):
        try:
            with open(p,'r',encoding='utf-8') as f:
                obj = json.load(f)
            if now - obj.get("_ts",0) <= ttl:
                return obj["data"]
        except: pass

    # fetch with retry/backoff on transient errors
    timeout = CFG.get("limits","http_timeout_sec", default=12)
    last_err = None
    for i in range(5):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                data = json.loads(r.read().decode())
                with open(p,'w',encoding='utf-8') as f:
                    json.dump({"_ts": now, "data": data}, f)
                return data
        except Exception as e:
            last_err = e
            sleep_retry(i)
    raise last_err

BASE = "https://fapi.binance.com"

def get_klines(symbol:str, interval:str, limit:int=300):
    return _get(BASE+"/fapi/v1/klines",
                {"symbol":symbol,"interval":interval,"limit":str(limit)},
                key=f"k_{symbol}_{interval}_{limit}")

def get_ticker_24h():
    return _get(BASE+"/fapi/v1/ticker/24hr", key="t24_all", ttl=60)

def get_funding_hist(symbol:str, limit:int=300):
    return _get(BASE+"/fapi/v1/fundingRate",
                {"symbol":symbol,"limit":str(limit)},
                key=f"fund_{symbol}_{limit}", ttl=3600)

def get_open_interest_hist(symbol:str, period:str="1h", limit:int=200):
    return _get(BASE+"/futures/data/openInterestHist",
                {"symbol":symbol,"period":period,"limit":str(limit)},
                key=f"oi_{symbol}_{period}_{limit}", ttl=1800)