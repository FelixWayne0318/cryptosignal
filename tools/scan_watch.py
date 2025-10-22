# coding: utf-8
"""
批量扫描候选池并输出（可选发送到 Telegram）：

- 候选池优先来自 ats_core.pools.overlay_builder.build()
  * 支持返回 list[dict]（含 symbol）或 list[str]
- 若无 overlay 候选，则退回 CFG.universe；再没有则给一组常用符号兜底
- 输出统一走 render_watch 模板（已开启：六维恒显 + 自动解释 + 动态小数位）
- 可用 --only-prime 控制“仅发送 prime=True 的信号”（打印仍可全量，便于人工复核）
"""

from __future__ import annotations
import sys
import os
import argparse
import importlib
from typing import List

# 让模板恒显 六维 + 解释 + 动态小数位
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


def _normalize_candidates(arr) -> List[str]:
    """
    将 overlay_builder 返回的结果归一为符号列表：
      - 若是 list[dict]，尝试取 "symbol"/"sym"/"ticker"
      - 若是 list[str]，原样返回
    否则返回空列表
    """
    if isinstance(arr, list) and arr:
        if isinstance(arr[0], dict):
            out = []
            for it in arr:
                sym = it.get("symbol") or it.get("sym") or it.get("ticker")
                if sym:
                    out.append(sym)
            return out
        if isinstance(arr[0], str):
            return list(arr)
    return []


def get_candidates(limit: int | None = None) -> List[str]:
    """获取候选符号列表，按优先级：overlay_builder -> CFG.universe -> 兜底清单。"""
    syms: List[str] = []

    # 1) 试 overlay_builder
    try:
        ob = importlib.import_module("ats_core.pools.overlay_builder")
        for name in ("build", "build_overlay", "build_candidates", "build_pool"):
            if hasattr(ob, name):
                raw = getattr(ob, name)()
                syms = _normalize_candidates(raw)
                if syms:
                    break
    except Exception:
        pass

    # 2) 退回 CFG.universe
    if not syms:
        uni = CFG.get("universe", default=None)
        if isinstance(uni, (list, tuple)) and uni and isinstance(uni[0], str):
            syms = list(uni)

    # 3) 兜底
    if not syms:
        syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "COAIUSDT", "CLOUSDT", "XPLUSDT"]

    return syms[:limit] if (limit and limit > 0) else syms


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="发送到 Telegram")
    ap.add_argument("--n", type=int, default=12, help="最多处理多少个候选")
    ap.add_argument(
        "--only-prime",
        action="store_true",
        help="仅发送 prime=True 的（默认全部作为 watch 打印；发送时按该开关过滤）",
    )
    args = ap.parse_args(argv)

    syms = get_candidates(limit=args.n)
    if not syms:
        print("候选池为空")
        return 2

    send_enabled = bool(args.send and telegram_send)
    failed = 0

    for s in syms:
        try:
            r = analyze_symbol(s)  # analyze_symbol(symbol, ctx_market=None) 兼容
            r["symbol"] = s
            pub = (r.get("publish") or {})
            txt = render_watch(r)

            # 控制台打印，便于人工复核
            print(f"\n==== {s} ====\n{txt}\n", flush=True)

            # 仅在需要时发送；--only-prime 只在发送层面生效
            if send_enabled:
                if (not args.only_prime) or pub.get("prime"):
                    try:
                        telegram_send(txt)
                        print(f"[SENT] {s}", flush=True)
                    except Exception as e:
                        failed += 1
                        print(f"[SEND FAIL] {s} -> {e}", file=sys.stderr, flush=True)
        except Exception as e:
            failed += 1
            print(f"[ANALYZE FAIL] {s} -> {e}", file=sys.stderr, flush=True)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))