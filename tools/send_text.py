# coding: utf-8
from __future__ import annotations
import os, argparse
from ats_core.outputs.publisher import telegram_send

def pick_chat_id(dest: str|None, chat_id_cli: str|None) -> str:
    if chat_id_cli:
        return chat_id_cli
    # 正式/观察/默认三路
    envs = []
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
    ap = argparse.ArgumentParser(description="手动发送纯文本到 Telegram（不跑分析）")
    ap.add_argument("--to", choices=["prime","watch","base"], default="base",
                    help="发送目标：prime / watch / base(默认)")
    ap.add_argument("--chat-id", default=None, help="直接指定 chat_id（覆盖 --to）")
    ap.add_argument("--tag", choices=["prime","watch","none"], default="none",
                    help="自动加【正式】/【观察】标签")
    ap.add_argument("text", help="要发送的文本（支持 HTML）")
    args = ap.parse_args()

    cid = pick_chat_id(args.to, args.chat_id)
    if not cid:
        raise SystemExit("❌ 没有可用 chat_id，请导出 TELEGRAM_CHAT_ID* 或用 --chat-id 指定。")

    txt = args.text
    if args.tag == "prime":
        txt = "【正式】\n" + txt
    elif args.tag == "watch":
        txt = "【观察】\n" + txt

    # 不改 publisher 签名：用环境变量临时指定目标频道
    os.environ["TELEGRAM_CHAT_ID"] = cid
    os.environ["ATS_TELEGRAM_CHAT_ID"] = cid
    telegram_send(txt)

if __name__ == "__main__":
    main()