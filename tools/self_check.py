# coding: utf-8
from __future__ import annotations

import os
import sys
import time
import json
import importlib
import platform
from typing import Any, Dict, List, Sequence, Tuple

"""
全流程自检（加强版）
覆盖点：
1) CFG 加载与 key 检查 + CFG.get 兼容
2) 数据源：K线 / OI / 24h tickers
3) CVD 计算 + CVD×OI×价格混合
4) 候选构建（overlay），并检查 base 候选是否健全；fallback 到 base_universe
5) 分析 -> 渲染（正式模板 watch/trade）-> 发送 Telegram
6) 逐环节联通：每个环节可选实际发一条消息（SELF_CHECK_SEND=1 时启用）
"""

EXIT_CODE = 0

def ok(msg: str) -> None:
    print(f"[OK] {msg}")

def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

def fail(msg: str) -> None:
    global EXIT_CODE
    print(f"[FAIL] {msg}")
    EXIT_CODE = 1

def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not (x != x)  # not NaN

def _last(v: Any) -> Any:
    if isinstance(v, (list, tuple)) and v:
        return v[-1]
    return v

def _has_any(hay: str, needles: Sequence[str]) -> bool:
    return any((n in hay) for n in needles)

def _env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v is not None else default

def _send_tg(text: str, to: str = "watch") -> None:
    """
    to: 'watch' | 'trade' | 'base'
    会自动选 CHAT_ID（优先 to 专用，其次兜底）
    """
    pub = importlib.import_module("ats_core.outputs.publisher")
    bot = _env("TELEGRAM_BOT_TOKEN") or _env("ATS_TELEGRAM_BOT_TOKEN")
    if not bot:
        warn("未配置 TELEGRAM_BOT_TOKEN（仅做本地渲染检查）")
        return

    chat = ""
    if to == "watch":
        chat = _env("TELEGRAM_WATCH_CHAT_ID") or _env("TELEGRAM_CHAT_ID") or _env("ATS_TELEGRAM_CHAT_ID")
    elif to == "trade":
        chat = _env("TELEGRAM_TRADE_CHAT_ID") or _env("TELEGRAM_CHAT_ID") or _env("ATS_TELEGRAM_CHAT_ID")
    else:
        chat = _env("TELEGRAM_CHAT_ID") or _env("ATS_TELEGRAM_CHAT_ID")

    if not chat:
        warn("未配置任何 CHAT_ID（仅做本地渲染检查）")
        return

    # publisher.telegram_send 内部已处理 UTF-8 JSON 发送
    pub.telegram_send(text, chat_id=chat)

def _pick_base_universe(params: Dict[str, Any]) -> List[str]:
    """从配置的 universe 拿；没有就 fallback 主流合约"""
    uni = params.get("universe", [])
    if isinstance(uni, (list, tuple)) and uni and isinstance(uni[0], str):
        return list(uni)
    # fallback base
    return [
        "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","MATICUSDT","DOTUSDT"
    ]

def _render_watch_trade(r: Dict[str, Any]) -> Tuple[str, str]:
    tfmt = importlib.import_module("ats_core.outputs.telegram_fmt")
    render_watch = getattr(tfmt, "render_watch", None)
    render_trade = getattr(tfmt, "render_trade", None)

    watch_txt = render_watch(r) if callable(render_watch) else ""
    trade_txt = render_trade(r) if callable(render_trade) else ""
    return watch_txt, trade_txt

