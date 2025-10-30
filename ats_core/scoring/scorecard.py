def scorecard(scores, weights):
    """
    v5.0评分系统：加权平均（权重百分比系统）

    核心逻辑：
    - 因子输出: -100到+100（便于理解和展示）
    - 权重百分比: weight / total_weight（如 T=25/180=13.9%）
    - 加权平均: Σ(score × weight) / Σ(weight)
    - 总分范围: -100到+100（归一化后）

    示例：
        scores = {"T": -100, "M": -80, "F": +72}
        weights = {"T": 25, "M": 15, "F": 18}  # 总权重=180

        计算过程：
        T贡献: -100 × (25/180) = -13.9
        M贡献: -80 × (15/180) = -6.7
        F贡献: +72 × (18/180) = +7.2
        总分: -13.9 - 6.7 + 7.2 = -13.4

    Args:
        scores: dict，因子分数 {"T": -100, "M": +20, ...} (每个因子-100到+100)
        weights: dict，权重配置 {"T": 25, "M": 15, ...}

    Returns:
        (weighted_score, confidence, edge)
        - weighted_score: -100到+100的加权分数
        - confidence: 绝对值（0-100）
        - edge: -1.0到+1.0的优势度
    """
    # 计算加权总分
    total = 0.0
    weight_sum = 0.0

    for dim, score in scores.items():
        if dim in weights:
            total += score * weights[dim]
            weight_sum += weights[dim]

    # 归一化到 -100 到 +100（加权平均）
    if weight_sum > 0:
        weighted_score = total / weight_sum
    else:
        weighted_score = 0.0

    weighted_score = max(-100.0, min(100.0, weighted_score))

    # 置信度：绝对值
    confidence = abs(weighted_score)

    # 优势度：-1.0 到 +1.0
    edge = weighted_score / 100.0

    # 返回整数类型（避免格式化错误）
    return int(round(weighted_score)), int(round(confidence)), edge


def get_factor_contributions(scores, weights):
    """
    计算每个因子对总分的贡献（用于电报消息显示）

    Args:
        scores: dict，因子分数 {"T": -100, "M": -80, ...}
        weights: dict，权重配置 {"T": 25, "M": 15, ...}

    Returns:
        dict: {
            "T": {
                "score": -100,
                "weight": 25,
                "weight_pct": 13.9,  # 权重百分比
                "contribution": -13.9  # 对总分的贡献
            },
            ...
            "total_weight": 180,
            "weighted_score": -13
        }

    示例输出用于电报：
        T趋势: -100 (13.9%, 贡献-13.9)
        M动量: -80  (8.3%,  贡献-6.7)
        F资金: +72  (10.0%, 贡献+7.2)
        ──────────────────
        总分: -13 (看空)
    """
    weight_sum = sum(weights.values())
    contributions = {}

    for dim in scores.keys():
        if dim in weights:
            score = scores[dim]
            weight = weights[dim]
            weight_pct = (weight / weight_sum * 100) if weight_sum > 0 else 0
            contribution = (score * weight / weight_sum) if weight_sum > 0 else 0

            contributions[dim] = {
                "score": score,
                "weight": weight,
                "weight_pct": round(weight_pct, 1),
                "contribution": round(contribution, 1)
            }

    # 计算总分
    weighted_score, confidence, edge = scorecard(scores, weights)

    contributions["total_weight"] = weight_sum
    contributions["weighted_score"] = weighted_score
    contributions["confidence"] = confidence
    contributions["edge"] = edge

    return contributions


