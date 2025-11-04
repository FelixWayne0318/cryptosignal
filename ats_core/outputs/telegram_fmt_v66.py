#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ats_core/outputs/telegram_fmt_v66.py

v6.6 富媒体Telegram消息模板

9个信息块设计：
1. 信号头部 - 方向、交易对、强度emoji
2. 核心指标 - 评分、edge、概率、EV、信心指数
3. 因子明细 - Top 4贡献因子
4. 调制器状态 - L/S/F/I调制器详情
5. 入场与止损止盈 - 价格、距离、RR比
6. 仓位建议 - 基准仓位、L调制、分配策略
7. 风险提示 - 流动性、结构、独立性、数据质量警告
8. 市场环境 - BTC趋势、市场情绪、波动率
9. 元数据 - 时间戳、版本、链接

特点：
- 基于telegram_fmt.py但更丰富
- Github-flavored markdown格式
- 支持compact/rich/debug三种模式
- 单条消息≤4096字符（Telegram限制）

作者：Claude (Sonnet 4.5)
日期：2025-11-03
版本：v6.6
"""

from typing import Dict, Any, Optional
from datetime import datetime


def render_v66_signal(
    signal_data: Dict[str, Any],
    mode: str = "rich"
) -> str:
    """
    渲染v6.6富媒体信号消息

    参数：
    - signal_data: analyze_symbol()返回的信号数据
    - mode: 消息模式
      - "rich": 富信息（9个block，默认）~1800字符
      - "compact": 简洁（6个block）~900字符
      - "debug": 调试（完整信息）~3000字符

    返回：
    - Telegram消息文本（markdown格式）
    """
    if mode == "compact":
        return _render_compact(signal_data)
    elif mode == "debug":
        return _render_debug(signal_data)
    else:
        return _render_rich(signal_data)


def _render_rich(data: Dict[str, Any]) -> str:
    """渲染富信息模式（9 blocks）"""

    # ============ Block 1: 信号头部 ============
    direction = data.get("side", "unknown").upper()
    symbol = data.get("symbol", "UNKNOWN")
    score = data.get("weighted_score", 0)

    # v6.6修复：确保score是数值类型（防止dict导致abs()错误）
    if isinstance(score, dict):
        score = 0
    elif not isinstance(score, (int, float)):
        score = 0

    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    strength_emoji = _get_strength_emoji(abs(score))

    header = f"""
{direction_emoji} **{direction} {symbol}** {strength_emoji}
━━━━━━━━━━━━━━━━━━━━
"""

    # ============ Block 2: 核心指标 ============
    edge = data.get("edge", 0)
    probability = data.get("probability", 0)
    confidence = data.get("confidence", 0)

    # v6.6修复：确保数值类型（防止dict导致格式化错误）
    if isinstance(edge, dict):
        edge = 0
    if isinstance(probability, dict):
        probability = 0
    if isinstance(confidence, dict):
        confidence = 0

    # v6.6: 使用软约束的EV
    publish_info = data.get("publish", {})
    EV = publish_info.get("EV", 0)
    if isinstance(EV, dict):
        EV = 0

    core_metrics = f"""
