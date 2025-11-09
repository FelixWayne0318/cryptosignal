# coding: utf-8
"""
F（资金领先性）维度

核心理念：
因果链：资金是因，价格是果
- 最佳入场点：资金强势流入，但价格还未充分反应（蓄势待发）
- 追高风险：价格已经大涨，但资金流入减弱或流出（派发阶段）

F 的定义：
F = f(资金动量 - 价格动量)
范围：-100 到 +100（带符号）

- F >= +60：资金强势领先价格（蓄势待发）✅✅✅
- F >= +30：资金温和领先价格（机会较好）✅
- -30 < F < +30：资金价格同步（一般）
- F <= -30：价格温和领先资金（追高风险）⚠️
- F <= -60：价格强势领先资金（风险很大）❌

P0.4改进（crowding veto）：
- 检测市场过热（basis或funding极端）
- 在crowding时降低F因子分数（防止追高）
- 应用惩罚而非硬拒绝（保持连续性）

v3.0配置管理（2025-11-09）：
- 移除硬编码参数，改为从配置文件读取
- 支持向后兼容（params参数优先级高于配置文件）
- 使用统一的数据质量检查阈值

输入：
- oi_change_pct: OI 24小时变化率（%）
- vol_ratio: v5/v20 量能比值
- cvd_change: CVD 6小时变化（归一化）
- price_change_pct: 价格 24小时变化率（%）
- price_slope: 价格斜率（EMA30的斜率）
"""
from typing import Dict, Any, Tuple, Optional, List
from ats_core.features.scoring_utils import directional_score
from ats_core.config.factor_config import get_factor_config
import math
import numpy as np


