def scorecard(scores, weights):
    """
    改进版scorecard：支持7维度评分（T/M/C/S/V/O/E）
    - 旧版：T/A/S/V/O/E（6维）
    - 新版：T/M/C/S/V/O/E（7维，A拆分为M和C）
    """
    # 计算加权总分
    total = 0.0
    for dim, score in scores.items():
        if dim in weights:
            total += score * weights[dim]

    Up = total / 100.0
    Up = max(0.0, min(100.0, Up))
    Down = 100.0 - Up
    edge = (Up - Down) / 100.0
    return Up, Down, edge