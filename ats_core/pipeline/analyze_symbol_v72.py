# coding: utf-8
"""
信号分析模块 v7.2阶段1（集成版）

这个文件展示如何集成v7.2的所有改进：
1. F因子v2（精确定义）
2. 因子分组（TC/VOM/B）
3. 四道闸门
4. 统计校准

使用方式：
    from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements

    # 在现有的analyze_symbol结果基础上应用v7.2增强
    result = analyze_symbol(symbol)  # 原有函数
    result_v72 = analyze_with_v72_enhancements(result, symbol, klines, oi_data, cvd_series, atr_now)

注意：这是一个渐进式改进，不破坏现有系统
"""

from typing import Dict, Any
import math

def analyze_with_v72_enhancements(
    original_result: Dict[str, Any],
    symbol: str,
    klines: list,
    oi_data: list,
    cvd_series: list,
    atr_now: float
) -> Dict[str, Any]:
    """
    在原有分析结果基础上应用v7.2增强

    改进点：
    1. 重新计算F因子（使用v2精确定义）
    2. 重新计算weighted_score（使用因子分组）
    3. 应用四道闸门过滤
    4. 使用统计校准获取真实概率

    Args:
        original_result: 原有analyze_symbol的结果
        symbol: 币种符号
        klines: K线数据
        oi_data: OI数据
        cvd_series: CVD序列
        atr_now: 当前ATR

    Returns:
        增强后的结果字典
    """
    # ===== 0. 获取中间数据（L1修复：使用基础层提供的数据，避免重复计算）=====
    intermediate = original_result.get('intermediate_data', {})

    # 优先使用intermediate_data，如果没有则使用传入的参数（向后兼容）
    cvd_series = intermediate.get('cvd_series', cvd_series)
    klines = intermediate.get('klines', klines)
    oi_data = intermediate.get('oi_data', oi_data)
    atr_now = intermediate.get('atr_now', atr_now)

    # ===== 0.5 加载配置（阶段2.2：使用配置文件）=====
    from ats_core.config.threshold_config import get_thresholds
    config = get_thresholds()

    # v7.2.9修复：加载F因子动量阈值（避免硬编码）
    try:
        F_strong_momentum = config.config.get('F因子动量阈值', {}).get('F_strong_momentum', 30)
        F_moderate_momentum = config.config.get('F因子动量阈值', {}).get('F_moderate_momentum', 15)
    except:
        F_strong_momentum = 30
        F_moderate_momentum = 15

    # ===== 1. 获取F因子（A1修复：基础层已使用v2，直接使用）=====
    # 基础层已经统一使用score_fund_leading_v2，直接使用其结果
    F_v2 = original_result.get('F', 0)
    F_v2_meta = original_result.get('scores_meta', {}).get('F', {})

    # ===== 2. 重新计算weighted_score（因子分组+配置化权重） =====
    from ats_core.scoring.factor_groups import calculate_grouped_score

    # 提取原有因子分数
    T = original_result.get('T', 0)
    M = original_result.get('M', 0)
    C = original_result.get('C', 0)
    V = original_result.get('V', 0)
    O = original_result.get('O', 0)
    B = original_result.get('B', 0)

    # 阶段2.2：从配置文件获取权重
    weights = config.get_factor_weights()

    # 分组计算（使用配置化权重）
    weighted_score_v72, group_meta = calculate_grouped_score(T, M, C, V, O, B, params=weights)
    confidence_v72 = abs(weighted_score_v72)
    side_long_v72 = (weighted_score_v72 > 0)

    # ===== 2.5 提取I因子（C1 CRITICAL FIX：必须在统计校准之前定义）=====
    # v7.2增强：显式提取I因子用于展示和校准
    # I因子在基础分析中已计算（通过calculate_independence）
    # 这里直接使用，无需重复计算（需要BTC/ETH数据）
    I_v2 = original_result.get('I', 50)
    I_meta = original_result.get('scores_meta', {}).get('I', {})

    # ===== 3. 统计校准概率（P0.3增强：支持F/I因子）=====
    from ats_core.calibration.empirical_calibration import EmpiricalCalibrator

    calibrator = EmpiricalCalibrator()

    # P0.3修复：如果使用启发式（冷启动），传递F和I因子进行多维度评估
    if not calibrator.calibration_table:
        # 冷启动模式：使用改进的启发式公式
        P_calibrated = calibrator._bootstrap_probability(
            confidence=confidence_v72,
            F_score=F_v2,
            I_score=I_v2
        )
    else:
        # 统计校准模式：使用历史数据
        P_calibrated = calibrator.get_calibrated_probability(confidence_v72)

    # ===== 4. 计算EV（阶段2.2：使用配置化参数）=====
    # 从配置文件获取EV计算参数
    spread_bps = config.get_ev_params('spread_bps', 2.5)
    impact_bps = config.get_ev_params('impact_bps', 3.0)
    funding_hold_hours = config.get_ev_params('funding_hold_hours', 4.0)
    default_RR = config.get_ev_params('default_RR', 2.0)
    atr_multiplier = config.get_ev_params('atr_multiplier', 1.5)

    # 成本估算
    cost_bps = spread_bps / 2 + impact_bps

    # 资金费
    B_meta = original_result.get('scores_meta', {}).get('B', {})
    funding_rate = B_meta.get('funding_rate', 0.0001)
    # 按持有时间计算资金费（从配置读取）
    funding_bps = abs(funding_rate) * 10000 * (funding_hold_hours / 8.0)

    total_cost_pct = (cost_bps + funding_bps) / 10000

    # 止损/止盈（使用配置化参数）
    stop_loss_result = original_result.get('stop_loss', {})
    SL_distance_pct = stop_loss_result.get('distance_pct', atr_now / original_result['price'] * atr_multiplier)
    TP_distance_pct = SL_distance_pct * default_RR  # 使用配置的RR

    # EV = P×TP - (1-P)×SL - cost
    EV_net = P_calibrated * TP_distance_pct - (1 - P_calibrated) * SL_distance_pct - total_cost_pct

    # ===== 5. 五道闸门（v7.2 重构 + v3.1增强：新增I×Market联合闸门） =====
    # Q3 FIX: 修正注释编号（删除重复的I因子定义）
    # v7.2设计理念：
    # - 基础分析（analyze_symbol）已经完成了完整的闸门检查
    # - v7.2增强层只需重新计算部分因子（F_v2），然后应用简化的质量检查
    # - 避免重复实现复杂的闸门逻辑（订单簿、DataQual等）

    # v3.1新增：Gate 5 - I×Market联合检查（过滤"低独立性+逆势"的危险信号）

    # 方案：使用简化的五道检查（只检查关键指标）
    # 阶段2.2：从配置文件读取闸门阈值
    min_klines = config.get_gate_threshold('gate1_data_quality', 'min_klines', 100)
    P_min = config.get_gate_threshold('gate4_probability', 'P_min', 0.50)
    EV_min = config.get_gate_threshold('gate3_ev', 'EV_min', 0.0)
    F_min = config.get_gate_threshold('gate2_fund_support', 'F_min', -15)
    I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 30)  # v3.1新增
    market_regime_threshold = config.get_gate_threshold('gate5_independence_market', 'market_regime_threshold', 30)  # v3.1新增
    # v7.2.9修复：从配置读取I因子相关阈值（避免硬编码）
    I_high_independence = config.get_gate_threshold('gate5_independence_market', 'I_high_independence', 60)
    confidence_boost_aligned = config.get_gate_threshold('gate5_independence_market', 'confidence_boost_aligned', 1.2)
    # v7.2.10修复：从配置读取闸门通过阈值（避免硬编码0.5）
    gate_pass_threshold = config.get_gate_threshold('v72闸门阈值', 'gate_pass_threshold', 0.5)

    gates_data_quality = 1.0 if len(klines) >= min_klines else 0.0
    gates_ev = 1.0 if EV_net > EV_min else 0.0
    gates_probability = 1.0 if P_calibrated >= P_min else 0.0

    # F因子闸门（v7.2特有：使用F_v2）
    # F >= F_min: 资金支撑合格
    # F < F_min: 价格领先资金，追高风险
    gates_fund_support = 1.0 if F_v2 >= F_min else 0.0

    # Gate 5: I×Market联合闸门（v3.1新增）
    # 过滤"低独立性+逆势"的危险信号
    market_regime = original_result.get('market_regime', 0)

    if I_v2 >= I_high_independence:
        # 高独立性：不受大盘影响，直接通过
        gates_independence_market = 1.0
        conflict_reason = "high_independence"
        conflict_mult = 1.0
    elif I_v2 < I_min:
        # 低独立性：需要检查与大盘方向是否一致
        if side_long_v72 and market_regime < -market_regime_threshold:
            # 危险信号：做多但熊市（低独立性+逆势）
            gates_independence_market = 0.0
            conflict_reason = "low_independence_bear_market_long"
            conflict_mult = 0.0
        elif not side_long_v72 and market_regime > market_regime_threshold:
            # 危险信号：做空但牛市（低独立性+逆势）
            gates_independence_market = 0.0
            conflict_reason = "low_independence_bull_market_short"
            conflict_mult = 0.0
        elif side_long_v72 and market_regime > market_regime_threshold:
            # 优质信号：做多且牛市（低独立性+顺势）- 放大信心
            gates_independence_market = 1.0
            conflict_reason = "low_independence_bull_align"
            conflict_mult = confidence_boost_aligned  # v7.2.9修复：从配置读取
        elif not side_long_v72 and market_regime < -market_regime_threshold:
            # 优质信号：做空且熊市（低独立性+顺势）- 放大信心
            gates_independence_market = 1.0
            conflict_reason = "low_independence_bear_align"
            conflict_mult = confidence_boost_aligned  # v7.2.9修复：从配置读取
        else:
            # 正常情况：市场中性或轻度趋势
            gates_independence_market = 1.0
            conflict_reason = "normal"
            conflict_mult = 1.0
    else:
        # 中等独立性：正常通过
        gates_independence_market = 1.0
        conflict_reason = "normal"
        conflict_mult = 1.0

    # 综合判定（所有五道闸门都通过才发布）
    # v7.2.10修复：使用配置的gate_pass_threshold替代硬编码0.5
    pass_gates = all([
        gates_data_quality > gate_pass_threshold,
        gates_ev > gate_pass_threshold,
        gates_probability > gate_pass_threshold,
        gates_fund_support > gate_pass_threshold,
        gates_independence_market > gate_pass_threshold  # v3.1新增
    ])

    # 闸门原因
    if not pass_gates:
        failed_gates = []
        if gates_data_quality <= gate_pass_threshold:
            failed_gates.append(f"数据质量不足(bars={len(klines)}, 需要>={min_klines})")
        if gates_ev <= gate_pass_threshold:
            failed_gates.append(f"EV≤{EV_min}({EV_net:.4f})")
        if gates_probability <= gate_pass_threshold:
            failed_gates.append(f"P<{P_min}({P_calibrated:.3f})")
        if gates_fund_support <= gate_pass_threshold:
            failed_gates.append(f"F因子过低({F_v2}, 需要>={F_min})")
        if gates_independence_market <= gate_pass_threshold:
            # v3.1新增：I×Market冲突检测
            direction = "做多" if side_long_v72 else "做空"
            market_trend = "牛市" if market_regime > 0 else "熊市"
            failed_gates.append(f"I×Market冲突({direction}+{market_trend}, I={I_v2:.0f}<{I_min}, Market={market_regime:.0f})")
        gate_reason = "; ".join(failed_gates)
    else:
        gate_reason = "all_gates_passed"

    # 闸门详情
    gate_details = {
        "all_pass": pass_gates,
        "details": [
            {"gate": 1, "name": "data_quality", "pass": gates_data_quality > gate_pass_threshold, "value": gates_data_quality},
            {"gate": 2, "name": "fund_support", "pass": gates_fund_support > gate_pass_threshold, "value": F_v2, "threshold": -15},
            {"gate": 3, "name": "ev", "pass": gates_ev > gate_pass_threshold, "value": EV_net, "threshold": 0.0},
            {"gate": 4, "name": "probability", "pass": gates_probability > gate_pass_threshold, "value": P_calibrated, "threshold": 0.50},
            {"gate": 5, "name": "independence_market", "pass": gates_independence_market > gate_pass_threshold,
             "value": I_v2, "market_regime": market_regime, "conflict_reason": conflict_reason,
             "threshold": I_min}  # v3.1新增
        ]
    }

    # v3.1增强：应用I×Market对齐倍数（提升顺势信号信心）
    # 当低独立性币种与大盘方向一致时，放大信心度×1.2
    confidence_v72_adjusted = confidence_v72 * conflict_mult

    # ===== 6. 最终判定 =====
    is_prime_v72 = pass_gates
    signal_v72 = None
    if is_prime_v72:
        signal_v72 = "LONG" if side_long_v72 else "SHORT"

    # ===== 7. 组装v7.2结果 =====
    result_v72 = {
        # 原始结果（保留）
        **original_result,

        # v7.2增强字段
        "v72_enhancements": {
            "version": "v7.2_stage1",

            # F因子v2（资金领先性）
            "F_v2": F_v2,
            "F_v2_meta": F_v2_meta,
            "F_original": original_result.get('F', 0),
            "F_comparison": {
                "v1": original_result.get('F', 0),
                "v2": F_v2,
                "diff": F_v2 - original_result.get('F', 0)
            },

            # I因子（市场独立性）
            "I_v2": I_v2,
            "I_meta": I_meta,

            # v3.1新增：I×Market对齐分析
            "independence_market_analysis": {
                "I_score": I_v2,
                "market_regime": market_regime,
                "conflict_reason": conflict_reason,
                "confidence_multiplier": conflict_mult,
                "alignment": "顺势" if conflict_mult > 1.0 else ("逆势" if conflict_mult == 0.0 else "正常")
            },

            # 因子分组
            "grouped_score": {
                "weighted_score": round(weighted_score_v72, 2),
                "confidence": round(confidence_v72, 2),
                "confidence_adjusted": round(confidence_v72_adjusted, 2),  # v3.1新增：应用I×Market调整后的信心度
                "side_long": side_long_v72,
                "group_meta": group_meta
            },
            "score_comparison": {
                "original": round(original_result.get('weighted_score', 0), 2),
                "grouped": round(weighted_score_v72, 2),
                "diff": round(weighted_score_v72 - original_result.get('weighted_score', 0), 2)
            },

            # 统计校准
            "probability": {
                "original": round(original_result.get('probability', 0.5), 3),
                "calibrated": round(P_calibrated, 3),
                "method": "empirical" if calibrator.calibration_table else "bootstrap"
            },

            # 期望值
            "EV": {
                "net": round(EV_net, 4),
                "TP_distance": round(TP_distance_pct, 4),
                "SL_distance": round(SL_distance_pct, 4),
                "cost": round(total_cost_pct, 4),
                "RR": round(TP_distance_pct / SL_distance_pct if SL_distance_pct > 0 else 0, 2)
            },

            # 四道闸门
            "gates": {
                "pass_all": pass_gates,
                "reason": gate_reason,
                "details": gate_details
            },

            # 最终判定
            "final_decision": {
                "is_prime": is_prime_v72,
                "signal": signal_v72,
                "original_was_prime": original_result.get('publish', {}).get('prime', False),
                "decision_changed": is_prime_v72 != original_result.get('publish', {}).get('prime', False)
            },

            # ===== Telegram模板兼容字段（扁平化，便于render_trade_v72读取） =====
            "P_calibrated": round(P_calibrated, 3),
            "EV_net": round(EV_net, 4),
            "confidence_v72": round(confidence_v72, 2),
            "group_scores": {
                "TC": group_meta.get('TC_group'),
                "VOM": group_meta.get('VOM_group'),
                "B": group_meta.get('B_group')
            },
            "gate_results": gate_details,

            # ===== 蓄势待发标记（核心功能）=====
            # v7.2.9修复：从配置读取F因子动量阈值（避免硬编码）
            # F因子 > F_strong_momentum = 资金强势领先 = 蓄势待发
            # F因子 > F_moderate_momentum = 资金明显领先 = 即将爆发
            "is_momentum_ready": F_v2 > F_strong_momentum,
            "is_breakout_soon": F_v2 > F_moderate_momentum,
            "momentum_level": (
                "strong" if F_v2 > F_strong_momentum else
                "moderate" if F_v2 > F_moderate_momentum else
                "weak" if F_v2 > 0 else
                "negative"
            )
        }
    }

    # 更新顶层字段（覆盖原有值）
    result_v72.update({
        "F": F_v2,  # 使用v2的F
        "weighted_score": weighted_score_v72,  # 使用分组的score
        "confidence": confidence_v72,
        "probability_calibrated": P_calibrated,
        "EV_net": EV_net,
        "is_prime_v72": is_prime_v72,
        "signal_v72": signal_v72
    })

    return result_v72