def get_factor_description(factor, score):
    """
    根据因子分数生成简要描述

    Args:
        factor: str，因子代号（如 "T", "M", "C"）
        score: int，因子分数（-100到+100）

    Returns:
        str: 简要描述

    示例：
        get_factor_description("T", -100) → "强势下跌趋势"
        get_factor_description("M", +85) → "强劲上涨动能"
        get_factor_description("F", +72) → "资金领先价格"
    """
    # 因子名称映射
    factor_names = {
        "T": "趋势",
        "M": "动量",
        "C": "CVD",
        "S": "结构",
        "V": "量能",
        "O": "持仓",
        "L": "流动性",
        "B": "基差",
        "Q": "清算",
        "I": "独立性",
        "F": "资金",
        "E": "废弃"
    }

    # 描述模板（根据分数范围）
    descriptions = {
        "T": {
            "strong_bull": "强势上涨趋势",
            "bull": "上涨趋势",
            "weak_bull": "弱上涨趋势",
            "neutral": "横盘震荡",
            "weak_bear": "弱下跌趋势",
            "bear": "下跌趋势",
            "strong_bear": "强势下跌趋势"
        },
        "M": {
            "strong_bull": "强劲上涨动能",
            "bull": "上涨动能",
            "weak_bull": "弱上涨动能",
            "neutral": "动能中性",
            "weak_bear": "弱下跌动能",
            "bear": "下跌动能",
            "strong_bear": "强劲下跌动能"
        },
        "C": {
            "strong_bull": "资金大量流入",
            "bull": "资金流入",
            "weak_bull": "资金略微流入",
            "neutral": "资金平衡",
            "weak_bear": "资金略微流出",
            "bear": "资金流出",
            "strong_bear": "资金大量流出"
        },
        "S": {
            "strong_bull": "结构极佳",
            "bull": "结构良好",
            "weak_bull": "结构尚可",
            "neutral": "结构中性",
            "weak_bear": "结构较弱",
            "bear": "结构不佳",
            "strong_bear": "结构极差"
        },
        "V": {
            "strong_bull": "放量上涨",
            "bull": "量能配合上涨",
            "weak_bull": "略微放量",
            "neutral": "量能平稳",
            "weak_bear": "缩量下跌",
            "bear": "量能配合下跌",
            "strong_bear": "放量下跌"
        },
        "O": {
            "strong_bull": "持仓大幅增加",
            "bull": "持仓增加",
            "weak_bull": "持仓略增",
            "neutral": "持仓平稳",
            "weak_bear": "持仓略减",
            "bear": "持仓减少",
            "strong_bear": "持仓大幅减少"
        },
        "L": {
            "strong_bull": "流动性极佳",
            "bull": "流动性良好",
            "weak_bull": "流动性尚可",
            "neutral": "流动性一般",
            "weak_bear": "流动性较差",
            "bear": "流动性不佳",
            "strong_bear": "流动性极差"
        },
        "B": {
            "strong_bull": "基差溢价显著",
            "bull": "基差正溢价",
            "weak_bull": "基差略有溢价",
            "neutral": "基差中性",
            "weak_bear": "基差略有折价",
            "bear": "基差负折价",
            "strong_bear": "基差折价显著"
        },
        "Q": {
            "strong_bull": "大量空单爆仓",
            "bull": "空单清算压力",
            "weak_bull": "略有空单清算",
            "neutral": "清算压力平衡",
            "weak_bear": "略有多单清算",
            "bear": "多单清算压力",
            "strong_bear": "大量多单爆仓"
        },
        "I": {
            "strong_bull": "走势高度独立",
            "bull": "走势较独立",
            "weak_bull": "走势略独立",
            "neutral": "跟随大盘",
            "weak_bear": "弱于大盘",
            "bear": "明显弱于大盘",
            "strong_bear": "严重弱于大盘"
        },
        "F": {
            "strong_bull": "资金强势领先",
            "bull": "资金领先价格",
            "weak_bull": "资金略微领先",
            "neutral": "资金价格同步",
            "weak_bear": "资金略微滞后",
            "bear": "价格领先资金",
            "strong_bear": "资金严重滞后"
        }
    }

    # 根据分数确定级别
    if score >= 70:
        level = "strong_bull"
    elif score >= 40:
        level = "bull"
    elif score >= 15:
        level = "weak_bull"
    elif score > -15:
        level = "neutral"
    elif score > -40:
        level = "weak_bear"
    elif score > -70:
        level = "bear"
    else:
        level = "strong_bear"

    # 获取描述
    if factor in descriptions:
        return descriptions[factor].get(level, "数据异常")
    else:
        # 未定义的因子，使用通用描述
        if score > 50:
            return "强势看多"
        elif score > 15:
            return "偏多"
        elif score > -15:
            return "中性"
        elif score > -50:
            return "偏空"
        else:
            return "强势看空"


def format_factor_for_telegram(factor, score, contribution_pct, include_description=True):
    """
    格式化因子信息用于电报消息

    Args:
        factor: str，因子代号（如 "T"）
        score: int，因子分数（-100到+100）
        contribution_pct: float，贡献百分比（如 -13.9）
        include_description: bool，是否包含描述

    Returns:
        str: 格式化的字符串

    示例：
        format_factor_for_telegram("T", -100, -13.9)
        → "T趋势: -100 (-13.9%)，强势下跌趋势"

        format_factor_for_telegram("F", +72, +7.2, include_description=False)
        → "F资金: +72 (+7.2%)"
    """
    # 因子全称
    factor_names = {
        "T": "T趋势",
        "M": "M动量",
        "C": "C资金流",
        "S": "S结构",
        "V": "V量能",
        "O": "O持仓",
        "L": "L流动性",
        "B": "B基差",
        "Q": "Q清算",
        "I": "I独立性",
        "F": "F资金领先",
        "E": "E废弃"
    }

    full_name = factor_names.get(factor, factor)

    # 格式化分数（带符号）
    score_str = f"{score:+d}"

    # 格式化贡献百分比（带符号）
    contribution_str = f"{contribution_pct:+.1f}%"

    # 基础格式
    result = f"{full_name}: {score_str} ({contribution_str})"

    # 添加描述
    if include_description:
        description = get_factor_description(factor, score)
        result += f"，{description}"

    return result
