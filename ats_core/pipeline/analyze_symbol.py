# coding: utf-8
from __future__ import annotations

"""
兼容版 analyze_symbol：
- 适配 score_trend 返回 (T, Tm) 中 Tm 可能为 dict 或 数值 的两种形态；
- 对所有末值访问统一做“标量直返 / 序列[-1]”兼容，避免 'int' object is not subscriptable；
- 计算基础 ema/atr，并把模板常用字段补齐，避免渲染阶段缺键。
"""

from typing import List, Dict, Any, Sequence, Optional
import math

from ats_core.cfg import CFG
from ats_core.sources.binance import get_klines


# ------------------------
# 小工具
# ------------------------
def _to_f(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _last(x):
    """标量则原样（转 float），序列则取最后一个。"""
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x[-1])
    except Exception:
        return _to_f(x)

def _ema(seq: Sequence[float], n: int) -> List[float]:
    out: List[float] = []
    if not seq or n <= 1:
        return [float(_to_f(v)) for v in seq]
    k = 2.0 / (n + 1.0)
    ema_val: Optional[float] = None
    for v in seq:
        x = _to_f(v)
        ema_val = x if ema_val is None else (ema_val + k * (x - ema_val))
        out.append(ema_val)
    return out

def _atr(h: Sequence[float], l: Sequence[float], c: Sequence[float], period: int = 14) -> List[float]:
    """简化 ATR（SMA 版）"""
    n = min(len(h), len(l), len(c))
    if n == 0:
        return []
    tr_list: List[float] = []
    prev_c = _to_f(c[0])
    for i in range(n):
        hi = _to_f(h[i]); lo = _to_f(l[i]); ci = _to_f(c[i])
        tr = max(hi - lo, abs(hi - prev_c), abs(lo - prev_c))
        tr_list.append(tr)
        prev_c = ci
    out: List[float] = []
    s = 0.0
    for i, v in enumerate(tr_list):
        s += v
        if i + 1 < period:
            out.append(s / (i + 1))
        else:
            # 简单移动平均
            if i + 1 == period:
                out.append(s / period)
            else:
                s -= tr_list[i - period + 1]
                out.append(s / period)
    return out

def _safe_dict(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}


# ------------------------
# 业务兼容：score_trend
# ------------------------
def _score_trend(h: List[float], l: List[float], c: List[float], c4: List[float], trend_cfg: Dict[str, Any]):
    """
    兼容旧/新版本 features.trend.score_trend：
      - 标准返回: (T:int, Tm:dict)
      - 旧版可能返回: (T:int, slope:float)
    """
    try:
        from ats_core.features.trend import score_trend  # 用你项目里的实现
    except Exception:
        # 兜底：没有 trend 模块就返回 0
        return 0, {"slopeATR": 0.0, "emaOrder": 0}

    T, Tm = score_trend(h, l, c, c4, trend_cfg)
    return T, Tm


def _norm_trend_meta(Tm: Any, ema30: Sequence[float], atr_now: float) -> Dict[str, Any]:
    """
    把 Tm 规范成 dict，至少包含：
      - slopeATR: float
      - emaOrder: int
    若 Tm 本身不是 dict，则把它当作 slope 数字塞回去；
    若没有 slopeATR，则按 ema30 的斜率 / ATR 估一个。
    """
    if isinstance(Tm, dict):
        meta = dict(Tm)
    else:
        # 旧版返回的是一个数，按 slope 使用
        try:
            meta = {"slopeATR": float(Tm)}
        except Exception:
            meta = {"slopeATR": 0.0}
    # 补默认键
    if not isinstance(meta.get("emaOrder", None), (int, float)):
        meta["emaOrder"] = 0

    if not isinstance(meta.get("slopeATR", None), (int, float)):
        meta["slopeATR"] = 0.0

    # 如果 slopeATR 还是 0，则用 ema30 的近端斜率估一个
    if abs(meta["slopeATR"]) < 1e-12 and isinstance(ema30, Sequence) and len(ema30) >= 6:
        slope = ( _last(ema30) - _to_f(ema30[-6]) ) / max(atr_now, 1e-9)
        meta["slopeATR"] = float(slope)

    meta["slopeATR"] = float(meta["slopeATR"])
    meta["emaOrder"] = int(meta["emaOrder"])
    return meta


# ------------------------
# 主函数
# ------------------------
def analyze_symbol(symbol: str) -> Dict[str, Any]:
    """
    返回一个面向渲染层的结果 dict，包含：
      T, T_meta, strong, m15_ok, ema30, atr_now, close, structure 等
    其他模块/模板即使多取了字段，也不会因为缺键或类型不符而炸。
    """
    p: Dict[str, Any] = CFG.params or {}

    trend_cfg = _safe_dict(p.get("trend"))
    # 结构阈值：若未配置，则给一份温和默认，确保模板/分析取到键不爆
    structure_cfg = _safe_dict(p.get("structure")) or {
        "ema_order_min_bars": int(trend_cfg.get("ema_order_min_bars", 6)),
        "slope_atr_min_long": float(trend_cfg.get("slope_atr_min_long", 0.30)),
        "slope_atr_min_short": float(trend_cfg.get("slope_atr_min_short", 0.20)),
    }

    # 取 K 线：1h 与 4h
    k1 = get_klines(symbol, "1h", 300)
    k4 = get_klines(symbol, "4h", 200)

    if not k1 or len(k1) < 50:
        # 数据不足，返回一个最小可渲染包，避免 crash
        return {
            "T": 0,
            "T_meta": {"slopeATR": 0.0, "emaOrder": 0},
            "strong": False,
            "m15_ok": False,
            "ema30": 0.0,
            "atr_now": 0.0,
            "close": 0.0,
            "structure": structure_cfg,
        }

    h = [_to_f(r[2]) for r in k1]
    l = [_to_f(r[3]) for r in k1]
    c = [_to_f(r[4]) for r in k1]
    c4 = ([_to_f(r[4]) for r in k4] if k4 else list(c))

    # 基础指标
    ema30 = _ema(c, 30)
    atr_series = _atr(h, l, c, int(trend_cfg.get("atr_period", 14)))
    atr_now = _last(atr_series)

    # 趋势打分（兼容不同返回）
    T, Tm = _score_trend(h, l, c, c4, trend_cfg)
    T_meta = _norm_trend_meta(Tm, ema30, atr_now)

    # strong 判定阈值（沿用你的配置）
    slope_min = float(trend_cfg.get("slope_atr_min_long", 0.30))
    strong = (T_meta.get("slopeATR", 0.0) >= slope_min)

    res: Dict[str, Any] = {
        "T": int(T or 0),
        "T_meta": T_meta,               # 渲染模板通常会取到这个字典里的 slopeATR/emaOrder
        "strong": bool(strong),
        "m15_ok": False,                # 如果后续你有 15m 校验，可以在这里补真值
        "ema30": _last(ema30),
        "atr_now": float(atr_now),
        "close": _last(c),
        "structure": structure_cfg,     # 避免模板/后续流程报 KeyError: 'structure'
    }
    return res