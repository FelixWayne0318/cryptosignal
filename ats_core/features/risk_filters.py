# coding: utf-8
"""
多层风险过滤器（v2.2）

集成所有风险检测机制：
1. 流动性风险（订单簿深度）
2. 极端资金费风险
3. FWI窗口拥挤风险
4. 指标冲突风险

使用方式：
- 在计算基础分数后应用
- 根据风险等级调整分数或跳过信号
"""
from typing import Dict, List, Tuple


def apply_liquidity_filter(
    base_score: float,
    spread_bps: float,
    obi: float
) -> Tuple[float, List[str], bool]:
    """
    流动性风险过滤器

    Args:
        base_score: 基础分数
        spread_bps: 买卖价差（基点）
        obi: 订单簿失衡

    Returns:
        (调整后分数, 警告列表, 是否应跳过)

    逻辑:
        - spread > 20bps: 严重流动性枯竭 → 跳过信号
        - spread > 10bps: 流动性不足 → 分数 × 0.5
        - spread 5-10bps: 轻度警告 → 分数 × 0.8
    """
    warnings = []
    adjusted_score = base_score
    should_skip = False

    if spread_bps > 20:
        warnings.append(f"严重流动性风险: 点差{spread_bps:.1f}bps > 20bps")
        should_skip = True
    elif spread_bps > 10:
        warnings.append(f"流动性枯竭: 点差{spread_bps:.1f}bps > 10bps")
        adjusted_score *= 0.5
    elif spread_bps > 5:
        warnings.append(f"流动性不足: 点差{spread_bps:.1f}bps > 5bps")
        adjusted_score *= 0.8

    return adjusted_score, warnings, should_skip


def apply_funding_filter(
    base_score: float,
    funding_rate: float,
    basis_bps: float
) -> Tuple[float, List[str]]:
    """
    资金费风险过滤器

    Args:
        base_score: 基础分数
        funding_rate: 资金费率
        basis_bps: 基差（基点）

    Returns:
        (调整后分数, 警告列表)

    逻辑:
        - |funding| > 0.15%: 极端资金费 → 分数 × 0.7
        - |funding| > 0.10%: 高资金费 → 分数 × 0.85
    """
    warnings = []
    adjusted_score = base_score

    abs_funding = abs(funding_rate)
    funding_pct = abs_funding * 100

    if abs_funding > 0.0015:
        warnings.append(f"极端资金费: {funding_pct:.2f}% (>0.15%)")
        adjusted_score *= 0.7
    elif abs_funding > 0.001:
        warnings.append(f"高资金费: {funding_pct:.2f}% (>0.10%)")
        adjusted_score *= 0.85

    return adjusted_score, warnings


def apply_fwi_filter(
    base_score: float,
    fwi: float,
    fwi_warning: bool
) -> Tuple[float, List[str]]:
    """
    FWI窗口拥挤过滤器

    Args:
        base_score: 基础分数
        fwi: FWI指数
        fwi_warning: FWI警告标志

    Returns:
        (调整后分数, 警告列表)

    逻辑:
        - |FWI| > 2.0 且方向一致: 窗口拥挤 → 分数 × 0.3
        - |FWI| > 2.0 且方向相反: 轻度警告 → 分数 × 0.8
    """
    warnings = []
    adjusted_score = base_score

    if not fwi_warning:
        return adjusted_score, warnings

    # FWI警告触发
    warnings.append(f"资金费窗口拥挤: FWI={fwi:.2f}")

    # 检查方向一致性
    # 如果信号方向与FWI方向一致，大幅降权
    if (base_score > 0 and fwi > 0) or (base_score < 0 and fwi < 0):
        # 方向一致：可能是挤兑前的最后一波，风险极高
        warnings.append("信号方向与FWI一致，挤兑风险极高")
        adjusted_score *= 0.3
    else:
        # 方向相反：可能是反转信号，轻度降权
        warnings.append("信号方向与FWI相反，存在反转可能")
        adjusted_score *= 0.8

    return adjusted_score, warnings


def detect_indicator_conflict(
    T_score: int,
    M_score: int,
    C_score: int,
    O_score: int,
    D_score: int,
    F_score: int
) -> Tuple[bool, List[str]]:
    """
    检测指标冲突

    Args:
        T_score: 趋势分数
        M_score: 动量分数
        C_score: CVD分数
        O_score: OI分数
        D_score: 订单簿深度分数
        F_score: 资金费分数

    Returns:
        (是否有冲突, 冲突描述)

    逻辑:
        严重冲突定义：
        1. 趋势层（T+M）与原因层（C+O+D+F）方向完全相反
        2. 原因层内部严重分歧（>3个指标方向不一致）
    """
    warnings = []
    has_conflict = False

    # 1. 计算趋势层综合方向
    trend_layer = T_score + M_score
    trend_direction = 1 if trend_layer > 0 else -1 if trend_layer < 0 else 0

    # 2. 计算原因层综合方向
    cause_layer = C_score + O_score + D_score + F_score
    cause_direction = 1 if cause_layer > 0 else -1 if cause_layer < 0 else 0

    # 3. 检测趋势层与原因层冲突
    if trend_direction != 0 and cause_direction != 0:
        if trend_direction != cause_direction:
            # 趋势与原因方向相反
            if abs(trend_layer) > 30 and abs(cause_layer) > 30:
                # 两边信号都很强，但方向相反
                warnings.append(
                    f"严重冲突: 趋势层{'看多' if trend_direction > 0 else '看空'}"
                    f"但原因层{'看多' if cause_direction > 0 else '看空'}"
                )
                has_conflict = True

    # 4. 检测原因层内部分歧
    cause_scores = [C_score, O_score, D_score, F_score]
    positive_count = sum(1 for s in cause_scores if s > 10)
    negative_count = sum(1 for s in cause_scores if s < -10)

    if positive_count >= 2 and negative_count >= 2:
        warnings.append(
            f"原因层分歧: {positive_count}个看多, {negative_count}个看空"
        )
        has_conflict = True

    return has_conflict, warnings


