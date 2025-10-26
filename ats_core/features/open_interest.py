# ats_core/features/open_interest.py
"""
O（持仓）评分 - 使用方向性软映射（v2.0 ±100对称设计）

改进v2.0：
- ✅ 分数范围：-100 到 +100（0为中性）
- ✅ 方向自包含：正值=OI上升，负值=OI下降
- ✅ 移除side_long：不再需要多空参数
- ✅ 使用对称评分函数
"""
from statistics import median
from typing import Dict, Tuple, Any
from ats_core.sources.oi import fetch_oi_hourly, pct, pct_series
from ats_core.features.scoring_utils import directional_score_symmetric

def score_open_interest(symbol: str,
                        closes,
                        params: Dict[str, Any],
                        cvd6_fallback: float) -> Tuple[int, Dict[str, Any]]:
    """
    专注"变化率"的 OI 评分（v2.0 对称版本）

    Args:
        symbol: 交易对
        closes: 收盘价序列
        params: 参数配置
        cvd6_fallback: CVD兜底值（OI数据不足时使用）

    Returns:
        (O分数 -100~+100, 元数据)
        - 正值：OI上升（多头持仓增加）→ 适合做多
        - 负值：OI下降（空头持仓减少）→ 适合做空
        - 0：OI无明显变化 → 中性

    评分逻辑：
      - 主分量：oi24（24h变化率，对称评分）
      - 辅分量：价格OI同向性（净同向次数）
      - 拥挤度：若 oi24 超过 p95，扣分
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
        O = directional_score_symmetric(
            cvd6_fallback,
            neutral=0.0,
            scale=0.02
        )
        # 限制在±40以内（因为CVD不如OI准确）
        O = int(max(-40, min(40, O)))
        return O, {
            "oi1h_pct": None,
            "oi24h_pct": None,
            "dndn12":   None,
            "upup12":   None,
            "crowding_warn": False,
            "data_source": "cvd_fallback"
        }

    den = median(oi[max(0, len(oi) - 168):])
    # 归一变化率
    oi1h = pct(oi[-1], oi[-2], den)
    oi24 = pct(oi[-1], oi[-25], den) if len(oi) >= 25 else 0.0

    # 最近 12 小时价格 vs OI 同向统计（对称版本）
    k = min(12, len(closes) - 1, len(oi) - 1)
    up_up = dn_dn = 0  # 改为统计 up_up 和 dn_dn
    for i in range(1, k + 1):
        dp = closes[-i] - closes[-i - 1]
        doi = oi[-i] - oi[-i - 1]
        if dp > 0 and doi > 0:
            up_up += 1  # 价格上涨 + OI上升（多头增仓）
        if dp < 0 and doi < 0:
            dn_dn += 1  # 价格下跌 + OI下降（空头减仓）

    # 净同向次数（对称指标）
    # 正值 = 上涨趋势（up_up多）
    # 负值 = 下跌趋势（dn_dn多）
    net_alignment = up_up - dn_dn

    # 拥挤度：oi24 的历史分布（最近 look=24 的变化率序列）
    hist24 = pct_series(oi, 24)
    crowding_warn = False
    p95 = None
    if hist24:
        s = sorted(hist24)
        p95 = s[int(0.95 * (len(s) - 1))]
        crowding_warn = (abs(oi24) >= abs(p95))  # 绝对值判断拥挤

    # —— 对称评分 ——
    # OI 变化评分（正值=上升，负值=下降）
    oi_score = directional_score_symmetric(
        oi24,
        neutral=0.0,
        scale=par["oi24_scale"]
    )  # -100 到 +100

    # 同向性评分（正值=多头趋势，负值=空头趋势）
    align_score = directional_score_symmetric(
        net_alignment,
        neutral=0.0,
        scale=par["align_scale"]
    )  # -100 到 +100

    # 加权平均
    O_raw = par["oi_weight"] * oi_score + par["align_weight"] * align_score

    # 拥挤度惩罚（对称：正负都惩罚）
    if crowding_warn:
        if O_raw > 0:
            O_raw -= par["crowding_p95_penalty"]
        else:
            O_raw += par["crowding_p95_penalty"]

    O = int(round(max(-100.0, min(100.0, O_raw))))

    meta = {
        "oi1h_pct": round(oi1h * 100, 2),
        "oi24h_pct": round(oi24 * 100, 2),
        "dndn12": dn_dn,
        "upup12": up_up,
        "net_alignment": net_alignment,
        "crowding_warn": crowding_warn,
        "p95_oi24": round(p95 * 100, 2) if p95 is not None else None,
        "den": den,
        "oi_score": oi_score,
        "align_score": align_score,
        "data_source": "oi_data",
        "interpretation": "OI上升" if O > 20 else ("OI下降" if O < -20 else "OI中性")
    }
    return O, meta