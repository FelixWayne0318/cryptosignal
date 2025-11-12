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

# v7.2.27新增：导入线性函数工具和F多空适配函数
from ats_core.utils.math_utils import linear_reduce, get_effective_F

# v7.2.30新增：新币阈值统一获取函数
def _get_threshold_by_phase(config, coin_phase: str, key: str, default: Any = None) -> Any:
    """
    根据币种阶段获取对应阈值（统一函数）

    与analyze_symbol.py中的同名函数保持一致
    """
    if not config:
        return default

    # 提取阶段标识
    if "newcoin_ultra" in coin_phase or coin_phase == "newcoin_ultra":
        return config.get_newcoin_threshold('ultra', key, default)
    elif "newcoin_phaseA" in coin_phase or coin_phase == "newcoin_phaseA":
        return config.get_newcoin_threshold('phaseA', key, default)
    elif "newcoin_phaseB" in coin_phase or coin_phase == "newcoin_phaseB":
        return config.get_newcoin_threshold('phaseB', key, default)
    else:
        # mature或其他情况
        return config.get_mature_threshold(key, default)

# v7.2.21修复：使用模块级单例，避免重复初始化和日志污染
from ats_core.calibration.empirical_calibration import EmpiricalCalibrator
_calibrator_singleton = None

def _get_calibrator() -> EmpiricalCalibrator:
    """
    获取校准器单例

    修复原因（v7.2.21）：
    - 之前每次调用analyze_with_v72_enhancements都创建新实例
    - 导致每个币种扫描都打印"数据不足(0/30)，使用启发式规则"
    - 406个币种 = 406条重复警告，严重污染日志
    - 且浪费性能（重复加载calibration_history.json）

    Returns:
        全局单例校准器实例
    """
    global _calibrator_singleton
    if _calibrator_singleton is None:
        _calibrator_singleton = EmpiricalCalibrator()
    return _calibrator_singleton

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

    # v7.2.30新增：获取币种阶段信息（用于阈值选择）
    metadata = original_result.get('metadata', {})
    coin_phase = metadata.get('coin_phase', 'mature')  # 默认为成熟币

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

    # ===== 2.3 v7.2.27修复：计算有效F（考虑做多/做空方向）=====
    # 做多时F>0好（资金领先价格，蓄势），做空时F<0好（资金流出快于价格下跌，恐慌逃离）
    # 因此做空时将F取反，使F>0统一表示好信号
    F_effective = get_effective_F(F_v2, side_long_v72)

    # ===== 2.5 提取I因子（C1 CRITICAL FIX：必须在统计校准之前定义）=====
    # v7.2增强：显式提取I因子用于展示和校准
    # I因子在基础分析中已计算（通过calculate_independence）
    # 这里直接使用，无需重复计算（需要BTC/ETH数据）
    I_v2 = original_result.get('I', 50)
    I_meta = original_result.get('scores_meta', {}).get('I', {})

    # ===== 3. 统计校准概率（P0.3增强：支持F/I因子）=====
    # v7.2.21修复：使用模块级单例，避免重复初始化
    calibrator = _get_calibrator()

    # P0.3修复：如果使用启发式（冷启动），传递F和I因子进行多维度评估
    if not calibrator.calibration_table:
        # 冷启动模式：使用改进的启发式公式
        # v7.2.28修复：传入side_long参数，正确处理空单F逻辑
        P_calibrated = calibrator._bootstrap_probability(
            confidence=confidence_v72,
            F_score=F_v2,
            I_score=I_v2,
            side_long=side_long_v72
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

    # ===== 4.5. v7.2.26改进：F因子驱动的蓄势检测（线性平滑降低） =====
    # 核心理念：F因子是最领先的指标（-4~8h），当F高时应降低其他阈值提前入场
    #
    # v7.2.26改进：从断崖式分级改为线性平滑降低
    # - 避免F=69.9和F=70之间的阈值突变（断崖效应）
    # - 线性公式：reduction_ratio = (F - 50) / 20，当F在50-70区间时线性插值
    # - 支持两种模式：linear（推荐）和 stepped（向后兼容）

    # 初始化默认值（防止作用域问题）
    momentum_enabled = True
    momentum_mode = "linear"
    momentum_level = 0
    momentum_desc = "正常模式"
    momentum_confidence_min = None
    momentum_P_min = None
    momentum_EV_min = None
    momentum_F_min = None
    momentum_position_mult = 1.0

    try:
        # 读取蓄势配置
        momentum_config = config.config.get('蓄势分级配置', {})
        momentum_enabled = momentum_config.get('_enabled', True)
        momentum_mode = momentum_config.get('_mode', 'linear')

        if momentum_enabled:
            # ==== 模式1：线性平滑降低（推荐，避免断崖效应） ====
            if momentum_mode == "linear":
                # v7.2.27修复：使用F_effective考虑多空方向
                # 读取线性模式参数
                linear_params = momentum_config.get('线性模式参数', {})
                F_threshold_min = linear_params.get('F_threshold_min', 50)
                F_threshold_max = linear_params.get('F_threshold_max', 70)

                max_reduction = linear_params.get('最大阈值降低', {})
                confidence_reduction = max_reduction.get('confidence_reduction', 5)
                P_reduction = max_reduction.get('P_reduction', 0.08)
                EV_reduction = max_reduction.get('EV_reduction', 0.007)
                F_min_increase = max_reduction.get('F_min_increase', 60)
                position_reduction = max_reduction.get('position_reduction', 0.5)

                # v7.2.27新增：F≥90极值警戒处理
                extreme_config = momentum_config.get('F极值警戒配置', {})
                F_extreme_threshold = extreme_config.get('F_extreme_threshold', 90)

                if F_effective >= F_extreme_threshold and extreme_config.get('_enabled', True):
                    # F≥90：极值警戒（保守策略：反而提高质量要求）
                    if extreme_config.get('strategy') == 'conservative':
                        conservative_mode = extreme_config.get('conservative_mode', {})
                        momentum_confidence_min = conservative_mode.get('confidence_min', 12)
                        momentum_P_min = conservative_mode.get('P_min', 0.50)
                        momentum_EV_min = conservative_mode.get('EV_min', 0.015)
                        momentum_F_min = conservative_mode.get('F_min', 50)
                        momentum_position_mult = conservative_mode.get('position_mult', 0.5)
                        momentum_level = 3
                        momentum_desc = "极限蓄势（警戒）"
                elif F_effective >= F_threshold_max:
                    # 70≤F<90：完全降低
                    momentum_level = 3
                    momentum_desc = "极早期蓄势"

                    # 获取基准阈值（v7.2.30修复：使用币种阶段特定阈值）
                    base_confidence = _get_threshold_by_phase(config, coin_phase, 'confidence_min', 15)
                    base_P = config.get_gate_threshold('gate4_probability', 'P_min', 0.50)
                    base_EV = config.get_gate_threshold('gate3_ev', 'EV_min', 0.015)
                    base_F = config.get_gate_threshold('gate2_fund_support', 'F_min', -10)

                    # 应用最大降低
                    momentum_confidence_min = base_confidence - confidence_reduction
                    momentum_P_min = base_P - P_reduction
                    momentum_EV_min = base_EV - EV_reduction
                    momentum_F_min = base_F + F_min_increase
                    momentum_position_mult = 1.0 - position_reduction
                elif F_effective >= F_threshold_min:
                    # 50≤F<70：线性插值（平滑过渡）
                    # v7.2.27改进：使用linear_reduce简化计算

                    # 获取基准阈值（v7.2.30修复：使用币种阶段特定阈值）
                    base_confidence = _get_threshold_by_phase(config, coin_phase, 'confidence_min', 15)
                    base_P = config.get_gate_threshold('gate4_probability', 'P_min', 0.50)
                    base_EV = config.get_gate_threshold('gate3_ev', 'EV_min', 0.015)
                    base_F = config.get_gate_threshold('gate2_fund_support', 'F_min', -10)

                    # 使用linear_reduce进行线性插值
                    momentum_confidence_min = linear_reduce(
                        F_effective, F_threshold_min, F_threshold_max,
                        base_confidence, base_confidence - confidence_reduction
                    )
                    momentum_P_min = linear_reduce(
                        F_effective, F_threshold_min, F_threshold_max,
                        base_P, base_P - P_reduction
                    )
                    momentum_EV_min = linear_reduce(
                        F_effective, F_threshold_min, F_threshold_max,
                        base_EV, base_EV - EV_reduction
                    )
                    momentum_F_min = linear_reduce(
                        F_effective, F_threshold_min, F_threshold_max,
                        base_F, base_F + F_min_increase
                    )
                    momentum_position_mult = linear_reduce(
                        F_effective, F_threshold_min, F_threshold_max,
                        1.0, 1.0 - position_reduction
                    )

                    # 根据F值判定显示级别（仅用于Telegram显示）
                    if F_effective >= 65:
                        momentum_level = 3
                        momentum_desc = "极早期蓄势"
                    elif F_effective >= 55:
                        momentum_level = 2
                        momentum_desc = "早期蓄势"
                    else:
                        momentum_level = 1
                        momentum_desc = "蓄势待发"
                else:
                    # F<50：正常模式
                    momentum_level = 0
                    momentum_desc = "正常模式"

            # ==== 模式2：分级降低（向后兼容，保留断崖式） ====
            elif momentum_mode == "stepped":
                # v7.2.27修复：使用F_effective考虑多空方向
                # 读取分级阈值
                level_3_config = momentum_config.get('level_3_极早期', {})
                level_2_config = momentum_config.get('level_2_早期', {})
                level_1_config = momentum_config.get('level_1_强势', {})

                level_3_threshold = level_3_config.get('F_threshold', 70)
                level_2_threshold = level_2_config.get('F_threshold', 60)
                level_1_threshold = level_1_config.get('F_threshold', 50)

                # 判断当前F因子属于哪个级别（明确区间，提升可读性）
                if F_effective >= level_3_threshold:  # F≥70
                    momentum_level = 3
                    momentum_config_active = level_3_config
                    momentum_desc = "极早期蓄势"
                elif level_2_threshold <= F_effective < level_3_threshold:  # 60≤F<70
                    momentum_level = 2
                    momentum_config_active = level_2_config
                    momentum_desc = "早期蓄势"
                elif level_1_threshold <= F_effective < level_2_threshold:  # 50≤F<60
                    momentum_level = 1
                    momentum_config_active = level_1_config
                    momentum_desc = "蓄势待发"
                else:  # F<50
                    momentum_level = 0
                    momentum_config_active = None
                    momentum_desc = "正常模式"

                # 应用分级阈值
                if momentum_level > 0 and momentum_config_active:
                    threshold_config = momentum_config_active.get('阈值降低', {})
                    momentum_confidence_min = threshold_config.get('confidence_min', 15)
                    momentum_P_min = threshold_config.get('P_min', 0.50)
                    momentum_EV_min = threshold_config.get('EV_min', 0.015)
                    momentum_F_min = threshold_config.get('F_min', -10)
                    momentum_position_mult = momentum_config_active.get('仓位倍数', 1.0)

            else:
                # 未知模式
                momentum_desc = f"未知模式: {momentum_mode}"

    except Exception as e:
        # 配置加载失败，使用正常模式
        momentum_level = 0
        momentum_desc = f"配置加载失败: {e}"
        momentum_confidence_min = None
        momentum_P_min = None
        momentum_EV_min = None
        momentum_F_min = None
        momentum_position_mult = 1.0

    # ===== 5. 五道闸门（v7.2 重构 + v3.1增强：新增I×Market联合闸门） =====
    # Q3 FIX: 修正注释编号（删除重复的I因子定义）
    # v7.2设计理念：
    # - 基础分析（analyze_symbol）已经完成了完整的闸门检查
    # - v7.2增强层只需重新计算部分因子（F_v2），然后应用简化的质量检查
    # - 避免重复实现复杂的闸门逻辑（订单簿、DataQual等）

    # v3.1新增：Gate 5 - I×Market联合检查（过滤"低独立性+逆势"的危险信号）

    # 方案：使用简化的五道检查（只检查关键指标）
    # 阶段2.2：从配置文件读取闸门阈值
    # v7.2.25：如果触发蓄势级别，使用降低后的阈值
    min_klines = config.get_gate_threshold('gate1_data_quality', 'min_klines', 100)

    # v7.2.25: 动态阈值（蓄势时降低）
    if momentum_P_min is not None:
        # 使用蓄势级别的降低阈值
        P_min = momentum_P_min
        EV_min = momentum_EV_min
        F_min = momentum_F_min
        # confidence_min在因子分组时使用（这里不需要）
    else:
        # 使用正常阈值
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
    # v7.2.27修复：使用F_effective考虑多空方向
    # 做多：F_effective >= F_min (资金领先价格，蓄势待发)
    # 做空：F_effective >= F_min (资金逃离快于价格下跌，恐慌抛售)
    gates_fund_support = 1.0 if F_effective >= F_min else 0.0

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
            "version": "v7.2.26_linear_momentum",

            # F因子v2（资金领先性）
            # v7.2.15修复：移除F_comparison冗余结构（A1修复后基础层已统一使用v2）
            "F_v2": F_v2,
            "F_v2_meta": F_v2_meta,

            # v7.2.26改进：蓄势检测信息（支持线性/分级两种模式）
            "momentum_grading": {
                "level": momentum_level,
                "description": momentum_desc,
                "mode": momentum_mode,
                "enabled": momentum_enabled,
                "dynamic_thresholds": {
                    "P_min": P_min,
                    "EV_min": EV_min,
                    "F_min": F_min,
                    "confidence_min": momentum_confidence_min if momentum_confidence_min else config.get_mature_threshold('confidence_min', 15)
                },
                "position_multiplier": momentum_position_mult
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
        # v7.2.15移除：F_changed_sign（A1修复后F已统一为v2，不再有符号变化）
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

            # v7.2.15修复：移除F_changed_sign统计（A1修复后F已统一为v2）

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

    print(f"\n1. F因子:")
    print(f"   F_v2: {v72['F_v2']}")
    print(f"   元数据: {v72['F_v2_meta']}")

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