def apply_risk_filters(
    base_score: float,
    D_meta: dict,
    F_meta: dict,
    fwi_result: dict,
    indicator_scores: dict = None
) -> dict:
    """
    应用所有风险过滤器（主函数）

    Args:
        base_score: 基础分数
        D_meta: 订单簿深度元数据
        F_meta: 资金费元数据
        fwi_result: FWI计算结果
        indicator_scores: 各指标分数（用于冲突检测）

    Returns:
        风险过滤结果字典

    返回格式:
        {
            'adjusted_score': 调整后分数,
            'warnings': 警告列表,
            'should_skip': 是否应跳过信号,
            'has_conflict': 是否有指标冲突,
            'risk_level': 风险等级 (low/medium/high)
        }
    """
    all_warnings = []
    adjusted_score = base_score
    should_skip = False

    # 1. 流动性过滤器
    adjusted_score, liquidity_warnings, liquidity_skip = apply_liquidity_filter(
        adjusted_score,
        D_meta.get('spread_bps', 0),
        D_meta.get('obi', 0)
    )
    all_warnings.extend(liquidity_warnings)
    if liquidity_skip:
        should_skip = True

    # 2. 资金费过滤器
    adjusted_score, funding_warnings = apply_funding_filter(
        adjusted_score,
        F_meta.get('funding_rate', 0),
        F_meta.get('basis_bps', 0)
    )
    all_warnings.extend(funding_warnings)

    # 3. FWI过滤器
    adjusted_score, fwi_warnings = apply_fwi_filter(
        adjusted_score,
        fwi_result.get('fwi', 0),
        fwi_result.get('fwi_warning', False)
    )
    all_warnings.extend(fwi_warnings)

    # 4. 指标冲突检测
    has_conflict = False
    if indicator_scores:
        has_conflict, conflict_warnings = detect_indicator_conflict(
            T_score=indicator_scores.get('T', 0),
            M_score=indicator_scores.get('M', 0),
            C_score=indicator_scores.get('C', 0),
            O_score=indicator_scores.get('O', 0),
            D_score=indicator_scores.get('D', 0),
            F_score=indicator_scores.get('F', 0)
        )
        all_warnings.extend(conflict_warnings)

        if has_conflict:
            # 指标冲突时跳过信号
            should_skip = True

    # 5. 计算风险等级
    risk_level = calculate_risk_level(
        len(all_warnings),
        should_skip,
        has_conflict
    )

    return {
        'adjusted_score': adjusted_score,
        'warnings': all_warnings,
        'should_skip': should_skip,
        'has_conflict': has_conflict,
        'risk_level': risk_level
    }


def calculate_risk_level(
    warning_count: int,
    should_skip: bool,
    has_conflict: bool
) -> str:
    """
    计算综合风险等级

    Args:
        warning_count: 警告数量
        should_skip: 是否应跳过
        has_conflict: 是否有冲突

    Returns:
        'low' / 'medium' / 'high'
    """
    if should_skip or has_conflict:
        return 'high'
    elif warning_count >= 2:
        return 'medium'
    elif warning_count >= 1:
        return 'medium'
    else:
        return 'low'


def format_risk_report(risk_result: dict) -> str:
    """
    格式化风险报告

    Args:
        risk_result: apply_risk_filters的返回结果

    Returns:
        格式化的风险报告字符串
    """
    lines = []
    lines.append("=" * 50)
    lines.append("风险过滤报告")
    lines.append("=" * 50)

    lines.append(f"风险等级: {risk_result['risk_level'].upper()}")
    lines.append(f"原始分数: {risk_result.get('base_score', 0):.1f}")
    lines.append(f"调整后分数: {risk_result['adjusted_score']:.1f}")
    lines.append(f"是否跳过: {'是' if risk_result['should_skip'] else '否'}")
    lines.append(f"指标冲突: {'是' if risk_result['has_conflict'] else '否'}")

    if risk_result['warnings']:
        lines.append("\n警告:")
        for i, warning in enumerate(risk_result['warnings'], 1):
            lines.append(f"  {i}. {warning}")
    else:
        lines.append("\n无警告")

    lines.append("=" * 50)

    return "\n".join(lines)
