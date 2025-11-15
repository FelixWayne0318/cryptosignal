# coding: utf-8
"""
Telegram message formatting (v6.6 architecture)

v6.6架构（2025-11-05）：
━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 A层：方向判断（6因子，权重100%）
  - T趋势(24%) + M动量(17%) + C资金(24%) + V量能(12%) + O持仓(17%) + B基差(6%)

⚙️ B层：调制器（4因子，权重0%，仅调节执行参数）
  - L流动性 → position_mult, cost
  - S结构   → confidence, Teff
  - F资金领先→ Teff, p_min
  - I独立性 → Teff, cost

🚪 四门槛：质量控制（gate_multiplier影响Prime强度）
  - Gate 1: DataQual（数据质量）
  - Gate 2: EV（期望值）
  - Gate 3: Execution（执行质量）
  - Gate 4: Probability（概率门槛）
━━━━━━━━━━━━━━━━━━━━━━━━━━

设计原则：
- 使用不同图标区分三个层次（圆形🔴/齿轮⚙️/门🚪）
- A层决定方向，B层调节参数，四门槛控制质量
- 所有约束都是软约束，不硬拒绝信号
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List
import math

# v7.3.45: 导入配置管理器（用于F因子蓄势阈值）
try:
    from ats_core.config.threshold_config import get_thresholds
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# Public API
__all__ = [
    'render_signal',
    'render_watch',
    'render_trade',
    'render_signal_detailed',
    'format_factor_with_weight',
    'render_weights_summary',
    'render_prime_breakdown',
    'render_four_gates',
    'render_modulators',
    'render_five_piece_report',
    # v6.7新增：整合v66特性
    'render_v67_rich',
    'render_v67_compact',
    # v7.2新增：规则增强版
    'render_signal_v72',
    'render_watch_v72',
    'render_trade_v72'
]

# ---------- small utils ----------

def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        v = float(x)
    except Exception:
        return 50.0
    return max(lo, min(hi, v))

def _as_int_score(x: Any, default: int = 0, allow_negative: bool = True) -> int:
    """
    转换为整数分数（统一±100系统）

    Args:
        x: 分数值
        default: 默认值（0=中性）
        allow_negative: 是否允许负数（True=±100系统，False=0-100系统）
    """
    try:
        if x is None:
            return default
        if isinstance(x, (list, tuple)) and len(x) > 0:
            # allow last value fallback
            try:
                x = x[-1]
            except Exception:
                pass
        score = int(round(float(x)))
        # 统一±100系统：允许负数
        if allow_negative:
            return max(-100, min(100, score))
        else:
            # 兼容旧版0-100系统
            return int(round(_clamp(float(x))))
    except Exception:
        return default

def _get(d: Any, key: str, default: Any = None) -> Any:
    """safe dict get with dotted path support, tolerant of non-dicts."""
    if d is None:
        return default
    if not isinstance(key, str) or key == "":
        return default
    cur = d
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur

def _get_dict(d: Any, key: str, default: dict = None) -> dict:
    """
    安全获取字典类型值（v7.3.47修复）

    解决'str' object has no attribute 'get'错误：
    - 如果返回值是字典：正常返回
    - 如果返回值是非字典（包括字符串）：返回空字典

    Args:
        d: 源字典
        key: 键（支持点分路径，如"v72.scores"）
        default: 默认值（None时使用{}）

    Returns:
        dict: 安全的字典对象

    Example:
        # Before (v7.3.46 - 可能失败)
        scores = _get_dict(r, "scores")  # 如果scores="string"，or返回"string"
        T = scores.get("T")  # AttributeError: 'str' object has no attribute 'get'

        # After (v7.3.47 - 安全)
        scores = _get_dict(r, "scores")  # 如果scores="string"，返回{}
        T = scores.get("T")  # 正常工作
    """
    if default is None:
        default = {}
    result = _get(d, key)
    return result if isinstance(result, dict) else default

def _fmt_price(x: Any) -> str:
    try:
        v = float(x)
        # pick decimals based on magnitude
        if v >= 10000:
            return f"{v:,.0f}"
        if v >= 1000:
            return f"{v:,.1f}"
        if v >= 1:
            return f"{v:,.2f}"
        # small prices keep more decimals
        return f"{v:,.6f}".rstrip("0").rstrip(".")
    except Exception:
        return "-"

def _ttl_hours(r: Dict[str, Any]) -> int:
    # try r['ttl_h'] or r['ttl_hours'] or r['publish']['ttl_h'] else 8
    return (
        _get(r, "ttl_h")
        or _get(r, "ttl_hours")
        or _get(r, "publish.ttl_h")
        or 8
    )

# ---------- score → emoji / description ----------

def _emoji_by_score(s: int) -> str:
    """
    分数转emoji（统一±100系统，优化颜色方案）

    颜色方案（体现强度和方向）：
    - s >= 60:  🟢 绿色（强势正向）
    - 30-60:    🟡 黄色（中等正向）
    - -30到+30: 🟤 蓝色（中性）
    - -60到-30: 🟠 橙色（中等负向）
    - s <= -60: 🔴 红色（强势负向）

    注：颜色同时体现方向和强度
    """
    if s >= 60:
        return "🟢"  # 强势正向
    elif s >= 30:
        return "🟡"  # 中等正向
    elif s >= -30:
        return "🟤"  # 中性
    elif s >= -60:
        return "🟠"  # 中等负向
    else:  # s < -60
        return "🔴"  # 强势负向

def _desc_trend(s: int, Tm: int = None) -> str:
    """
    描述趋势（统一±100系统）

    Args:
        s: T 分数 (-100到+100，正数=上涨，负数=下跌)
        Tm: 趋势强度指标（保留用于额外信息）
    """
    # 基于符号的描述（±100系统）
    if s >= 80:
        desc = "强势上行"
    elif s >= 60:
        desc = "温和上行"
    elif s >= 30:
        desc = "偏多震荡"
    elif s >= -30:
        desc = "中性震荡"
    elif s >= -60:
        desc = "偏空震荡"
    elif s >= -80:
        desc = "温和下行"
    else:  # s < -80
        desc = "强势下行"

    # 附加趋势方向（如果有Tm）
    if Tm is not None:
        if Tm > 0:
            desc += " [多头]"
        elif Tm < 0:
            desc += " [空头]"
        else:
            desc += " [震荡]"

    return desc

def _desc_structure(s: int, theta: float = None) -> str:
    """
    描述结构（统一±100系统）

    Args:
        s: S 分数 (-100到+100，正数=好，负数=差)
        theta: 结构一致性角度 (0.25-0.60)
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "结构清晰/多周期共振"
    elif s >= 30:
        desc = "结构尚可/回踩确认"
    elif s >= -30:
        desc = "结构一般/级别分歧"
    else:  # s < -30
        desc = "结构杂乱/级别相抵"

    # 附加结构角度
    if theta is not None:
        desc += f" (θ={theta:.2f})"

    return desc

def _desc_volume(s: int, v5v20: float = None) -> str:
    """
    描述量能（统一±100系统）

    Args:
        s: V 分数 (-100到+100，正数=放量，负数=缩量)
        v5v20: 短期/长期量能比率
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "放量明显/跟随积极"
    elif s >= 30:
        desc = "量能偏强/逐步释放"
    elif s >= -30:
        desc = "量能中性"
    else:  # s < -30
        desc = "量能不足/跟随意愿弱"

    # 附加量能比率
    if v5v20 is not None:
        desc += f" (v5/v20={v5v20:.2f})"

    return desc

def _desc_momentum(s: int, slope_now: float = None) -> str:
    """
    描述动量（统一±100系统）

    Args:
        s: M 分数 (-100到+100，正数=上行加速，负数=下行加速)
        slope_now: 当前动量斜率（可选）
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "强劲上行加速"
    elif s >= 30:
        desc = "温和上行加速"
    elif s >= -30:
        desc = "动量中性"
    elif s >= -60:
        desc = "温和下行加速"
    else:  # s < -60
        desc = "强劲下行加速"

    # 附加斜率信息（如果有）
    if slope_now is not None:
        desc += f" (斜率={slope_now:.2f})"

    return desc

def _desc_accel(s: int, is_long: bool = True, cvd6: float = None) -> str:
    """
    描述加速（旧版A维度，保留兼容性）

    Args:
        s: A 分数 (0-100)
        is_long: 是否做多
        cvd6: CVD 6小时变化百分比
    """
    direction = "上行" if is_long else "下行"
    if s >= 80: desc = f"{direction}加速强/持续性好"
    elif s >= 60: desc = f"{direction}加速偏强/待确认"
    elif s >= 40: desc = "加速一般"
    else: desc = "加速不足/有背离风险"

    # 附加 CVD 变化
    if cvd6 is not None:
        cvd_pct = cvd6 * 100
        if cvd_pct >= 0:
            desc += f" (CVD+{cvd_pct:.1f}%)"
        else:
            desc += f" (CVD{cvd_pct:.1f}%)"

    return desc

def _desc_cvd_flow(s: int, is_long: bool = True, cvd6: float = None,
                   consistency: float = None, is_consistent: bool = None) -> str:
    """
    描述CVD资金流（明确买入/卖出方向 + 持续性）

    Args:
        s: C 分数 (-100到+100，带符号！)
        is_long: 是否做多（已弃用，仅保留兼容性）
        cvd6: CVD 6小时变化（已归一化到价格）
        consistency: （已弃用，保留参数兼容性）
        is_consistent: 是否持续（R²>=0.7，变化平稳）

    分数对称映射：
        ≥ +80: 强劲资金流入
        ≥ +60: 偏强资金流入
        ≥ +40: 中等资金流入
        ≥ +20: 轻微资金流入
        -20~+20: 资金流平衡
        ≤ -20: 轻微资金流出
        ≤ -40: 中等资金流出
        ≤ -60: 偏强资金流出
        ≤ -80: 强劲资金流出
    """
    # 根据分数正负和强度确定资金流方向
    # 正数 = 资金流入，负数 = 资金流出
    if s >= 80:
        desc = "强劲资金流入"
    elif s >= 60:
        desc = "偏强资金流入"
    elif s >= 40:
        desc = "中等资金流入"
    elif s >= 20:
        desc = "轻微资金流入"
    elif s >= -20:
        desc = "资金流平衡"
    elif s >= -40:
        desc = "轻微资金流出"
    elif s >= -60:
        desc = "中等资金流出"
    elif s >= -80:
        desc = "偏强资金流出"
    else:  # s < -80
        desc = "强劲资金流出"

    # 附加 CVD 6小时变化百分比（归一化到价格）
    if cvd6 is not None:
        cvd_pct = cvd6 * 100

        # 数据异常检查：如果绝对值>1000%，说明数据异常，不显示
        if abs(cvd_pct) > 1000:
            desc += f" (CVD数据异常"
        elif cvd_pct >= 0:
            desc += f" (CVD+{cvd_pct:.1f}%"
        else:
            desc += f" (CVD{cvd_pct:.1f}%"

        # 附加持续性标注（基于R²拟合优度）
        if is_consistent is not None:
            if is_consistent:
                desc += ", 持续✓"  # R²>=0.7，变化平稳
            else:
                desc += ", 震荡"    # R²<0.7，波动大

        desc += ")"

    return desc

