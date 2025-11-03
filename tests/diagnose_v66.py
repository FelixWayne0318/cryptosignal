#!/usr/bin/env python3
# coding: utf-8
"""
v6.6架构诊断工具 - 深度分析单个币种

用于诊断：
1. 每个因子的原始值和计算过程
2. 调制器是否正确运行
3. 最终分数计算过程
4. 发布判定逻辑
"""

import sys
import os

# 启用详细因子日志（诊断模式）
os.environ['VERBOSE_FACTOR_LOG'] = '1'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.logging import log


def diagnose_symbol(symbol: str):
    """深度诊断单个币种"""

    log("=" * 80)
    log(f"🔍 v6.6架构深度诊断 - {symbol}")
    log("=" * 80)
    log("")

    try:
        # 分析币种
        result = analyze_symbol(symbol)

        if not result or result.get('error'):
            log(f"❌ 分析失败: {result.get('error', '未知错误') if result else '无结果'}")
            return

        # ====== 1. 基础信息 ======
        log("【1. 基础信息】")
        log(f"  符号: {result.get('symbol')}")
        log(f"  价格: {result.get('price', 0):.2f}")
        log(f"  成功: {not result.get('error', False)}")
        log("")

        # ====== 2. 核心因子详情 ======
        log("【2. A层核心因子 (6个, 参与评分, 权重100%)】")
        scores = result.get('scores', {})
        scores_meta = result.get('scores_meta', {})

        CORE_FACTORS = ['T', 'M', 'C', 'V', 'O', 'B']
        core_total = 0

        for f in CORE_FACTORS:
            value = scores.get(f, 0)
            meta = scores_meta.get(f, {})
            core_total += value
            log(f"  {f} ({'趋势' if f=='T' else '动量' if f=='M' else 'CVD' if f=='C' else '量能' if f=='V' else '持仓' if f=='O' else '基差'}): {value:+7.1f}")
            if meta:
                # 显示元数据的关键信息
                if isinstance(meta, dict):
                    for k, v in list(meta.items())[:3]:  # 只显示前3个
                        if isinstance(v, (int, float)):
                            log(f"    └─ {k}: {v:.4f}")

        log(f"  核心因子平均值: {core_total/6:+.1f}")
        log("")

        # ====== 3. 调制器详情 ======
        log("【3. B层调制器 (4个, 不参与评分, 权重0%)】")
        modulation = result.get('modulation', {})

        MODULATORS = ['L', 'S', 'F', 'I']
        for m in MODULATORS:
            value = modulation.get(m, 0)
            log(f"  {m} ({'流动性' if m=='L' else '结构' if m=='S' else '资金领先' if m=='F' else '独立性'}): {value:+7.1f}")
        log("")

        # ====== 4. 调制器输出 (关键！) ======
        log("【4. 调制器输出 (调制执行参数)】")
        modulator_output = result.get('modulator_output', {})

        if modulator_output:
            log(f"  仓位倍数 (L调制): {result.get('position_mult', 1.0):.3f} (范围: 0.30-1.00)")
            log(f"  有效时间 (F/I调制): {result.get('Teff_final', 0):.2f}h")
            log(f"  调制成本 (L调制): {result.get('cost_modulated', 0):.6f}")

            if isinstance(modulator_output, dict):
                log(f"  置信度倍数 (S调制): {modulator_output.get('confidence_mult', 1.0):.3f}")
                log(f"  成本倍数: {modulator_output.get('cost_mult', 1.0):.3f}")
        else:
            log(f"  ⚠️ 调制器输出为空！调制器可能未正确运行")
        log("")

        # ====== 5. 评分计算 ======
        log("【5. 评分计算过程】")
        weighted_score = result.get('weighted_score', 0)
        confidence = result.get('confidence', 0)
        edge = result.get('edge', 0)

        log(f"  加权总分: {weighted_score:+.2f} (核心因子加权平均)")
        log(f"  置信度: {confidence:.2f} (|加权总分|)")
        log(f"  Edge: {edge:+.6f} (加权总分/100)")
        log("")

        # ====== 6. 概率计算 ======
        log("【6. 概率计算】")
        probability = result.get('probability', 0)
        P_long = result.get('P_long', 0)
        P_short = result.get('P_short', 0)
        side = result.get('side', 'neutral')

        log(f"  方向: {side}")
        log(f"  P_long: {P_long:.4f}")
        log(f"  P_short: {P_short:.4f}")
        log(f"  选择概率: {probability:.4f}")
        log("")

        # ====== 7. 软约束检查 (关键！) ======
        log("【7. 软约束检查 (决定是否发布)】")
        publish = result.get('publish', {})

        ev = publish.get('EV', 0)
        ev_positive = publish.get('EV_positive', False)
        p_threshold = publish.get('P_threshold', 0.58)
        p_above_threshold = publish.get('P_above_threshold', False)
        soft_filtered = publish.get('soft_filtered', False)

        log(f"  EV (期望值): {ev:+.6f} {'✅ >0' if ev_positive else '❌ ≤0'}")
        log(f"  P门槛: {p_threshold:.4f}")
        log(f"  P检查: {probability:.4f} {'✅ ≥门槛' if p_above_threshold else '❌ <门槛'}")
        log(f"  软过滤: {'⚠️ 是 (被标记但不硬拒绝)' if soft_filtered else '✅ 否'}")
        log("")

        # ====== 8. 发布判定 ======
        log("【8. 发布判定】")
        is_prime = publish.get('prime', False)
        is_watch = publish.get('watch', False)
        prime_strength = publish.get('prime_strength', 0)
        prime_threshold = publish.get('prime_strength_threshold', 60)
        rejection_reason = publish.get('rejection_reason', [])

        log(f"  Prime强度: {prime_strength:.1f} / {prime_threshold:.1f}")
        log(f"  Prime信号: {'🟢 是' if is_prime else '❌ 否'}")
        log(f"  Watch信号: {'🟡 是' if is_watch else '❌ 否'}")

        if not is_prime and not is_watch:
            log(f"  ⚪ 不发布")
            if rejection_reason:
                log(f"  拒绝原因: {', '.join(rejection_reason)}")
        log("")

        # ====== 9. 诊断结论 ======
        log("【9. 诊断结论】")

        # 检查分数是否过低
        if abs(weighted_score) < 20:
            log(f"  ⚠️ 加权分数过低 ({weighted_score:+.1f})")
            log(f"     原因: 6个核心因子的值都比较小，市场可能处于横盘或震荡状态")
            log(f"     建议: 这是正常现象，等待更强的信号")

        # 检查软约束
        if soft_filtered:
            if not ev_positive:
                log(f"  ⚠️ EV≤0 导致软过滤")
                log(f"     EV={ev:.6f}")
                log(f"     说明: 期望收益为负，即使有信号也不值得交易")
            if not p_above_threshold:
                log(f"  ⚠️ 概率低于阈值导致软过滤")
                log(f"     P={probability:.4f} < {p_threshold:.4f}")
                log(f"     说明: 胜率太低，不满足最低概率要求")

        # 检查调制器
        if not modulator_output:
            log(f"  ❌ 调制器输出为空！")
            log(f"     这不正常，调制器应该输出仓位倍数、Teff等参数")

        # 检查Prime强度
        if prime_strength < prime_threshold - 20:
            log(f"  ⚠️ Prime强度不足 ({prime_strength:.1f} < {prime_threshold:.1f})")
            log(f"     即使通过软约束，Prime强度也需要达到阈值")

        log("")
        log("=" * 80)

        # 返回关键指标
        return {
            'weighted_score': weighted_score,
            'confidence': confidence,
            'probability': probability,
            'ev': ev,
            'prime_strength': prime_strength,
            'soft_filtered': soft_filtered,
            'is_prime': is_prime,
            'modulator_working': bool(modulator_output)
        }

    except Exception as e:
        log(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 默认测试BTCUSDT，可以通过命令行参数指定
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    diagnose_symbol(symbol)
