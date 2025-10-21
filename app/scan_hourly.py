import os, json, datetime, urllib.request
from app.common import load_env, tg_send

def fetch_24h_tickers():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    load_env()
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")
    # 演示：找 24h 涨跌幅 |priceChangePercent| 排名前 5 的 USDT 合约
    data = fetch_24h_tickers()
    fut = [d for d in data if d.get("symbol","").endswith("USDT")]
    movers = sorted(fut, key=lambda d: abs(float(d.get("priceChangePercent","0") or 0)), reverse=True)[:5]
    lines = [f"🧭 [ANALYZER] 扫描完成 {now}", f"Top movers(24h%%)："]
    for d in movers:
        sym = d["symbol"]; chg = float(d.get("priceChangePercent","0") or 0)
        lines.append(f"- {sym:<12} {chg:+.2f}%")
    tg_send("\n".join(lines))
    print("\n".join(lines))

if __name__ == "__main__":
    main()
