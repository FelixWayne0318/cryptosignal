# ats_core/features/open_interest.py
"""
O（持仓）评分 - 统一±100系统

核心逻辑：
- OI上升 = 正分（看多或看空杠杆增加）
- OI下降 = 负分（杠杆减少）
- 配合价格方向判断多空

改进（v2.1）：
- 使用线性回归+R²（对标CVD）
- 避免被单根K线异常值误导

P0.3改进（自适应阈值）：
- 价格方向阈值不再固定为1%
- 根据历史波动率自适应调整

P1.2改进（Notional OI）：
- 使用名义持仓量（OI × 价格）而非合约张数
- 解决跨币种比较不准确问题（BTC vs 山寨币合约乘数差异）

v2.5++最终方案（2025-11-05）：
- 使用相对历史归一化（与CVD/M一致）
- 核心理念：判断OI变化方向和速度，与绝对持仓量无关
- 相对强度 = 当前OI斜率 / 历史平均OI斜率
- 自动适应不同币种的持仓规模特征
- 解决不同持仓规模币种的跨币种可比性问题
"""
from statistics import median
from typing import Dict, Tuple, Any, List, Optional
import numpy as np
from ats_core.sources.oi import fetch_oi_hourly, pct, pct_series
from ats_core.features.scoring_utils import directional_score  # 保留用于内部计算
from ats_core.utils.outlier_detection import detect_outliers_iqr, apply_outlier_weights
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例
_oi_chain = StandardizationChain(alpha=0.25, tau=5.0, z0=3.0, z0=2.5, zmax=6.0, lam=1.5)


def get_adaptive_oi_price_threshold(
    closes: list,
    lookback: int = 12,
    mode: str = 'hybrid',
    min_data_points: int = 50
) -> float:
    """
    计算自适应价格方向阈值（P0.3修复）

    Args:
        closes: 历史收盘价列表
        lookback: 计算变化率的回溯周期（默认12，与OI同向统计周期一致）
        mode: 'adaptive' | 'legacy' | 'hybrid'
        min_data_points: 最小数据点数（默认50）

    Returns:
        price_threshold: 价格方向判定阈值（如0.01表示±1%）
    """
    # Legacy模式或数据不足时使用固定阈值
    if mode == 'legacy' or len(closes) < min_data_points:
        return 0.01  # 固定1%

    # 计算历史价格变化率
    closes_array = np.array(closes)
    price_changes = []

    # 计算每个lookback周期的涨跌幅
    for i in range(lookback, len(closes_array)):
        price_start = closes_array[i - lookback]
        price_end = closes_array[i]
        if price_start != 0:
            change_pct = (price_end - price_start) / abs(price_start)
            price_changes.append(change_pct)

    if len(price_changes) < 10:
        return 0.01  # 数据不足，fallback

    # 使用价格变化的70分位数绝对值作为阈值
    # （比V因子的50分位更高，因为O因子考察的是12小时周期，更长期）
    abs_changes = np.abs(price_changes)
    threshold = float(np.percentile(abs_changes, 70))  # 70分位

    # 边界保护
    threshold = np.clip(threshold, 0.003, 0.03)  # 0.3% - 3%

    return threshold


def calculate_notional_oi(
    oi_contracts: List[float],
    prices: List[float],
    contract_multiplier: float = 1.0
) -> List[float]:
    """
    计算名义持仓量（P1.2修复）

    将合约张数转换为名义价值（USD），解决跨币种比较问题。

    Args:
        oi_contracts: 持仓合约张数列表
        prices: 对应的价格列表
        contract_multiplier: 合约乘数（永续合约通常=1.0）

    Returns:
        notional_oi: 名义持仓量列表（USD）

    示例：
        BTC: 10000张合约 × $50000 × 1.0 = $500M
        山寨币: 10000张合约 × $10 × 1.0 = $100K
    """
    if len(oi_contracts) != len(prices):
        # 长度不匹配，使用最后一个价格填充
        if len(prices) > 0:
            prices = list(prices) + [prices[-1]] * (len(oi_contracts) - len(prices))
        else:
            # 没有价格数据，返回原始OI
            return oi_contracts

    notional_oi = []
    for oi, price in zip(oi_contracts, prices):
        notional = oi * price * contract_multiplier
        notional_oi.append(notional)

    return notional_oi