def _desc_positions(s: int, oi24h_pct: float = None) -> str:
    """
    描述持仓（统一±100系统）

    Args:
        s: O 分数 (-100到+100，正数=增加，负数=减少)
        oi24h_pct: OI 24小时变化百分比
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "持仓显著增长/可能拥挤"
    elif s >= 30:
        desc = "持仓温和上升/活跃"
    elif s >= -30:
        desc = "持仓温和变化"
    else:  # s < -30
        desc = "持仓走弱/去杠杆"

    # 附加 OI 24h 变化
    if oi24h_pct is not None:
        if oi24h_pct >= 0:
            desc += f" (OI+{oi24h_pct:.1f}%)"
        else:
            desc += f" (OI{oi24h_pct:.1f}%)"

    return desc

def _desc_env(s: int, chop: float = None) -> str:
    """
    描述震荡（统一±100系统）

    Args:
        s: E 分数 (-100到+100，正数=震荡小空间大，负数=震荡大空间小)
        chop: Chop 指数 (0-100，越高越震荡)
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "趋势明确/空间充足"
    elif s >= 30:
        desc = "偏趋势/空间尚可"
    elif s >= -30:
        desc = "震荡偏强/空间有限"
    else:  # s < -30
        desc = "强烈震荡/空间狭窄"

    # 附加 Chop 指数
    if chop is not None:
        desc += f" (Chop={chop:.0f})"

    return desc

def _desc_fund_leading(s: int, leading_raw: float = None) -> str:
    """
    描述资金领先性（方案C：分开描述，去除程度修饰）

    Args:
        s: F 分数 (-100 到 +100)
        leading_raw: 真实的领先性数值（用于调试，可选）

    Returns:
        简洁描述（"资金领先价格" or "价格领先资金" or "资金价格同步"）
    """
    if s >= 10:
        desc = "资金领先价格"
    elif s >= -10:
        desc = "资金价格同步"
    else:
        desc = "价格领先资金"

    return desc

def _desc_liquidity(s: int, spread_bps: float = None, obi: float = None) -> str:
    """
    描述流动性（v6.0新增，统一±100系统）

    Args:
        s: L 分数 (-100到+100，正数=高流动性，负数=低流动性）
        spread_bps: 价差（基点）
        obi: 订单簿失衡度（-1到+1）
    """
    if s >= 60:
        desc = "流动性极佳/深度充足"
    elif s >= 30:
        desc = "流动性良好/承载力强"
    elif s >= -30:
        desc = "流动性一般/注意滑点"
    else:  # s < -30
        desc = "流动性不足/高滑点风险"

    # 附加价差信息
    if spread_bps is not None:
        desc += f" (点差{spread_bps:.1f}bps"
        if obi is not None:
            desc += f", OBI{obi:+.2f}"
        desc += ")"
    elif obi is not None:
        desc += f" (OBI{obi:+.2f})"

    return desc

def _desc_basis_funding(s: int, basis_bps: float = None, funding_rate: float = None) -> str:
    """
    描述基差+资金费（v6.0新增，统一±100系统）

    Args:
        s: B 分数 (-100到+100，正数=看涨情绪，负数=看跌情绪）
        basis_bps: 基差（基点，正数=期货溢价）
        funding_rate: 资金费率（小数，如0.0001=0.01%）
    """
    if s >= 60:
        desc = "强烈看涨情绪/市场亢奋"
    elif s >= 30:
        desc = "偏多情绪/期货溢价"
    elif s >= -30:
        desc = "市场情绪中性"
    elif s >= -60:
        desc = "偏空情绪/期货折价"
    else:  # s < -60
        desc = "强烈看跌情绪/恐慌性贴水"

    # 附加基差和资金费率信息
    details = []
    if basis_bps is not None:
        if basis_bps >= 0:
            details.append(f"基差+{basis_bps:.0f}bps")
        else:
            details.append(f"基差{basis_bps:.0f}bps")
    if funding_rate is not None:
        funding_pct = funding_rate * 100
        if funding_pct >= 0:
            details.append(f"费率+{funding_pct:.3f}%")
        else:
            details.append(f"费率{funding_pct:.3f}%")

    if details:
        desc += f" ({', '.join(details)})"

    return desc

def _desc_liquidation(s: int, lti: float = None) -> str:
    """
    描述清算密度（v6.0新增，统一±100系统）

    Args:
        s: Q 分数 (-100到+100，正数=空单密集，负数=多单密集）
        lti: LTI清算倾斜指数
    """
    if s >= 60:
        desc = "空单密集/向上清算风险"
    elif s >= 30:
        desc = "偏空清算/上行阻力"
    elif s >= -30:
        desc = "清算分布均衡"
    elif s >= -60:
        desc = "偏多清算/下行支撑"
    else:  # s < -60
        desc = "多单密集/向下清算风险"

    if lti is not None:
        desc += f" (LTI{lti:+.2f})"

    return desc

def _desc_independence(s: int, beta_sum: float = None) -> str:
    """
    描述独立性（v6.0新增，统一±100系统）

    Args:
        s: I 分数 (-100到+100，正数=独立，负数=跟随）
        beta_sum: β总和（vs BTC/ETH）
    """
    if s >= 60:
        desc = "高度独立/自主行情"
    elif s >= 30:
        desc = "偏独立/弱相关性"
    elif s >= -30:
        desc = "中等相关/跟随市场"
    else:  # s < -30
        desc = "高度跟随/被动走势"

    if beta_sum is not None:
        desc += f" (β={beta_sum:.2f})"

    return desc

def _emoji_by_fund_leading(s: int) -> str:
    """
    F调节器质量标识（方案C：反映信号质量，不是方向）

    资金领先价格 (F>0) = ✅ 好信号（蓄势待发）
    价格领先资金 (F<0) = ⚠️ 风险（追涨/杀跌）

    Args:
        s: F 分数 (-100 到 +100)

    Returns:
        ✅ 或 ⚠️
    """
    if s >= 10:
        return "✅"  # 资金领先，质量好
    else:
        return "⚠️"  # 价格领先或同步，有风险

# ---------- extract scores robustly ----------

def _score_trend(r: Dict[str, Any]) -> int:
    # 优先使用顶层 T 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "T")
    if v is None:
        v = _get(r, "trend.score")
    return _as_int_score(v, default=0, allow_negative=True)

def _score_structure(r: Dict[str, Any]) -> int:
    # 优先使用顶层 S 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "S")
    if v is None:
        v = _get(r, "structure.score")
    if v is None:
        v = _get(r, "structure.fallback_score")
    if v is None:
        v = _get(r, "structure", {})
        if isinstance(v, dict) and "fallback_score" in v:
            v = v["fallback_score"]
    return _as_int_score(v, default=0, allow_negative=True)

def _score_volume(r: Dict[str, Any]) -> int:
    # 优先使用顶层 V 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "V")
    if v is not None:
        return _as_int_score(v, default=0, allow_negative=True)

    # 兼容旧版：尝试从元数据计算
    z = _get(r, "volume.z1h") or _get(r, "z_volume_1h") or _get(r, "momentum.z1h")
    if isinstance(z, (int, float)):
        return _as_int_score(50 + 12 * float(z), default=50, allow_negative=False)
    ratio = _get(r, "volume.v5_over_v20") or _get(r, "v5_over_v20")
    if isinstance(ratio, (int, float)):
        return _as_int_score(50 + 30 * (float(ratio) - 1.0), default=50, allow_negative=False)
    return 0

def _score_accel(r: Dict[str, Any]) -> int:
    # 优先使用顶层 A 字段（来自新版 analyze_symbol）
    v = _get(r, "A")
    if v is not None:
        return _as_int_score(v, 50)

    # 兼容旧版：尝试从元数据计算
    slope_atr = _get(r, "trend.slopeATR") or _get(r, "Tm.slopeATR")
    if isinstance(slope_atr, (int, float)):
        return _as_int_score(200 * float(slope_atr), 50)
    dP1h = _get(r, "momentum.dP1h_abs_pct") or _get(r, "dP1h_abs_pct")
    if isinstance(dP1h, (int, float)):
        return _as_int_score(40 + 40 * min(1.0, float(dP1h) / 0.01), 50)
    return 50

def _score_positions(r: Dict[str, Any]) -> int:
    # 优先使用顶层 O 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "O")
    if v is not None:
        return _as_int_score(v, default=0, allow_negative=True)

    # 兼容旧版：尝试从元数据计算
    oi_z = _get(r, "oi.z20") or _get(r, "oi_z20")
    cvd_z = _get(r, "cvd.z20") or _get(r, "cvd_z20")
    vals: List[float] = []
    if isinstance(oi_z, (int, float)):
        vals.append(float(oi_z))
    if isinstance(cvd_z, (int, float)):
        vals.append(float(cvd_z))
    if vals:
        m = sum(vals) / len(vals)
        return _as_int_score(50 + 12 * m, default=50, allow_negative=False)
    return 0

def _score_env(r: Dict[str, Any]) -> int:
    # 优先使用顶层 E 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "E")
    if v is not None:
        return _as_int_score(v, default=0, allow_negative=True)

    # 兼容旧版：尝试从元数据计算
    atr_now = _get(r, "atr.now") or _get(r, "atr_now") or _get(r, "vol.atr_pct")
    if isinstance(atr_now, (int, float)):
        x = float(atr_now)
        if x <= 0:
            return -10
        import math as _m
        score = 60 - 20 * abs(_m.log10(x) - _m.log10(0.01))
        return _as_int_score(score, default=50, allow_negative=False)
    return 0

def _score_momentum(r: Dict[str, Any]) -> int:
    # 优先使用顶层 M 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "M")
    return _as_int_score(v, default=0, allow_negative=True)

def _score_cvd_flow(r: Dict[str, Any]) -> int:
    """
    获取CVD分数（支持负数：-100到+100）

    注意：CVD现在是带符号的，正数=买入压力，负数=卖出压力
    """
    v = _get(r, "C")
    if v is None:
        return 0  # 默认0=中性
    try:
        # 直接转换，不做0-100限制
        score = int(round(float(v)))
        # 限制在-100到+100
        return max(-100, min(100, score))
    except Exception:
        return 0

def _score_fund_leading(r: Dict[str, Any]) -> int:
    # F调节器（±100系统）
    v = _get(r, "F_score") or _get(r, "F")
    return _as_int_score(v, default=0, allow_negative=True)

def _score_liquidity(r: Dict[str, Any]) -> int:
    # L因子（v6.0新增，±100系统）
    v = _get(r, "L")
    return _as_int_score(v, default=0, allow_negative=True)

def _score_basis_funding(r: Dict[str, Any]) -> int:
    # B因子（v6.0新增，±100系统）
    v = _get(r, "B")
    return _as_int_score(v, default=0, allow_negative=True)

def _score_liquidation(r: Dict[str, Any]) -> int:
    # Q因子（v6.0新增，±100系统）
    v = _get(r, "Q")
    return _as_int_score(v, default=0, allow_negative=True)

def _score_independence(r: Dict[str, Any]) -> int:
    # I因子（v6.0新增，±100系统）
    v = _get(r, "I")
    return _as_int_score(v, default=0, allow_negative=True)

def _six_scores(r: Dict[str, Any]) -> Tuple[int,int,int,int,int,int,int]:
    """兼容：返回T/S/V/M/C/O/E/F（实际8维）- 保留向后兼容"""
    T  = _score_trend(r)
    S  = _score_structure(r)
    V  = _score_volume(r)
    M  = _score_momentum(r)
    C  = _score_cvd_flow(r)
    OI = _score_positions(r)
    E  = _score_env(r)
    F  = _score_fund_leading(r)
    return T, S, V, M, OI, E, F  # 返回7维+F（去掉C保持兼容）

def _ten_scores(r: Dict[str, Any]) -> Tuple[int,int,int,int,int,int,int,int,int,int,int]:
    """兼容：返回T/M/C/S/V/O/L/B/Q/I/F（10维+调节器）- 保留向后兼容"""
    T  = _score_trend(r)
    M  = _score_momentum(r)
    C  = _score_cvd_flow(r)
    S  = _score_structure(r)
    V  = _score_volume(r)
    OI = _score_positions(r)
    L  = _score_liquidity(r)
    B  = _score_basis_funding(r)
    Q  = _score_liquidation(r)
    I  = _score_independence(r)
    F  = _score_fund_leading(r)
    return T, M, C, S, V, OI, L, B, Q, I, F

