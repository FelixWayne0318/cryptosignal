# coding: utf-8
"""
全流程：候选 -> 分析 -> 过滤 -> 输出 -> （可选）发送 & 落盘
用法示例：
  python3 -m tools.full_run --limit 50
  python3 -m tools.full_run --send --only-prime
  python3 -m tools.full_run --limit 50 --save-json
"""

import os, sys, json, argparse, importlib
from datetime import datetime, timezone
from pathlib import Path

# 让模板恒显“六维+解释+动态小数位”，便于排查
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

from ats_core.cfg import CFG
from ats_core.sources.klines import klines_1h, split_ohlcv
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_watch

try:
    from ats_core.outputs.publisher import telegram_send
except Exception:
    telegram_send = None


def _symbols_from_overlay():
    """调用 overlay_builder，返回符号列表（str）"""
    try:
        ob = importlib.import_module("ats_core.pools.overlay_builder")
        for name in ("build", "build_overlay", "build_candidates", "build_pool"):
            if hasattr(ob, name):
                res = getattr(ob, name)()
                if isinstance(res, list) and res:
                    if isinstance(res[0], dict):
                        out = []
                        for it in res:
                            s = it.get("symbol") or it.get("sym") or it.get("ticker")
                            if s:
                                out.append(s)
                        return out
                    if isinstance(res[0], str):
                        return list(res)
                return []
    except Exception:
        return []
    return []


def _ctx_prior_market():
    """提供 analyze_symbol 需要的 btc/eth 1h close 作为 prior 计算上下文"""
    ctx = {}
    try:
        k1 = klines_1h("BTCUSDT", 300)
        _, _, _, c, _, _, _ = split_ohlcv(k1)
        if c:
            ctx["btc_c"] = c
    except Exception:
        pass
    try:
        k1 = klines_1h("ETHUSDT", 300)
        _, _, _, c, _, _, _ = split_ohlcv(k1)
        if c:
            ctx["eth_c"] = c
    except Exception:
        pass
    return ctx if ("btc_c" in ctx and "eth_c" in ctx) else None


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=24, help="最多处理多少个候选")
    ap.add_argument("--send", action="store_true", help="发送到 Telegram（需要 publisher 配置可用）")
    ap.add_argument("--only-prime", dest="only_prime", action="store_true",
                    help="只发送 prime=True 的")
    ap.add_argument("--save-json", action="store_true", help="把每个标的的分析结果落盘 JSON")
    args = ap.parse_args(argv)

    # 打印关键配置
    ov = CFG.get("overlay", default={})
    uni = CFG.get("universe", default=[])
    print(f"[CFG] overlay: {ov}")
    print(f"[CFG] universe size: {len(uni)}")

    # prior 上下文
    ctx_market = _ctx_prior_market()
    print(f"[CTX] prior context: {'ok' if ctx_market else 'fallback'}")

    # 候选
    syms = _symbols_from_overlay()
    if not syms:
        if isinstance(uni, (list, tuple)) and uni and isinstance(uni[0], str):
            syms = list(uni)
        else:
            syms = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","COAIUSDT","CLOUSDT","XPLUSDT"]
    if args.limit and args.limit > 0:
        syms = syms[:args.limit]
    print(f"[CAND] count={len(syms)} examples={syms[:7]}")

    # 落盘目录（可选）
    results_dir = None
    if args.save_json:
        stamp = datetime.now(timezone.utc).strftime("run_%Y%m%d-%H%M%S")
        results_dir = Path("data") / stamp
        results_dir.mkdir(parents=True, exist_ok=True)

    do_send = bool(args.send and telegram_send)

    analyzed = 0
    prime_count = 0
    sent = 0
    fails = 0

    for s in syms:
        try:
            r = analyze_symbol(s, ctx_market=ctx_market)
            analyzed += 1
            pub = r.get("publish") or {}

            txt = render_watch(r)
            print(f"\n==== {s} ====\n{txt}\n", flush=True)

            if pub.get("prime"):
                prime_count += 1

            # 发送
            if do_send and (not args.only_prime or pub.get("prime")):
                try:
                    telegram_send(txt)
                    sent += 1
                    print(f"[SENT] {s}", flush=True)
                except Exception as e:
                    fails += 1
                    print(f"[SEND FAIL] {s} -> {e}", file=sys.stderr, flush=True)

            # 落盘
            if results_dir is not None:
                fn = (results_dir / f"{s}.json")
                with open(fn.as_posix(), "w", encoding="utf-8") as f:
                    json.dump(r, f, ensure_ascii=False, indent=2)

        except Exception as e:
            fails += 1
            print(f"[ANALYZE FAIL] {s} -> {e}", file=sys.stderr, flush=True)

    print("\n—— SUMMARY ——")
    print(f"candidates: {len(syms)}")
    print(f"analyzed:   {analyzed}")
    print(f"prime:      {prime_count}")
    print(f"sent:       {sent}")
    print(f"fails:      {fails}")
    if results_dir is not None:
        print(f"results dir: {results_dir.resolve()}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))