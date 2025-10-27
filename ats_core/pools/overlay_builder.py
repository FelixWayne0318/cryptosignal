# coding: utf-8
from __future__ import annotations

"""
Overlay 候选构建（统一使用 cvd.py）
- 读取 1h K 线 + 1h OI，计算：
   dP1h_abs_pct、v5_over_v20、cvd_mix_abs_per_h
- 满足 overlay["triple_sync"] 阈值即入选
- 同时兼容 z24/24h_quote 的基础筛
"""

from typing import List, Dict, Any
from statistics import mean

from ats_core.cfg import CFG
from ats_core.sources.tickers import all_24h
from ats_core.sources.binance import get_klines, get_open_interest_hist
from ats_core.features.cvd import cvd_mix_with_oi_price
from ats_core.logging import log

# ------- utils -------
def _to_f(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _last(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x[-1])
    except Exception:
        return _to_f(x)

def _pct(a, b) -> float:
    a = _to_f(a); b = _to_f(b)
    if b == 0: return 0.0
    return a / b - 1.0

def _ma(xs, n):
    if not xs: return 0.0
    if len(xs) < n: return sum(_to_f(v) for v in xs) / len(xs)
    return sum(_to_f(v) for v in xs[-n:]) / n

# ------- main -------
def build() -> List[str]:
    params: Dict[str, Any] = CFG.get("overlay", default={})
    tri: Dict[str, Any] = params.get("triple_sync", {}) or {}
    new_coin_cfg: Dict[str, Any] = CFG.get("new_coin", default={}) or {}

    # 基础 universe：优先 params.universe，否则 24h 列表里的前若干主流
    uni: List[str] = CFG.get("universe", default=[]) or []
    if not uni:
        # 兜底：取 24h 数据里的 USDT 线性合约（符号以 USDT 结尾）
        tks = all_24h()
        uni = [t["symbol"] for t in tks if isinstance(t, dict) and str(t.get("symbol","")).endswith("USDT")]

    out: List[str] = []
    new_coins: List[str] = []  # 记录新币

    # 可选：z24 & 24h 成交额过滤
    z24_q = params.get("z24_and_24h_quote", {})
    need_z24 = _to_f(z24_q.get("z24", 0.0))
    need_quote = _to_f(z24_q.get("quote", 0.0))

    t24 = {t["symbol"]: t for t in all_24h() if isinstance(t, dict) and t.get("symbol")}

    log(f"📊 Overlay候选池：开始扫描 {len(uni)} 个交易对...")
    log(f"   检测模式：{'三选二' if tri.get('mode') == '2of3' else '全部满足'}")

    for idx, sym in enumerate(uni, 1):
        try:
            # 显示进度（每10个显示一次，避免刷屏）
            if idx % 10 == 0 or idx == 1 or idx == len(uni):
                log(f"   [{idx}/{len(uni)}] {sym}...")

            t = t24.get(sym, {})
            if need_quote > 0 and _to_f(t.get("quoteVolume")) < need_quote:
                continue
            # 你项目里如果有 z24 字段就用；没有就跳过该过滤
            z24_val = _to_f(t.get("z24", 0.0))
            if need_z24 > 0 and z24_val < need_z24:
                continue

            # --- 新币检测（优先检查，快速通道）---
            new_coin_enabled = new_coin_cfg.get("enabled", False)
            if new_coin_enabled:
                min_hours = int(new_coin_cfg.get("min_hours", 1))  # 最早1小时
                max_days = int(new_coin_cfg.get("max_days", 30))    # 最多30天
                min_volume = _to_f(new_coin_cfg.get("min_volume_24h", 10000000))  # 1000万USDT

                # 快速检测：获取最多720根1h K线（30天）
                k_check = get_klines(sym, "1h", max_days * 24 + 10)
                if k_check:
                    coin_age_hours = len(k_check)
                    coin_age_days = coin_age_hours / 24

                    # 新币条件：1小时-30天 + 高成交额
                    if coin_age_hours >= min_hours and coin_age_days <= max_days:
                        quote_vol = _to_f(t.get("quoteVolume", 0))
                        if quote_vol >= min_volume:
                            # 新币直接加入overlay（跳过三重共振检测）
                            out.append(sym)
                            new_coins.append(sym)
                            if idx % 10 != 0 and idx != 1:
                                log(f"   [{idx}/{len(uni)}] {sym} 🆕 新币 (上线{coin_age_days:.1f}天, 成交{quote_vol/1e6:.0f}M)")
                            continue  # 跳过后续的三重共振检测

            # --- 1h K 线 + OI ---（常规币种三重共振检测）
            k1 = get_klines(sym, "1h", 60)
            if not k1 or len(k1) < 25:
                continue
            oi = get_open_interest_hist(sym, "1h", 60)

            close = [_to_f(r[4]) for r in k1]
            vol_quote = [_to_f(r[7]) for r in k1]  # quoteAssetVolume

            # dP1h_abs_pct
            dp1h = abs(_pct(close[-1], close[-2]))

            # v5_over_v20
            v5 = _ma(vol_quote, 5)
            v20 = _ma(vol_quote, 20)
            v5_over_v20 = (v5 / v20) if v20 > 0 else 0.0

            # cvd_mix_abs_per_h（来自 cvd.py，标准化混合动量末值的绝对值）
            _, mix = cvd_mix_with_oi_price(k1, oi, window=20)
            cvd_mix_abs_per_h = abs(_last(mix)) if mix else 0.0

            # === 回撤过滤：避免追高/追跌 ===
            anti_chase = tri.get("anti_chase", {}) or {}
            if anti_chase.get("enabled", False):
                high = [_to_f(r[2]) for r in k1]
                low = [_to_f(r[3]) for r in k1]
                lookback = int(anti_chase.get("lookback", 72))  # 72小时
                max_distance = float(anti_chase.get("max_distance_pct", 0.05))  # 5%

                if len(high) >= lookback and len(low) >= lookback:
                    hh = max(high[-lookback:])  # 最高点
                    ll = min(low[-lookback:])   # 最低点
                    current = close[-1]

                    # 距离高点太近（可能追高）
                    if current > hh * (1 - max_distance):
                        continue
                    # 距离低点太近（可能追跌做空）
                    if current < ll * (1 + max_distance):
                        continue

            # 阈值
            need_dp = _to_f(tri.get("dP1h_abs_pct", 0.0))
            need_vr = _to_f(tri.get("v5_over_v20", 0.0))
            need_cvd = _to_f(tri.get("cvd_mix_abs_per_h", 0.0))

            # 三选二模式（优化：降低严格度）
            mode = tri.get("mode", "all")  # "all"=全部满足, "2of3"=三选二

            conditions = [
                dp1h >= need_dp,
                v5_over_v20 >= need_vr,
                cvd_mix_abs_per_h >= need_cvd
            ]

            if mode == "2of3":
                # 三选二：至少满足2个条件
                if sum(conditions) >= 2:
                    out.append(sym)
                    if idx % 10 != 0 and idx != 1:
                        log(f"   [{idx}/{len(uni)}] {sym} ✓ 三重共振 (dP={dp1h:.2%}, v5/v20={v5_over_v20:.2f}, cvd={cvd_mix_abs_per_h:.2f})")
            else:
                # 默认：全部满足（原有逻辑）
                if all(conditions):
                    out.append(sym)
                    if idx % 10 != 0 and idx != 1:
                        log(f"   [{idx}/{len(uni)}] {sym} ✓ 三重共振 (dP={dp1h:.2%}, v5/v20={v5_over_v20:.2f}, cvd={cvd_mix_abs_per_h:.2f})")

        except Exception:
            continue

    # 输出结果
    log(f"✅ Overlay候选池构建完成：{len(out)} 个交易对")
    if new_coins:
        log(f"   🆕 新币: {len(new_coins)} 个 ({', '.join(new_coins)})")
    if len(out) > 0:
        log(f"   前5名: {', '.join(out[:5])}")

    # 可选：Hot 衰减 / OI 变化 / 1h 成交额门槛等，仍按你 params.overlay 里的其他键在这里扩展
    return out