def batch_analyze_with_v72(symbols: list, data_getter_func) -> Dict[str, Any]:
    """
    批量分析多个币种（应用v7.2增强）

    Args:
        symbols: 币种列表
        data_getter_func: 获取数据的函数(symbol) -> (klines, oi_data, cvd, atr)

    Returns:
        批量分析结果
    """
    results = {}
    stats = {
        "total": len(symbols),
        "v72_improved": 0,  # v7.2判定与原始不同
        "gates_rejected": 0,  # 四道闸门拒绝
        "F_changed_sign": 0,  # F因子符号改变
    }

    for symbol in symbols:
        try:
            # 获取原始分析结果
            from ats_core.pipeline.analyze_symbol import analyze_symbol
            original = analyze_symbol(symbol)

            # 获取数据
            klines, oi_data, cvd, atr = data_getter_func(symbol)

            # 应用v7.2增强
            result_v72 = analyze_with_v72_enhancements(
                original, symbol, klines, oi_data, cvd, atr
            )

            # 统计
            v72_enhancements = result_v72["v72_enhancements"]
            if v72_enhancements["final_decision"]["decision_changed"]:
                stats["v72_improved"] += 1

            if not v72_enhancements["gates"]["pass_all"]:
                stats["gates_rejected"] += 1

            F_comp = v72_enhancements["F_comparison"]
            if (F_comp["v1"] > 0) != (F_comp["v2"] > 0):
                stats["F_changed_sign"] += 1

            results[symbol] = result_v72

        except Exception as e:
            results[symbol] = {"error": str(e)}

    return {
        "results": results,
        "stats": stats
    }


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("v7.2阶段1集成测试")
    print("=" * 60)

    # 模拟数据
    class MockResult:
        def get(self, key, default=None):
            mock_data = {
                "T": 65,
                "M": 55,
                "C": 70,
                "V": 45,
                "O": 60,
                "B": 15,
                "F": 40,  # 原始F
                "I": 55,
                "weighted_score": 58.5,
                "probability": 0.62,
                "market_regime": -20,
                "price": 50000,
                "publish": {"prime": True},
                "scores_meta": {"B": {"funding_rate": 0.0001}},
                "stop_loss": {"distance_pct": 0.015}
            }
            return mock_data.get(key, default)

    # 模拟K线和数据
    klines = [[0, 49000, 50500, 49000, 50000, 1000000, 0, 0, 0, 0, 0, 0] for _ in range(20)]
    oi_data = [[i * 3600000, 1000000 + i * 1000] for i in range(20)]
    cvd_series = [i * 100 for i in range(20)]
    atr_now = 750

    result = analyze_with_v72_enhancements(
        original_result=MockResult(),
        symbol="BTCUSDT",
        klines=klines,
        oi_data=oi_data,
        cvd_series=cvd_series,
        atr_now=atr_now
    )

    print("\nv7.2增强结果:")
    v72 = result["v72_enhancements"]

    print(f"\n1. F因子对比:")
    print(f"   原始F: {v72['F_comparison']['v1']}")
    print(f"   v2 F: {v72['F_comparison']['v2']}")
    print(f"   差异: {v72['F_comparison']['diff']}")

    print(f"\n2. 分数对比:")
    print(f"   原始分数: {v72['score_comparison']['original']}")
    print(f"   分组分数: {v72['score_comparison']['grouped']}")
    print(f"   差异: {v72['score_comparison']['diff']}")

    print(f"\n3. 概率校准:")
    print(f"   原始概率: {v72['probability']['original']}")
    print(f"   校准概率: {v72['probability']['calibrated']}")
    print(f"   方法: {v72['probability']['method']}")

    print(f"\n4. 期望值:")
    print(f"   EV净值: {v72['EV']['net']:.4f}")
    print(f"   RR比: {v72['EV']['RR']:.2f}")

    print(f"\n5. 四道闸门:")
    print(f"   全部通过: {v72['gates']['pass_all']}")
    print(f"   原因: {v72['gates']['reason']}")

    print(f"\n6. 最终判定:")
    print(f"   v7.2判定: {v72['final_decision']['signal']}")
    print(f"   原始判定: {'LONG/SHORT' if v72['final_decision']['original_was_prime'] else 'None'}")
    print(f"   判定改变: {v72['final_decision']['decision_changed']}")

    print("\n" + "=" * 60)