📊 **核心指标**
• 综合评分: {score:+.1f}/100
• 优势边际: {edge:+.2f}
• 胜率: {probability:.1%}
• 期望收益: {EV:+.2%}
• 信心指数: {confidence:.0f}/100
"""

    # ============ Block 3: 因子明细 ============
    # 获取因子贡献（Top 4）
    factor_contribs = data.get("factor_contributions", {})
    if factor_contribs:
        # v6.6修复：过滤掉汇总键，只保留真正的因子
        # 汇总键列表
        summary_keys = {"total_weight", "weighted_score", "confidence", "edge"}

        # 过滤出真正的因子（T, M, C, V, O, B, L, S, F, I）
        real_factors = {
            k: v for k, v in factor_contribs.items()
            if k not in summary_keys and isinstance(v, dict)
        }

        # 按贡献绝对值排序取Top 4
        def safe_contrib(factor_dict):
            """安全获取贡献值"""
            if isinstance(factor_dict, dict):
                contrib = factor_dict.get("contribution", 0)
                if isinstance(contrib, (int, float)):
                    return abs(contrib)
            return 0

        sorted_factors = sorted(
            real_factors.items(),
            key=lambda x: safe_contrib(x[1]),
            reverse=True
        )[:4]

        factor_lines = []
        for name, factor_dict in sorted_factors:
            emoji = _get_factor_emoji(name)

            # 从factor_dict中提取数据
            score = factor_dict.get("score", 0)
            weight_pct = factor_dict.get("weight_pct", 0)
            contribution = factor_dict.get("contribution", 0)

            # 确保数值类型
            if not isinstance(score, (int, float)):
                score = 0
            if not isinstance(weight_pct, (int, float)):
                weight_pct = 0
            if not isinstance(contribution, (int, float)):
                contribution = 0

            factor_lines.append(
                f"  {emoji} {name}: {score:+3.0f} ({weight_pct:.1f}%) → {contribution:+.1f}"
            )

        factor_detail = f"""
🎯 **因子分析** (Top 4)
{chr(10).join(factor_lines)}
"""
    else:
        factor_detail = ""

    # ============ Block 4: 调制器状态 ============
    modulator_output = data.get("modulator_output", {})

    if modulator_output:
        L_data = modulator_output.get("L", {})
        S_data = modulator_output.get("S", {})
        F_data = modulator_output.get("F", {})
        I_data = modulator_output.get("I", {})
        fusion = modulator_output.get("fusion", {})

        # v6.6: 获取分数
        modulation = data.get("modulation", {})
        L_score = modulation.get("L", 0)
        S_score = modulation.get("S", 0)
        F_score = modulation.get("F", 0)
        I_score = modulation.get("I", 0)

        modulator_status = f"""
⚙️ **调制器状态**
• L(流动性): {L_score}/100
  → 仓位调整: {L_data.get('position_mult', 1.0):.0%}
  → 成本调整: {L_data.get('cost_eff', 0):+.3%}

• S(结构): {S_score:+d}/100
  → 信心倍数: {S_data.get('confidence_mult', 1.0):.2f}x
  → Teff倍数: {S_data.get('Teff_mult', 1.0):.2f}x

• F(资金领先): {F_score:+d}/100
  → Teff倍数: {F_data.get('Teff_mult', 1.0):.2f}x

• I(独立性): {I_score:+d}/100
  → Teff倍数: {I_data.get('Teff_mult', 1.0):.2f}x
  → 成本调整: {I_data.get('cost_eff', 0):+.3%}

📈 融合结果:
  Teff = {fusion.get('Teff_final', 2.0):.2f} (基准2.0)
  成本 = {fusion.get('cost_final', 0.0015):.3%}
"""
    else:
        modulator_status = ""

    # ============ Block 5: 入场与止损止盈 ============
    current_price = data.get("price", 0)
    stop_loss_data = data.get("stop_loss", {})
    take_profit_data = data.get("take_profit", {})

    sl_price = stop_loss_data.get("stop_price", 0)
    sl_distance_pct = stop_loss_data.get("distance_pct", 0)
    sl_distance_usdt = stop_loss_data.get("distance_usdt", 0)
    sl_method_cn = stop_loss_data.get("method_cn", "未知")
    sl_confidence = stop_loss_data.get("confidence", 0)

    tp_price = take_profit_data.get("price", 0)
    tp_distance_pct = take_profit_data.get("distance_pct", 0)
    tp_distance_usdt = take_profit_data.get("distance_usdt", 0)
    rr_ratio = take_profit_data.get("rr_ratio", 0)

    rr_emoji = "✅" if rr_ratio >= 2.0 else "⚠️" if rr_ratio >= 1.5 else "❌"

    entry_stop_block = f"""
💰 **入场与止损止盈**
• 入场价: {current_price:.4f} USDT

