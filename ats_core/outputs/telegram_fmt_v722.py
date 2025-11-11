# coding: utf-8
"""
v7.2.22 Telegram消息模板 - 非专业人士友好版

设计理念：
- 用通俗语言代替专业术语
- 突出核心交易参数
- 简化技术指标，增加解释性文字
- 提供明确的操作建议
"""

from typing import Dict, Any


def _get(data: dict, key_path: str, default=None):
    """
    安全获取嵌套字典值

    Args:
        data: 字典
        key_path: 键路径，支持点号分隔（如 "a.b.c"）
        default: 默认值

    Returns:
        值或默认值
    """
    if not isinstance(data, dict):
        return default

    keys = key_path.split('.')
    result = data

    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return default

        if result is None:
            return default

    return result


def _fmt_price(price) -> str:
    """格式化价格显示"""
    if price is None or price == 0:
        return "—"

    try:
        price = float(price)
        if price >= 1000:
            return f"{price:,.2f}"
        elif price >= 1:
            return f"{price:.3f}"
        elif price >= 0.01:
            return f"{price:.4f}"
        else:
            return f"{price:.6f}"
    except (ValueError, TypeError):
        return "—"


def _format_timestamp(ts: float) -> str:
    """格式化时间戳为UTC+8时间"""
    if not ts:
        return "—"
    try:
        from datetime import datetime, timedelta, timezone
        tz_utc8 = timezone(timedelta(hours=8))
        dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=tz_utc8)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "—"


