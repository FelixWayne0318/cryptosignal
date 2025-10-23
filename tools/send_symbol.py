# coding: utf-8
from __future__ import annotations
import os, argparse
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_watch
from ats_core.outputs.publisher import telegram_send

def pick_chat_id(dest: str|None, chat_id_cli: str|None) -> str:
    if chat_id_cli:
        return chat_id_cli
    if dest == "prime":
        envs = ["TELEGRAM_CHAT_ID_PRIME","ATS_TELEGRAM_CHAT_ID_PRIME",
                "TELEGRAM_CHAT_ID","ATS_TELEGRAM_CHAT_ID"]
    elif dest == "watch":
        envs = ["TELEGRAM_CHAT_ID_WATCH","ATS_TELEGRAM_CHAT_ID_WATCH",
                "TELEGRAM_CHAT_ID","ATS_TELEGRAM_CHAT_ID"]
    else:
        envs = ["TELEGRAM_CHAT_ID","ATS_TELEGRAM_CHAT_ID"]
    for k in envs:
        v = os.getenv(k)
        if v:
            return v
    return ""

def main():
    ap = argparse.ArgumentParser(description="强制渲染并发送某个标的（忽略 prime/观察判定）")
    ap.add_argument("--symbol", required=True, help="如 BTCUSDT")
    ap.add_argument("--to", choices=["prime","watch","base"], default="base")
    ap.add_argument("--chat-id", default=None)
    ap.add_argument("--tag", choices=["prime","watch","none"], default="none")
    ap.add_argument("--note", default="", help="附加在文首的一段备注")
    args = ap.parse_args()

    res = analyze_symbol(args.symbol)
    res["symbol"] = args.symbol
    txt = render_watch(res)
    if args.note:
        txt = f"{args.note}\n{txt}"
    if args.tag == "prime":
        txt = "【正式】\n" + txt
    elif args.tag == "watch":
        txt = "【观察】\n" + txt

    cid = pick_chat_id(args.to, args.chat_id)
    if not cid:
        raise SystemExit("❌ 没有可用 chat_id，请导出 TELEGRAM_CHAT_ID* 或用 --chat-id 指定。")
    os.environ["TELEGRAM_CHAT_ID"] = cid
    os.environ["ATS_TELEGRAM_CHAT_ID"] = cid
    telegram_send(txt)

if __name__ == "__main__":
    main()