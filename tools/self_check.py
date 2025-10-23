# coding: utf-8
from __future__ import annotations

import os
import sys
import time
import json
import importlib
import platform
from typing import Any, Dict, List

EXIT_CODE = 0

def ok(msg: str) -> None:
    print(f"[OK] {msg}")

def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

def fail(msg: str) -> None:
    global EXIT_CODE
    print(f"[FAIL] {msg}")
    EXIT_CODE = 1

def main(argv: List[str]) -> int:
    # 0) Python 版本
    pyv = sys.version_info
    if (pyv.major, pyv.minor) < (3, 8):
        fail(f"Python >= 3.8 要求，当前 {pyv.major}.{pyv.minor}")
    else:
        ok(f"Python {pyv.major}.{pyv.minor} OK")

    # 1) 加载配置
    try:
        from ats_core.cfg import CFG
    except Exception as e:
        fail(f"导入 ats_core.cfg 失败：{e}")
        return EXIT_CODE

    try:
        p: Dict[str, Any] = CFG.params or {}
        if not p:
            fail("CFG.params 为空，说明配置未加载")
        else:
            ok("CFG.params 加载成功")

        # 校验必须参数
        trend = p.get("trend", {})
        overlay = p.get("overlay", {})
        uni = p.get("universe", [])

        need_trend_keys = ["ema_order_min_bars", "slope_atr_min_long", "slope_atr_min_short", "slope_lookback", "atr_period"]
        miss = [k for k in need_trend_keys if trend.get(k) is None]
        if miss:
            fail(f"trend 缺少关键参数：{miss}")
        else:
            ok(f"trend 参数完整：{ {k: trend[k] for k in need_trend_keys} }")

        need_overlay_keys = ["oi_1h_pct_big", "oi_1h_pct_small", "hot_decay_hours"]
        miss2 = [k for k in need_overlay_keys if overlay.get(k) is None]
        if miss2:
            fail(f"overlay 缺少关键参数：{miss2}")
        else:
            ok(f"overlay 参数：{ {k: overlay[k] for k in need_overlay_keys} }")

        if isinstance(uni, (list, tuple)) and len(uni) > 0 and isinstance(uni[0], str):
            ok(f"universe 数量：{len(uni)}")
        else:
            warn("universe 为空或无效（不是硬性错误，后续会回退到常见主流币）")

        # 兼容性：验证 CFG.get 三种用法均可
        try:
            _a = CFG.get("overlay", {})
            _b = CFG.get("overlay", default={})
            _c = CFG.get("overlay", {}, default={})
            if not isinstance(_a, dict) or not isinstance(_b, dict) or not isinstance(_c, dict):
                fail("CFG.get 返回类型异常（不是 dict）")
            else:
                ok("CFG.get(*, default=*) 兼容性 OK")
        except Exception as e:
            fail(f"CFG.get 兼容性问题：{e}")

    except Exception as e:
        fail(f"读取 CFG.params 失败：{e}")
        return EXIT_CODE

    # 2) Overlay 候选构建
    try:
        ob = importlib.import_module("ats_core.pools.overlay_builder")
        cands = ob.build()
        if isinstance(cands, list):
            ok(f"overlay 构建 OK，候选数：{len(cands)}")
        else:
            warn("overlay 构建返回的不是列表")
    except Exception as e:
        warn(f"overlay 构建失败：{e}")

    # 3) 单标的分析与渲染
    try:
        analyze_symbol = importlib.import_module("ats_core.pipeline.analyze_symbol").analyze_symbol
        render_watch = importlib.import_module("ats_core.outputs.telegram_fmt").render_watch
    except Exception as e:
        fail(f"导入分析/渲染模块失败：{e}")
        return EXIT_CODE

    test_syms: List[str] = []
    if isinstance(uni, (list, tuple)) and uni and isinstance(uni[0], str):
        test_syms.extend(list(uni[:5]))
    # fallback 主流
    for s in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]:
        if s not in test_syms:
            test_syms.append(s)

    analyzed_ok = 0
    for s in test_syms:
        try:
            r = analyze_symbol(s)
            if not isinstance(r, dict):
                warn(f"analyze_symbol({s}) 返回非 dict")
                continue
            r["symbol"] = s
            txt = render_watch(r)
            if isinstance(txt, str) and ("六" in txt or "<b>" in txt):
                ok(f"分析+渲染 OK：{s}")
                analyzed_ok += 1
                break
            else:
                warn(f"渲染文本异常：{s}")
        except Exception as e:
            warn(f"分析失败 {s} -> {e}")

    if analyzed_ok == 0:
        fail("所有测试符号 analyze/render 失败")

    # 4) Telegram 发送连通性（只在 env 设置时测试）
    bot = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("ATS_TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ATS_TELEGRAM_CHAT_ID")
    if bot and chat:
        try:
            telegram_send = importlib.import_module("ats_core.outputs.publisher").telegram_send
            telegram_send(f"✅ 自检通过 {time.strftime('%F %T')} @ {platform.node()}")
            ok("telegram_send 发送 OK（已连接）")
        except Exception as e:
            warn(f"telegram_send 失败：{e}")
    else:
        warn("未设置 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID，跳过连通性测试")

    print("\n—— SELF-CHECK SUMMARY ——")
    print(f"exit_code: {EXIT_CODE}")
    return EXIT_CODE

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))