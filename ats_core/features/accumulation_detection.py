# coding: utf-8
"""
ats_core/features/accumulation_detection.py

蓄势待发检测增强模块（P2.1）

目标：
- 在原有screening逻辑基础上增加veto条件
- 防止虚假蓄势信号（追高风险）
- 提升检测准确率从60%到80%

改进：
1. 保留原有screening逻辑（F≥85, C≥60, T∈[-10,40]）
2. 新增veto条件（crowding, liquidity, momentum）
3. Trigger逻辑作为可选功能

作者：Claude (Sonnet 4.5)
日期：2025-11-05
版本：P2.1
"""

from typing import Dict, Tuple, Any


def detect_accumulation_v1(
    factors: Dict[str, float],
    meta: Dict[str, Dict],
    params: Dict[str, Any] = None
) -> Tuple[bool, str, int]:
    """
    蓄势待发检测 v1.0（当前版本）

    逻辑：
    - 强势蓄势：F≥90 ∧ C≥60 ∧ T<40 → threshold=35
    - 深度蓄势：F≥85 ∧ C≥70 ∧ T<30 ∧ V<0 → threshold=38

    Args:
        factors: 因子字典 {T, M, C, V, O, B, L, S, F, I}
        meta: 因子元数据
        params: 参数配置

    Returns:
        (is_accumulating, reason, threshold)
    """
    F = factors.get('F', 0)
    C = factors.get('C', 0)
    T = factors.get('T', 0)
    V = factors.get('V', 0)

    if F >= 90 and C >= 60 and T < 40:
        return True, "强势蓄势(F≥90+C≥60+T<40)", 35

    elif F >= 85 and C >= 70 and T < 30 and V < 0:
        return True, "深度蓄势(F≥85+C≥70+V<0+T<30)", 38

    return False, "", 50


def detect_accumulation_v2(
    factors: Dict[str, float],
    meta: Dict[str, Dict],
    params: Dict[str, Any] = None
) -> Tuple[bool, str, int]:
    """
    蓄势待发检测 v2.0（P2.1增强版本）

    改进：
    1. 放宽screening阈值（F≥85, T∈[-10,40]）
    2. 新增veto条件（防止追高）
    3. 动态调整threshold

    Args:
        factors: 因子字典 {T, M, C, V, O, B, L, S, F, I}
        meta: 因子元数据
        params: 参数配置

    Returns:
        (is_accumulating, reason, threshold)
    """
    # 默认参数
    default_params = {
        # Screening阈值
        'F_min': 85,
        'C_min': 60,
        'T_range': [-10, 40],
        'base_threshold': 35,
        # Veto阈值
        'basis_bps_max': 150,    # basis>150bps视为过热
        'L_min': 50,             # 流动性最低要求
        'M_min': -50,            # 动量最低要求（防止向下趋势）
        'veto_penalty_min': 0.6  # 最小veto_penalty，低于此值取消蓄势
    }

    p = dict(default_params)
    if params:
        p.update(params)

    T = factors.get('T', 0)
    M = factors.get('M', 0)
    C = factors.get('C', 0)
    V = factors.get('V', 0)
    O = factors.get('O', 0)
    B = factors.get('B', 0)
    F = factors.get('F', 0)
    L = factors.get('L', 0)
    S = factors.get('S', 0)
    I = factors.get('I', 0)

    # ========== Stage 1: Screening ==========
    screening_passed = False
    base_threshold = p['base_threshold']

    # 检查screening条件
    if F >= p['F_min'] and C >= p['C_min'] and p['T_range'][0] <= T <= p['T_range'][1]:
        screening_passed = True
        reason = f"资金蓄势(F≥{p['F_min']}+C≥{p['C_min']}+T∈{p['T_range']})"
    else:
        return False, "", 50  # Screening未通过

    # ========== Stage 2: Veto Conditions ==========
    veto_penalty = 1.0
    veto_reasons = []

    # Veto 1: Crowding（basis过热）
    basis_meta = meta.get('B', {})
    basis_bps = basis_meta.get('basis_bps', 0)
    if abs(basis_bps) > p['basis_bps_max']:
        veto_penalty *= 0.7
        veto_reasons.append(f"basis过热({abs(basis_bps):.0f}bps)")

    # Veto 2: Liquidity（流动性过低）
    if L < p['L_min']:
        veto_penalty *= 0.85
        veto_reasons.append(f"流动性偏低(L={L:.0f})")

    # Veto 3: Momentum contradiction（动量矛盾）
    if M < p['M_min']:
        veto_penalty *= 0.8
        veto_reasons.append(f"动量向下(M={M:.0f})")

    # Veto 4: OI reduction（持仓减少）
    if O < -30:
        veto_penalty *= 0.85
        veto_reasons.append(f"持仓减少(O={O:.0f})")

    # ========== Stage 3: 应用veto惩罚 ==========
    if veto_penalty < p['veto_penalty_min']:
        # veto惩罚过重，取消蓄势状态
        veto_summary = ','.join(veto_reasons) if veto_reasons else 'unknown'
        return False, f"veto过多({veto_summary})", 50

    # 动态调整threshold
    adjusted_threshold = base_threshold / veto_penalty
    adjusted_threshold = int(round(min(adjusted_threshold, 50)))  # 不超过50

    # 更新reason
    if veto_reasons:
        reason += f" [veto: {','.join(veto_reasons)}]"

    return True, reason, adjusted_threshold