def _v66_scores(r: Dict[str, Any]) -> Dict[str, int]:
    """
    v6.6架构：A层6因子 + B层4调制器

    Returns:
        {
            'A': {'T': int, 'M': int, 'C': int, 'V': int, 'O': int, 'B': int},
            'B': {'L': int, 'S': int, 'F': int, 'I': int}
        }
    """
    return {
        'A': {  # A层：方向判断（6因子，权重100%）
            'T': _score_trend(r),       # 趋势 24%
            'M': _score_momentum(r),    # 动量 17%
            'C': _score_cvd_flow(r),    # 资金 24%
            'V': _score_volume(r),      # 量能 12%
            'O': _score_positions(r),   # 持仓 17%
            'B': _score_basis_funding(r) # 基差 6%
        },
        'B': {  # B层：调制器（4因子，权重0%）
            'L': _score_liquidity(r),     # 流动性调制器
            'S': _score_structure(r),     # 结构调制器
            'F': _score_fund_leading(r),  # 资金领先调制器
            'I': _score_independence(r)   # 独立性调制器
        }
    }

def _conviction_and_side(r: Dict[str, Any], seven: Tuple[int,int,int,int,int,int,int]) -> Tuple[int, str]:
    # 优先使用概率 P（转换为百分比）
    prob = _get(r, "probability")
    if isinstance(prob, (int, float)):
        conv = int(round(prob * 100))
    else:
        # 兜底：使用六维平均分
        conv = int(round(sum(six) / 6))

    side = (_get(r, "side") or _get(r, "publish.side") or "").lower()
    # normalize side label
    if side in ("long", "buy", "bull", "多", "做多"):
        side_lbl = "🟩 做多"
    elif side in ("short", "sell", "bear", "空", "做空"):
        side_lbl = "🟥 做空"
    else:
        side_lbl = "🟦 中性"
    return conv, side_lbl

# ---------- enhanced monitoring functions (v6.0+) ----------

def format_factor_with_weight(
    factor: str,
    score: int,
    weight: float,
    contribution: float,
    emoji: str,
    description: str
) -> str:
    """
    格式化因子显示（带权重和贡献度）

    Args:
        factor: 因子名称（如 "T趋势"）
        score: 分数 (-100到+100)
        weight: 权重百分比 (如 13.9)
        contribution: 贡献值 (如 +14.4)
        emoji: 状态emoji
        description: 描述文本

    Returns:
        格式化字符串: "🟢 T趋势 +80 (18.0%) → +14.4  强势上行"
    """
    return (
        f"{emoji} {factor} "
        f"{score:+d} "
        f"({weight:.1f}%) → "
        f"{contribution:+.1f}  "
        f"{description}"
    )


def render_weights_summary(r: Dict[str, Any]) -> str:
    """
    v6.6架构：渲染权重汇总表

    显示：
    - 🔵 A层：方向判断（6因子，权重100%）
    - ⚙️ B层：调制器（4因子，权重0%）

    Returns:
        权重汇总字符串（表格格式）
    """
    # 获取v6.6分数
    v66 = _v66_scores(r)
    A_scores = v66['A']
    B_scores = v66['B']

    # v6.6权重（A层总计100%，B层为0%）
    weights = _get(r, "weights") or {
        # A层（方向判断，权重100%）
        "T": 24.0, "M": 17.0, "C": 24.0, "V": 12.0, "O": 17.0, "B": 6.0,
        # B层（调制器，权重0%）
        "L": 0.0, "S": 0.0, "F": 0.0, "I": 0.0
    }

    # 计算贡献
    from ats_core.scoring.scorecard import get_factor_contributions
    scores_dict = {**A_scores, **B_scores}
    contributions = get_factor_contributions(scores_dict, weights)

    lines = []

    # ========== A层：方向判断 ==========
    lines.append("━━━━━ 🔵 A层：方向判断 ━━━━━")

    # A层6因子（使用圆形图标区分正负）
    a_factors = [
        ("T", "趋势", lambda: _desc_trend(A_scores["T"], _get(r, "scores_meta.T.Tm"))),
        ("M", "动量", lambda: _desc_momentum(A_scores["M"], _get(r, "scores_meta.M.slope_now"))),
        ("C", "资金", lambda: _desc_cvd_flow(
            A_scores["C"], True,
            _get(r, "scores_meta.C.cvd6"),
            _get(r, "scores_meta.C.consistency"),
            _get(r, "scores_meta.C.is_consistent")
        )),
        ("V", "量能", lambda: _desc_volume(A_scores["V"], _get(r, "scores_meta.V.v5v20"))),
        ("O", "持仓", lambda: _desc_positions(A_scores["O"], _get(r, "scores_meta.O.oi24h_pct"))),
        ("B", "基差", lambda: _desc_basis_funding(
            A_scores["B"],
            _get(r, "scores_meta.B.basis_bps"),
            _get(r, "scores_meta.B.funding_rate")
        ))
    ]

    for dim, name, desc_fn in a_factors:
        if dim in contributions:
            info = contributions[dim]
            score = info["score"]
            weight = info["weight_pct"]
            contrib = info["contribution"]

            # 使用圆形图标（蓝色系）
            if score > 60:
                emoji = "🔵"  # 强正向
            elif score > 20:
                emoji = "🟦"  # 正向
            elif score >= -20:
                emoji = "⚪"  # 中性
            elif score >= -60:
                emoji = "🟥"  # 负向
            else:
                emoji = "🔴"  # 强负向

            desc = desc_fn()
            lines.append(format_factor_with_weight(
                name, score, weight, contrib, emoji, desc
            ))

    # A层总分
    weighted_score = contributions.get("weighted_score", 0)
    lines.append(f"\n💎 加权总分: {weighted_score:+d}")

    # ========== B层：调制器 ==========
    lines.append("\n━━━━━ ⚙️ B层：调制器 ━━━━━")
    lines.append("（权重0%，仅调节执行参数）")

    # B层4调制器（使用齿轮/工具图标）
    b_modulators = [
        ("L", "流动性", "⚡", lambda: _desc_liquidity(
            B_scores["L"],
            _get(r, "scores_meta.L.spread_bps"),
            _get(r, "scores_meta.L.obi")
        )),
        ("S", "结构", "🎯", lambda: _desc_structure(B_scores["S"], _get(r, "scores_meta.S.theta"))),
        ("F", "资金领先", "🔧", lambda: _desc_fund_leading(B_scores["F"], _get(r, "scores_meta.F.leading_raw"))),
        ("I", "独立性", "⚙️", lambda: _desc_independence(B_scores["I"], _get(r, "scores_meta.I.beta_sum")))
    ]

    for dim, name, emoji, desc_fn in b_modulators:
        score = B_scores[dim]
        if score != 0:  # 只显示非零的调制器
            desc = desc_fn()
            # B层不显示权重和贡献，只显示分数和描述
            lines.append(f"{emoji} {name} {score:+d}  {desc}")

    return "\n".join(lines)


def render_prime_breakdown(r: Dict[str, Any]) -> str:
    """
    渲染Prime分数详细分解

    Returns:
        Prime分数分解字符串
    """
    prime = _get(r, "prime_strength") or _get(r, "prime") or 0
    confidence = _get(r, "confidence") or abs(_get(r, "weighted_score") or 0)
    probability = _get(r, "probability") or 0.5

    # Prime计算：confidence × 0.6 + prob_bonus
    # prob_bonus: (probability - 0.5) × 2 × 100 = (p - 0.5) × 200
    base_strength = confidence * 0.6
    prob_bonus = (probability - 0.5) * 2 * 100
    prime_calc = base_strength + prob_bonus

    lines = []
    lines.append("━━━━━ Prime分数分解 ━━━━━")
    lines.append(f"置信度: {confidence:.1f}")
    lines.append(f"基础强度: {confidence:.1f} × 0.6 = {base_strength:.1f}")
    lines.append(f"概率: {probability:.1%}")
    lines.append(f"概率加成: ({probability:.3f} - 0.5) × 200 = {prob_bonus:+.1f}")
    lines.append(f"Prime总分: {base_strength:.1f} + {prob_bonus:+.1f} = {prime_calc:.1f}")
    lines.append(f"最终Prime: {prime:.0f}/100")

    # Prime等级
    if prime >= 70:
        grade = "🟢 优秀（强势信号）"
    elif prime >= 50:
        grade = "🟡 良好（可靠信号）"
    elif prime >= 35:
        grade = "🔵 合格（基础信号）"
    else:
        grade = "🔴 不合格（信号过弱）"

    lines.append(f"Prime等级: {grade}")

    return "\n".join(lines)


def render_four_gates(r: Dict[str, Any]) -> str:
    """
    v6.6架构：渲染四门槛质量控制状态

    显示：
    - 🚪 Gate 1: DataQual（数据质量）
    - 💰 Gate 2: EV（期望值）
    - ⚡ Gate 3: Execution（执行质量）
    - 🎯 Gate 4: Probability（概率门槛）

    Returns:
        四门验证字符串
    """
    lines = []
    lines.append("━━━━━ 🚪 四门槛：质量控制 ━━━━━")

    # 获取gate数据
    gates_data = _get_dict(r, "gates")

    # 🚪 Gate 1: DataQual（数据质量）
    data_qual = _get(r, "data_quality") or _get(r, "DataQual") or gates_data.get("data_qual", 1.0)
    gate1_value = data_qual
    gate1_pass = data_qual >= 0.90

    lines.append(f"\n🚪 Gate 1：数据质量")
    lines.append(f"   {'✅' if gate1_pass else '❌'} DataQual = {data_qual:.2%} {'≥' if gate1_pass else '<'} 90%")
    if not gate1_pass:
        lines.append(f"   ⚠️ 数据质量不足，Prime强度降低")

    # 💰 Gate 2: EV（期望值）
    ev = _get(r, "expected_value") or _get(r, "EV") or gates_data.get("ev", 0)
    gate2_pass = ev > 0

    lines.append(f"\n💰 Gate 2：期望值")
    lines.append(f"   {'✅' if gate2_pass else '❌'} EV = {ev:+.2%} {'>' if gate2_pass else '≤'} 0")
    if not gate2_pass:
        lines.append(f"   ⚠️ 负期望值，Prime强度最多降低30%")

    # ⚡ Gate 3: Execution（执行质量，基于L流动性）
    L_score = _get(r, "L") or 0
    gates_execution = 0.5 + L_score / 200.0  # L映射到[0, 1]
    spread_bps = _get(r, "scores_meta.L.spread_bps") or 0
    impact_bps = _get(r, "slippage_bps") or 0

    lines.append(f"\n⚡ Gate 3：执行质量")
    lines.append(f"   执行评分: {gates_execution:.2f} (基于L={L_score:+d})")
    lines.append(f"   点差: {spread_bps:.1f}bps, 冲击: {impact_bps:.1f}bps")
    if gates_execution < 0.5:
        lines.append(f"   ⚠️ 流动性较差，Prime强度降低{(1-gates_execution)*100:.0f}%")

    # 🎯 Gate 4: Probability（概率门槛）
    probability = _get(r, "probability") or 0.5
    p_min = _get(r, "p_min") or 0.58
    gates_probability = 2 * probability - 1

    lines.append(f"\n🎯 Gate 4：概率门槛")
    lines.append(f"   概率: P = {probability:.1%}")
    lines.append(f"   门槛: p_min = {p_min:.1%}")
    lines.append(f"   概率评分: {gates_probability:.2f}")
    if probability < p_min:
        lines.append(f"   ⚠️ 概率低于门槛，Prime强度降低")

    # gate_multiplier影响（v6.6关键机制）
    gate_multiplier = _get(r, "gate_multiplier") or 1.0
    strength_before = _get(r, "prime_breakdown.strength_before_gates") or 0
    strength_after = _get(r, "prime_breakdown.strength_after_gates") or 0

    lines.append(f"\n🔗 四门槛综合影响:")
    lines.append(f"   gate_multiplier = {gate_multiplier:.3f}")
    if strength_before > 0 and strength_after > 0:
        impact_pct = (strength_after - strength_before) / strength_before * 100
        lines.append(f"   Prime强度: {strength_before:.1f} → {strength_after:.1f} ({impact_pct:+.1f}%)")
    else:
        lines.append(f"   Prime强度调节: ×{gate_multiplier:.3f}")

    # 总体状态
    if gate_multiplier >= 0.95:
        status = "🟢 优秀（几乎无惩罚）"
    elif gate_multiplier >= 0.85:
        status = "🟡 良好（轻微惩罚）"
    elif gate_multiplier >= 0.70:
        status = "🟠 一般（中度惩罚）"
    else:
        status = "🔴 较差（显著惩罚）"

    lines.append(f"\n整体评级: {status}")

    return "\n".join(lines)


