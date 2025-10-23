# coding: utf-8
"""
tools/send_symbol.py
手动发送“正式模板”信号的统一入口：
- 解析命令行参数（symbol / to / note / tag / ttl）
- 调用 analyze_symbol 产出指标
- 用 telegram_fmt 的正式模板渲染
- 依据 --to 选择合适的 Telegram Chat 并发送
"""

from __future__ import annotations
import os
import sys
import argparse
from typing import Any, Dict

# --- 业务依赖 ---
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.publisher import telegram_send

# 模板渲染：优先直接用 render_signal（可区分“观察/正式”）；若老版本仅有 render_watch，则降级兼容
try:
    from ats_core.outputs.telegram_fmt import render_signal, render_watch  # type: ignore
    HAS_RENDER_SIGNAL = True
except Exception:
    from ats_core.outputs.telegram_fmt import render_watch  # type: ignore
    HAS_RENDER_SIGNAL = False
    def render_signal(r: Dict[str, Any], is_watch: bool = True) -> str:
        # 兼容兜底：没有 render_signal 就用 render_watch（样式可能少“正式”的标题）
        return render_watch(r)


def _choose_chat_id(dest: str, override_chat: str | None) -> str:
    """
    依据 --to 选择 Chat：
      - trade/prime -> TELEGRAM_TRADE_CHAT_ID or TELEGRAM_PRIME_CHAT_ID or TELEGRAM_CHAT_ID
      - watch/base  -> TELEGRAM_WATCH_CHAT_ID or TELEGRAM_CHAT_ID
    手动指定 --chat-id 优先。
    """
    if override_chat:
        return override_chat

    env = os.environ
    if dest in ("trade", "prime"):
        return (
            env.get("TELEGRAM_TRADE_CHAT_ID")
            or env.get("TELEGRAM_PRIME_CHAT_ID")
            or env.get("TELEGRAM_CHAT_ID", "")
        )
    else:
        return env.get("TELEGRAM_WATCH_CHAT_ID") or env.get("TELEGRAM_CHAT_ID", "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True, help="如：BTCUSDT")
    parser.add_argument(
        "--to",
        default="watch",
        choices=["watch", "trade", "prime", "base"],
        help="发送目标：watch(观察) / trade(正式) / prime(正式别名) / base",
    )
    parser.add_argument(
        "--chat-id",
        default=None,
        help="可手动覆盖目标 Chat ID；不传则按 --to 走环境变量映射",
    )
    parser.add_argument(
        "--tag",
        default="none",
        choices=["watch", "trade", "prime", "none"],
        help="附加在消息末尾的标签（#watch/#trade/#prime），不影响模板本身",
    )
    parser.add_argument(
        "--note",
        default="",
        help="备注说明，出现在模板的备注段落",
    )
    parser.add_argument(
        "--ttl-h",
        type=int,
        default=8,
        help="模板 TTL（小时），默认 8h",
    )
    args = parser.parse_args()

    # 1) 分析
    res: Dict[str, Any] = analyze_symbol(args.symbol)
    if not isinstance(res, dict):
        print("analyze_symbol 未返回 dict，发送中止。", file=sys.stderr)
        sys.exit(1)

    # 2) 组装渲染 payload
    payload: Dict[str, Any] = dict(res)
    payload["symbol"] = args.symbol
    if args.note:
        payload["note"] = args.note

    # TTL / publish 信息（模板会读取）
    publish = dict(payload.get("publish") or {})
    publish.setdefault("ttl_h", args.ttl_h)
    publish["dest"] = args.to
    payload["publish"] = publish

    # 3) 模板渲染（统一用正式模板通道）
    is_watch = args.to in ("watch", "base")
    try:
        text = render_signal(payload, is_watch=is_watch)
    except TypeError:
        # 万一老版本 render_signal 签名不带 is_watch，就降级
        text = render_watch(payload) if is_watch else render_signal(payload)

    # 可选：附加一个纯标签行，不改变模板主体
    if args.tag != "none":
        text = f"{text}\n#{args.tag}"

    # 4) 选择 Chat 并发送
    chat_id = _choose_chat_id(args.to, args.chat_id)
    if not chat_id:
        print(
            "❌ 未找到可用 Chat ID。请设置：\n"
            "  - 观察：TELEGRAM_WATCH_CHAT_ID 或 TELEGRAM_CHAT_ID\n"
            "  - 正式：TELEGRAM_TRADE_CHAT_ID 或 TELEGRAM_PRIME_CHAT_ID 或 TELEGRAM_CHAT_ID",
            file=sys.stderr,
        )
        sys.exit(2)

    # publisher.telegram_send 读取 TELEGRAM_CHAT_ID，这里临时覆盖确保发到正确频道
    os.environ["TELEGRAM_CHAT_ID"] = chat_id
    telegram_send(text)
    print(f"✅ 已发送：symbol={args.symbol} to={args.to} chat={chat_id}")


if __name__ == "__main__":
    main()