def scorecard(scores, weights):
    """
    改进版scorecard：统一±100系统

    核心改进：
    - 所有维度都是 -100到+100（带符号）
    - 加权求和直接计算
    - weighted_score > 0 → 看多，< 0 → 看空

    Args:
        scores: dict，如 {"T": +60, "M": +20, "C": -40, "S": +10, "V": +30, "O": +15, "E": -20}
        weights: dict，如 {"T": 20, "M": 10, "C": 10, "S": 10, "V": 20, "O": 15, "E": 15}

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

    # 归一化到 -100 到 +100
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