def render_modulators(r: Dict[str, Any]) -> str:
    """
    v6.6架构：渲染B层调制器详细信息

    显示所有4个B层调制器（L/S/F/I）及其调制效果：
    - ⚡ L流动性 → position_mult, cost
    - 🎯 S结构   → confidence, Teff
    - 🔧 F资金领先→ Teff, p_min
    - ⚙️ I独立性 → Teff, cost

    Returns:
        调节器信息字符串
    """
    lines = []
    lines.append("━━━━━ ⚙️ B层：调制器 ━━━━━")
    lines.append("（权重0%，仅调节执行参数）\n")

    # 获取modulator_output（如果有）
    mod_output = _get_dict(r, "modulator_output")

    # ⚡ L流动性调制器
    L_score = _get(r, "L") or 0
    position_mult = mod_output.get("position_mult", 1.0) if mod_output else 1.0
    cost_eff_L = mod_output.get("cost_eff_L", 0.0) if mod_output else 0.0

    l_desc = _desc_liquidity(L_score, _get(r, "scores_meta.L.spread_bps"), _get(r, "scores_meta.L.obi"))
    lines.append(f"⚡ L流动性 {L_score:+d}: {l_desc}")
    lines.append(f"   └─ 仓位调节: {position_mult:.0%}")
    if cost_eff_L != 0:
        lines.append(f"   └─ 成本调节: {cost_eff_L:+.2%}")

    # 🎯 S结构调制器
    S_score = _get(r, "S") or 0
    confidence_mult = mod_output.get("confidence_mult", 1.0) if mod_output else 1.0
    Teff_S = mod_output.get("Teff_S", 1.0) if mod_output else 1.0

    s_desc = _desc_structure(S_score, _get(r, "scores_meta.S.theta"))
    lines.append(f"\n🎯 S结构 {S_score:+d}: {s_desc}")
    if confidence_mult != 1.0:
        lines.append(f"   └─ 信心倍数: ×{confidence_mult:.2f}")
    if Teff_S != 1.0:
        lines.append(f"   └─ 温度倍数: ×{Teff_S:.2f}")

    # 🔧 F资金领先调制器
    F_score = _get(r, "F") or 0
    Teff_F = mod_output.get("Teff_F", 1.0) if mod_output else 1.0

    # v6.7++: 使用FIModulator的统一阈值信息
    fi_thresholds = _get_dict(r, "fi_thresholds")
    adj_F = fi_thresholds.get("adj_F", 0.0)  # F的p_min调整量
    adj_I = fi_thresholds.get("adj_I", 0.0)  # I的p_min调整量

    f_desc = _desc_fund_leading(F_score, _get(r, "scores_meta.F.leading_raw"))
    lines.append(f"\n🔧 F资金领先 {F_score:+d}: {f_desc}")
    if Teff_F != 1.0:
        lines.append(f"   └─ 温度倍数: ×{Teff_F:.2f}")
    if adj_F != 0:
        lines.append(f"   └─ p_min调整(F): {adj_F:+.3f}")

    # ⚙️ I独立性调制器
    I_score = _get(r, "I") or 0
    Teff_I = mod_output.get("Teff_I", 1.0) if mod_output else 1.0
    cost_eff_I = mod_output.get("cost_eff_I", 0.0) if mod_output else 0.0

    i_desc = _desc_independence(I_score, _get(r, "scores_meta.I.beta_sum"))
    lines.append(f"\n⚙️ I独立性 {I_score:+d}: {i_desc}")
    if Teff_I != 1.0:
        lines.append(f"   └─ 温度倍数: ×{Teff_I:.2f}")
    if cost_eff_I != 0:
        lines.append(f"   └─ 成本调节: {cost_eff_I:+.2%}")
    if adj_I != 0:
        lines.append(f"   └─ p_min调整(I): {adj_I:+.3f}")

    # 融合结果（如果有）
    if mod_output:
        Teff_final = mod_output.get("Teff_final", 2.0)
        cost_final = mod_output.get("cost_final", 0.0015)
        lines.append(f"\n🔗 融合结果:")
        lines.append(f"   └─ 最终温度: {Teff_final:.3f}")
        lines.append(f"   └─ 最终成本: {cost_final:.4f} ({cost_final*10000:.1f}bps)")

        # v6.7++: 添加统一后的p_min信息
        if fi_thresholds:
            p_min_base = fi_thresholds.get("p_min_base", 0.0)
            p_min_final = fi_thresholds.get("p_min_adjusted", 0.0)
            total_adj = adj_F + adj_I
            safety_adj = fi_thresholds.get("safety_adjustment", 0.0)
            if p_min_final > 0:
                lines.append(f"   └─ 概率阈值: {p_min_base:.3f} + F{adj_F:+.3f} + I{adj_I:+.3f} + 安全{safety_adj:+.3f} = {p_min_final:.3f}")

    return "\n".join(lines)


def render_signal_detailed(r: Dict[str, Any], is_watch: bool = False) -> str:
    """
    详细模式：显示所有因子、权重、贡献、调节器、Prime、四门

    适用场景：调试、监控、深度分析
    """
    l1, l2 = _header_lines(r, is_watch)
    pricing = _pricing_block(r)

    # 主要内容块
    weights_summary = render_weights_summary(r)
    modulators = render_modulators(r)
    four_gates = render_four_gates(r)
    prime = render_prime_breakdown(r)

    # 组装消息
    body = f"{l1}\n{l2}\n{pricing}\n\n{weights_summary}\n\n{modulators}\n\n{four_gates}\n\n{prime}\n\n{_note_and_tags(r, is_watch)}"

    return body


# ---------- main render ----------

def _header_lines(r: Dict[str, Any], is_watch: bool) -> Tuple[str, str]:
    sym = _get(r, "symbol") or _get(r, "ticker") or _get(r, "sym") or "—"
    price = (
        _get(r, "price")
        or _get(r, "last")
        or _get(r, "one_24h.lastPrice")
        or _get(r, "quote.last")
    )
    price_s = _fmt_price(price)

    ttl_h = int(_ttl_hours(r))
    # compute six + conviction/side
    six = _six_scores(r)
    conv, side_lbl = _conviction_and_side(r, six)

    line1 = f"🔹 {sym} · 现价 {price_s}"

    # v6.7新增：蓄势待发标识
    publish_info = _get_dict(r, "publish")
    is_accumulating = publish_info.get("is_accumulating", False)
    accumulating_reason = publish_info.get("accumulating_reason", "")

    # 不再区分观察/正式，统一为正式信号
    line2 = f"{side_lbl} 概率{conv}% · 有效期{ttl_h}h"

    # 如果是蓄势信号，添加特殊标识
    if is_accumulating:
        line2 += f"\n🔍 蓄势待发 · {accumulating_reason}"

    return line1, line2

def _six_block(r: Dict[str, Any]) -> str:
    """
    v6.6架构：生成多维因子显示块（美化简洁版）

    显示：
    - 🔵 A层：方向判断（6因子：T/M/C/V/O/B）
    - ⚙️ B层：调制器（4因子：L/S/F/I，仅显示非零）
    - 📊 大盘环境

    优化：
    - 使用彩色渐变圆形图标（🟢🟡⚪🟠🔴）
    - 使用独特彩色图标（💧🏗️💰🎯）
    - 优化对齐和排版
    """
    # 获取v6.6分数
    v66 = _v66_scores(r)
    A_scores = v66['A']
    B_scores = v66['B']

    # 获取方向
    side = (_get(r, "side") or "").lower()
    is_long = side in ("long", "buy", "bull", "多", "做多")

    # 获取各维度的真实数据
    T_meta = _get_dict(r, "scores_meta.T")
    M_meta = _get_dict(r, "scores_meta.M")
    C_meta = _get_dict(r, "scores_meta.C")
    V_meta = _get_dict(r, "scores_meta.V")
    O_meta = _get_dict(r, "scores_meta.O")
    B_meta = _get_dict(r, "scores_meta.B")

    # 提取A层具体指标
    Tm = T_meta.get("Tm")
    slope = M_meta.get("slope_now")
    cvd6 = C_meta.get("cvd6")
    cvd_consistency = C_meta.get("consistency")
    cvd_is_consistent = C_meta.get("is_consistent")
    v5v20 = V_meta.get("v5v20")
    oi24h_pct = O_meta.get("oi24h_pct")
    basis_bps = B_meta.get("basis_bps")
    funding_rate = B_meta.get("funding_rate")

    def get_color_emoji(score: int) -> str:
        """获取彩色渐变圆形图标"""
        if score >= 70:
            return "🟢"  # 强正向：绿色
        elif score >= 40:
            return "🟡"  # 正向：黄色
        elif score >= -40:
            return "🟠"  # 中性：橙色（黄橙之间，更清晰）
        elif score >= -70:
            return "🔴"  # 负向：红色
        else:
            return "🔵"  # 强负向：深蓝色

    lines = []

    # ========== 🎯 A层：方向判断（6因子） ==========
    lines.append("━━━ 🎯 A层：方向判断 ━━━")
    lines.append("")

    # A层6因子（使用彩色圆形图标）
    a_factors = [
        ("趋势", A_scores['T'], _desc_trend(A_scores['T'], Tm)),
        ("动量", A_scores['M'], _desc_momentum(A_scores['M'], slope)),
        ("资金", A_scores['C'], _desc_cvd_flow(A_scores['C'], is_long, cvd6, cvd_consistency, cvd_is_consistent)),
        ("量能", A_scores['V'], _desc_volume(A_scores['V'], v5v20)),
        ("持仓", A_scores['O'], _desc_positions(A_scores['O'], oi24h_pct)),
        ("基差", A_scores['B'], _desc_basis_funding(A_scores['B'], basis_bps, funding_rate))
    ]

    for name, score, desc in a_factors:
        emoji = get_color_emoji(score)
        # 使用固定宽度对齐
        lines.append(f"{emoji} {name:>2} {score:>4d}  {desc}")

    # ========== ⚙️ B层：调制器（4因子） ==========
    b_displayed = []

    # L流动性调制器（💧 水滴图标）
    if B_scores['L'] != 0:
        L_meta = _get_dict(r, "scores_meta.L")
        spread_bps = L_meta.get("spread_bps")
        obi = L_meta.get("obi")
        mod_output = _get_dict(r, "modulator_output")
        # 修复：从嵌套结构中提取position_mult（如果有）
        position_mult = mod_output.get("L", {}).get("position_mult", mod_output.get("position_mult", 1.0))
        desc = _desc_liquidity(B_scores['L'], spread_bps, obi)
        b_displayed.append(f"💧 流动 {B_scores['L']:>4d}  仓位{position_mult:>3.0%} · {desc}")

    # S结构调制器（🏗️ 建筑图标）
    if B_scores['S'] != 0:
        S_meta = _get_dict(r, "scores_meta.S")
        theta = S_meta.get("theta")
        mod_output = _get_dict(r, "modulator_output")
        # 修复：从嵌套结构中提取Teff值
        Teff_S = mod_output.get("S", {}).get("Teff_mult", 1.0)
        desc = _desc_structure(B_scores['S'], theta)
        b_displayed.append(f"🏗️ 结构 {B_scores['S']:>4d}  T×{Teff_S:>4.2f} · {desc}")

    # F资金领先调制器（💰 钱袋图标）
    if B_scores['F'] != 0:
        F_meta = _get_dict(r, "scores_meta.F")
        leading_raw = F_meta.get("leading_raw")
        mod_output = _get_dict(r, "modulator_output")
        # 修复：从嵌套结构中提取Teff值
        Teff_F = mod_output.get("F", {}).get("Teff_mult", 1.0)
        desc = _desc_fund_leading(B_scores['F'], leading_raw)
        b_displayed.append(f"💰 资金 {B_scores['F']:>4d}  T×{Teff_F:>4.2f} · {desc}")

    # I独立性调制器（🎯 靶心图标）
    if B_scores['I'] != 0:
        I_meta = _get_dict(r, "scores_meta.I")
        beta_sum = I_meta.get("beta_sum")
        mod_output = _get_dict(r, "modulator_output")
        # 修复：从嵌套结构中提取Teff值
        Teff_I = mod_output.get("I", {}).get("Teff_mult", 1.0)
        desc = _desc_independence(B_scores['I'], beta_sum)
        b_displayed.append(f"🎯 独立 {B_scores['I']:>4d}  T×{Teff_I:>4.2f} · {desc}")

    if b_displayed:
        lines.append("")
        lines.append("━━━ ⚙️ B层：调制器 ━━━")
        lines.append("")
        lines.extend(b_displayed)

    # ========== 📊 大盘环境 ==========
    market_regime = _get(r, "market_regime")
    market_meta = _get_dict(r, "market_meta")

    if market_regime is not None:
        regime_desc = market_meta.get("regime_desc", "未知")
        btc_trend = market_meta.get("btc_trend", 0)
        eth_trend = market_meta.get("eth_trend", 0)
        market_emoji = get_color_emoji(market_regime)

        lines.append("")
        lines.append("━━━ 📊 大盘环境 ━━━")
        lines.append("")
        lines.append(f"{market_emoji} {regime_desc} (市场{market_regime:>4d})")
        # 给BTC和ETH添加图标和└─前缀
        btc_emoji = get_color_emoji(btc_trend)
        eth_emoji = get_color_emoji(eth_trend)
        lines.append(f"   └─ {btc_emoji} BTC{btc_trend:>4d} · {eth_emoji} ETH{eth_trend:>4d}")

    return "\n".join(lines)