def render_signal_v722(r: Dict[str, Any], is_watch: bool = False) -> str:
    """
    v7.2.22 电报消息模板 - 非专业人士友好版

    核心改进：
    1. 用通俗语言解释专业术语
    2. 突出核心交易参数
    3. 简化技术细节
    4. 增加操作指引

    Args:
        r: 信号数据
        is_watch: 是否为观察信号

    Returns:
        格式化的Telegram消息
    """

    # ========== 1. 基础信息提取 ==========
    sym = _get(r, "symbol", "—")
    price = _get(r, "price") or _get(r, "last", 0)
    price_s = _fmt_price(price)

    # 方向判断
    side = (_get(r, "side", "").lower())
    if side in ("long", "buy", "bull", "多", "做多"):
        side_icon = "📈"
        side_text = "做多"
        side_desc = "买入后等待上涨"
    elif side in ("short", "sell", "bear", "空", "做空"):
        side_icon = "📉"
        side_text = "做空"
        side_desc = "卖出后等待下跌"
    else:
        side_icon = "⚪"
        side_text = "观察"
        side_desc = "暂时观察"

    # v7.2数据
    v72 = _get(r, "v72_enhancements", {})
    if not isinstance(v72, dict):
        v72 = {}

    # 核心指标
    P_calibrated = _get(v72, "P_calibrated") or _get(r, "probability", 0.5)
    P_pct = int(P_calibrated * 100)
    EV_net = _get(v72, "EV_net") or _get(r, "expected_value", 0)

    # 止损止盈
    TP_pct = _get(r, "tp_pct", 0.03)
    SL_pct = _get(r, "sl_pct", 0.015)
    RR = TP_pct / SL_pct if SL_pct > 0 else 2.0

    # F因子（资金流向）
    F_v2 = _get(v72, "F_v2", 0)
    is_momentum_ready = F_v2 > 30  # 资金强势领先

    # ========== 2. 头部：核心信息 ==========
    if is_momentum_ready:
        header = "🚀 ** 蓄势待发信号 **\n"
        momentum_tip = "资金正在持续流入，有爆发潜力"
    else:
        header = f"{'📍 观察信号' if is_watch else '💰 交易信号'}\n"
        momentum_tip = None

    header += f"\n{side_icon} **{sym}**"
    header += f"\n当前价格：{price_s}"
    header += f"\n\n{'┈' * 20}\n"

    # 核心参数
    header += f"\n📊 **核心数据**"
    header += f"\n• 操作方向：{side_text} ({side_desc})"
    header += f"\n• 预计胜率：{P_pct}%"
    header += f"\n• 期望收益：{EV_net:+.1%}"
    header += f"\n• 盈亏比例：{RR:.1f}:1"

    if momentum_tip:
        header += f"\n\n💡 {momentum_tip}"

    # ========== 3. 交易参数：入场止损止盈 ==========
    params = f"\n\n{'┈' * 20}\n"
    params += f"\n💼 **交易参数**\n"

    # 计算具体价格
    entry = price if price is not None else 0
    if entry > 0:
        if side in ("long", "buy", "bull", "多", "做多"):
            tp_price = entry * (1 + TP_pct)
            sl_price = entry * (1 - SL_pct)
        else:
            tp_price = entry * (1 - TP_pct)
            sl_price = entry * (1 + SL_pct)
    else:
        tp_price = 0
        sl_price = 0

    tp_s = _fmt_price(tp_price)
    sl_s = _fmt_price(sl_price)
    sl_dist = abs(SL_pct * 100)
    tp_dist = abs(TP_pct * 100)

    params += f"\n📍 **入场价**：{_fmt_price(entry)}"
    params += f"\n   现在就可以买入/卖出"

    params += f"\n\n🛑 **止损价**：{sl_s}"
    params += f"\n   跌幅 {sl_dist:.1f}% 时自动止损"
    params += f"\n   （亏损控制在{sl_dist:.1f}%以内）"

    params += f"\n\n🎯 **止盈价**：{tp_s}"
    params += f"\n   涨幅 {tp_dist:.1f}% 时获利了结"
    params += f"\n   （预计盈利{tp_dist:.1f}%）"

    # 仓位建议
    position_base = _get(r, "position_size", 0.05)
    position_pct = position_base * 100

    params += f"\n\n💰 **仓位建议**"
    params += f"\n   建议使用总资金的 {position_pct:.0f}%"
    params += f"\n   （例如1万元，建议用{int(10000*position_base)}元）"

    # ========== 4. 信号强度说明 ==========
    strength = f"\n\n{'┈' * 20}\n"
    strength += f"\n🔬 **信号强度分析**\n"

    # F因子（资金流向）
    F_v2_int = int(round(F_v2))
    if F_v2_int > 30:
        F_icon = "🔥🔥"
        F_desc = "资金强势流入"
        F_explain = "大资金正在积极买入，行情可能即将启动"
    elif F_v2_int > 15:
        F_icon = "🔥"
        F_desc = "资金明显流入"
        F_explain = "资金流入趋势明显，短期看涨概率较大"
    elif F_v2_int > 0:
        F_icon = "✅"
        F_desc = "资金温和流入"
        F_explain = "资金小幅流入，适度关注"
    elif F_v2_int > -15:
        F_icon = "⚠️"
        F_desc = "资金轻微流出"
        F_explain = "资金流出不明显，需谨慎观察"
    else:
        F_icon = "❌"
        F_desc = "资金明显流出"
        F_explain = "资金正在撤离，风险较高"

    strength += f"\n{F_icon} **资金流向** ({F_v2_int:+d}分)"
    strength += f"\n   {F_desc}"
    strength += f"\n   💡 {F_explain}"

    # I因子（市场独立性）
    I_v2 = _get(v72, "I_v2", 50)
    I_v2_int = int(round(I_v2))

    # 获取市场对齐分析
    market_analysis = _get(v72, "independence_market_analysis", {})
    if not isinstance(market_analysis, dict):
        market_analysis = {}

    market_regime = market_analysis.get("market_regime", 0)
    alignment = market_analysis.get("alignment", "正常")

    # 市场趋势描述
    if market_regime > 30:
        market_trend = "大盘上涨"
        market_icon = "📈"
    elif market_regime < -30:
        market_trend = "大盘下跌"
        market_icon = "📉"
    else:
        market_trend = "大盘震荡"
        market_icon = "↔️"

    # 独立性说明
    if I_v2_int > 60:
        I_icon = "💎"
        I_desc = "高度独立"
        I_explain = "走势独立于大盘，不受BTC影响"
    elif I_v2_int > 30:
        I_icon = "✅"
        I_desc = "相对独立"
        I_explain = "有一定独立性，但仍受大盘影响"
    else:
        I_icon = "🔗"
        I_desc = "跟随大盘"
        I_explain = "走势与BTC高度相关"

    strength += f"\n\n{I_icon} **市场独立性** ({I_v2_int}分)"
    strength += f"\n   {I_desc}"
    strength += f"\n   💡 {I_explain}"
    strength += f"\n   {market_icon} 当前：{market_trend}"

    # 对齐状态提示
    if alignment == "顺势":
        strength += f"\n   🎯 信号方向与大盘一致（风险较低）"
    elif alignment == "逆势":
        strength += f"\n   ⚠️ 信号方向与大盘相反（风险较高）"

    # ========== 5. 质量检查（简化版）==========
    quality_check = f"\n\n{'┈' * 20}\n"
    quality_check += f"\n✅ **信号质量检查**\n"

    # 获取gate详情
    gate_details_v72 = _get(v72, "gates", {})
    if not isinstance(gate_details_v72, dict):
        gate_details_v72 = {}

    gate_details_list = gate_details_v72.get("details", [])

    # 构建gate字典
    gates = {}
    for gate_info in gate_details_list:
        if not isinstance(gate_info, dict):
            continue
        gate_num = gate_info.get("gate")
        gates[f"gate{gate_num}"] = gate_info

    # 提取各个闸门
    gate1 = gates.get("gate1", {})
    gate2 = gates.get("gate2", {})
    gate3 = gates.get("gate3", {})
    gate4 = gates.get("gate4", {})
    gate5 = gates.get("gate5", {})

    g1_pass = gate1.get("pass", True)
    g2_pass = gate2.get("pass", True)
    g3_pass = gate3.get("pass", True)
    g4_pass = gate4.get("pass", True)
    g5_pass = gate5.get("pass", True)

    # 计算通过的闸门数
    gates_passed = sum([g1_pass, g2_pass, g3_pass, g4_pass, g5_pass])

    # 简化显示
    if gates_passed == 5:
        quality_icon = "✅✅✅"
        quality_desc = "优秀"
        quality_explain = "通过所有质量检查，信号可靠"
    elif gates_passed == 4:
        quality_icon = "✅✅"
        quality_desc = "良好"
        quality_explain = "通过大部分质量检查，信号较可靠"
    elif gates_passed == 3:
        quality_icon = "✅"
        quality_desc = "合格"
        quality_explain = "通过基础质量检查，可谨慎参考"
    else:
        quality_icon = "⚠️"
        quality_desc = "一般"
        quality_explain = "质量检查通过较少，建议观察"

    quality_check += f"\n{quality_icon} 信号质量：{quality_desc} ({gates_passed}/5项通过)"
    quality_check += f"\n💡 {quality_explain}"

    # ========== 6. 操作建议 ==========
    suggestion = f"\n\n{'┈' * 20}\n"
    suggestion += f"\n📋 **操作建议**\n"

    # 根据各项指标给出建议
    if is_momentum_ready and gates_passed >= 4 and P_pct >= 55:
        suggestion += f"\n🔥 **强烈推荐**"
        suggestion += f"\n资金强势+质量优秀+胜率高"
        suggestion += f"\n建议按照交易参数及时进场"
    elif gates_passed >= 4 and P_pct >= 50:
        suggestion += f"\n✅ **推荐关注**"
        suggestion += f"\n信号质量良好，胜率可接受"
        suggestion += f"\n可适度参与，严格止损"
    elif gates_passed >= 3:
        suggestion += f"\n💡 **谨慎参考**"
        suggestion += f"\n信号基本合格，建议小仓位试探"
        suggestion += f"\n务必设置止损，控制风险"
    else:
        suggestion += f"\n⚠️ **仅供观察**"
        suggestion += f"\n质量检查通过较少"
        suggestion += f"\n建议观察，不建议重仓"

    # 风险提示
    suggestion += f"\n\n⚠️ **风险提示**"
    suggestion += f"\n• 币圈波动大，请控制仓位"
    suggestion += f"\n• 务必设置止损，严格执行"
    suggestion += f"\n• 不要孤注一掷，分散风险"

    # ========== 7. 页脚 ==========
    timestamp = _get(r, "timestamp", 0)
    time_str = _format_timestamp(timestamp)

    footer = f"\n\n{'┈' * 20}\n"
    footer += f"\n⏱ {time_str}"
    footer += f"\n🤖 CryptoSignal v7.2.22"
    footer += f"\n🔗 币种：#{sym}"

    # ========== 组装完整消息 ==========
    message = header + params + strength + quality_check + suggestion + footer

    return message


def render_trade_v722(r: Dict[str, Any]) -> str:
    """v7.2.22交易信号（非专业人士友好版）"""
    return render_signal_v722(r, is_watch=False)


def render_watch_v722(r: Dict[str, Any]) -> str:
    """v7.2.22观察信号（非专业人士友好版）"""
    return render_signal_v722(r, is_watch=True)
