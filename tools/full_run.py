# coding: utf-8
"""
一次性全流程跑：候选 -> 分析 -> 筛选 -> 渲染 -> (可选) 发送
用法示例：
  # 只看输出（不发）
  python3 -m tools.full_run --limit 20

  # 真正发送到 Telegram（仅 prime）
  python3 -m tools.full_run --send --only-prime

  # 发送所有（prime/watch 都发），并保存每个币的 JSON 结果
  python3 -m tools.full_run --send --save-json --limit 30
"""

from __future__ import annotations
import os, sys, argparse, importlib, json, traceback, time, pathlib
from typing import List, Dict, Any, Optional

# —— 强制使用新版模版：六维恒显 + 解释 + 动态小数位；去掉“[手动]”前缀 ——
os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")
os.environ.setdefault("ATS_FMT_EXPLAIN", "1")
os.environ.setdefault("ATS_FMT_DECIMALS_AUTO", "1")
os.environ.pop("ATS_VIA", None)

from ats_core.cfg import CFG
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_watch, render_prime
from ats_core.sources.klines import klines_1h, split_ohlcv

# 发送器（可选）
try:
    from ats_core.outputs.publisher import telegram_send
except Exception:
    telegram_send = None

REPO = pathlib.Path(__file__).resolve().parents[1]  # ~/ats-analyzer


def _load_market_ctx() -> Dict[str, Any]:
    """预取 BTC/ETH 1h 收盘，供 analyze_symbol 用于 prior 计算。"""
    ctx: Dict[str, Any] = {}
    try:
        btc = klines_1h("BTCUSDT", 300)
        eth = klines_1h("ETHUSDT", 300)
        if btc and eth:
            _, _, _, btc_c, *_ = split_ohlcv(btc)
            _, _, _, eth_c, *_ = split_ohlcv(eth)
            if btc_c and eth_c:
                ctx = {"btc_c": btc_c, "eth_c": eth_c}
    except Exception:
        pass
    return ctx


def _get_candidates(limit: Optional[int]) -> List[str]:
    """优先 overlay_builder；为空则回退到 CFG.universe；再不行用默认集合。"""
    syms: List[str] = []

    # 1) overlay_builder
    try:
        ob = importlib.import_module("ats_core.pools.overlay_builder")
        for name in ("build", "build_overlay", "build_candidates", "build_pool"):
            if hasattr(ob, name):
                arr = getattr(ob, name)()
                if isinstance(arr, list) and arr:
                    if isinstance(arr[0], dict):
                        syms = [x.get("symbol") or x.get("sym") for x in arr if (x.get("symbol") or x.get("sym"))]
                    elif isinstance(arr[0], str):
                        syms = list(arr)
                break
    except Exception as e:
        print(f"[overlay_builder] 加载失败：{e}", file=sys.stderr)

    # 2) universe
    if not syms:
        uni = CFG.get("universe", default=None)
        if isinstance(uni, (list, tuple)) and uni and isinstance(uni[0], str):
            syms = list(uni)

    # 3) 兜底
    if not syms:
        syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "COAIUSDT", "CLOUSDT", "XPLUSDT"]

    if limit and limit > 0:
        syms = syms[:limit]
    return syms


def _decide_text(res: Dict[str, Any]) -> str:
    """依据 prime/watch 选择模版；默认 watch 更安全。"""
    pub = res.get("publish") or {}
    return render_prime(res) if pub.get("prime") else render_watch(res)


def _maybe_send(txt: str) -> bool:
    """如配置成功，发送到 Telegram。返回是否发送成功。"""
    if telegram_send is None:
        print("[SEND] 跳过（未配置 telegram_send）")
        return False
    try:
        telegram_send(txt)
        return True
    except Exception as e:
        print(f"[SEND FAIL] -> {e}", file=sys.stderr)
        traceback.print_exc()
        return False


def _save_json(res_dir: pathlib.Path, sym: str, res: Dict[str, Any]) -> None:
    res_dir.mkdir(parents=True, exist_ok=True)
    p = res_dir / f"{sym}.json"
    with p.open("w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="发送到 Telegram（默认只打印不发）")
    ap.add_argument("--only-prime", dest="only_prime", action="store_true", help="仅发送 prime=True 的信号")
    ap.add_argument("--limit", type=int, default=24, help="最多处理多少个候选")
    ap.add_argument("--save-json", action="store_true", help="保存 analyze 结果 JSON 到 data/run_*/")
    ap.add_argument("--dry-run", action="store_true", help="强制不发送（即便带了 --send）")
    args = ap.parse_args(argv)

    # 运行信息
    overlay_cfg = CFG.get("overlay", default={})
    uni = CFG.get("universe", default=[])
    print(f"[CFG] overlay: {overlay_cfg}")
    print(f"[CFG] universe size: {len(uni)}")
    ctx = _load_market_ctx()
    print(f"[CTX] prior context: {'ok' if ctx else 'empty'}")

    syms = _get_candidates(args.limit)
    print(f"[CAND] count={len(syms)} examples={syms[:10]}")

    run_id = time.strftime("%Y%m%d-%H%M%S")
    out_dir = REPO / "data" / f"run_{run_id}"

    sent = 0
    fails = 0
    analyzed = 0
    primes = 0

    for s in syms:
        try:
            res = analyze_symbol(s, ctx_market=ctx)
            analyzed += 1

            pub = res.get("publish") or {}
            if pub.get("prime"):
                primes += 1

            txt = _decide_text(res)
            print(f"\n==== {s} ====\n{txt}\n", flush=True)

            if args.save_json:
                try:
                    _save_json(out_dir, s, res)
                except Exception as e:
                    print(f"[SAVE JSON FAIL] {s}: {e}", file=sys.stderr)

            do_send = args.send and (not args.dry_run)
            # —— 修复点：使用 args.only_prime 而不是 args.only-prime ——
            if do_send and args.only_prime and (not pub.get("prime")):
                # 仅 prime，跳过非 prime
                continue

            if do_send:
                ok = _maybe_send(txt)
                sent += int(ok)

        except Exception as e:
            fails += 1
            print(f"[ANALYZE FAIL] {s} -> {e}", file=sys.stderr)
            traceback.print_exc()

    print("\n—— SUMMARY ——")
    print(f"candidates: {len(syms)}")
    print(f"analyzed:   {analyzed}")
    print(f"prime:      {primes}")
    print(f"sent:       {sent}")
    print(f"fails:      {fails}")
    if args.save_json:
        print(f"results dir: {out_dir}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))