def _pricing_block(r: Dict[str, Any]) -> str:
    """
    生成价格信息块（v6.7简洁增强版）

    显示：
    - 入场区间
    - 止损（距离% · 方法 · 置信度）
    - 止盈1/2（距离%）
    - 盈亏比
    """
    # 获取价格数据
    price = _get(r, "price") or _get(r, "last") or 0
    stop_loss = _get_dict(r, "stop_loss")
    take_profit = _get_dict(r, "take_profit")
    pricing = _get_dict(r, "pricing")

    lines = []

    # 入场区间
    entry_lo = pricing.get("entry_lo") or price
    entry_hi = pricing.get("entry_hi") or price
    if abs(entry_lo - entry_hi) < 0.0001:
        lines.append(f"📍 入场价: {_fmt_price(entry_lo)}")
    else:
        lines.append(f"📍 入场区间: {_fmt_price(entry_lo)} - {_fmt_price(entry_hi)}")

    # 止损（增强显示）
    sl_price = stop_loss.get("stop_price")
    if sl_price:
        sl_distance_pct = stop_loss.get("distance_pct", 0)
        sl_method_cn = stop_loss.get("method_cn", "")
        sl_confidence = stop_loss.get("confidence", 0)

        # 构建止损描述
        sl_details = []
        if sl_distance_pct:
            sl_details.append(f"距离{abs(sl_distance_pct):.1%}")
        if sl_method_cn:
            sl_details.append(sl_method_cn)
        if sl_confidence:
            sl_details.append(f"置信{sl_confidence}")

        if sl_details:
            lines.append(f"🛑 止损: {_fmt_price(sl_price)} ({' · '.join(sl_details)})")
        else:
            lines.append(f"🛑 止损: {_fmt_price(sl_price)}")

    # 止盈1
    tp1_price = take_profit.get("price") or pricing.get("tp1")
    if tp1_price and price:
        tp1_dist_pct = abs(tp1_price - price) / price
        lines.append(f"🎯 止盈1: {_fmt_price(tp1_price)} (距离{tp1_dist_pct:.1%})")

    # 止盈2（如果有）
    tp2_price = pricing.get("tp2")
    if tp2_price and price:
        tp2_dist_pct = abs(tp2_price - price) / price
        lines.append(f"🎯 止盈2: {_fmt_price(tp2_price)} (距离{tp2_dist_pct:.1%})")

    if lines:
        return "\n" + "\n".join(lines)
    return ""


def _core_metrics_block(r: Dict[str, Any]) -> str:
    """
    生成核心指标块（v6.7新增）

    显示：期望收益和盈亏比（一行）
    """
    # 期望收益
    publish_info = _get_dict(r, "publish")
    EV = publish_info.get("EV") or _get(r, "expected_value") or 0

    # v6.7类型安全
    if isinstance(EV, dict):
        EV = 0

    # 盈亏比
    take_profit = _get_dict(r, "take_profit")
    rr_ratio = take_profit.get("rr_ratio", 0)

    # 盈亏比emoji
    if rr_ratio >= 2.0:
        rr_emoji = "✅"
    elif rr_ratio >= 1.5:
        rr_emoji = "⚠️"
    else:
        rr_emoji = "❌"

    return f"期望收益 {EV:+.1%} · 盈亏比 1:{rr_ratio:.1f} {rr_emoji}"


def _position_block(r: Dict[str, Any]) -> str:
    """
    生成仓位建议块（v6.7简洁版）

    显示：基准、调制、分配策略
    """
    position_mult = _get(r, "position_mult") or 1.0
    modulation = _get_dict(r, "modulation")
    L_score = modulation.get("L", 50)

    base_position = 10000
    adjusted_position = base_position * position_mult
    entry_immediate = adjusted_position * 0.60
    entry_reserve = adjusted_position * 0.40

    lines = []
    lines.append("💼 仓位建议")
    lines.append(f"• 基准仓位: ${base_position:.0f}")
    lines.append(f"• L调制器: {position_mult:.0%} (L={L_score})")
    lines.append(f"• 调整后: ${adjusted_position:.0f}")
    lines.append(f"  ├─ 立即入场: ${entry_immediate:.0f} (60%)")
    lines.append(f"  └─ 预留加仓: ${entry_reserve:.0f} (40%)")

    return "\n" + "\n".join(lines)


def _risk_alerts_block(r: Dict[str, Any]) -> str:
    """
    生成风险提示块（v6.7自动化）

    根据各项指标自动生成风险警告
    """
    alerts = []
    modulation = _get_dict(r, "modulation")
    modulator_output = _get_dict(r, "modulator_output")
    publish_info = _get_dict(r, "publish")

    # 风险1：流动性
    L_score = modulation.get("L", 50)
    if L_score < 50:
        L_meta = modulator_output.get("L", {}).get("meta", {})
        warnings = L_meta.get("warnings", [])
        if warnings:
            alerts.append(f"⚠️ [流动性] {'; '.join(warnings)}")
        else:
            alerts.append("⚠️ [流动性] 流动性偏低，注意滑点")

    # 风险2：结构
    S_score = modulation.get("S", 0)
    if S_score < -50:
        alerts.append("⚠️ [结构] 市场结构混乱，止损可能频繁触发")

    # 风险3：成交量
    T, M, C, S, V, OI, L, B, Q, I, F = _ten_scores(r)
    if V < -60:
        alerts.append("⚠️ [成交量] 量能不足，注意追涨风险")

    # 风险4：独立性
    I_score = modulation.get("I", 0)
    if I_score < -30:
        alerts.append("⚠️ [独立性] 跟随性强，注意市场联动风险")

    # 风险5：数据质量
    data_qual = _get(r, "data_qual") or 1.0
    if data_qual < 0.95:
        alerts.append(f"⚠️ [数据] 数据质量略低({data_qual:.0%})，建议复核")

    # 风险6：软约束
    soft_filtered = publish_info.get("soft_filtered", False)
    if soft_filtered:
        reason = publish_info.get("soft_filter_reason", "")
        alerts.append(f"ℹ️ [软约束] {reason}")

    # v6.7新增：蓄势信号的特殊提示
    is_accumulating = publish_info.get("is_accumulating", False)
    if is_accumulating:
        alerts.insert(0, "💡 [蓄势信号] 资金已流入但价格未涨，建议分批建仓，不要急于梭哈")

    if alerts:
        return "\n\n🚨 风险提示\n" + "\n".join(alerts)
    return ""

def _note_and_tags(r: Dict[str, Any], is_watch: bool) -> str:
    note = _get(r, "note") or _get(r, "publish.note") or ""
    tag = "#watch" if is_watch else "#trade"
    sym = _get(r, "symbol")
    symtag = f" #{sym}" if isinstance(sym, str) and sym else ""
    tail = ""
    if note:
        tail += f"备注：{note}\n"
    tail += f"{tag}{symtag}"
    return tail

def render_signal(r: Dict[str, Any], is_watch: bool = False) -> str:
    """
    v6.7简洁模板：适合非专业人士

    特点：
    - 清晰的结构和emoji
    - 核心信息前置（期望收益、盈亏比）
    - 止损止盈详细信息（距离、方法）
    - 仓位建议完整（基准、调制、分配）
    - 多维分析简洁（主要因子）
    - 自动风险提示
    """
    # 1. 头部（交易对、价格、方向、概率、有效期）
    l1, l2 = _header_lines(r, is_watch)

    # 2. 核心指标（期望收益、盈亏比）
    core_metrics = _core_metrics_block(r)

    # 3. 入场止损止盈
    pricing = _pricing_block(r)

    # 4. 仓位建议
    position = _position_block(r)

    # 5. 多维分析（因子列表）
    factors = _six_block(r)

    # 6. 风险提示（如果有）
    risk_alerts = _risk_alerts_block(r)

    # 7. 标签
    tags = _note_and_tags(r, is_watch)

    # 组装消息（v6.7优化：增加空行便于区分各部分）
    body = f"{l1}\n{l2}\n{core_metrics}\n"  # 盈亏比后面空一行
    body += pricing  # pricing已包含\n开头
    body += "\n"  # 止盈后面空一行
    body += position
    body += f"\n\n多维分析\n{factors}"
    body += risk_alerts
    body += f"\n\n{tags}"

    return body

def render_watch(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=True)

def render_trade(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=False)


