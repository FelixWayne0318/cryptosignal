# coding: utf-8
from __future__ import annotations

import os
import argparse
from typing import Dict, Any

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_watch  # 统一用一个渲染器
from ats_core.outputs.publisher import telegram_send

from ats_core.sources.binance import get_klines, get_open_interest_hist
from ats_core.features.cvd import cvd_from_klines, cvd_mix_with_oi_price, zscore_last


def _ensure_env_for_channel(to: str, chat_id_cli: str | None) -> None:
    """
    选择对应频道的 CHAT_ID（支持 --to trade）。
    优先级：命令行 -> 专用环境变量 -> 通用 TELEGRAM_CHAT_ID
    """
    if chat_id_cli:
        os.environ["TELEGRAM_CHAT_ID"] = chat_id_cli
        return

    # 优先各自专用变量
    if to == "watch":
        cid = os.getenv("TELEGRAM_WATCH_CHAT_ID") or os.getenv("ATS_TELEGRAM_WATCH_CHAT_ID")
    elif to in ("prime", "trade"):
        cid = os.getenv("TELEGRAM_TRADE_CHAT_ID") or os.getenv("ATS_TELEGRAM_TRADE_CHAT_ID")
    elif to == "base":
        cid = os.getenv("TELEGRAM_BASE_CHAT_ID") or os.getenv("ATS_TELEGRAM_BASE_CHAT_ID")
    else:
        cid = None

    # 退化到通用
    if not cid:
        cid = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ATS_TELEGRAM_CHAT_ID")

    if not cid:
        raise RuntimeError("没有可用的 Telegram Chat ID，请设置 TELEGRAM_CHAT_ID 或对应频道专用变量。")

    os.environ["TELEGRAM_CHAT_ID"] = cid


def _last(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x[-1])
    except Exception:
        return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True, dest="symbol", help="例如：BTCUSDT")
    ap.add_argument("--to", choices=("prime", "watch", "base", "trade"), default="watch")
    ap.add_argument("--chat-id", dest="chat_id", default=None, help="覆盖发送目标 Chat ID")
    ap.add_argument("--tag", choices=("prime", "watch", "none", "trade"), default="watch")
    ap.add_argument("--note", default="", help="附加注释（可选）")
    args = ap.parse_args()

    if not (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("ATS_TELEGRAM_BOT_TOKEN")):
        raise RuntimeError("未设置 TELEGRAM_BOT_TOKEN（或 ATS_TELEGRAM_BOT_TOKEN）。")

    # 1) 先跑你原有的分析逻辑
    res: Dict[str, Any] = analyze_symbol(args.symbol)

    # 2) 追加 CVD 指标（不改动你的业务判定，只是“补充字段”）
    k1 = get_klines(args.symbol, "1h", 200)
    oi = get_open_interest_hist(args.symbol, "1h", len(k1))
    cvd = cvd_from_klines(k1)
    _, mix = cvd_mix_with_oi_price(k1, oi)

    res["cvd_z20"] = float(zscore_last(cvd, 20)) if cvd else 0.0
    res["cvd_mix_abs_per_h"] = float(abs(mix[-1])) if mix else 0.0

    # 3) 渲染（统一使用 render_watch，避免模板缺失）
    #    把 symbol/tag/note 附到 res 里，供模板展示（模板里不存在也不会出错）
    payload = dict(res)
    payload["symbol"] = args.symbol
    payload["tag"] = args.tag
    if args.note:
        payload["note"] = args.note

    text = render_watch(payload)

    # 4) 选择目标频道并发送
    _ensure_env_for_channel(args.to, args.chat_id)
    telegram_send(text)


if __name__ == "__main__":
    main()