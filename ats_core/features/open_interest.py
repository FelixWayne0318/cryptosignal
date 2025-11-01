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
"""
from statistics import median
from typing import Dict, Tuple, Any, List
from ats_core.sources.oi import fetch_oi_hourly, pct, pct_series
from ats_core.features.scoring_utils import directional_score  # 保留用于内部计算
from ats_core.utils.outlier_detection import detect_outliers_iqr, apply_outlier_weights
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例
_oi_chain = StandardizationChain(alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5)


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
        "oi24_scale": 3.0,          # OI 24h变化率缩放系数（3% 给约 69 分）
        "align_scale": 4.0,          # 同向次数缩放系数（4次 给约 69 分）
        "oi_weight": 0.7,            # OI 变化率权重
        "align_weight": 0.3,         # 同向权重
        "crowding_p95_penalty": 10,  # 拥挤度惩罚
        "min_oi_samples": 30,        # 最少 OI 数据点
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
            "method": "cvd_fallback"
        }

    den = median(oi[max(0, len(oi) - 168):])

    # ========== 改进v2.1：使用线性回归 + 异常值过滤（对标CVD） ==========
    # 初始化变量
    r_squared = 0.0
    is_consistent = False
    outliers_filtered = 0

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

        # 归一化斜率（除以中位数，避免量级差异）
        slope_normalized = slope / max(1e-12, den)

        # 24小时总变化 = 斜率 × 24（平均每小时 × 小时数）
        oi24_trend = slope_normalized * 24

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

    if len(closes) >= k + 1:
        price_start = closes[-(k + 1)]
        price_end = closes[-1]
        price_trend_pct = (price_end - price_start) / max(1e-12, abs(price_start))

        # 判断价格方向（阈值：±1%）
        if price_trend_pct > 0.01:
            price_direction = 1   # 上涨
        elif price_trend_pct < -0.01:
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

    return O, {
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
    }