def render_five_piece_report(r: Dict[str, Any], is_watch: bool = False) -> str:
    """
    渲染五段式报告（完整监控格式）

    五段结构：
    1. 基础信息：Symbol, Side, Probability, EV, Prime
    2. 分数明细：All factor scores with weights and contributions
    3. 调制器：F/I adjustments, cost_eff, thresholds
    4. 四门验证：DataQual, EV, Execution, Probability
    5. 风险参数：Position size, R-value, Stop-loss/Take-profit

    适用场景：监控报告、交易复盘、完整审计
    """
    # ========== 第一段：基础信息 ==========
    sym = _get(r, "symbol") or _get(r, "ticker") or "—"
    price = _get(r, "price") or _get(r, "last") or _get(r, "one_24h.lastPrice")
    price_s = _fmt_price(price)

    side = (_get(r, "side") or "").lower()
    if side in ("long", "buy", "bull", "多", "做多"):
        side_lbl = "🟩 做多"
    elif side in ("short", "sell", "bear", "空", "做空"):
        side_lbl = "🟥 做空"
    else:
        side_lbl = "🟦 中性"

    probability = _get(r, "probability") or 0.5
    ev = _get(r, "expected_value") or _get(r, "EV") or 0
    prime = _get(r, "prime_strength") or _get(r, "prime") or 0
    ttl_h = int(_ttl_hours(r))

    piece1 = []
    piece1.append("━━━━━ ① 基础信息 ━━━━━")
    piece1.append(f"交易对: {sym}")
    piece1.append(f"现价: {price_s}")
    piece1.append(f"方向: {side_lbl}")
    piece1.append(f"胜率: {probability:.1%}")
    piece1.append(f"期望值: {ev:+.2%}")
    piece1.append(f"Prime强度: {prime:.0f}/100")
    piece1.append(f"有效期: {ttl_h}小时")

    # ========== 第二段：分数明细 ==========
    piece2 = []
    piece2.append("\n━━━━━ ② 分数明细 ━━━━━")
    piece2.append(render_weights_summary(r))

    # ========== 第三段：调制器 ==========
    piece3 = []
    piece3.append("\n━━━━━ ③ 调制器 ━━━━━")

    # F 资金领先
    F_score = _get(r, "F_score") or _get(r, "F") or 0
    F_adj = _get(r, "F_adjustment") or 1.0
    cost_eff = _get(r, "cost_eff") or 0.0
    f_desc = _desc_fund_leading(F_score)
    f_emoji = _emoji_by_fund_leading(F_score)

    piece3.append(f"{f_emoji} F资金领先 {F_score:+d}: {f_desc}")
    piece3.append(f"   └─ 概率调整: ×{F_adj:.2f}")
    piece3.append(f"   └─ 有效成本: {cost_eff:.4f} (交易费+滑点)")

    # F否决警告
    f_veto_warning = _get(r, "f_veto_warning")
    if f_veto_warning:
        piece3.append(f"   └─ ⚠️ {f_veto_warning}")

    # I 独立性
    I_score = _get(r, "I") or 0
    if I_score != 0:
        i_desc = _desc_independence(I_score, _get(r, "scores_meta.I.beta_sum"))
        i_emoji = _emoji_by_score(I_score)
        p_min = _get(r, "p_min") or 0.62
        delta_p_min = _get(r, "delta_p_min") or 0.12

        piece3.append(f"\n{i_emoji} I独立性 {I_score:+d}: {i_desc}")
        piece3.append(f"   └─ p_min阈值: {p_min:.1%}")
        piece3.append(f"   └─ Δp_min阈值: {delta_p_min:.1%}")

    # ========== 第四段：四门验证 ==========
    piece4 = []
    piece4.append("\n" + render_four_gates(r))

    # ========== 第五段：风险参数 ==========
    piece5 = []
    piece5.append("\n━━━━━ ⑤ 风险参数 ━━━━━")

    # 仓位与风险
    position_size = _get(r, "position_size") or _get(r, "qty")
    account_equity = _get(r, "account_equity") or 10000
    risk_pct = _get(r, "risk_pct") or 0.005
    atr = _get(r, "atr") or _get(r, "vol.atr_pct")

    if position_size is not None:
        piece5.append(f"建议仓位: {position_size:.4f} (合约)")

    piece5.append(f"账户权益: ${account_equity:,.0f}")
    piece5.append(f"风险比例: {risk_pct:.2%} (每笔交易)")

    if atr is not None:
        if isinstance(atr, float) and atr < 1:
            # ATR是百分比形式
            piece5.append(f"ATR: {atr:.2%}")
        else:
            # ATR是绝对值
            piece5.append(f"ATR: {atr:.2f}")

    # 止损止盈
    pricing = _get_dict(r, "pricing")
    entry_lo = pricing.get("entry_lo")
    entry_hi = pricing.get("entry_hi")
    sl = pricing.get("sl")
    tp1 = pricing.get("tp1")
    tp2 = pricing.get("tp2")

    if entry_lo is not None and entry_hi is not None:
        if abs(entry_lo - entry_hi) < 0.0001:
            piece5.append(f"入场价: {_fmt_price(entry_lo)}")
        else:
            piece5.append(f"入场区间: {_fmt_price(entry_lo)} - {_fmt_price(entry_hi)}")

    if sl is not None:
        piece5.append(f"止损: {_fmt_price(sl)}")
        if price:
            sl_dist_pct = abs(sl - price) / price * 100
            piece5.append(f"   └─ 止损距离: {sl_dist_pct:.2f}%")

    if tp1 is not None:
        piece5.append(f"止盈1: {_fmt_price(tp1)}")
        if price:
            tp1_dist_pct = abs(tp1 - price) / price * 100
            piece5.append(f"   └─ 盈利空间: {tp1_dist_pct:.2f}%")

    if tp2 is not None:
        piece5.append(f"止盈2: {_fmt_price(tp2)}")
        if price:
            tp2_dist_pct = abs(tp2 - price) / price * 100
            piece5.append(f"   └─ 盈利空间: {tp2_dist_pct:.2f}%")

    # 风险回报比
    if sl is not None and tp1 is not None and price is not None:
        risk = abs(price - sl)
        reward = abs(tp1 - price)
        if risk > 0:
            rr_ratio = reward / risk
            piece5.append(f"风险回报比: 1:{rr_ratio:.2f}")

    # ========== 组装消息 ==========
    note = _get(r, "note") or _get(r, "publish.note") or ""
    tag = "#watch" if is_watch else "#trade"
    symtag = f" #{sym}"

    footer = ""
    if note:
        footer += f"\n━━━━━━━━━━━━━━━\n备注：{note}\n"
    footer += f"\n{tag}{symtag}"

    # 合并所有段落
    report = "\n".join(piece1)
    report += "\n".join(piece2)
    report += "\n".join(piece3)
    report += "\n".join(piece4)
    report += "\n".join(piece5)
    report += footer

    return report


# ============================================================
# v6.7新增：整合v66的9块结构和富媒体特性
# ============================================================

def render_v67_rich(r: Dict[str, Any]) -> str:
    """
    v6.7富信息模式（整合v66的9块结构 + 旧模板的专业描述）

    9个信息块：
    1. 信号头部 - 方向、交易对、强度
    2. 核心指标 - 评分、edge、概率、EV、信心
    3. 因子明细 - Top 4因子贡献（带专业描述）
    4. 调制器状态 - L/S/F/I详情
    5. 入场止损止盈 - 价格、距离、RR比
    6. 仓位建议 - 基准仓位、调制、分配
    7. 风险提示 - 自动识别警告
    8. 市场环境 - BTC、情绪、波动
    9. 元数据 - 时间、版本、链接

    特点：结合v66的结构化和旧模板的专业描述
    """

    # ============ Block 1: 信号头部 ============
    direction = (_get(r, "side") or "unknown").upper()
    symbol = _get(r, "symbol") or _get(r, "ticker") or "UNKNOWN"
    score = _get(r, "weighted_score") or 0

    # v6.7类型安全：防止dict导致abs()错误
    if isinstance(score, dict):
        score = 0
    elif not isinstance(score, (int, float)):
        score = 0

    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    strength_emoji = _get_strength_emoji_v67(abs(score))

    header = f"""{direction_emoji} **{direction} {symbol}** {strength_emoji}
━━━━━━━━━━━━━━━━━━━━
"""

    # ============ Block 2: 核心指标 ============
    edge = _get(r, "edge") or 0
    probability = _get(r, "probability") or 0
    confidence = _get(r, "confidence") or 0

    # v6.7类型安全
    if isinstance(edge, dict):
        edge = 0
    if isinstance(probability, dict):
        probability = 0
    if isinstance(confidence, dict):
        confidence = 0

    publish_info = _get_dict(r, "publish")
    EV = _get(publish_info, "EV") or 0
    if isinstance(EV, dict):
        EV = 0

    core_metrics = f"""📊 **核心指标**
• 综合评分: {score:+.1f}/100
• 优势边际: {edge:+.2f}
• 胜率: {probability:.1%}
• 期望收益: {EV:+.2%}
• 信心指数: {confidence:.0f}/100
"""

    # ============ Block 3: 因子明细 (使用专业描述) ============
    factor_contribs = _get_dict(r, "factor_contributions")
    factor_detail = ""

    if factor_contribs:
        # v6.7修复：过滤汇总键
        summary_keys = {"total_weight", "weighted_score", "confidence", "edge"}
        real_factors = {
            k: v for k, v in factor_contribs.items()
            if k not in summary_keys and isinstance(v, dict)
        }

        # 按贡献排序取Top 4
        def safe_contrib(factor_dict):
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
            emoji = _emoji_by_score(factor_dict.get("score", 0))
            score_val = factor_dict.get("score", 0)
            weight_pct = factor_dict.get("weight_pct", 0)
            contribution = factor_dict.get("contribution", 0)

            # 类型安全
            if not isinstance(score_val, (int, float)):
                score_val = 0
            if not isinstance(weight_pct, (int, float)):
                weight_pct = 0
            if not isinstance(contribution, (int, float)):
                contribution = 0

            # 使用专业描述函数
            desc = _get_factor_desc_v67(r, name, score_val)

            factor_lines.append(
                f"{emoji} **{name}** {score_val:+3.0f} ({weight_pct:.1f}%) → {contribution:+.1f}\n  {desc}"
            )

        factor_detail = f"""
🎯 **因子分析** (Top 4)
{chr(10).join(factor_lines)}
"""

    # ============ Block 4: 调制器状态 ============
    modulator_output = _get_dict(r, "modulator_output")
    modulator_status = ""

    if modulator_output:
        L_data = modulator_output.get("L", {})
        S_data = modulator_output.get("S", {})
        F_data = modulator_output.get("F", {})
        I_data = modulator_output.get("I", {})
        fusion = modulator_output.get("fusion", {})

        modulation = _get_dict(r, "modulation")
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

    # ============ Block 5: 入场止损止盈 (带RR比emoji) ============
    price = _get(r, "price") or _get(r, "last") or 0
    stop_loss_data = _get_dict(r, "stop_loss")
    take_profit_data = _get_dict(r, "take_profit")

    sl_price = stop_loss_data.get("stop_price", 0)
    sl_distance_pct = stop_loss_data.get("distance_pct", 0)
    sl_distance_usdt = stop_loss_data.get("distance_usdt", 0)
    sl_method_cn = stop_loss_data.get("method_cn", "未知")
    sl_confidence = stop_loss_data.get("confidence", 0)

    tp_price = take_profit_data.get("price", 0)
    tp_distance_pct = take_profit_data.get("distance_pct", 0)
    tp_distance_usdt = take_profit_data.get("distance_usdt", 0)
    rr_ratio = take_profit_data.get("rr_ratio", 0)

    # v6.7改进：RR比emoji标识
    rr_emoji = "✅" if rr_ratio >= 2.0 else "⚠️" if rr_ratio >= 1.5 else "❌"

    entry_stop_block = f"""
💰 **入场与止损止盈**
• 入场价: {_fmt_price(price)}
• 止损: {_fmt_price(sl_price)}
  └ 距离: {sl_distance_pct:.2%} (${sl_distance_usdt:.2f}/1000U)
  └ 方法: {sl_method_cn}
  └ 置信: {sl_confidence}/100
• 止盈: {_fmt_price(tp_price)}
  └ 距离: {tp_distance_pct:.2%} (${tp_distance_usdt:.2f}/1000U)
• 盈亏比: 1:{rr_ratio:.1f} {rr_emoji}
"""

    # ============ Block 6: 仓位建议 ============
    position_mult = _get(r, "position_mult") or 1.0
    base_position = 10000
    adjusted_position = base_position * position_mult

    entry_immediate = adjusted_position * 0.60
    entry_reserve = adjusted_position * 0.40

    if position_mult > 0.9:
        position_note = "流动性优秀，可满仓"
    elif position_mult > 0.6:
        position_note = "流动性中等，适度降低仓位"
    else:
        position_note = "流动性较差，建议小仓位试探"

    modulation = _get_dict(r, "modulation")
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

    # ============ Block 7: 风险提示 (v6.7自动化) ============
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
    data_qual = _get(r, "data_qual") or 1.0
    if data_qual and data_qual < 0.95:
        alerts.append(f"⚠️ [数据] 数据质量略低({data_qual:.0%})，建议复核")

    # 风险5：软约束 (v6.7新增)
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
    market_meta = _get_dict(r, "market_meta")
    btc_trend_val = market_meta.get("btc_trend", 0)
    market_regime = _get(r, "market_regime") or 0

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

    volatility = _get(r, "optimization_meta.volatility") or "中等"

    context_block = f"""
🌍 **市场环境**
• BTC趋势: {btc_trend_text}
• 市场情绪: {sentiment}
• 波动率: {volatility}
"""

    # ============ Block 9: 元数据 (v6.7新增Binance链接) ============
    from datetime import datetime, timezone
    # UTC时区（统一使用UTC，与Binance API保持一致）
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    version = "v6.7"
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


