# coding: utf-8
"""
扫描候选并渲染 watch 文本（可选择发送到 Telegram）

示例：
  # 仅打印
  python3 -m tools.scan_watch --n 12

  # 打印并发送到 Telegram
  python3 -m tools.scan_watch --n 12 --send

  # 仅发送 prime=True 的（打印仍全量，便于人工复核）
  python3 -m tools.scan_watch --n 12 --send --only-prime
"""

import sys
import argparse
import importlib
import os

# 让模板恒显六维 + 解释 + 动态小数位
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


def _normalize_symbols(pool):
    """接受 overlay_builder 返回的 list[dict] 或 list[str]，统一提取符号列表"""
    if not isinstance(pool, list) or not pool:
        return []
    if isinstance(pool[0], dict):
        out = []
        for it in pool:
            s = it.get("symbol") or it.get("sym") or it.get("ticker")
            if isinstance(s, str):
                out.append(s)
        return out
    if isinstance(pool[0], str):
        return pool
    return []


def get_candidates(limit=None):
    syms = []
    # 优先 overlay_builder
    try:
        ob = importlib.import_module("ats_core.pools.overlay_builder")
        for name in ("build", "build_overlay", "build_candidates", "build_pool"):
            if hasattr(ob, name):
                arr = getattr(ob, name)()
                syms = _normalize_symbols(arr)
                break
    except Exception:
        pass

    # 退化到 universe
    if not syms:
        uni = CFG.get("universe", default=None)
        if isinstance(uni, (list, tuple)):
            syms = [s for s in uni if isinstance(s, str)]

    # 最后兜底
    if not syms:
        syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "COAIUSDT", "CLOUSDT", "XPLUSDT"]

    return syms[:limit] if (limit and limit > 0) else syms


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="发送到 Telegram")
    ap.add_argument("--n", type=int, default=12, help="最多处理多少个候选")
    ap.add_argument("--only-prime", dest="only_prime", action="store_true",
                    help="只发送 prime=True 的（打印仍全量）")
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

            # 仅在需要时发送；--only-prime 只在“发送层面”生效
            if args.send and telegram_send:
                if (not args.only_prime) or pub.get("prime"):
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