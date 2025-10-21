import os, json, datetime, urllib.request, pathlib
from app.common import load_env, tg_send

def fetch_24h_tickers():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    load_env()
    min_quote = float(os.getenv("MIN_QUOTE_24H_USDT", "10000000"))

    data = fetch_24h_tickers()
    # 仅保留 USDT 永续（以 USDT 结尾，且忽略带杠杆/奇怪符号的现货对）
    fut = [d for d in data if d.get("symbol","").endswith("USDT")]
    # 过滤成交额（quoteVolume 是以 quote 计价的成交量，期货这里近似使用）
    base = [d for d in fut if float(d.get("quoteVolume","0") or 0) >= min_quote]
    base_sorted = sorted(base, key=lambda d: float(d.get("quoteVolume","0") or 0), reverse=True)

    # 落地报告
    reports = pathlib.Path("reports"); reports.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    rp = reports / f"base_pool_{today}.md"
    lines = [f"# Base Pool {today}", f"- min_quote_24h = {min_quote:,.0f} USDT", f"- symbols = {len(base_sorted)}", ""]
    for i,d in enumerate(base_sorted[:50], 1):  # 只列前50，避免太长
        sym = d["symbol"]; qv = float(d.get("quoteVolume","0") or 0)
        chg = float(d.get("priceChangePercent","0") or 0)
        lines.append(f"{i:>2}. {sym:>12} | quoteVol≈{qv:,.0f} | 24h%={chg:+.2f}")
    rp.write_text("\n".join(lines), encoding="utf-8")

    # 发群简报
    msg = (
        f"🗂️ [ANALYZER] 基础池刷新 {today}\n"
        f"阈值：24h报价额 ≥ {min_quote:,.0f} USDT\n"
        f"纳入：{len(base_sorted)} 个（前50已落地 reports）"
    )
    tg_send(msg)
    print(msg)

if __name__ == "__main__":
    main()
