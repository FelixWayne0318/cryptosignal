sudo -u linuxuser -H bash -lc 'cat > /opt/ats-quant/tools/full_run.py << "PY"
# coding: utf-8
from __future__ import annotations
"""
full_run.py — one-shot pipeline (repo-only safe version, ASCII only)
1) load params.yml / overlay candidates
2) pick symbols -> analyze -> render
3) optional: send to Telegram
Falls back to local minimal impl if ats_core is unavailable.
"""
import argparse, json, os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]  # tools/ -> repo root

def _env(name: str, default=None):
    return os.getenv(name, default)

_USING_CORE = False
try:
    from ats_core.cfg import CFG as CORE_CFG  # type: ignore
    from ats_core.outputs.telegram_fmt import render_watch as CORE_RENDER  # type: ignore
    from ats_core.outputs.publisher import telegram_send as CORE_TG_SEND  # type: ignore
    from ats_core.pools import overlay_builder as CORE_OVERLAY  # type: ignore
    from ats_core.pipeline.analyze_symbol import analyze_symbol as CORE_ANALYZE  # type: ignore
    _USING_CORE = True
except Exception:
    _USING_CORE = False

if not _USING_CORE:
    try:
        import yaml
    except Exception:
        yaml = None

    class CFG:
        _data: Dict[str, Any] | None = None
        @classmethod
        def _load(cls):
            if cls._data is not None: return
            data: Dict[str, Any] = {}
            yml = REPO_ROOT / "params.yml"
            if yml.exists() and yaml is not None:
                try:
                    with yml.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                except Exception:
                    data = {}
            cls._data = data
        @classmethod
        def get(cls, key: str, default=None):
            cls._load(); cur: Any = cls._data or {}
            if not key: return cur
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur: cur = cur[part]
                else: return default
            return cur

    def build_overlay_candidates() -> List[str]:
        cands = CFG.get("overlay.candidates") or CFG.get("overlay.whitelist")
        if isinstance(cands, list) and cands:
            return [str(x).upper() for x in cands]
        return []

    import requests
    def telegram_send(text: str, chat_id: Optional[str] = None, token: Optional[str] = None,
                      parse_mode: str = "HTML", disable_preview: bool = True) -> Dict[str, Any]:
        token = token or _env("TELEGRAM_BOT_TOKEN") or _env("ATS_TELEGRAM_BOT_TOKEN")
        if not token: raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
        chat_id = chat_id or _env("TELEGRAM_CHAT_ID_WATCH") or _env("TELEGRAM_CHAT_ID_PRIME") or _env("TELEGRAM_CHAT_ID")
        if not chat_id: raise RuntimeError("TELEGRAM_CHAT_ID(_WATCH/_PRIME) not set")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={
            "chat_id": chat_id, "text": text, "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview}, timeout=10)
        r.raise_for_status(); data = r.json()
        if not data.get("ok"): raise RuntimeError(f"Telegram error: {data}")
        return data

    def render_watch(res: Dict[str, Any]) -> str:
        s = res.get("symbol", "?"); prime = bool(res.get("prime", False))
        header = f"[PRIME] {s}" if prime else f"[WATCH] {s}"; lines = [header]
        def _fmt(k, label=None, suffix=""):
            v = res.get(k)
            if v is None: return
            if isinstance(v, float):
                try: v = f"{v:.4f}"
                except Exception: v = str(v)
            lines.append(f"{label or k}: {v}{suffix}")
        _fmt("price","price"); _fmt("chg_pct","change","%"); _fmt("score","score")
        note = res.get("note"); 
        if note: lines.append(f"note: {note}")
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"); lines.append(ts)
        return "\n".join(lines)

    def analyze_symbol_basic(symbol: str) -> Dict[str, Any]:
        import requests
        url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol.upper()}"
        r = requests.get(url, timeout=10); r.raise_for_status(); t = r.json()
        last = float(t["lastPrice"]); open_ = float(t["openPrice"])
        chg_pct = (last - open_) / open_ * 100 if open_ else 0.0
        prime_thr = CFG.get("overlay.prime.min_change_pct", 1.5) or CFG.get("overlay.prime_min_change_pct", 1.5)
        score = chg_pct; is_prime = chg_pct >= float(prime_thr)
        return {"symbol": symbol.upper(), "price": last, "chg_pct": round(chg_pct,3),
                "score": round(score,3), "prime": bool(is_prime), "source": "binance.24hr"}

    def _CFG_get(key: str, default=None): return CFG.get(key, default)
    def _overlay_build(): return build_overlay_candidates()
    def _render(res: Dict[str, Any]) -> str: return render_watch(res)
    def _tg_send(txt: str, chat_id: Optional[str] = None): return telegram_send(txt, chat_id=chat_id)
    def _analyze(symbol: str) -> Dict[str, Any]: return analyze_symbol_basic(symbol)