• 止损: {sl_price:.4f} USDT
  └ 距离: {sl_distance_pct:.2%} (${sl_distance_usdt:.2f}/1000U)
  └ 方法: {sl_method_cn}
  └ 置信: {sl_confidence}/100

• 止盈: {tp_price:.4f} USDT
  └ 距离: {tp_distance_pct:.2%} (${tp_distance_usdt:.2f}/1000U)

• 盈亏比: 1:{rr_ratio:.1f} {rr_emoji}
"""

    # ============ Block 6: 仓位建议 ============
    position_mult = data.get("position_mult", 1.0)
    base_position = 10000  # 假设基准10000 USDT
    adjusted_position = base_position * position_mult

    entry_immediate = adjusted_position * 0.60
    entry_reserve = adjusted_position * 0.40

    if position_mult > 0.9:
        position_note = "流动性优秀，可满仓"
    elif position_mult > 0.6:
        position_note = "流动性中等，适度降低仓位"
    else:
        position_note = "流动性较差，建议小仓位试探"

    position_block = f"""
💼 **仓位建议**
• 基准仓位: ${base_position:.0f}
• L调制器: {position_mult:.0%} (L={modulation.get('L', 50)})
• 调整后: ${adjusted_position:.0f}

分配策略:
  ├─ 立即入场: ${entry_immediate:.0f} (60%)
  └─ 预留加仓: ${entry_reserve:.0f} (40%)

说明: {position_note}
"""

    # ============ Block 7: 风险提示 ============
    alerts = []

    # 风险1：流动性
    L_score_val = modulation.get("L", 50)
    if L_score_val < 50:
        L_meta = modulator_output.get("L", {}).get("meta", {})
        warnings = L_meta.get("warnings", [])
        if warnings:
            alerts.append(f"⚠️ [流动性] {'; '.join(warnings)}")
        else:
            alerts.append("⚠️ [流动性] 流动性偏低，注意滑点")

    # 风险2：结构
    S_score_val = modulation.get("S", 0)
    if S_score_val < -50:
        alerts.append("⚠️ [结构] 市场结构混乱，止损可能频繁触发")

    # 风险3：独立性
    I_score_val = modulation.get("I", 0)
    if I_score_val < -30:
        alerts.append("⚠️ [独立性] 跟随性强，注意市场联动风险")

    # 风险4：数据质量
    data_qual = data.get("data_qual", 1.0)
    if data_qual and data_qual < 0.95:
        alerts.append(f"⚠️ [数据] 数据质量略低({data_qual:.0%})，建议复核")

    # 风险5：软约束
    soft_filtered = publish_info.get("soft_filtered", False)
    if soft_filtered:
        reason = publish_info.get("soft_filter_reason", "")
        alerts.append(f"ℹ️ [软约束] {reason}（信号标记但可交易）")

    risk_block = ""
    if alerts:
        risk_block = f"""
🚨 **风险提示**
{chr(10).join(alerts)}
"""

    # ============ Block 8: 市场环境 ============
    market_meta = data.get("market_meta", {})
    btc_trend_val = market_meta.get("btc_trend", 0)
    market_regime = data.get("market_regime", 0)

    if btc_trend_val > 0:
        btc_trend_text = "上升"
    elif btc_trend_val < 0:
        btc_trend_text = "下降"
    else:
        btc_trend_text = "震荡"

    if market_regime > 0.5:
        sentiment = "乐观"
    elif market_regime < -0.5:
        sentiment = "悲观"
    else:
        sentiment = "中性"

    # 获取波动率
    volatility = data.get("optimization_meta", {}).get("volatility", "中等")

    context_block = f"""
🌍 **市场环境**
• BTC趋势: {btc_trend_text}
• 市场情绪: {sentiment}
• 波动率: {volatility}
"""

    # ============ Block 9: 元数据 ============
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    version = "v6.6"
    binance_url = f"https://www.binance.com/en/futures/{symbol}"

    footer = f"""
