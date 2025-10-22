# coding: utf-8
"""
整套全流程执行：取候选 -> 分析 -> 渲染 -> （可选）发送 -> 汇总

示例：
  # 仅打印，不发
  python3 -m tools.full_run --limit 24

  # 仅发送 prime=True 的
  python3 -m tools.full_run --send --only-prime

  # 全部发送并保存 JSON
  python3 -m tools.full_run --send --save-json --limit 30
"""

import sys
import os
import json
import argparse
import importlib
from datetime import datetime

# 模板显示控制
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")

from ats_core.cfg import CFG
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_watch
from ats_core.sources.klines import klines_1h, split_ohlcv

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


def _ctx_prior_market():
    """构造 BTC/ETH 1h 收盘序列，供 prior_up 计算使用"""
    try:
        b = klines_1h("BTCUSDT", 300)
        e = klines_1h("ETHUSDT", 300)
        _, _, _, bc, *_ = split_ohlcv(b)
        _, _, _, ec, *_ = split_ohlcv(e)
        if len(bc) >= 120 and len(ec) >= 120:
            return {"btc_c": bc, "eth_c": ec}
    except Exception:
        pass
    return None


def _get_candidates(limit=None):
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
    ap.add_argument("--only-prime", dest="only_prime", action="store_true",
                    help="只发送 prime=True 的信号（打印仍全量）")
    ap.add_argument("--limit", type=int, default=24, help="最多处理多少个候选")
    ap.add_argument("--save-json", action="store_true", help="保存每个符号的分析 JSON 到 data/run_* 目录")
    args = ap.parse_args(argv)

    # 打印配置概览
    overlay_cfg = CFG.get("overlay", default={})
    uni = CFG.get("universe", default=[])
    if not isinstance(uni, (list, tuple)):
        uni = []
    print(f"[CFG] overlay: {overlay_cfg}")
    print(f"[CFG] universe size: {len([s for s in uni if isinstance(s, str)])}")

    # prior 上下文
    ctx_market = _ctx_prior_market()
    print(f"[CTX] prior context: {'ok' if ctx_market else 'fallback'}")

    # 候选
    syms = _get_candidates(limit=args.limit)
    print(f"[CAND] count={len(syms)} examples={syms[:7]}")

    # 保存目录
    results_dir = None
    if args.save_json:
        results_dir = os.path.join("data", f"run_{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}")
        os.makedirs(results_dir, exist_ok=True)

    # 遍历分析
    analyzed = 0
    sent = 0
    prime_cnt = 0
    fails = 0

    for s in syms:
        try:
            r = analyze_symbol(s, ctx_market=ctx_market)
            r["symbol"] = s
            pub = r.get("publish") or {}
            txt = render_watch(r)

            print(f"\n==== {s} ====\n{txt}\n", flush=True)

            if pub.get("prime"):
                prime_cnt += 1

            # 发送逻辑
            if args.send and telegram_send:
                if (not args.only_prime) or pub.get("prime"):
                    try:
                        telegram_send(txt)
                        sent += 1
                    except Exception as e:
                        fails += 1
                        print(f"[SEND FAIL] {s} -> {e}", file=sys.stderr, flush=True)

            # 保存 JSON
            if results_dir:
                try:
                    with open(os.path.join(results_dir, f"{s}.json"), "w", encoding="utf-8") as f:
                        json.dump(r, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"[SAVE FAIL] {s} -> {e}", file=sys.stderr, flush=True)

            analyzed += 1
        except Exception as e:
            fails += 1
            print(f"[ANALYZE FAIL] {s} -> {e}", file=sys.stderr, flush=True)

    # 汇总
    print("\n—— SUMMARY ——")
    print(f"candidates: {len(syms)}")
    print(f"analyzed:   {analyzed}")
    print(f"prime:      {prime_cnt}")
    print(f"sent:       {sent}")
    print(f"fails:      {fails}")
    if results_dir:
        print(f"results dir: {os.path.abspath(results_dir)}")

    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))