def detect_accumulation(
    factors: Dict[str, float],
    meta: Dict[str, Dict],
    version: str = 'v2',
    params: Dict[str, Any] = None
) -> Tuple[bool, str, int]:
    """
    蓄势待发检测统一接口

    Args:
        factors: 因子字典
        meta: 因子元数据
        version: 'v1' | 'v2'
        params: 参数配置

    Returns:
        (is_accumulating, reason, threshold)
    """
    if version == 'v1':
        return detect_accumulation_v1(factors, meta, params)
    elif version == 'v2':
        return detect_accumulation_v2(factors, meta, params)
    else:
        raise ValueError(f"不支持的版本: {version}")


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("蓄势待发检测测试")
    print("=" * 60)

    # 测试用例
    test_cases = [
        {
            'name': "理想蓄势（无veto）",
            'factors': {'T': 20, 'M': 10, 'C': 70, 'V': 10, 'O': 30, 'B': 20, 'F': 90, 'L': 70, 'S': 0, 'I': 0},
            'meta': {'B': {'basis_bps': 50}}
        },
        {
            'name': "basis过热",
            'factors': {'T': 20, 'M': 10, 'C': 70, 'V': 10, 'O': 30, 'B': 80, 'F': 90, 'L': 70, 'S': 0, 'I': 0},
            'meta': {'B': {'basis_bps': 200}}
        },
        {
            'name': "流动性过低",
            'factors': {'T': 20, 'M': 10, 'C': 70, 'V': 10, 'O': 30, 'B': 20, 'F': 90, 'L': 30, 'S': 0, 'I': 0},
            'meta': {'B': {'basis_bps': 50}}
        },
        {
            'name': "动量向下",
            'factors': {'T': 20, 'M': -60, 'C': 70, 'V': 10, 'O': 30, 'B': 20, 'F': 90, 'L': 70, 'S': 0, 'I': 0},
            'meta': {'B': {'basis_bps': 50}}
        },
        {
            'name': "多重veto",
            'factors': {'T': 20, 'M': -60, 'C': 70, 'V': 10, 'O': -40, 'B': 80, 'F': 90, 'L': 30, 'S': 0, 'I': 0},
            'meta': {'B': {'basis_bps': 200}}
        },
        {
            'name': "screening未通过",
            'factors': {'T': 20, 'M': 10, 'C': 40, 'V': 10, 'O': 30, 'B': 20, 'F': 70, 'L': 70, 'S': 0, 'I': 0},
            'meta': {'B': {'basis_bps': 50}}
        },
    ]

    print("\n[V1测试]")
    for case in test_cases:
        is_acc, reason, threshold = detect_accumulation_v1(case['factors'], case['meta'])
        status = "✅" if is_acc else "❌"
        print(f"{status} {case['name']:20s}: is_acc={is_acc}, threshold={threshold}, reason={reason}")

    print("\n[V2测试]")
    for case in test_cases:
        is_acc, reason, threshold = detect_accumulation_v2(case['factors'], case['meta'])
        status = "✅" if is_acc else "❌"
        print(f"{status} {case['name']:20s}: is_acc={is_acc}, threshold={threshold}")
        if reason:
            print(f"   reason: {reason}")

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