def render_v67_compact(r: Dict[str, Any]) -> str:
    """v6.7简洁模式（6个核心块）"""

    # Block 1: 头部
    direction = (_get(r, "side") or "unknown").upper()
    symbol = _get(r, "symbol") or _get(r, "ticker") or "UNKNOWN"
    score = _get(r, "weighted_score") or 0

    # 类型安全
    if isinstance(score, dict):
        score = 0
    elif not isinstance(score, (int, float)):
        score = 0

    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    strength_emoji = _get_strength_emoji_v67(abs(score))

    message = f"{direction_emoji} **{direction} {symbol}** {strength_emoji}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Block 2: 核心指标
    edge = _get(r, "edge") or 0
    probability = _get(r, "probability") or 0
    EV = _get(r, "publish.EV") or 0

    # 类型安全
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
    factor_contribs = _get_dict(r, "factor_contributions")
    if factor_contribs:
        # 过滤汇总键
        summary_keys = {"total_weight", "weighted_score", "confidence", "edge"}
        real_factors = {
            k: v for k, v in factor_contribs.items()
            if k not in summary_keys and isinstance(v, dict)
        }

        def safe_contrib(factor_dict):
            if isinstance(factor_dict, dict):
                contrib = factor_dict.get("contribution", 0)
                if isinstance(contrib, (int, float)):
                    return abs(contrib)
            return 0

        sorted_factors = sorted(
            real_factors.items(),
            key=lambda x: safe_contrib(x[1]),
            reverse=True
        )[:3]

        message += "🎯 **因子**: "
        factor_strs = [
            f"{name}({factor_dict.get('score', 0):+d})"
            for name, factor_dict in sorted_factors
        ]
        message += ", ".join(factor_strs) + "\n\n"

    # Block 5: 止损止盈
    price = _get(r, "price") or _get(r, "last") or 0
    sl_price = _get(r, "stop_loss.stop_price") or 0
    tp_price = _get(r, "take_profit.price") or 0
    rr = _get(r, "take_profit.rr_ratio") or 0

    message += f"""💰 **交易**
入场:{_fmt_price(price)} | 止损:{_fmt_price(sl_price)} | 止盈:{_fmt_price(tp_price)}
RR: 1:{rr:.1f}

"""

    # Block 6: 仓位
    position_mult = _get(r, "position_mult") or 1.0
    message += f"💼 **仓位**: {position_mult:.0%}\n\n"

    # Block 9: 元数据
    from datetime import datetime, timedelta, timezone
    # UTC+8时区（北京时间）
    tz_utc8 = timezone(timedelta(hours=8))
    timestamp = datetime.now(tz_utc8).strftime("%Y-%m-%d %H:%M:%S")
    message += f"━━━━━━━━━━━━━━━━━━━━\n⏰ {timestamp} | 🤖 v6.7"

    return message


def _get_strength_emoji_v67(score: float) -> str:
    """获取强度emoji (v6.7)"""
    if score >= 80:
        return "🔥🔥🔥"
    elif score >= 60:
        return "🔥🔥"
    elif score >= 40:
        return "🔥"
    else:
        return "⚡"


