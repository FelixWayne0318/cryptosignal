# coding: utf-8
from __future__ import annotations
from typing import List, Sequence, Tuple, Optional, Union
import math
from ats_core.utils.outlier_detection import detect_volume_outliers, apply_outlier_weights

def _to_f(x) -> float:
    try:
        return float(x)
    except Exception:
        return float('nan')

def _col(kl: Sequence[Sequence], idx: int) -> List[float]:
    return [_to_f(r[idx]) for r in kl if isinstance(r, (list, tuple)) and len(r) > idx]

def _pct_change(arr: Sequence[float]) -> List[float]:
    out: List[float] = []
    prev = None
    for x in arr:
        x = _to_f(x)
        if not math.isfinite(x) or prev is None or prev == 0:
            out.append(0.0)
        else:
            out.append((x - prev) / prev)
        prev = x
    return out

def _z_all(a: Sequence[float]) -> List[float]:
    xs = [float(x) for x in a if isinstance(x, (int, float)) and math.isfinite(x)]
    if not xs:
        return [0.0] * len(a)
    m = sum(xs) / len(xs)
    var = sum((x - m) ** 2 for x in xs) / max(1, len(xs) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return [0.0] * len(a)
    return [((float(v) - m) / std) if isinstance(v, (int, float)) and math.isfinite(v) else 0.0 for v in a]

def _close_prices(kl: Sequence[Sequence]) -> List[float]:
    # Binance futures klines: [0] openTime, [1] open, [2] high, [3] low, [4] close, [5] volume, ...
    return _col(kl, 4)

def cvd_from_klines(
    klines: Sequence[Sequence],
    use_taker_buy: bool = True,
    use_quote: bool = True,
    filter_outliers: bool = True,
    outlier_weight: float = 0.5,
    expose_meta: bool = False
) -> Union[List[float], Tuple[List[float], dict]]:
    """
    计算CVD (Cumulative Volume Delta)

    Args:
        klines: Binance 期货 klines（12列）
            Quote CVD（use_quote=True）:
                [10]: takerBuyQuoteVolume（主动买入成交额，USDT）
                [7]: quoteAssetVolume（总成交额，USDT）
            Base CVD（use_quote=False）:
                [9]: takerBuyBaseVolume（主动买入量，币数量）
                [5]: volume（总成交量，币数量）
        use_taker_buy: 是否使用真实的taker buy volume
                      True: 使用真实数据（推荐）
                      False: 使用tick rule估算（兼容旧版）
        use_quote: 是否使用Quote CVD（v7.3.44新增）
                  True: 使用USDT单位（推荐，不受币价波动影响）
                  False: 使用币数量单位（兼容旧版）
        filter_outliers: 是否过滤异常值（巨量K线）
                        True: 对异常值降权（推荐）
                        False: 不处理异常值
        outlier_weight: 异常值权重（0-1），默认0.5表示降低50%
        expose_meta: v7.3.46新增 - 是否暴露meta信息（包括imbalance_ratio）
                    True: 返回 (cvd, meta)
                    False: 仅返回 cvd（兼容旧版）

    Returns:
        CVD序列：Σ(买入量 - 卖出量)
        如果expose_meta=True，返回 (cvd, meta)

    改进（v2.2）:
        - v7.3.46: 新增imbalance_ratio支持（尺度异方差对冲）
        - v7.3.44: 新增Quote CVD支持（USDT单位，更准确反映资金流）
        - v2.1: 添加IQR异常值检测
        - v2.1: 对巨量K线降权，避免被单笔大额交易误导
        - v7.4.2: P0-1修复 - 增强K线格式验证，添加异常处理
    """
    # v7.4.2 P0-1修复: 增强K线格式验证
    if use_taker_buy and klines:
        try:
            # 检查K线格式：需要至少11列（index 0-10用于Quote CVD）
            if not klines[0] or len(klines[0]) < 11:
                # 降级：K线格式不足，返回零CVD
                return ([0.0] * len(klines), {"degraded": True, "reason": "insufficient_kline_columns"}) if expose_meta else [0.0] * len(klines)

            # v7.3.44: 优化方法，支持Quote CVD和Base CVD
            if use_quote:
                # Quote CVD（USDT单位）- 更准确，不受币价波动影响
                taker_buy = _col(klines, 10)  # takerBuyQuoteVolume（主动买入成交额）
                total_vol = _col(klines, 7)   # quoteAssetVolume（总成交额）
            else:
                # Base CVD（币数量单位）- 兼容旧版
                taker_buy = _col(klines, 9)   # takerBuyBaseVolume（主动买入量）
                total_vol = _col(klines, 5)   # volume（总成交量）
        except (IndexError, TypeError, AttributeError) as e:
            # P0-1修复: 捕获格式异常，返回零CVD
            return ([0.0] * len(klines), {"degraded": True, "reason": f"kline_format_error: {e}"}) if expose_meta else [0.0] * len(klines)

        n = min(len(taker_buy), len(total_vol))

        # ========== 异常值检测（新增） ==========
        deltas: List[float] = []
        for i in range(n):
            buy = taker_buy[i]
            total = total_vol[i]
            if not (math.isfinite(buy) and math.isfinite(total)):
                deltas.append(0.0)
            else:
                delta = 2.0 * buy - total
                deltas.append(delta)

        # 检测成交量异常值
        if filter_outliers and n >= 20:
            outlier_mask = detect_volume_outliers(total_vol, deltas, multiplier=1.5)
            # 对异常值降权
            deltas = apply_outlier_weights(deltas, outlier_mask, outlier_weight)

        # 累积CVD
        s = 0.0
        cvd: List[float] = []
        for delta in deltas:
            s += delta
            cvd.append(s)

        # v7.3.46: 计算imbalance_ratio（条件1 - 尺度异方差对冲）
        if expose_meta:
            epsilon = 1.0  # 防止除零，1 USDT
            imbalance_ratios: List[float] = []
            for i in range(n):
                delta = deltas[i]
                vol = total_vol[i]
                # imbalance_ratio = ΔC / max(quoteVol, ε)
                # 理论边界 [-1, 1]
                ratio = delta / max(vol, epsilon) if vol > 0 else 0.0
                imbalance_ratios.append(ratio)

            meta = {
                "imbalance_ratios": imbalance_ratios,
                "use_quote": use_quote,
                "filter_outliers": filter_outliers
            }
            return cvd, meta
        else:
            return cvd
    else:
        # ⚠️ DEPRECATED: 旧方法Tick Rule估算（不准确，仅保留兼容性）
        # v7.3.42警告：此方法使用"阳线=买盘、阴线=卖盘"判断，会系统性误判！
        #
        # 问题：阳线（close>=open）≠买盘，阴线≠卖盘
        # 例如：主动买盘推高后回落形成阴线，但前期都是买盘
        #
        # 解决方案：确保K线数据包含takerBuyVolume（第9列），设置use_taker_buy=True
        #
        # 此分支将在未来版本中移除！
        import warnings
        warnings.warn(
            "CVD计算正在使用不准确的Tick Rule估算（阳线=买盘、阴线=卖盘）！"
            "\n这会导致系统性误判资金流向。"
            "\n请确保K线数据包含takerBuyVolume（第9列），并使用use_taker_buy=True。"
            "\n此方法将在未来版本中移除。",
            DeprecationWarning,
            stacklevel=2
        )
        o = _col(klines, 1)
        c = _col(klines, 4)
        v = _col(klines, 5)
        n = min(len(o), len(c), len(v))
        s = 0.0
        cvd: List[float] = []
        for i in range(n):
            oi, ci, vi = o[i], c[i], v[i]
            if not (math.isfinite(oi) and math.isfinite(ci) and math.isfinite(vi)):
                cvd.append(s)
                continue
            sign = 1.0 if ci >= oi else -1.0  # ⚠️ 错误：阳线≠买盘
            s += sign * vi
            cvd.append(s)
        return cvd

def zscore_last(xs: Sequence[float], window: int = 20) -> float:
    if not xs:
        return 0.0
    w = xs[-window:] if len(xs) >= window else list(xs)
    w = [float(x) for x in w if isinstance(x, (int, float)) and math.isfinite(x)]
    if len(w) < 2:
        return 0.0
    mean = sum(w) / len(w)
    var = sum((x - mean) ** 2 for x in w) / max(1, len(w) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    return (w[-1] - mean) / std

def cvd_from_spot_klines(klines: Sequence[Sequence], use_quote: bool = True) -> List[float]:
    """
    计算现货CVD (使用真实taker buy volume)

    Args:
        klines: Binance 现货 klines（12列）
            Quote CVD（use_quote=True）:
                [10]: takerBuyQuoteVolume（主动买入成交额，USDT）
                [7]: quoteAssetVolume（总成交额，USDT）
            Base CVD（use_quote=False）:
                [9]: takerBuyBaseVolume（主动买入量，币数量）
                [5]: volume（总成交量，币数量）
        use_quote: 是否使用Quote CVD（v7.3.44新增）
                  True: 使用USDT单位（推荐）
                  False: 使用币数量单位（兼容旧版）

    Returns:
        现货CVD序列
    """
    # 现货数据格式与合约相同，直接调用
    return cvd_from_klines(klines, use_taker_buy=True, use_quote=use_quote)


def cvd_combined(
    futures_klines: Sequence[Sequence],
    spot_klines: Sequence[Sequence] = None,
    use_dynamic_weight: bool = True,
    use_quote: bool = True,
    min_quote_factor: float = 0.05,
    min_quote_window: int = 96,
    min_quote_fallback: float = 10000,
    max_discard_ratio: float = 0.05,
    return_meta: bool = False
) -> Union[List[float], Tuple[List[float], dict]]:
    """
    组合现货+合约CVD（v7.3.46增强版）

    Args:
        futures_klines: 合约K线数据
        spot_klines: 现货K线数据（可选）
        use_dynamic_weight: 是否使用动态权重（按成交额比例）
                          True: 根据实际成交额动态计算权重（推荐）
                          False: 使用固定权重（70%合约 + 30%现货）
        use_quote: 是否使用Quote CVD（USDT单位）
                  True: 使用USDT单位（推荐）
                  False: 使用币数量单位（兼容旧版）
        min_quote_factor: 动态最小成交额系数（默认0.05 = 5%中位数）
        min_quote_window: 动态阈值计算窗口（96根1h K线 = 4天）
        min_quote_fallback: 最小回退阈值（10k USDT）
        max_discard_ratio: K线对齐最大丢弃比例（默认5%），超过自动降级
        return_meta: v7.3.46新增 - 是否返回meta信息（包括degraded标志）
                    True: 返回 (cvd, meta)
                    False: 仅返回 cvd（兼容旧版）

    Returns:
        如果return_meta=False: 组合后的CVD序列
        如果return_meta=True: (cvd_series, meta_dict)
            meta_dict包含:
                - degraded: bool（是否降级）
                - degrade_reason: str（降级原因）
                - discard_ratio: float（丢弃率）
                - futures_weight: float（合约权重）
                - spot_weight: float（现货权重）
                - skipped_count: int（跳过K线数）
                - skipped_ratio: float（跳过比率）

    改进（v7.3.44）：
        - P1-1: openTime对齐检查（防止现货/合约K线错位）
        - P2-4: 缺失/极值容错（成交额过小时处理）
        - P2-3: Quote CVD支持（USDT单位）

    改进（v7.3.45）：
        - 动态最小成交额阈值（小币友好）
        - 自动降级逻辑（丢弃率>5%时自动切换单侧CVD）
        - 增强日志可观测性

    改进（v7.3.46）：
        - 条件4: 降级回写标记（degraded标志可观测）

    说明：
        - 动态权重：根据合约和现货的实际成交额（USDT）比例计算权重
        - 这样能真实反映不同市场的资金流向权重
        - 例如：某币合约日成交10亿，现货1亿 → 权重自动为 90.9% : 9.1%
    """
    # 导入工具函数
    from ats_core.utils.cvd_utils import (
        align_klines_by_open_time,
        compute_dynamic_min_quote
    )
    from ats_core.logging import warn, log

    # 计算合约CVD
    cvd_f = cvd_from_klines(futures_klines, use_taker_buy=True, use_quote=use_quote)

    if spot_klines is None or len(spot_klines) == 0:
        # 如果没有现货数据，只返回合约CVD
        if return_meta:
            meta = {
                "degraded": True,
                "degrade_reason": "no_spot_data",
                "discard_ratio": 0.0,
                "futures_weight": 1.0,
                "spot_weight": 0.0,
                "skipped_count": 0,
                "skipped_ratio": 0.0
            }
            return cvd_f, meta
        else:
            return cvd_f

    # v7.3.45: 计算动态最小成交额阈值
    dynamic_min_quote = compute_dynamic_min_quote(
        futures_klines,
        window=min_quote_window,
        factor=min_quote_factor,
        min_fallback=min_quote_fallback
    )

    # v7.3.45: P1-1 - openTime对齐检查（带自动降级）
    aligned_f, aligned_s, discarded, is_degraded = align_klines_by_open_time(
        futures_klines, spot_klines, max_discard_ratio=max_discard_ratio
    )

    # v7.3.45: 自动降级逻辑
    if is_degraded or not aligned_f:
        warn("⚠️  自动降级为单侧CVD（仅使用合约数据）")
        if return_meta:
            total = len(futures_klines) + len(spot_klines)
            discard_ratio = discarded / total if total > 0 else 0.0
            meta = {
                "degraded": True,
                "degrade_reason": "high_discard_ratio" if is_degraded else "alignment_failed",
                "discard_ratio": discard_ratio,
                "futures_weight": 1.0,
                "spot_weight": 0.0,
                "skipped_count": 0,
                "skipped_ratio": 0.0
            }
            return cvd_f, meta
        else:
            return cvd_f

    # 计算对齐后的CVD
    cvd_f = cvd_from_klines(aligned_f, use_taker_buy=True, use_quote=use_quote)
    cvd_s = cvd_from_spot_klines(aligned_s, use_quote=use_quote)

    n = len(aligned_f)  # 对齐后长度必然相同

    # 计算权重
    if use_dynamic_weight:
        # 方法1：按成交额（USDT）比例动态计算权重（区间权重）
        # K线第7列：quoteAssetVolume（成交额，单位USDT）
        f_quote_volume = sum([_to_f(k[7]) for k in aligned_f])
        s_quote_volume = sum([_to_f(k[7]) for k in aligned_s])
        total_quote = f_quote_volume + s_quote_volume

        if total_quote > 0:
            futures_weight = f_quote_volume / total_quote
            spot_weight = s_quote_volume / total_quote
        else:
            # 降级到固定比例
            futures_weight = 0.7
            spot_weight = 0.3
    else:
        # 方法2：固定权重
        futures_weight = 0.7
        spot_weight = 0.3

    # v7.3.45: 日志可观测性
    log(f"📊 CVD组合统计: 丢弃{discarded}根, "
        f"期货权重={futures_weight:.2%}, 现货权重={spot_weight:.2%}, "
        f"动态阈值={dynamic_min_quote:.0f} USDT")

    # v7.3.45: P2-4 - 加权组合CVD增量（动态成交额过滤）
    result: List[float] = []
    skipped_count = 0

    for i in range(n):
        # 获取当前K线的成交额
        f_quote = _to_f(aligned_f[i][7])
        s_quote = _to_f(aligned_s[i][7])
        total_quote_i = f_quote + s_quote

        # 计算每根K线的CVD增量
        if i == 0:
            delta_f = cvd_f[i]
            delta_s = cvd_s[i]
        else:
            delta_f = cvd_f[i] - cvd_f[i-1]
            delta_s = cvd_s[i] - cvd_s[i-1]

        # v7.3.45: 动态成交额过滤
        if total_quote_i < dynamic_min_quote:
            # 成交额过小，使用上一根CVD值（跳过组合）
            skipped_count += 1
            if i == 0:
                result.append(0.0)
            else:
                result.append(result[-1])
            continue

        # 加权混合增量
        combined_delta = futures_weight * delta_f + spot_weight * delta_s

        # 累加
        if i == 0:
            result.append(combined_delta)
        else:
            result.append(result[-1] + combined_delta)

    # v7.3.45: 成交额过滤统计
    skip_ratio = skipped_count / n if n > 0 else 0.0
    if skipped_count > 0:
        log(f"📊 CVD成交额过滤: 跳过{skipped_count}/{n}根 ({skip_ratio:.2%})")

    # v7.3.46: 构建meta字典
    if return_meta:
        total = len(futures_klines) + len(spot_klines)
        discard_ratio = discarded / total if total > 0 else 0.0
        meta = {
            "degraded": False,
            "degrade_reason": "",
            "discard_ratio": discard_ratio,
            "futures_weight": futures_weight,
            "spot_weight": spot_weight,
            "skipped_count": skipped_count,
            "skipped_ratio": skip_ratio
        }
        return result, meta
    else:
        return result


def cvd_mix_with_oi_price(
    klines: Sequence[Sequence],
    oi_hist: Sequence[dict],
    spot_klines: Sequence[Sequence] = None,
    use_quote: bool = True,
    rolling_window: int = 96,
    use_robust: bool = True,
    use_strict_oi_align: bool = False,
    oi_align_tolerance_ms: int = 5000,
    return_meta: bool = False
) -> Union[Tuple[List[float], List[float]], Tuple[List[float], List[float], dict]]:
    """
    组合信号：CVD（现货+合约）+ 价格收益 + OI 变化（v7.3.46增强版）

    Args:
        klines: 合约K线数据
        oi_hist: 持仓量历史数据
        spot_klines: 现货K线数据（可选）
        use_quote: 是否使用Quote CVD（USDT单位）
                  True: 使用USDT单位（推荐）
                  False: 使用币数量单位（兼容旧版）
        rolling_window: 滚动窗口大小（96根1h K线 = 4天）
                       用于滚动Z标准化
        use_robust: 是否使用稳健Z-score（MAD）
                   True: 使用MAD（对异常值稳健）
                   False: 使用std（传统方法）
        use_strict_oi_align: v7.3.46新增 - 是否使用严格OI对齐（取前不取后）
                            True: 使用align_oi_to_klines_strict（条件2）
                            False: 使用简单对齐（兼容旧版）
        oi_align_tolerance_ms: OI对齐时间容忍度（毫秒），默认5000ms
        return_meta: v7.3.46新增 - 是否返回mix_meta信息
                    True: 返回 (cvd, mix, meta)
                    False: 返回 (cvd, mix)（兼容旧版）

    Returns:
        如果return_meta=False: (cvd_series, mix_series)
        如果return_meta=True: (cvd_series, mix_series, mix_meta)
            - cvd_series: 组合后的CVD（如果有现货数据则为现货+合约）
            - mix_series: 综合强度（标准化），越大代表量价+OI同向越强
            - mix_meta: 统计信息（均值、标准差、偏度、OI缺失率等）

    改进（v7.3.44）：
        - P1-2: 滚动Z标准化（避免前视偏差）
        - 对增量（ΔC, ΔP, ΔOI）做标准化，而不是累计值
        - 使用rolling_z替代全局_z_all

    改进（v7.3.45）：
        - 修复CVD增量计算bug（使用diff而不是pct_change）
        - OI数据对齐到K线（按closeTime匹配）
        - 删除冗余window参数
        - 增加mix统计日志

    改进（v7.3.46）：
        - 条件2: 取前不取后OI对齐（align_oi_to_klines_strict）
        - 条件6: 统一索引切齐（在变换前对齐所有序列）
        - 增加mix_meta输出（可观测性）
    """
    # 导入工具函数
    from ats_core.utils.cvd_utils import (
        rolling_z, _diff, align_oi_to_klines, align_oi_to_klines_strict
    )
    from ats_core.logging import log
    import math

    # 计算CVD（现货+合约组合，如果有现货数据）
    if spot_klines and len(spot_klines) > 0:
        cvd = cvd_combined(klines, spot_klines, use_quote=use_quote)
    else:
        cvd = cvd_from_klines(klines, use_taker_buy=True, use_quote=use_quote)

    # 提取价格序列
    closes = _close_prices(klines)

    # v7.3.46: 严格OI对齐（条件2 - 取前不取后）
    oi_missing_ratio = 0.0
    if use_strict_oi_align:
        oi_vals, oi_missing_ratio = align_oi_to_klines_strict(
            oi_hist, klines, tolerance_ms=oi_align_tolerance_ms
        )
    else:
        # v7.3.45: 简单OI对齐（兼容旧版）
        oi_vals = align_oi_to_klines(oi_hist, klines)

    # v7.3.46: 条件6 - 统一索引切齐（在变换前对齐所有序列）
    # 确保cvd, closes, oi_vals长度完全一致
    n = min(len(cvd), len(closes), len(oi_vals))
    if n == 0:
        # 空数据，返回空序列
        if return_meta:
            meta = {"error": "empty_data", "oi_missing_ratio": 1.0}
            return [], [], meta
        else:
            return [], []

    cvd = cvd[-n:]
    closes = closes[-n:]
    oi_vals = oi_vals[-n:]

    # v7.3.45: 修复CVD增量计算bug
    # 对于累计量CVD，应该使用diff而不是pct_change
    # pct_change在CVD接近0时会爆炸，且对负数没有意义
    delta_cvd = _diff(cvd)  # ✅ 使用一阶差分

    # 价格和OI使用百分比变化（正确）
    ret_p = _pct_change(closes)
    d_oi = _pct_change(oi_vals) if any(oi > 0 for oi in oi_vals) else [0.0] * n

    # v7.3.44: P1-2 - 滚动Z标准化（无前视偏差）
    z_cvd = rolling_z(delta_cvd, window=rolling_window, robust=use_robust)
    z_p = rolling_z(ret_p, window=rolling_window, robust=use_robust)
    z_oi = rolling_z(d_oi, window=rolling_window, robust=use_robust)

    # 组合权重：CVD权重提升（更重要）
    mix = [1.2 * z_cvd[i] + 0.4 * z_p[i] + 0.4 * z_oi[i] for i in range(n)]

    # v7.3.45: mix统计日志（可观测性）
    mean_mix = sum(mix) / len(mix) if len(mix) > 0 else 0.0
    variance_mix = sum((m - mean_mix)**2 for m in mix) / len(mix) if len(mix) > 0 else 0
    std_mix = math.sqrt(variance_mix)
    skewness_mix = sum((m - mean_mix)**3 for m in mix) / (len(mix) * std_mix**3) if std_mix > 0 and len(mix) > 0 else 0

    log(f"📊 CVD Mix统计: 均值={mean_mix:.2f}, 标准差={std_mix:.2f}, 偏度={skewness_mix:.2f}")

    # v7.3.46: 构建mix_meta
    if return_meta:
        meta = {
            "mean": mean_mix,
            "std": std_mix,
            "skewness": skewness_mix,
            "oi_missing_ratio": oi_missing_ratio,
            "sequence_length": n,
            "rolling_window": rolling_window,
            "use_robust": use_robust,
            "use_strict_oi_align": use_strict_oi_align
        }
        return cvd, mix, meta
    else:
        return cvd, mix

__all__ = [
    "cvd_from_klines",
    "cvd_from_spot_klines",
    "cvd_combined",
    "cvd_mix_with_oi_price",
    "zscore_last"
]