━━━━━━━━━━━━━━━━━━━━
⏰ {timestamp}
🤖 CryptoSignal {version} | 🔗 [{symbol}]({binance_url})
"""

    # ============ 组装消息 ============
    message = (
        header +
        core_metrics +
        factor_detail +
        modulator_status +
        entry_stop_block +
        position_block +
        risk_block +
        context_block +
        footer
    )

    return message


def _render_compact(data: Dict[str, Any]) -> str:
    """渲染简洁模式（6 blocks: 1+2+3+5+6+9）"""

    # Block 1: 头部
    direction = data.get("side", "unknown").upper()
    symbol = data.get("symbol", "UNKNOWN")
    score = data.get("weighted_score", 0)

    # v6.6修复：确保score是数值类型（防止dict导致abs()错误）
    if isinstance(score, dict):
        score = 0
    elif not isinstance(score, (int, float)):
        score = 0

    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    strength_emoji = _get_strength_emoji(abs(score))

    message = f"{direction_emoji} **{direction} {symbol}** {strength_emoji}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Block 2: 核心指标
    edge = data.get("edge", 0)
    probability = data.get("probability", 0)
    EV = data.get("publish", {}).get("EV", 0)

    # v6.6修复：确保数值类型
    if isinstance(edge, dict):
        edge = 0
    if isinstance(probability, dict):
        probability = 0
    if isinstance(EV, dict):
        EV = 0

    message += f"""📊 **核心**
评分:{score:+.1f} | Edge:{edge:+.2f} | P:{probability:.0%} | EV:{EV:+.2%}

"""

    # Block 3: 因子Top 3
    factor_contribs = data.get("factor_contributions", {})
    if factor_contribs:
        # v6.6修复：确保contrib是数值类型（防止dict导致abs()错误）
        def safe_abs(value):
            if isinstance(value, dict):
                return 0
            elif isinstance(value, (int, float)):
                return abs(value)
            else:
                return 0

        sorted_factors = sorted(
            factor_contribs.items(),
            key=lambda x: safe_abs(x[1]),
            reverse=True
        )[:3]

        message += "🎯 **因子**: "
        factor_strs = [
            f"{name}({data.get('scores', {}).get(name, 0):+d})"
            for name, _ in sorted_factors
        ]
        message += ", ".join(factor_strs) + "\n\n"

    # Block 5: 止损止盈
    current_price = data.get("price", 0)
    sl_price = data.get("stop_loss", {}).get("stop_price", 0)
    tp_price = data.get("take_profit", {}).get("price", 0)
    rr = data.get("take_profit", {}).get("rr_ratio", 0)

    message += f"""💰 **交易**
入场:{current_price:.4f} | 止损:{sl_price:.4f} | 止盈:{tp_price:.4f}
RR: 1:{rr:.1f}