def score_fund_leading(
    oi_change_pct: float,
    vol_ratio: float,
    cvd_change: float,
    price_change_pct: float,
    price_slope: float,
    params: Dict[str, Any] = None,
    basis_history: Optional[List[float]] = None,
    funding_history: Optional[List[float]] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    F（资金领先性）评分 - 移除circular dependency + P0.4 crowding veto

    计算资金动量与价格动量的差值（带符号）：
    - F > 0: 资金偏多（OI上升、CVD流入、价格上涨但不强）→ 看多信号
    - F < 0: 资金偏空（OI下降、CVD流出、价格下跌但不强）→ 看空信号

    P0.4新增：
    - 检测市场crowding（basis或funding极端）
    - 应用惩罚系数降低F分数（防止追高）

    Args:
        oi_change_pct: OI 24小时变化率（%），如 +3.5 表示上升 3.5%
        vol_ratio: v5/v20 量能比值，如 1.4 表示近期量能是均值的 1.4 倍
        cvd_change: CVD 6小时变化（归一化到价格），通常在 -0.05 ~ +0.05 范围
        price_change_pct: 价格 24小时变化率（%）
        price_slope: 价格斜率（EMA30 的斜率/ATR）
        params: 参数配置（v3.0：可选，优先级高于配置文件）
        basis_history: 历史basis数据（bps），用于crowding检测（P0.4新增）
        funding_history: 历史funding rate数据，用于crowding检测（P0.4新增）

    Returns:
        (F分数 [-100, +100], 元数据)

    v3.0改进：
    - 从配置文件读取默认参数
    - 传入的params参数优先级高于配置文件（向后兼容）
    """
    # v3.0: 从配置文件读取默认参数
    try:
        config = get_factor_config()
        config_params = config.get_factor_params("F")
    except Exception as e:
        # 配置加载失败时使用硬编码默认值（向后兼容）
        print(f"⚠️ F因子配置加载失败，使用默认值: {e}")
        config_params = {
            "oi_weight": 0.4,
            "vol_weight": 0.3,
            "cvd_weight": 0.3,
            "trend_weight": 0.6,
            "slope_weight": 0.4,
            "oi_scale": 3.0,
            "vol_scale": 0.3,
            "cvd_scale": 0.02,
            "price_scale": 3.0,
            "slope_scale": 0.01,
            "leading_scale": 200.0,
            "crowding_veto_enabled": True,
            "crowding_percentile": 90,
            "crowding_penalty": 0.5,
            "crowding_min_data": 100,
        }

    # 合并配置参数：配置文件 < 传入的params（向后兼容）
    p = dict(config_params)
    if isinstance(params, dict):
        p.update(params)

    # ========== 1. 资金动量（绝对方向计算）==========
    # OI上升 → 正分，OI下降 → 负分
    # CVD流入 → 正分，CVD流出 → 负分
    # 量能放大 → 正分，量能萎缩 → 负分

    # P2.4修复：使用min_score=0确保对称映射（0-100而非10-100）
    oi_score = directional_score(oi_change_pct, neutral=0.0, scale=p["oi_scale"], min_score=0.0)
    cvd_score = directional_score(cvd_change, neutral=0.0, scale=p["cvd_scale"], min_score=0.0)
    vol_score = directional_score(vol_ratio, neutral=1.0, scale=p["vol_scale"], min_score=0.0)

    # 加权平均（返回 -100 到 +100 的带符号分数）
    # P2.4修复：映射 0-100 → -100到+100（对称映射，避免饱和）
    fund_momentum = (
        p["oi_weight"] * ((oi_score - 50) * 2) +
        p["vol_weight"] * ((vol_score - 50) * 2) +
        p["cvd_weight"] * ((cvd_score - 50) * 2)
    )

    # ========== 2. 价格动量（绝对方向计算）==========
    # 价格上涨 → 正分，价格下跌 → 负分
    # 斜率向上 → 正分，斜率向下 → 负分

    # P2.4修复：使用min_score=0确保对称映射
    trend_score = directional_score(price_change_pct, neutral=0.0, scale=p["price_scale"], min_score=0.0)
    slope_score = directional_score(price_slope, neutral=0.0, scale=p["slope_scale"], min_score=0.0)

    # 加权平均（返回 -100 到 +100 的带符号分数）
    # P2.4修复：映射 0-100 → -100到+100（对称映射，避免饱和）
    price_momentum = (
        p["trend_weight"] * ((trend_score - 50) * 2) +
        p["slope_weight"] * ((slope_score - 50) * 2)
    )

    # ========== 3. 资金领先性 ==========
    # leading = 资金动量 - 价格动量
    # leading > 0：资金强于价格（蓄势）✅
    # leading < 0：价格强于资金（追高）⚠️

    leading_raw = fund_momentum - price_momentum

    # 映射到 -100 到 +100（带符号）
    # 正数 = 资金领先价格（蓄势待发）
    # 负数 = 价格领先资金（追高风险）
    normalized = math.tanh(leading_raw / p["leading_scale"])
    F_raw = 100.0 * normalized

    # ========== 4. P0.4 Crowding Veto检测 ==========
    veto_penalty = 1.0
    veto_reasons = []
    veto_applied = False

    if p["crowding_veto_enabled"]:
        min_data = p["crowding_min_data"]
        percentile = p["crowding_percentile"]

        # Veto 1: Basis极端检测
        if basis_history and len(basis_history) >= min_data:
            basis_array = np.abs(basis_history)  # 使用绝对值
            basis_threshold = np.percentile(basis_array, percentile)
            current_basis = abs(basis_history[-1])

            if current_basis > basis_threshold:
                veto_penalty *= p["crowding_penalty"]
                veto_reasons.append(f"basis过热({current_basis:.1f} > q{percentile}={basis_threshold:.1f}bps)")
                veto_applied = True

        # Veto 2: Funding极端检测
        if funding_history and len(funding_history) >= min_data:
            funding_array = np.abs(funding_history)  # 使用绝对值
            funding_threshold = np.percentile(funding_array, percentile)
            current_funding = abs(funding_history[-1])

            if current_funding > funding_threshold:
                veto_penalty *= p["crowding_penalty"]
                veto_reasons.append(f"funding极端({current_funding:.4f} > q{percentile}={funding_threshold:.4f})")
                veto_applied = True

    # 应用veto惩罚
    F_final = F_raw * veto_penalty
    F = int(round(max(-100.0, min(100.0, F_final))))

    # ========== 5. 元数据 ==========
    meta = {
        "fund_momentum": round(fund_momentum, 1),
        "price_momentum": round(price_momentum, 1),
        "leading_raw": round(leading_raw, 1),
        "oi_score": oi_score,
        "vol_score": vol_score,
        "cvd_score": cvd_score,
        "trend_score": trend_score,
        "slope_score": slope_score,
        # 原始输入（便于调试）
        "oi_change_pct": round(oi_change_pct, 2),
        "vol_ratio": round(vol_ratio, 2),
        "cvd_change": round(cvd_change, 4),
        "price_change_pct": round(price_change_pct, 2),
        "price_slope": round(price_slope, 4),
        # P0.4: Crowding veto信息
        "F_raw": round(F_raw, 1),
        "veto_penalty": round(veto_penalty, 3),
        "veto_applied": veto_applied,
        "veto_reasons": veto_reasons if veto_reasons else None,
    }

    return F, meta


def score_fund_leading_v2(
    cvd_series: List[float],
    oi_data: List,
    klines: List,
    atr_now: float,
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    F因子v2（v7.2阶段1）：精确的资金领先性

    理论：资金流入速度 vs 价格上涨速度
    公式：F = (资金动量 - 价格动量) × 归一化因子

    优势：
    - 精确定义，可操作
    - 直接使用原始数据，不需要预处理
    - 归一化到ATR，适应不同波动率

    Args:
        cvd_series: CVD序列（现货+永续合成）
        oi_data: OI历史数据 [[timestamp, oi_value], ...]
        klines: K线数据（至少7根）
        atr_now: 当前ATR值
        params: 参数配置（v3.0：可选，优先级高于配置文件）

    Returns:
        (F分数 [-100, +100], 元数据)

    v3.0改进：
    - 从配置文件读取默认参数
    - 传入的params参数优先级高于配置文件（向后兼容）
    """
    # v3.0: 从配置文件读取默认参数（使用F_v2子配置或F配置）
    try:
        config = get_factor_config()
        # 尝试获取F_v2特定配置，如果不存在则使用F的基础配置
        try:
            config_params = config.get_factor_params("F_v2")
        except:
            # 使用F的基础配置中的v2参数
            f_params = config.get_factor_params("F")
            config_params = f_params.get("v2", {
                "cvd_weight": 0.6,
                "oi_weight": 0.4,
                "window_hours": 6,
                "scale": 2.0,
            })
    except Exception as e:
        # 配置加载失败时使用硬编码默认值（向后兼容）
        print(f"⚠️ F_v2因子配置加载失败，使用默认值: {e}")
        config_params = {
            "cvd_weight": 0.6,
            "oi_weight": 0.4,
            "window_hours": 6,
            "scale": 2.0,
        }

    # 合并配置参数：配置文件 < 传入的params（向后兼容）
    p = dict(config_params)
    if isinstance(params, dict):
        p.update(params)

    # === 1. 数据验证 ===
    if len(klines) < 7:
        # v3.1: 统一降级元数据结构（改用标准字段名）
        return 0, {
            "degradation_reason": "insufficient_data",
            "min_data_required": 7,
            "actual_data_points": len(klines)
        }

    if atr_now <= 0:
        atr_now = 1.0

    closes = [float(k[4]) for k in klines]
    close_now = closes[-1]

    # === 2. 价格变化（6h，约6根K线）===
    price_6h_ago = closes[-7] if len(closes) >= 7 else closes[0]
    price_change_6h = close_now - price_6h_ago
    price_change_pct = price_change_6h / price_6h_ago

    # === 3. CVD变化（6h）===
    if len(cvd_series) >= 7:
        cvd_6h_ago = cvd_series[-7]
        cvd_now = cvd_series[-1]
        cvd_change_6h = cvd_now - cvd_6h_ago
        # 归一化到价格（CVD是累积成交量，需要转为相对价格的比例）
        cvd_change_norm = cvd_change_6h / max(1e-9, abs(price_6h_ago))
    else:
        cvd_change_norm = 0.0

    # === 4. OI变化（6h，名义化）===
    if oi_data and len(oi_data) >= 7:
        try:
            oi_now = float(oi_data[-1][1])
            oi_6h_ago = float(oi_data[-7][1])

            # OI名义值（OI × Price）
            oi_notional_now = oi_now * close_now
            oi_notional_6h = oi_6h_ago * price_6h_ago

            # 名义化变化率
            oi_change_6h = (oi_notional_now - oi_notional_6h) / max(1e-9, abs(oi_notional_6h))
        except (ValueError, IndexError, TypeError):
            oi_change_6h = 0.0
    else:
        oi_change_6h = 0.0

    # === 5. 资金动量（CVD + OI，加权）===
    # 归一化到ATR（使资金动量和价格动量可比）
    # P1.2修复：防止ATR过小导致放大噪音
    atr_norm_factor = max(atr_now / close_now, 0.001)  # 最小0.1%，避免除以过小值

    fund_momentum_raw = p["cvd_weight"] * cvd_change_norm + p["oi_weight"] * oi_change_6h
    fund_momentum = fund_momentum_raw / atr_norm_factor

    # === 6. 价格动量（归一化到ATR）===
    price_momentum = price_change_pct / atr_norm_factor

    # === 7. F原始值（资金 - 价格）===
    F_raw = fund_momentum - price_momentum

    # === 8. 映射到±100（tanh平滑）===
    F_normalized = math.tanh(F_raw / p["scale"])
    F_score = 100.0 * F_normalized
    F_score = int(round(max(-100.0, min(100.0, F_score))))

    # === 9. 元数据 ===
    meta = {
        "fund_momentum": round(fund_momentum, 4),
        "price_momentum": round(price_momentum, 4),
        "F_raw": round(F_raw, 4),
        "cvd_6h_norm": round(cvd_change_norm, 4),
        "oi_6h_pct": round(oi_change_6h, 4),
        "price_6h_pct": round(price_change_pct * 100, 2),
        "atr_norm": round(atr_norm_factor, 4),
        "version": "v2_simplified"
    }

    return F_score, meta


def interpret_F(F_score: int) -> str:
    """
    解释 F 分数的含义

    Args:
        F_score: F 维度分数 (-100 到 +100)

    Returns:
        中文解释
    """
    if F_score >= 60:
        return "资金强势领先价格 (蓄势待发)"
    elif F_score >= 30:
        return "资金温和领先价格 (机会较好)"
    elif F_score >= 10:
        return "资金略微领先 (同步偏好)"
    elif F_score >= -10:
        return "资金价格同步 (中性)"
    elif F_score >= -30:
        return "价格略微领先 (同步偏差)"
    elif F_score >= -60:
        return "价格温和领先资金 (追高风险)"
    else:
        return "价格强势领先资金 (风险很大)"