def _linreg_r2(y: List[float]) -> Tuple[float, float]:
    """
    线性回归计算（与CVD/Trend统一方法）

    Args:
        y: 数值序列（如OI序列）

    Returns:
        (slope, r_squared)
        - slope: 斜率（趋势方向和强度）
        - r_squared: R²拟合优度（0-1，越大越线性）
    """
    n = len(y)
    if n <= 1:
        return 0.0, 0.0

    xs = list(range(n))
    mean_x = (n - 1) / 2.0
    mean_y = sum(y) / n

    # 计算斜率
    num = sum((xs[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0.0

    # 计算R²
    ss_tot = sum((yy - mean_y) ** 2 for yy in y)
    ss_res = sum((y[i] - (slope * xs[i] + (mean_y - slope * mean_x))) ** 2 for i in range(n))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    # 处理NaN和边界
    if not (r2 == r2):  # NaN check
        r2 = 0.0
    r2 = max(0.0, min(1.0, r2))

    return slope, r2

def score_open_interest(symbol: str,
                        closes,
                        params: Dict[str, Any],
                        cvd6_fallback: float,
                        oi_data: List = None) -> Tuple[int, Dict[str, Any]]:
    """
    O（持仓）评分 - 统一±100系统

    不再需要side_long参数，直接返回带符号的分数：
    - 正值：OI上升（杠杆增加，多空都可能）
    - 负值：OI下降（杠杆减少）
    - 配合价格涨跌判断具体多空

    Args:
        symbol: 交易对符号
        closes: 收盘价列表
        params: 参数配置
        cvd6_fallback: CVD 6小时变化（数据不足时兜底）
        oi_data: 预加载的OI数据（可选，优先使用）

    Returns:
        (O分数 [-100, +100], 元数据)
    """
    # 参数默认
    default_par = {
        # v2.5++修复（2025-11-05）：调整oi24_scale与C/M因子对齐
        # 修复前：oi24_scale=3.0 → 2x历史≈87分（相对C/M的76分更陡峭）
        # 修复后：oi24_scale=2.0 → 2x历史≈96分（与C/M一致，避免不一致的饱和特性）
        "oi24_scale": 2.0,          # OI 24h变化率缩放系数（原3.0，改为2.0与C/M对齐）
        "align_scale": 4.0,          # 同向次数缩放系数（4次 给约 69 分）
        "oi_weight": 0.7,            # OI 变化率权重
        "align_weight": 0.3,         # 同向权重
        "crowding_p95_penalty": 10,  # 拥挤度惩罚
        "min_oi_samples": 30,        # 最少 OI 数据点
        "adaptive_threshold_mode": "hybrid",  # P0.3: 自适应阈值模式
        # P1.2: Notional OI参数
        "use_notional_oi": True,     # 是否使用名义持仓量
        "contract_multiplier": 1.0,  # 合约乘数（永续通常=1）
    }
    par = dict(default_par)
    if isinstance(params, dict):
        par.update(params)

    # 优先使用预加载的数据，否则重新获取（向后兼容）
    if oi_data is not None and len(oi_data) > 0:
        # 预加载的数据可能是字典列表（原始API格式）或浮点数列表（已转换格式）
        # 统一转换为浮点数列表
        oi = []
        for x in oi_data:
            if isinstance(x, dict):
                # 字典格式：提取sumOpenInterest或openInterest字段
                v = x.get("sumOpenInterest") or x.get("openInterest")
                if v is not None:
                    try:
                        oi.append(float(v))
                    except:
                        pass
            elif isinstance(x, (int, float)):
                # 已经是数值格式，直接使用
                oi.append(float(x))
    else:
        oi = fetch_oi_hourly(symbol, limit=200)

    # ========== P1.2: Notional OI转换 ==========
    oi_type = "contracts"  # 默认为合约张数
    if par["use_notional_oi"] and len(closes) > 0:
        # 转换为名义持仓量（OI × 价格）
        # 需要将closes对齐到oi的长度
        if len(closes) >= len(oi):
            # closes足够长，截取最近len(oi)个
            prices_for_oi = list(closes[-len(oi):])
        else:
            # closes不够长，用最后一个价格填充
            prices_for_oi = list(closes) + [closes[-1]] * (len(oi) - len(closes))

        try:
            oi_original = oi.copy()  # 保存原始值用于metadata
            oi = calculate_notional_oi(
                oi_contracts=oi,
                prices=prices_for_oi,
                contract_multiplier=par["contract_multiplier"]
            )
            oi_type = "notional_usd"
        except Exception as e:
            # 转换失败，使用原始OI
            from ats_core.logging import warn
            warn(f"Notional OI转换失败 ({symbol}): {e}，使用原始合约张数")

    # 兜底：数据不足时使用 CVD proxy
    if len(oi) < par["min_oi_samples"]:
        # CVD作为代理（已经是带符号的）
        O = int(round(cvd6_fallback * 100))  # cvd6范围约-1到+1
        O = max(-100, min(100, O * 50))  # 缩放到±100
        return O, {
            "oi1h_pct": None,
            "oi24h_pct": None,
            "dnup12":   None,
            "upup12":   None,
            "crowding_warn": False,
            "data_source": "cvd_fallback",
            "r_squared": 0.0,
            "is_consistent": False,
            "method": "cvd_fallback",
            "oi_type": oi_type  # P1.2
        }

    den = median(oi[max(0, len(oi) - 168):])

    # ========== 改进v2.1：使用线性回归 + 异常值过滤（对标CVD） ==========
    # 初始化变量
    r_squared = 0.0
    is_consistent = False
    outliers_filtered = 0
    normalization_method = "median_fallback"  # v2.5++: 默认归一化方法
    avg_abs_oi_slope = None  # v2.5++: 历史平均斜率
    slope = 0.0  # v2.5++: 当前斜率

    # 旧方法：oi24 = pct(oi[-1], oi[-25], den)  # 简单两点比较
    # 新方法：线性回归斜率 + R²验证 + 异常值过滤
    if len(oi) >= 25:
        oi_window = oi[-25:]  # 24小时窗口

        # ========== 异常值检测和处理（新增v2.1） ==========
        # 检测OI变化异常值（如巨鲸突然建仓）
        oi_changes = [oi_window[i] - oi_window[i-1] for i in range(1, len(oi_window))]

        if len(oi_window) >= 20:
            outlier_mask = detect_outliers_iqr(oi_window, multiplier=1.5)
            outliers_filtered = sum(outlier_mask)

            # 对异常值降权（避免被巨鲸订单误导）
            if outliers_filtered > 0:
                oi_window = apply_outlier_weights(oi_window, outlier_mask, outlier_weight=0.5)

        # 线性回归分析
        slope, r_squared = _linreg_r2(oi_window)

        # ========== v2.5++: 相对历史归一化（与CVD/M一致） ==========
        # 计算历史所有24小时窗口的斜率
        use_historical_norm = (len(oi) >= 50)  # 至少50个数据点（约2天历史）
        if use_historical_norm:
            hist_oi_slopes = []
            for i in range(25, len(oi)):
                window = oi[i-24:i+1]
                if len(window) == 25:
                    s, _ = _linreg_r2(window)
                    hist_oi_slopes.append(s)

            # 计算历史平均绝对斜率
            if len(hist_oi_slopes) >= 10:
                avg_abs_oi_slope = sum(abs(s) for s in hist_oi_slopes) / len(hist_oi_slopes)
                avg_abs_oi_slope = max(1e-12, avg_abs_oi_slope)

                # 相对强度归一化
                slope_normalized = slope / avg_abs_oi_slope
                oi24_trend = slope_normalized * 2.0  # scale调整（相对强度范围不同）
                normalization_method = "relative_historical"
            else:
                # Fallback: 中位数归一化
                slope_normalized = slope / max(1e-12, den)
                oi24_trend = slope_normalized * 24
                normalization_method = "median_fallback"
                avg_abs_oi_slope = None
        else:
            # Fallback: 中位数归一化（历史数据不足）
            slope_normalized = slope / max(1e-12, den)
            oi24_trend = slope_normalized * 24
            normalization_method = "median_fallback"
            avg_abs_oi_slope = None

        # R²持续性验证（与CVD一致）
        is_consistent = (r_squared >= 0.7)
        if not is_consistent:
            # R²低时打折（震荡市，0.7x ~ 1.0x）
            stability_factor = 0.7 + 0.3 * (r_squared / 0.7)
            oi24_trend *= stability_factor

        oi24 = oi24_trend
    else:
        oi24 = 0.0

    # 1小时变化（保留用于参考）
    oi1h = pct(oi[-1], oi[-2], den) if len(oi) >= 2 else 0.0

    # 最近 12 小时价格 vs OI 同向统计
    k = min(12, len(closes) - 1, len(oi) - 1)
    up_up = dn_up = 0
    for i in range(1, k + 1):
        dp = closes[-i] - closes[-i - 1]
        doi = oi[-i] - oi[-i - 1]
        if dp > 0 and doi > 0:
            up_up += 1
        if dp < 0 and doi > 0:
            dn_up += 1

    # 拥挤度：oi24 的历史分布
    hist24 = pct_series(oi, 24)
    crowding_warn = False
    p95 = None
    if hist24:
        s = sorted(hist24)
        p95 = s[int(0.95 * (len(s) - 1))]
        crowding_warn = (oi24 >= p95)

    # —— 打分：OI变化的软映射（±100）—— v2.0修复多空对称性

    # 计算价格趋势（最近12根K线，与up_up/dn_up同周期）
    price_trend_pct = 0.0
    price_direction = 0  # -1=下跌, 0=中性, +1=上涨
    price_threshold = 0.01  # 默认阈值
    threshold_source = 'legacy'

    if len(closes) >= k + 1:
        # P0.3: 计算自适应阈值
        adaptive_mode = par["adaptive_threshold_mode"]
        if adaptive_mode != 'legacy' and len(closes) >= 50:
            price_threshold = get_adaptive_oi_price_threshold(
                closes,
                lookback=k,
                mode=adaptive_mode
            )
            threshold_source = 'adaptive'
        else:
            price_threshold = 0.01  # Fallback到固定阈值

        price_start = closes[-(k + 1)]
        price_end = closes[-1]
        price_trend_pct = (price_end - price_start) / max(1e-12, abs(price_start))

        # 判断价格方向（使用自适应阈值）
        if price_trend_pct > price_threshold:
            price_direction = 1   # 上涨
        elif price_trend_pct < -price_threshold:
            price_direction = -1  # 下跌
        else:
            price_direction = 0   # 中性

    # 1. OI变化强度（绝对值，未考虑方向）
    oi_score_raw = directional_score(oi24, neutral=0.0, scale=par["oi24_scale"])
    oi_strength = (oi_score_raw - 50) * 2  # 映射到 -100 到 +100

    # v2.0 修复：根据价格方向调整OI分数
    # - 价格上涨 + OI上升 → 正分（多头建仓）
    # - 价格下跌 + OI上升 → 负分（空头建仓）⭐ 修复重点
    # - 价格上涨 + OI下降 → 负分（多头离场）
    # - 价格下跌 + OI下降 → 正分（空头离场）
    if price_direction == -1:
        # 价格下跌：反转OI分数的符号
        oi_score = -oi_strength
    else:
        # 价格上涨或中性：保持OI分数的符号
        oi_score = oi_strength

    # 2. 同向得分：价格和OI同步变化次数（保留原逻辑，作为辅助）
    # up_up多 → 多头共振（正分）
    # dn_up多 → 空头共振（负分）
    align_diff = up_up - dn_up
    align_score_raw = directional_score(align_diff, neutral=0.0, scale=par["align_scale"])
    align_score = (align_score_raw - 50) * 2

    # 加权平均（v2.0：oi_score已考虑价格方向）
    O_raw = par["oi_weight"] * oi_score + par["align_weight"] * align_score

    # 拥挤度惩罚（降低分数的绝对值）
    if crowding_warn:
        penalty_factor = (100 - par["crowding_p95_penalty"]) / 100.0
        O_raw = O_raw * penalty_factor

    # v2.0合规：应用StandardizationChain
     # ✅ P0修复（2025-11-09）：重新启用StandardizationChain（参数已优化）
    O_pub, diagnostics = _oi_chain.standardize(O_raw)
    O = int(round(O_pub))

    # 解释（v2.0：考虑价格方向）
    if O >= 40:
        if price_direction == 1:
            interpretation = "多头持仓增加（价格上涨+OI上升）"
        elif price_direction == -1:
            interpretation = "空头持仓增加（价格下跌+OI上升）"
        else:
            interpretation = "持仓显著增长"
    elif O >= 10:
        if price_direction == 1:
            interpretation = "多头持仓温和增加"
        elif price_direction == -1:
            interpretation = "空头持仓温和增加"
        else:
            interpretation = "持仓温和增加"
    elif O >= -10:
        interpretation = "持仓平稳"
    elif O >= -40:
        if price_direction == 1:
            interpretation = "多头离场（价格上涨+OI减少）"
        elif price_direction == -1:
            interpretation = "空头离场（价格下跌+OI减少，可能见底）"
        else:
            interpretation = "持仓温和减少"
    else:
        if price_direction == 1:
            interpretation = "多头大幅离场（警告）"
        elif price_direction == -1:
            interpretation = "空头大幅离场（可能见底）"
        else:
            interpretation = "持仓大幅减少"

    # 构建元数据
    meta = {
        "oi1h_pct": round(oi1h, 2) if oi1h is not None else None,
        "oi24h_pct": round(oi24, 2) if oi24 is not None else None,
        "upup12": up_up,
        "dnup12": dn_up,
        "crowding_warn": crowding_warn,
        "p95_oi24": round(p95, 2) if p95 is not None else None,
        "oi_score": int(oi_score),
        "align_score": int(align_score),
        "oi_strength_raw": int(oi_strength),  # v2.0: 原始OI强度（未考虑方向）
        "price_trend_pct": round(price_trend_pct * 100, 2),  # v2.0: 价格涨跌幅（%）
        "price_direction": price_direction,  # v2.0: 价格方向（-1/0/+1）
        "interpretation": interpretation,
        "data_source": "oi",
        # v2.1: 线性回归指标（与CVD一致）
        "r_squared": round(r_squared, 3),
        "is_consistent": is_consistent,
        "method": "linear_regression+outlier_filter+price_direction",  # v2.0: 标记已修复对称性
        # v2.1: 异常值过滤统计
        "outliers_filtered": outliers_filtered,
        "symmetry_fixed": True,  # v2.0: 标记已修复多空对称性
        # P0.3: 自适应阈值信息
        "price_threshold": round(price_threshold * 100, 3),  # 阈值（%）
        "threshold_source": threshold_source,  # 'adaptive' or 'legacy'
        # P1.2: Notional OI信息
        "oi_type": oi_type,  # 'contracts' or 'notional_usd'
        # v2.5++: 相对历史归一化信息
        "normalization_method": normalization_method,
    }

    # 添加相对强度信息（如果使用历史归一化）
    if avg_abs_oi_slope is not None:
        meta["avg_abs_oi_slope"] = round(avg_abs_oi_slope, 6)
        meta["relative_oi_intensity"] = round(slope / avg_abs_oi_slope, 3)

    return O, meta
