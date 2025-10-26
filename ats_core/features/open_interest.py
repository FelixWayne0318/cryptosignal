# ats_core/features/open_interest.py
"""
O（持仓）评分 - 统一±100系统

核心逻辑：
- OI上升 = 正分（看多或看空杠杆增加）
- OI下降 = 负分（杠杆减少）
- 配合价格方向判断多空
"""
from statistics import median
from typing import Dict, Tuple, Any
from ats_core.sources.oi import fetch_oi_hourly, pct, pct_series
from ats_core.features.scoring_utils import directional_score

def score_open_interest(symbol: str,
                        closes,
                        params: Dict[str, Any],
                        cvd6_fallback: float) -> Tuple[int, Dict[str, Any]]:
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
            "data_source": "cvd_fallback"
        }

    den = median(oi[max(0, len(oi) - 168):])
    # 归一变化率
    oi1h = pct(oi[-1], oi[-2], den)
    oi24 = pct(oi[-1], oi[-25], den) if len(oi) >= 25 else 0.0

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

    # —— 打分：OI变化的软映射（±100）——
    # OI上升 = 正分，OI下降 = 负分
    oi_score_raw = directional_score(oi24, neutral=0.0, scale=par["oi24_scale"])
    oi_score = (oi_score_raw - 50) * 2  # 映射到 -100 到 +100

    # 同向得分：价格和OI同步变化次数
    # up_up多 → 多头共振（正分）
    # dn_up多 → 空头共振（负分）
    # 简化：用 up_up - dn_up 表示方向
    align_diff = up_up - dn_up
    align_score_raw = directional_score(align_diff, neutral=0.0, scale=par["align_scale"])
    align_score = (align_score_raw - 50) * 2

    # 加权平均
    O_raw = par["oi_weight"] * oi_score + par["align_weight"] * align_score

    # 拥挤度惩罚（降低分数的绝对值）
    if crowding_warn:
        penalty_factor = (100 - par["crowding_p95_penalty"]) / 100.0
        O_raw = O_raw * penalty_factor

    O = int(round(max(-100, min(100, O_raw))))

    # 解释
    if O >= 40:
        interpretation = "多头持仓增加"
    elif O >= 10:
        interpretation = "持仓温和增加"
    elif O >= -10:
        interpretation = "持仓平稳"
    elif O >= -40:
        interpretation = "持仓温和减少"
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
        "interpretation": interpretation,
        "data_source": "oi"
    }
