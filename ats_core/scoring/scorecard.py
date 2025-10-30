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