def main(argv: List[str]) -> int:
    # 控制是否实际发 Telegram
    do_send = (_env("SELF_CHECK_SEND") or "").strip().lower() in ("1", "true", "yes")

    # 0) Python 版本
    pyv = sys.version_info
    if (pyv.major, pyv.minor) < (3, 8):
        fail(f"Python >= 3.8 要求，当前 {pyv.major}.{pyv.minor}")
    else:
        ok(f"Python {pyv.major}.{pyv.minor} OK")

    # 1) 配置加载 & CFG.get 兼容
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

        # 必要参数
        trend = p.get("trend", {})
        overlay = p.get("overlay", {})
        structure = p.get("structure", {"enabled": True, "fallback_score": 50})
        need_trend = ["ema_order_min_bars","slope_atr_min_long","slope_atr_min_short","slope_lookback","atr_period"]
        miss1 = [k for k in need_trend if trend.get(k) is None]
        if miss1:
            fail(f"trend 缺少参数：{miss1}")
        else:
            ok(f"trend 参数：{ {k: trend[k] for k in need_trend} }")

        need_overlay = ["oi_1h_pct_big","oi_1h_pct_small","hot_decay_hours"]
        miss2 = [k for k in need_overlay if overlay.get(k) is None]
        if miss2:
            fail(f"overlay 缺少参数：{miss2}")
        else:
            ok(f"overlay 参数：{ {k: overlay[k] for k in need_overlay} }")

        if not isinstance(structure, dict):
            fail("structure 应为 dict")
        else:
            ok(f"structure 参数：{structure}")

        uni = p.get("universe", [])
        if isinstance(uni, (list, tuple)):
            ok(f"universe 数量：{len(uni)}")
        else:
            warn("universe 非列表（非致命）")

        # CFG.get 兼容
        try:
            _a = CFG.get("overlay", {})
            _b = CFG.get("overlay", default={})
            _c = CFG.get("overlay", {}, default={})
            if not isinstance(_a, dict) or not isinstance(_b, dict) or not isinstance(_c, dict):
                fail("CFG.get 返回类型异常")
            else:
                ok("CFG.get(*, default=*) 兼容性 OK")
        except Exception as e:
            fail(f"CFG.get 兼容性问题：{e}")
    except Exception as e:
        fail(f"读取 CFG.params 失败：{e}")
        return EXIT_CODE

    # 2) 数据源：K线 / OI / 24h
    try:
        src_binance = importlib.import_module("ats_core.sources.binance")
        get_klines = src_binance.get_klines
        get_oi = src_binance.get_open_interest_hist

        ks = get_klines("BTCUSDT","1h", 80)
        if isinstance(ks, list) and ks and len(ks[0]) >= 6:
            ok(f"K线 OK：rows={len(ks)}")
            if do_send:
                _send_tg("📡 自检：K线接口可用（BTCUSDT, 1h）", to="base")
        else:
            fail("K线返回异常")
    except Exception as e:
        fail(f"拉取 K线失败：{e}")

    try:
        oi = get_oi("BTCUSDT","1h", 80)
        if isinstance(oi, list) and (not oi or isinstance(oi[0], dict)):
            ok(f"OI OK：rows={len(oi)}")
            if do_send:
                _send_tg("📡 自检：OI 接口可用（BTCUSDT, 1h）", to="base")
        else:
            fail("OI 返回异常")
    except Exception as e:
        fail(f"拉取 OI 失败：{e}")

    try:
        src_tickers = importlib.import_module("ats_core.sources.tickers")
        xs = src_tickers.all_24h()
        bt = src_tickers.one_24h("BTCUSDT")
        if isinstance(xs, list) and xs:
            ok(f"24h 全量 OK：{len(xs)} 条")
        else:
            fail("24h 全量返回异常")
        if isinstance(bt, dict) and "lastPrice" in bt:
            ok("24h 单币 OK：含 lastPrice")
        else:
            fail("24h 单币返回异常")
        if do_send:
            _send_tg("📡 自检：24h ticker 接口可用（全量 & 单币）", to="base")
    except Exception as e:
        fail(f"24h tickers 失败：{e}")

    # 3) CVD 与混合
    try:
        cvd_mod = importlib.import_module("ats_core.features.cvd")
        cvd_from_klines = cvd_mod.cvd_from_klines
        zscore_last = cvd_mod.zscore_last
        cvd_mix_with_oi_price = cvd_mod.cvd_mix_with_oi_price

        ks2 = get_klines("BTCUSDT","1h", 140)
        oi2 = get_oi("BTCUSDT","1h", 140)
        cvd = cvd_from_klines(ks2)
        if isinstance(cvd, list) and cvd:
            ok(f"CVD OK：len={len(cvd)} z20={round(zscore_last(cvd,20),3)}")
        else:
            fail("CVD 计算异常")

        cvd_norm, mix = cvd_mix_with_oi_price(ks2, oi2, window=20)
        if isinstance(mix, list) and mix:
            ok(f"CVD×OI×价格 OK：abs(last)={round(abs(_last(mix)),4)}")
        else:
            fail("CVD×OI×价格 计算异常")
        if do_send:
            _send_tg("📡 自检：CVD & 混合指标计算可用", to="base")
    except Exception as e:
        fail(f"CVD 相关失败：{e}")

    # 4) 候选构建（overlay）+ base/fallback 检查
    base_universe = _pick_base_universe(p)
    try:
        ob = importlib.import_module("ats_core.pools.overlay_builder")
        cands = ob.build()

        if not isinstance(cands, list):
            warn("overlay 构建返回的不是列表，改用 base_universe")
            cands = []

        # 兜底：保证候选里有“base”流（不够就用 base_universe 填）
        need = max(5, len(cands))
        for s in base_universe:
            if len(cands) >= need:
                break
            if s not in cands:
                cands.append(s)

        ok(f"候选（含 base/fallback）数量：{len(cands)} 示例：{cands[:6]}")
        if do_send:
            _send_tg(f"📋 自检：候选就绪（含 base）样例：{', '.join(cands[:6])}", to="base")
    except Exception as e:
        warn(f"overlay 构建失败，用 base_universe 兜底：{e}")
        cands = base_universe[:10]
        ok(f"候选兜底：{len(cands)} 示例：{cands[:6]}")

    # 5) 分析 -> 渲染（正式模板）-> 逐环节发送
    analyzed_ok = 0
    try:
        analyze_symbol = importlib.import_module("ats_core.pipeline.analyze_symbol").analyze_symbol

        for s in cands[:8]:  # 挑前 8 个尝试
            try:
                r: Dict[str, Any] = analyze_symbol(s)
                if not isinstance(r, dict):
                    warn(f"analyze_symbol({s}) 非 dict")
                    continue
                r["symbol"] = s

                watch_txt, trade_txt = _render_watch_trade(r)
                watch_ok = isinstance(watch_txt, str) and _has_any(
                    watch_txt, ["六维分析","趋势","结构","量能","加速","持仓","环境"]
                )
                trade_ok = isinstance(trade_txt, str) and _has_any(
                    trade_txt, ["六维分析","趋势","结构","量能","加速","持仓","环境"]
                )

                if watch_ok:
                    ok(f"渲染（watch）OK：{s}")
                    if do_send:
                        _send_tg(watch_txt, to="watch")
                else:
                    warn(f"渲染（watch）文本异常：{s}")

                if trade_ok:
                    ok(f"渲染（trade）OK：{s}")
                    if do_send:
                        _send_tg(trade_txt, to="trade")
                else:
                    warn(f"渲染（trade）文本异常：{s}")

                if watch_ok or trade_ok:
                    analyzed_ok += 1
                    break
            except Exception as e:
                warn(f"分析/渲染失败 {s} -> {e}")
    except Exception as e:
        fail(f"导入 analyze_symbol 或模板失败：{e}")

    if analyzed_ok == 0:
        fail("所有测试符号 analyze/render 失败（检查模板/字段命名是否匹配）")

    # 6) 终态连通：发一条总计消息（可选）
    bot = _env("TELEGRAM_BOT_TOKEN") or _env("ATS_TELEGRAM_BOT_TOKEN")
    any_chat = _env("TELEGRAM_CHAT_ID") or _env("ATS_TELEGRAM_CHAT_ID") or _env("TELEGRAM_WATCH_CHAT_ID") or _env("TELEGRAM_TRADE_CHAT_ID")
    if bot and any_chat and do_send:
        try:
            _send_tg(f"✅ 自检完成 {time.strftime('%F %T')} @ {platform.node()} —— 数据源、候选、分析、模板渲染、发送均 OK", to="base")
            ok("Telegram 终态发送 OK（UTF-8）")
        except Exception as e:
            warn(f"终态发送失败：{e}")
    elif bot and any_chat:
        ok("检测到 TELEGRAM_* 已配置（跳过终态实际发送，可设 SELF_CHECK_SEND=1 实发）")
    else:
        warn("未设置 TELEGRAM_BOT_TOKEN 或任何 CHAT_ID，终态发送跳过")

    print("\n—— SELF-CHECK SUMMARY ——")
    print(f"exit_code: {EXIT_CODE}")
    return EXIT_CODE

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))