# coding: utf-8
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime

from ats_core.cfg import CFG
from ats_core.outputs.telegram_fmt import render_watch
from ats_core.outputs.publisher import telegram_send

def _bool(v):  # 兼容 '1'/'true'/'yes'
    return str(v).lower() in ("1","true","yes","y","on")

def _env(name: str, default=None):
    return os.getenv(name, default)

def _pick_universe(limit: int):
    # 先用 overlay 候选，其次用 params.universe，最后内置主流兜底
    try:
        from ats_core.pools import overlay_builder
        cands = overlay_builder.build()
        if isinstance(cands, list) and cands:
            return cands[:limit]
    except Exception:
        pass
    uni = CFG.get("universe", default=[])
    if isinstance(uni, list) and uni:
        return uni[:limit]
    fallback = [
        "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","MATICUSDT","DOTUSDT","LTCUSDT","BCHUSDT"
    ]
    return fallback[:limit]

def _analyze(symbol: str):
    from ats_core.pipeline.analyze_symbol import analyze_symbol
    return analyze_symbol(symbol)

def route_chat_id(is_prime: bool,
                  args_chat_prime: str|None,
                  args_chat_watch: str|None) -> str|None:
    """
    选择发送目标：
      1) CLI 覆盖：--prime-chat-id / --watch-chat-id
      2) 环境变量：TELEGRAM_CHAT_ID_PRIME / TELEGRAM_CHAT_ID_WATCH
      3) 回退：TELEGRAM_CHAT_ID / ATS_TELEGRAM_CHAT_ID
    """
    env_prime = _env("TELEGRAM_CHAT_ID_PRIME") or _env("ATS_TELEGRAM_CHAT_ID_PRIME")
    env_watch = _env("TELEGRAM_CHAT_ID_WATCH") or _env("ATS_TELEGRAM_CHAT_ID_WATCH")
    base      = _env("TELEGRAM_CHAT_ID") or _env("ATS_TELEGRAM_CHAT_ID")

    if is_prime:
        return args_chat_prime or env_prime or base
    else:
        return args_chat_watch or env_watch or base

def maybe_tag(text: str, is_prime: bool, add_tags: bool) -> str:
    if not add_tags:
        return text
    prefix = "【正式】" if is_prime else "【观察】"
    return f"{prefix}\n{text}"

def main():
    ap = argparse.ArgumentParser(description="全流程跑一遍，支持分流路由 prime/observe")
    ap.add_argument("--limit", type=int, default=30, help="最多分析多少个标的")
    ap.add_argument("--send", action="store_true", help="真的发送到 Telegram")
    ap.add_argument("--only-prime", dest="only_prime", action="store_true", help="仅发送 prime=True 的信号")
    ap.add_argument("--only-watch", dest="only_watch", action="store_true", help="仅发送 非 prime 的信号")
    ap.add_argument("--save-json", action="store_true", help="把每个标的结果落盘 JSON")
    ap.add_argument("--prime-chat-id", type=str, default=None, help="正式信号发送到的 Chat ID（覆盖环境变量）")
    ap.add_argument("--watch-chat-id", type=str, default=None, help="观察信号发送到的 Chat ID（覆盖环境变量）")
    ap.add_argument("--add-tags", action="store_true", help="在文本前添加【正式】/【观察】标签")
    args = ap.parse_args()

    # 读取一些 overlay 阈值做开场回显（便于排查）
    overlay = CFG.get("overlay", default={})
    print("[CFG] overlay:", overlay)
    uni = CFG.get("universe", default=[])
    print("[CFG] universe size:", len(uni))

    symbols = _pick_universe(args.limit)
    print("[CAND] count={} examples={}".format(len(symbols), symbols[:7]))

    out_rows = []
    prime_cnt = 0
    send_cnt  = 0
    fail_cnt  = 0

    # 结果保存目录
    results_dir = Path("data") / ("run_" + datetime.utcnow().strftime("%Y%m%d-%H%M%S"))
    if args.save_json:
        results_dir.mkdir(parents=True, exist_ok=True)

    for s in symbols:
        try:
            res = _analyze(s)
            if not isinstance(res, dict):
                raise RuntimeError("analyze_symbol 返回非 dict")
            res["symbol"] = s
            is_prime = bool(res.get("prime", False))

            # 过滤逻辑
            if args.only_prime and not is_prime:
                continue
            if args.only_watch and is_prime:
                continue

            # 渲染 & 打印
            txt = render_watch(res)
            if args.add_tags:
                txt = maybe_tag(txt, is_prime, add_tags=True)

            print(f"\n==== {s} ====\n{txt}\n")

            # 发送
            if args.send:
                cid = route_chat_id(is_prime, args.prime_chat_id, args.watch_chat_id)
                telegram_send(txt, chat_id=cid)
                send_cnt += 1

            if is_prime:
                prime_cnt += 1

            if args.save_json:
                Path(results_dir / f"{s}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))

            out_rows.append({"symbol": s, "prime": is_prime, "ok": True})
        except Exception as e:
            fail_cnt += 1
            print(f"[ANALYZE FAIL] {s} -> {e}")

    print("\n—— SUMMARY ——")
    print(f"candidates: {len(symbols)}")
    print(f"analyzed:   {len(out_rows)}")
    print(f"prime:      {prime_cnt}")
    print(f"sent:       {send_cnt}")
    print(f"fails:      {fail_cnt}")
    if args.save_json:
        print(f"results dir: {results_dir}")

if __name__ == "__main__":
    main()