def _get_factor_desc_v67(r: Dict[str, Any], factor_name: str, score: int) -> str:
    """获取因子专业描述 (v6.7)"""
    scores_meta = _get_dict(r, "scores_meta")

    if factor_name == "T":
        Tm = _get(scores_meta, "T.Tm")
        return _desc_trend(score, Tm)
    elif factor_name == "M":
        slope = _get(scores_meta, "M.slope_now")
        return _desc_momentum(score, slope)
    elif factor_name == "C":
        C_meta = scores_meta.get("C", {})
        cvd6 = C_meta.get("cvd6")
        consistency = C_meta.get("consistency")
        is_consistent = C_meta.get("is_consistent")
        side = (_get(r, "side") or "").lower()
        is_long = side in ("long", "buy", "bull", "多", "做多")
        return _desc_cvd_flow(score, is_long, cvd6, consistency, is_consistent)
    elif factor_name == "S":
        theta = _get(scores_meta, "S.theta")
        return _desc_structure(score, theta)
    elif factor_name == "V":
        v5v20 = _get(scores_meta, "V.v5v20")
        return _desc_volume(score, v5v20)
    elif factor_name == "O":
        oi24h_pct = _get(scores_meta, "O.oi24h_pct")
        return _desc_positions(score, oi24h_pct)
    elif factor_name == "L":
        L_meta = scores_meta.get("L", {})
        spread_bps = L_meta.get("spread_bps")
        obi = L_meta.get("obi")
        return _desc_liquidity(score, spread_bps, obi)
    elif factor_name == "B":
        B_meta = scores_meta.get("B", {})
        basis_bps = B_meta.get("basis_bps")
        funding_rate = B_meta.get("funding_rate")
        return _desc_basis_funding(score, basis_bps, funding_rate)
    elif factor_name == "Q":
        lti = _get(scores_meta, "Q.lti")
        return _desc_liquidation(score, lti)
    elif factor_name == "I":
        beta_sum = _get(scores_meta, "I.beta_sum")
        return _desc_independence(score, beta_sum)
    elif factor_name == "F":
        leading_raw = _get(scores_meta, "F.leading_raw")
        return _desc_fund_leading(score, leading_raw)
    else:
        return ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# v7.2 Telegram Message Rendering
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_signal_v72(r: Dict[str, Any], is_watch: bool = False) -> str:
    """
    v7.2信号消息模板（清晰简洁版）

    v7.3.43优化：恢复简洁格式，优化描述文字
    """
    # v7.3.41修复：类型检查，防止v72_enhancements不是字典导致的错误
    if not isinstance(r, dict):
        return f"❌ 错误：信号数据类型异常（期望dict，实际{type(r).__name__}）"

    # ========== 1. 头部：Symbol + 核心指标 ==========
    sym = _get(r, "symbol") or "—"
    price = _get(r, "price") or _get(r, "last")
    price_s = _fmt_price(price)

    # 方向
    side = (_get(r, "side") or "").lower()
    if side in ("long", "buy", "bull", "多", "做多"):
        side_icon = "🟩"
        side_lbl = "做多"
    elif side in ("short", "sell", "bear", "空", "做空"):
        side_icon = "🔴"
        side_lbl = "做空"
    else:
        side_icon = "⚪"
        side_lbl = "中性"

    # v7.2数据（v7.3.41修复：确保v72是字典）
    v72_raw = _get(r, "v72_enhancements")
    if not isinstance(v72_raw, dict):
        v72 = {}
    else:
        v72 = v72_raw
    P_calibrated = _get(v72, "P_calibrated") or _get(r, "probability") or 0.5
    P_pct = int(P_calibrated * 100)
    EV_net = _get(v72, "EV_net") or _get(r, "expected_value") or 0
    TP_pct = _get(r, "tp_pct") or 0.03
    SL_pct = _get(r, "sl_pct") or 0.015
    RR = TP_pct / SL_pct if SL_pct > 0 else 2.0
    ttl_h = int(_ttl_hours(r))

    # v7.3.46改进：从analyze结果直接读取momentum_grading信息（避免重复计算和硬编码）
    momentum_grading = _get(v72, "momentum_grading") or {}
    momentum_level = momentum_grading.get("level", 0)
    momentum_desc = momentum_grading.get("description", "正常模式")
    F_v2 = _get(v72, "F_v2") or 0

    # 构建头部（根据momentum_level显示不同标题，避免硬编码阈值）
    if momentum_level == 3:
        header = f"🚀🚀 极早期蓄势 · 强势机会\n"
    elif momentum_level == 2:
        header = f"🚀 早期蓄势 · 提前布局\n"
    elif momentum_level == 1:
        header = f"🚀 蓄势待发\n"
    else:
        header = f"{'📍 观察信号' if is_watch else '🚀 交易信号'}\n"

    header += f"🔹 {sym} · 现价 {price_s}\n"
    header += f"{side_icon} {side_lbl} 胜率{P_pct}% · 有效期{ttl_h}h\n"
    header += f"期望收益 {EV_net:+.1%} · 盈亏比 {RR:.1f}:1 ✅"

    # ========== 2. 执行参数 ==========
    # v7.3.41修复：确保price不为None
    entry = price if price is not None else 0
    entry_s = _fmt_price(entry)

    if entry > 0:
        if side in ("long", "buy", "bull", "多", "做多"):
            tp_price = entry * (1 + TP_pct)
            sl_price = entry * (1 - SL_pct)
        else:
            tp_price = entry * (1 - TP_pct)
            sl_price = entry * (1 + SL_pct)
    else:
        # price无效时使用占位符
        tp_price = 0
        sl_price = 0

    tp_s = _fmt_price(tp_price)
    sl_s = _fmt_price(sl_price)
    sl_dist = abs(SL_pct * 100)
    tp_dist = abs(TP_pct * 100)

    position_base = _get(r, "position_size") or 0.05
    position_pct = position_base * 100

    params = f"\n\n📍 入场价: {entry_s}\n"
    params += f"🛑 止损: {sl_s} (-{sl_dist:.1f}%)\n"
    params += f"🎯 止盈: {tp_s} (+{tp_dist:.1f}%)\n"
    params += f"\n💼 仓位建议\n"
    params += f"• 基准仓位: {position_pct:.1f}%"

    # ========== 3. v7.3.2-Full核心因子 ==========
    factors = f"\n\n━━━ 🔬 v7.3.2-Full核心因子 ━━━\n"

    # F因子（v7.3.46改进：直接使用momentum_level，避免硬编码阈值）
    F_v2 = _get(v72, "F_v2")
    if F_v2 is not None:
        F_v2_int = int(round(F_v2))

        # v7.3.46: 直接使用momentum_level判断（由analyze_symbol_v72.py计算）
        if momentum_level == 3:  # 极早期蓄势
            F_icon = "🚀🚀"
            F_desc = "强劲资金流入 [极早期蓄势]"
        elif momentum_level == 2:  # 早期蓄势
            F_icon = "🚀"
            F_desc = "偏强资金流入 [早期蓄势]"
        elif momentum_level == 1:  # 蓄势待发
            F_icon = "🔥"
            F_desc = "中等资金流入 [蓄势待发]"
        elif F_v2_int >= 20:
            F_icon = "🟢"
            F_desc = "轻微资金流入"
        elif F_v2_int >= -20:
            F_icon = "🟡"
            F_desc = "资金流平衡"
        elif F_v2_int >= -40:
            F_icon = "🟠"
            F_desc = "轻微资金流出"
        elif F_v2_int >= -60:
            F_icon = "🟠"
            F_desc = "中等资金流出 [追高风险]"
        elif F_v2_int >= -80:
            F_icon = "🔴"
            F_desc = "偏强资金流出 [高风险]"
        else:
            F_icon = "🔴"
            F_desc = "强劲资金流出 [极高风险]"

        factors += f"\n{F_icon} F资金领先  {F_v2_int:3d}  {F_desc}"

    # I因子（v7.3.44优化：通俗描述+丰富emoji）
    I_v2 = _get(v72, "I_v2")
    if I_v2 is not None:
        I_v2_int = int(round(I_v2))

        # 获取Beta值和市场对齐分析
        # v7.3.46修复：确保类型安全，防止字符串导致的.get()错误
        I_meta_raw = _get(v72, "I_meta")
        I_meta = I_meta_raw if isinstance(I_meta_raw, dict) else {}
        beta_btc = I_meta.get("beta_btc", 0)
        beta_eth = I_meta.get("beta_eth", 0)

        # v3.1新增：市场对齐分析
        # v7.3.46修复：确保类型安全
        market_analysis_raw = _get(v72, "independence_market_analysis")
        market_analysis = market_analysis_raw if isinstance(market_analysis_raw, dict) else {}
        market_regime = market_analysis.get("market_regime", 0)
        alignment = market_analysis.get("alignment", "正常")
        confidence_mult = market_analysis.get("confidence_multiplier", 1.0)

        # I因子状态（v7.3.44优化：9级分类，通俗描述）
        if I_v2_int >= 80:
            I_icon = "💎"
            I_desc = "完全独立走势"
        elif I_v2_int >= 60:
            I_icon = "✨"
            I_desc = "强独立走势"
        elif I_v2_int >= 40:
            I_icon = "🟢"
            I_desc = "中度独立"
        elif I_v2_int >= 20:
            I_icon = "🟢"
            I_desc = "轻度独立"
        elif I_v2_int >= -20:
            I_icon = "🟡"
            I_desc = "跟随大盘"
        elif I_v2_int >= -40:
            I_icon = "🟠"
            I_desc = "高度跟随"
        elif I_v2_int >= -60:
            I_icon = "🟠"
            I_desc = "强烈跟随"
        elif I_v2_int >= -80:
            I_icon = "🔴"
            I_desc = "完全跟随"
        else:
            I_icon = "🔴"
            I_desc = "极端跟随"

        # 市场趋势描述
        if market_regime > 30:
            market_trend = "牛市"
            market_icon = "📈"
        elif market_regime < -30:
            market_trend = "熊市"
            market_icon = "📉"
        else:
            market_trend = "震荡"
            market_icon = "↔️"

        # 对齐状态显示
        if alignment == "顺势":
            align_icon = "🎯"
            align_desc = f"顺势({confidence_mult:.1f}x)"
        elif alignment == "逆势":
            align_icon = "⚠️"
            align_desc = "逆势风险"
        else:
            align_icon = ""
            align_desc = ""

        factors += f"\n{I_icon} I市场独立  {I_v2_int:3d}  {I_desc}"
        factors += f"\n   Beta: BTC={beta_btc:.2f} ETH={beta_eth:.2f}"
        factors += f"\n   {market_icon} 大盘{market_trend}({market_regime:+.0f})"
        if align_desc:
            factors += f" {align_icon}{align_desc}"

    # ========== 4. 因子分组详情 ==========
    details = f"\n\n━━━ 📊 因子分组详情 ━━━\n"

    # 获取原始因子
    # v7.3.46修复：确保类型安全，防止字符串导致的.get()错误
    scores_raw = _get(r, "scores")
    scores = scores_raw if isinstance(scores_raw, dict) else {}
    T = _as_int_score(scores.get("T"), 0)
    M = _as_int_score(scores.get("M"), 0)
    C = _as_int_score(scores.get("C"), 0)
    V = _as_int_score(scores.get("V"), 0)
    O = _as_int_score(scores.get("O"), 0)
    B_raw = _as_int_score(scores.get("B"), 0)

    # v7.3.44优化：统一颜色方案（5色）+ 不同区域用不同图形
    # TC组使用方块 ■□，VOM组使用菱形 ◆◇，B组使用三角 ▲△
    def _factor_status_tc(val: int) -> tuple:
        """TC组因子状态（方块图形）"""
        if val >= 60:
            return "🟩", "强劲上涨" if val > 75 else "稳步上涨"
        elif val >= 20:
            return "🟢", "温和上涨"
        elif val >= -20:
            return "🟡", "横盘震荡"
        elif val >= -60:
            return "🟠", "温和下跌"
        else:
            return "🔴", "强劲下跌" if val < -75 else "稳步下跌"

    def _factor_status_vom(val: int) -> tuple:
        """VOM组因子状态（菱形图形）"""
        if val >= 60:
            return "💚", "活跃放量" if val > 75 else "温和放量"
        elif val >= 20:
            return "🟢", "小幅放量"
        elif val >= -20:
            return "🟡", "量能平衡"
        elif val >= -60:
            return "🟠", "小幅缩量"
        else:
            return "🔻", "显著缩量" if val < -75 else "温和缩量"

    def _factor_status_b(val: int) -> tuple:
        """B组因子状态（三角图形）"""
        if val >= 60:
            return "⬆️", "强烈正溢价" if val > 75 else "明显正溢价"
        elif val >= 20:
            return "🟢", "温和正溢价"
        elif val >= -20:
            return "🟡", "溢价平衡"
        elif val >= -60:
            return "🟠", "温和负溢价"
        else:
            return "⬇️", "强烈负溢价" if val < -75 else "明显负溢价"

    # TC组(50%)
    # v7.3.46修复：确保类型安全
    group_scores_raw = _get(v72, "group_scores")
    group_scores = group_scores_raw if isinstance(group_scores_raw, dict) else {}
    TC_score = group_scores.get("TC")
    if TC_score is not None:
        TC_int = int(round(TC_score))
        details += f"\nTC组(50%)  {TC_int:3d}  [趋势+资金流]"

        # T趋势（v7.3.44优化：通俗描述）
        T_icon, T_desc = _factor_status_tc(T)
        details += f"\n  {T_icon} 趋势 T  {T:3d}  {T_desc}"

        # M动量（v7.3.44优化：通俗描述）
        M_icon, M_desc = _factor_status_tc(M)
        details += f"\n  {M_icon} 动量 M  {M:3d}  {M_desc}"

        # C资金（v7.3.44优化：通俗描述）
        C_icon, C_desc = _factor_status_tc(C)
        details += f"\n  {C_icon} 资金 C  {C:3d}  {C_desc}"

    # VOM组(35%)
    VOM_score = group_scores.get("VOM")
    if VOM_score is not None:
        VOM_int = int(round(VOM_score))
        details += f"\n\nVOM组(35%) {VOM_int:3d}  [量能+持仓+动量]"

        # V量能（v7.3.44优化：通俗描述）
        V_icon, V_desc = _factor_status_vom(V)
        details += f"\n  {V_icon} 量能 V  {V:3d}  {V_desc}"

        # O持仓（v7.3.44优化：通俗描述）
        O_icon, O_desc = _factor_status_vom(O)
        details += f"\n  {O_icon} 持仓 O  {O:3d}  {O_desc}"

        # M动量（已在TC组显示，这里可以省略或注释）
        # details += f"\n  {M_icon} 动量 M  {M:3d}  {M_desc}"

    # B组(15%)
    B_score = group_scores.get("B")
    if B_score is not None:
        B_int = int(round(B_score))
        details += f"\n\nB组(15%)   {B_int:3d}  [基差]"

        # B基差（v7.3.44优化：通俗描述）
        B_icon, B_desc = _factor_status_b(B_raw)
        details += f"\n  {B_icon} 基差 B  {B_raw:3d}  {B_desc}"

    # ========== 5. 质量检查（v3.1增强：五道闸门）==========
    quality = f"\n\n━━━ ✅ 质量检查（五道闸门）━━━\n"

    # 获取gate_details（v7.2新格式）
    # v7.3.46修复：确保类型安全
    gate_details_v72_raw = _get(v72, "gates")
    gate_details_v72 = gate_details_v72_raw if isinstance(gate_details_v72_raw, dict) else {}
    gate_details_list = gate_details_v72.get("details", [])

    # 构建gate字典（兼容旧格式）
    # v7.3.47+: 添加类型检查，防止gate_info是字符串
    gates = {}
    for gate_info in gate_details_list:
        # 确保gate_info是字典
        if not isinstance(gate_info, dict):
            continue  # 跳过非字典元素
        gate_num = gate_info.get("gate")
        gates[f"gate{gate_num}"] = gate_info

    # 提取各个闸门
    gate1 = gates.get("gate1", {})
    gate2 = gates.get("gate2", {})
    gate3 = gates.get("gate3", {})
    gate4 = gates.get("gate4", {})
    gate5 = gates.get("gate5", {})  # v3.1新增

    g1_pass = gate1.get("pass", True)
    g2_pass = gate2.get("pass", True)
    g3_pass = gate3.get("pass", True)
    g4_pass = gate4.get("pass", True)
    g5_pass = gate5.get("pass", True)  # v3.1新增

    # 获取数值
    bars = _get(r, "klines") or []
    bars_count = len(bars) if isinstance(bars, list) else 0
    F_dir = gate2.get("value", F_v2 or 0)
    EV_gate = gate3.get("value", EV_net)
    P_gate = gate4.get("value", P_calibrated)
    I_gate = gate5.get("value", I_v2 or 50)  # v3.1新增

    g1_icon = "✅" if g1_pass else "❌"
    g2_icon = "✅" if g2_pass else "❌"
    g3_icon = "✅" if g3_pass else "❌"
    g4_icon = "✅" if g4_pass else "❌"
    g5_icon = "✅" if g5_pass else "❌"  # v3.1新增

    quality += f"\n{g1_icon} Gate1 数据充足 ({bars_count}根K线)"
    quality += f"\n{g2_icon} Gate2 资金支撑 (F={F_dir:.0f})"
    quality += f"\n{g3_icon} Gate3 期望收益 (EV={EV_gate:+.2%})"
    quality += f"\n{g4_icon} Gate4 胜率校准 (P={P_gate:.1%})"
    quality += f"\n{g5_icon} Gate5 市场对齐 (I={I_gate:.0f})"  # v3.1新增

    # ========== 6. 时间戳 + 标签 ==========
    timestamp = _get(r, "timestamp") or 0
    time_str = _format_timestamp(timestamp)

    footer = f"\n\n⏱ {time_str}\n"
    footer += f"🏷 v7.2\n"
    footer += f"\n#trade #{sym}"

    # ========== 组装完整消息 ==========
    message = header + params + factors + details + quality + footer

    return message


def render_watch_v72(r: Dict[str, Any]) -> str:
    """v7.2观察信号"""
    return render_signal_v72(r, is_watch=True)


def render_trade_v72(r: Dict[str, Any]) -> str:
    """v7.2交易信号"""
    return render_signal_v72(r, is_watch=False)


def _format_timestamp(ts: float) -> str:
    """格式化时间戳为UTC+8时间"""
    if not ts:
        return "—"
    try:
        from datetime import datetime, timedelta, timezone
        # 创建UTC+8时区
        tz_utc8 = timezone(timedelta(hours=8))
        # 转换时间戳为UTC+8
        dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=tz_utc8)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "—"