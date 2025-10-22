# coding: utf-8
"""
手动触发单/多币分析并（可选）发送到 Telegram。
- 默认使用「观察」抬头，但版式与正式模板完全一致（render_watch）。
- 如需使用正式抬头，可加 --prime。
- 支持多个符号；--send 开启发送。若设 ATS_SKIP_SEND=1 则即使 --send 也只打印不发送。

示例：
  python3 -m tools.oneoff CLOUSDT COAIUSDT XPLUSDT --send
  python3 -m tools.oneoff BTCUSDT --prime
"""
import os, sys, argparse, traceback

# 不要在标题里出现 [手动]
os.environ.pop("ATS_VIA", None)

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="+", help="符号，如 BTCUSDT/COAIUSDT …")
    parser.add_argument("--send", action="store_true", help="发送到 Telegram")
    parser.add_argument("--prime", action="store_true", help="使用正式抬头（无 🟡 观察 ·）")
    args = parser.parse_args(argv)

    # 上游分析 & 模板（与你当前仓库一致）
    from ats_core.pipeline.analyze_symbol import analyze_symbol
    from ats_core.outputs.telegram_fmt import render_watch, render_prime
    try:
        from ats_core.outputs.publisher import telegram_send
    except Exception:
        telegram_send = None

    had_error = False
    for s in args.symbols:
        sym = s.upper().strip()
        try:
            r = analyze_symbol(sym, ctx_market=None) or {}
            r["symbol"] = sym

            # 版式完全走正式模板；观察仅影响标题前缀（render_watch 内部处理）
            text = render_prime(r) if args.prime else render_watch(r)

            print(f"\n==== {sym} ====\n{text}\n", flush=True)

            if args.send and os.getenv("ATS_SKIP_SEND", "0") != "1":
                if telegram_send:
                    try:
                        telegram_send(text)
                        print(f"[SENT] {sym}", flush=True)
                    except Exception as e:
                        had_error = True
                        print(f"[SEND FAIL] {sym} -> {e}", file=sys.stderr, flush=True)
                        traceback.print_exc()
                else:
                    had_error = True
                    print("[NO TELEGRAM SENDER] telegram_send 不可用", file=sys.stderr, flush=True)

        except Exception as e:
            had_error = True
            print(f"[ANALYZE/RENDER FAIL] {sym} -> {e}", file=sys.stderr, flush=True)
            traceback.print_exc()

    sys.exit(1 if had_error else 0)

if __name__ == "__main__":
    main()