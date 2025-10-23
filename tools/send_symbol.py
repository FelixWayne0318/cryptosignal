# tools/send_symbol.py
# coding: utf-8
from __future__ import annotations
import argparse
import os

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_watch

# 兼容只提供 telegram_send(text) 的场景
try:
    from ats_core.outputs.publisher import telegram_send_to as _send_to  # type: ignore
except Exception:
    _send_to = None
from ats_core.outputs.publisher import telegram_send  # type: ignore

TO_ALIAS = {"trade": "prime"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True, dest="symbol")
    ap.add_argument("--to", choices=["prime", "watch", "base", "trade"], default="watch")
    ap.add_argument("--tag", choices=["prime", "watch", "none", "trade"], default="watch")
    ap.add_argument("--note", default="")
    ap.add_argument("--chat-id", dest="chat_id", default=None)
    args = ap.parse_args()

    dest = TO_ALIAS.get(args.to, args.to)
    tag  = TO_ALIAS.get(args.tag, args.tag)

    res = analyze_symbol(args.symbol)
    # 渲染
    txt = render_watch(dict(res, symbol=args.symbol))
    if args.note:
        txt = f"{args.note}\n\n{txt}"

    # 发送
    chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ATS_TELEGRAM_CHAT_ID")
    if _send_to is not None:
        try:
            _send_to(txt, to=dest, chat_id=chat_id)
            return
        except TypeError:
            pass  # 回退到简单接口
    telegram_send(txt)

if __name__ == "__main__":
    main()