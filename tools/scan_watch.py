cat > ~/ats-analyzer/tools/scan_watch.py <<'PY'
# coding: utf-8
import sys, argparse, importlib

# 让模板恒显六维 + 解释 + 动态小数位
import os
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

from ats_core.cfg import CFG
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_watch

try:
    from ats_core.outputs.publisher import telegram_send
except Exception:
    telegram_send = None

def get_candidates(limit=None):
    syms = []
    try:
        ob = importlib.import_module("ats_core.pools.overlay_builder")
        for name in ("build","build_overlay","build_candidates","build_pool"):
            if hasattr(ob, name):
                arr = getattr(ob, name)()
                if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                    syms = [x.get("symbol") or x.get("sym") for x in arr if (x.get("symbol") or x.get("sym"))]
                elif isinstance(arr, list) and arr and isinstance(arr[0], str):
                    syms = arr
                break
    except Exception:
        pass

    if not syms:
        uni = CFG.get("universe", default=None)
        if isinstance(uni, (list,tuple)) and uni and isinstance(uni[0], str):
            syms = list(uni)
        else:
            syms = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","COAIUSDT","CLOUSDT","XPLUSDT"]
    return syms[:limit] if (limit and limit>0) else syms

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="发送到 Telegram")
    ap.add_argument("--n", type=int, default=12, help="最多处理多少个候选")
    ap.add_argument("--only-prime", action="store_true", help="只发送 prime=True 的（默认全部作为 watch）")
    args = ap.parse_args(argv)

    syms = get_candidates(limit=args.n)
    if not syms:
        print("候选池为空")
        return 2

    fail = 0
    for s in syms:
        try:
            r = analyze_symbol(s)
            r["symbol"] = s
            pub = (r.get("publish") or {})
            txt = render_watch(r)

            print(f"\n==== {s} ====\n{txt}\n", flush=True)

            if args.send and (not args.only-prime or pub.get("prime")) and telegram_send:
                try:
                    telegram_send(txt)
                    print(f"[SENT] {s}", flush=True)
                except Exception as e:
                    fail += 1
                    print(f"[SEND FAIL] {s} -> {e}", file=sys.stderr, flush=True)
        except Exception as e:
            fail += 1
            print(f"[ANALYZE FAIL] {s} -> {e}", file=sys.stderr, flush=True)

    return 1 if fail else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
PY