else:
    def _CFG_get(key: str, default=None): return CORE_CFG.get(key, default)
    def _overlay_build():
        try: return CORE_OVERLAY.build()
        except Exception: return []
    def _render(res: Dict[str, Any]) -> str: return CORE_RENDER(res)
    def _tg_send(txt: str, chat_id: Optional[str] = None): return CORE_TG_SEND(txt, chat_id=chat_id)
    def _analyze(symbol: str) -> Dict[str, Any]: return CORE_ANALYZE(symbol)

FALLBACK_UNIVERSE = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
                     "TRXUSDT","AVAXUSDT","LINKUSDT","MATICUSDT","DOTUSDT","LTCUSDT","BCHUSDT"]

def _pick_universe(limit: int) -> List[str]:
    try:
        cands = _overlay_build()
        if isinstance(cands, list) and cands: return [s.upper() for s in cands[:limit]]
    except Exception: pass
    uni = _CFG_get("universe", default=[])
    if isinstance(uni, list) and uni: return [str(s).upper() for s in uni[:limit]]
    return FALLBACK_UNIVERSE[:limit]

def route_chat_id(is_prime: bool, args_chat_prime: Optional[str], args_chat_watch: Optional[str]) -> Optional[str]:
    env_prime = _env("TELEGRAM_CHAT_ID_PRIME") or _env("ATS_TELEGRAM_CHAT_ID_PRIME")
    env_watch = _env("TELEGRAM_CHAT_ID_WATCH") or _env("ATS_TELEGRAM_CHAT_ID_WATCH")
    base      = _env("TELEGRAM_CHAT_ID") or _env("ATS_TELEGRAM_CHAT_ID")
    return (args_chat_prime or env_prime or base) if is_prime else (args_chat_watch or env_watch or base)

def maybe_tag(text: str, is_prime: bool, add_tags: bool) -> str:
    if not add_tags: return text
    return f"{'[PRIME]' if is_prime else '[WATCH]'}\n{text}"

def main():
    ap = argparse.ArgumentParser(description="Full run (repo-only, ASCII)")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--only-prime", dest="only_prime", action="store_true")
    ap.add_argument("--only-watch", dest="only_watch", action="store_true")
    ap.add_argument("--save-json", action="store_true")
    ap.add_argument("--prime-chat-id", type=str, default=None)
    ap.add_argument("--watch-chat-id", type=str, default=None)
    ap.add_argument("--add-tags", action="store_true")
    args = ap.parse_args()

    overlay = _CFG_get("overlay", default={})
    print("[CFG] overlay:", overlay if isinstance(overlay, dict) else type(overlay).__name__)
    uni = _CFG_get("universe", default=[])
    print("[CFG] universe size:", len(uni) if isinstance(uni, list) else 0)

    symbols = _pick_universe(args.limit)
    print("[CAND] count={} examples={}".format(len(symbols), symbols[:7]))

    out_rows: List[Dict[str, Any]] = []; prime_cnt = send_cnt = fail_cnt = 0
    results_dir = REPO_ROOT / "data" / ("run_" + datetime.utcnow().strftime("%Y%m%d-%H%M%S"))
    if args.save_json: results_dir.mkdir(parents=True, exist_ok=True)

    for s in symbols:
        try:
            res = _analyze(s)
            if not isinstance(res, dict): raise RuntimeError("analyze_symbol returns non-dict")
            res["symbol"] = s; is_prime = bool(res.get("prime", False))

            if args.only_prime and not is_prime: continue
            if args.only_watch and is_prime: continue

            txt = _render(res)
            if args.add_tags: txt = maybe_tag(txt, is_prime, add_tags=True)

            print(f"\n==== {s} ====\n{txt}\n")

            if args.send:
                cid = route_chat_id(is_prime, args.prime_chat_id, args.watch_chat_id)
                _tg_send(txt, chat_id=cid); send_cnt += 1
            if args.save_json:
                (results_dir / f"{s}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
            if is_prime: prime_cnt += 1
            out_rows.append({"symbol": s, "prime": is_prime, "ok": True})
        except Exception as e:
            fail_cnt += 1; print(f"[ANALYZE FAIL] {s} -> {e}")

    print("\n-- SUMMARY --")
    print(f"candidates: {len(symbols)}")
    print(f"analyzed:   {len(out_rows)}")
    print(f"prime:      {prime_cnt}")
    print(f"sent:       {send_cnt}")
    print(f"fails:      {fail_cnt}")
    if args.save_json:
        print(f"results dir: {results_dir}")

if __name__ == "__main__":
    main()
PY'