"""

    # Block 6: 仓位
    position_mult = data.get("position_mult", 1.0)
    message += f"💼 **仓位**: {position_mult:.0%}\n\n"

    # Block 9: 元数据
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message += f"━━━━━━━━━━━━━━━━━━━━\n⏰ {timestamp} | 🤖 v6.6"

    return message


def _render_debug(data: Dict[str, Any]) -> str:
    """渲染调试模式（完整信息，用于开发测试）"""

    rich_msg = _render_rich(data)

    # 添加调试信息
    debug_info = "\n\n" + "=" * 40 + "\n"
    debug_info += "🔧 **调试信息**\n"
    debug_info += f"DataQual: {data.get('data_qual', 1.0):.2%}\n"
    debug_info += f"Teff_final: {data.get('Teff_final', 2.0):.3f}\n"
    debug_info += f"cost_modulated: {data.get('cost_modulated', 0.0015):.4f}\n"

    # 软约束状态
    publish_info = data.get("publish", {})
    debug_info += f"EV_positive: {publish_info.get('EV_positive', True)}\n"
    debug_info += f"P_above_threshold: {publish_info.get('P_above_threshold', True)}\n"
    debug_info += f"soft_filtered: {publish_info.get('soft_filtered', False)}\n"

    # Fallback链
    stop_loss_data = data.get("stop_loss", {})
    fallback_chain = stop_loss_data.get("fallback_chain", [])
    if fallback_chain:
        debug_info += f"\nFallback链: {[x[0] for x in fallback_chain]}\n"

    debug_info += "=" * 40

    return rich_msg + debug_info


def _get_strength_emoji(score: float) -> str:
    """获取强度emoji"""
    if score >= 80:
        return "🔥🔥🔥"
    elif score >= 60:
        return "🔥🔥"
    elif score >= 40:
        return "🔥"
    else:
        return "⚡"


def _get_factor_emoji(factor_name: str) -> str:
    """获取因子emoji"""
    emoji_map = {
        "T": "📈",  # 趋势
        "M": "⚡",  # 动量
        "C": "💎",  # CVD
        "V": "📊",  # 成交量
        "O": "🎯",  # 持仓量
        "B": "💰",  # 基差
        "S": "🏗️",  # 结构
        "L": "💧",  # 流动性
    }
    return emoji_map.get(factor_name, "•")


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("v6.6 Telegram消息模板测试")
    print("=" * 60)

    # 模拟信号数据
    test_signal = {
        "symbol": "ETHUSDT",
        "side": "long",
        "price": 3250.45,
        "weighted_score": 68.5,
        "edge": 0.85,
        "probability": 0.723,
        "confidence": 88,
        "publish": {
            "EV": 0.0057,
            "EV_positive": True,
            "P_above_threshold": True,
            "soft_filtered": False,
            "prime": True
        },
        "scores": {
            "T": 72,
            "M": 58,
            "C": 81,
            "V": 45,
            "O": 38,
            "B": 12
        },
        "factor_contributions": {
            "T": 17.3,
            "M": 9.9,
            "C": 19.4,
            "V": 5.4,
            "O": 6.5,
            "B": 0.7
        },
        "modulation": {
            "L": 45,
            "S": 65,
            "F": 38,
            "I": 22
        },
        "modulator_output": {
            "L": {
                "position_mult": 0.55,
                "cost_eff": -0.02,
                "meta": {}
            },
            "S": {
                "confidence_mult": 1.20,
                "Teff_mult": 0.90
            },
            "F": {
                "Teff_mult": 0.92
            },
            "I": {
                "Teff_mult": 0.97,
                "cost_eff": -0.033
            },
            "fusion": {
                "Teff_final": 1.613,
                "cost_final": 0.0001
            }
        },
        "position_mult": 0.55,
        "Teff_final": 1.613,
        "cost_modulated": 0.0001,
        "stop_loss": {
            "stop_price": 3165.20,
            "distance_pct": 0.0262,
            "distance_usdt": 26.20,
            "method": "structure_swing",
            "method_cn": "结构低点 (Swing Low)",
            "confidence": 90,
            "fallback_chain": [("structure", {})]
        },
        "take_profit": {
            "price": 3420.80,
            "distance_pct": 0.0524,
            "distance_usdt": 52.40,
            "rr_ratio": 2.0
        },
        "market_meta": {
            "btc_trend": 1,
            "regime_desc": "上升"
        },
        "market_regime": 0.6,
        "optimization_meta": {
            "volatility": "中等"
        },
        "data_qual": 0.95
    }

    print("\n【测试1】Rich模式（9 blocks）")
    print("-" * 60)
    rich_msg = render_v66_signal(test_signal, mode="rich")
    print(rich_msg)
    print(f"\n字符数: {len(rich_msg)}")

    print("\n" + "=" * 60)
    print("\n【测试2】Compact模式（6 blocks）")
    print("-" * 60)
    compact_msg = render_v66_signal(test_signal, mode="compact")
    print(compact_msg)
    print(f"\n字符数: {len(compact_msg)}")

    print("\n" + "=" * 60)
    print("测试完成！模板工作正常。")
    print("=" * 60)
