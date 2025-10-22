# coding: utf-8
"""
scan_watch: 读取候选池(overlay_builder 或 universe)，逐个调用 analyze_symbol，
把六维分析渲染成文案；可选择发送到 Telegram。
支持直接在命令行传入若干 symbol，跳过候选池。
"""
from __future__ import annotations
import os
import sys
import argparse
import importlib

# 统一输出风格（六维+解释+自动小数位），可被外部覆盖
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

from ats_core.cfg import CFG
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_watch

try:
    from ats_core.outputs.publisher import telegram_send  # 可选
except Exception:
    telegram_send = None


def _symbols_from_overlay(limit: int | None) -> list[str]:
    """
    优先从 overlay_builder 获取候选；否则退化到 config.universe；
    最后兜底给一小组常见合约。
    """
    # 1) overlay_builder（若存在）
    try:
        ob = importlib.import_module("ats_core.pools.overlay_builder")
        for name in ("build", "build_overlay", "build_candidates", "build_pool"):
            if hasattr(ob, name):
                arr = getattr(ob, name)()
                if isinstance(arr, list) and arr:
                    # 兼容 [{'symbol': 'BTCUSDT', ...}] 或 ['BTCUSDT', ...]
                    if isinstance(arr[0], dict):
                        syms = [x.get("symbol") or x.get("sym") or x.get("ticker")
                                for x in arr if (x.get("symbol") or x.get("sym") or x.get("ticker"))]
                    else:
                        syms = [str(x) for x in arr]
                    return syms[:limit] if (limit and limit > 0) else syms
    except Exception:
        pass

    # 2) universe
    uni = CFG.get("universe", default=None)
    if isinstance(uni, (list, tuple)) and uni and isinstance(uni[0], str):
        syms = list(uni)
        return syms[:limit] if (limit and limit > 0) else syms

    # 3) 兜底
    fallback = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "COAIUSDT", "CLOUSDT", "XPLUSDT"]
    return fallback[:limit] if (limit and limit > 0) else fallback


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="扫描候选并输出六维分析（可选发送 Telegram）")
    ap.add_argument("--send", action="store_true", help="发送到 Telegram（默认只打印）")
    ap.add_argument("--n", type=int, default=12, help="最多处理多少个候选")
    ap.add_argument("--only-prime", dest="only_prime", action="store_true",
                    help="只发送 prime=True 的信号（打印仍然全量，便于复核）")
    ap.add_argument("symbols", nargs="*", help="可选：直接指定若干 symbol，跳过候选池")

    args = ap.parse_args(argv)
    do_send = args.send and (telegram_send is not None)

    # 符号来源：优先命令行显式符号；否则从 overlay/universe 获取
    if args.symbols:
        syms = [s.upper() for s in args.symbols]
    else:
        syms = _symbols_from_overlay(limit=args.n)

    if not syms:
        print("候选池为空")
        return 2

    fail = 0
    sent = 0
    prime_cnt = 0

    for s in syms:
        try:
            r = analyze_symbol(s)
            r["symbol"] = s
            pub = r.get("publish") or {}
            txt = render_watch(r)

            print(f"\n==== {s} ====\n{txt}\n", flush=True)

            if pub.get("prime"):
                prime_cnt += 1

            # 仅在需要时发送；--only-prime 只影响发送层面
            if do_send and (not args.only_prime or pub.get("prime")):
                try:
                    telegram_send(txt)
                    sent += 1
                    print(f"[SENT] {s}", flush=True)
                except Exception as e:
                    fail += 1
                    print(f"[SEND FAIL] {s} -> {e}", file=sys.stderr, flush=True)

        except Exception as e:
            fail += 1
            print(f"[ANALYZE FAIL] {s} -> {e}", file=sys.stderr, flush=True)

    print(f"\n—— SUMMARY ——\n"
          f"candidates: {len(syms)}\n"
          f"analyzed:   {len(syms) - fail}\n"
          f"prime:      {prime_cnt}\n"
          f"sent:       {sent}\n"
          f"fails:      {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))