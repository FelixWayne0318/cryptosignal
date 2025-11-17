# coding: utf-8
"""
S（结构）评分 - 统一±100系统

v3.1 P0修复（2025-11-09）：
- 重新启用StandardizationChain（优化参数：alpha=0.05, lam=3.0）
- 修复zigzag无限循环风险（迭代次数保护）

v3.0配置管理（2025-11-09）：
- 移除硬编码参数，改为从配置文件读取
- 支持向后兼容（params参数优先级高于配置文件）
- 使用统一的数据质量检查阈值
"""
from ats_core.features.ta_core import ema
from ats_core.scoring.scoring_utils import StandardizationChain
from ats_core.config.factor_config import get_factor_config
from typing import Optional
import math

# v3.0: 模块级StandardizationChain实例（延迟初始化）
_structure_chain: Optional[StandardizationChain] = None


def _get_structure_chain() -> StandardizationChain:
    """
    获取StandardizationChain实例（延迟初始化）

    v3.0改进：从配置文件读取参数，而非硬编码
    """
    global _structure_chain

    if _structure_chain is None:
        try:
            config = get_factor_config()
            std_params = config.get_standardization_params("S")

            # 检查是否启用StandardizationChain
            if std_params.get('enabled', True):
                _structure_chain = StandardizationChain(
                    alpha=std_params['alpha'],
                    tau=std_params['tau'],
                    z0=std_params['z0'],
                    zmax=std_params['zmax'],
                    lam=std_params['lam']
                )
            else:
                # 如果配置禁用，使用默认参数创建（向后兼容）
                _structure_chain = StandardizationChain(
                    alpha=0.15, tau=2.0, z0=2.5, zmax=6.0, lam=1.5
                )
        except Exception as e:
            # 配置加载失败时使用默认参数（向后兼容）
            print(f"⚠️ S因子StandardizationChain配置加载失败，使用默认参数: {e}")
            _structure_chain = StandardizationChain(
                alpha=0.15, tau=2.0, z0=2.5, zmax=6.0, lam=1.5
            )

    return _structure_chain

def _theta(base_big, base_small, overlay_add, phaseA_add, strong_sub, is_big, is_overlay, is_phaseA, strong_regime):
    th = (base_big if is_big else base_small)
    if is_overlay: th += overlay_add
    if is_phaseA: th += phaseA_add
    if strong_regime: th -= strong_sub
    return max(0.25, min(0.60, th))

def _zigzag_last(h,l, c, theta_atr):
    """
    ZigZag算法 - 识别关键高低点

    v3.1 P0修复：添加安全保护
    - theta_atr最小值检查（防止过密采样）
    - 最大点数限制（防止内存溢出）
    """
    # v3.1: 安全检查 - theta_atr必须大于极小值
    if theta_atr < 1e-8:
        # theta过小会导致过度采样，返回空结果
        return []

    pts=[("H", h[0], 0),("L", l[0], 0)]
    state="init"; lastp = c[0]

    # v3.1: 最大点数限制（防止异常数据导致过度采样）
    max_points = len(c) * 2  # 理论最大值：每根K线最多2个点

    for i in range(1,len(c)):
        # v3.1: 安全保护 - 检查点数上限
        if len(pts) >= max_points:
            break

        if state in ("init","down"):
            if h[i]-lastp >= theta_atr:
                pts.append(("H",h[i],i)); lastp=h[i]; state="down"
            if lastp - l[i] >= theta_atr:
                pts.append(("L",l[i],i)); lastp=l[i]; state="up"
        elif state=="up":
            if h[i]-lastp >= theta_atr:
                pts.append(("H",h[i],i)); lastp=h[i]; state="down"
            if lastp - l[i] >= theta_atr:
                pts.append(("L",l[i],i)); lastp=l[i]; state="up"

    return pts[-6:] if len(pts)>6 else pts

def score_structure(h,l,c, ema30_last, atr_now, params=None, ctx=None):
    """
    S（结构）评分 - 统一±100系统

    返回：
    - 正分：结构质量好（技术形态完整）
    - 负分：结构质量差（形态混乱）
    - 0：中性

    v3.0改进：
    - params参数可选，从配置文件读取默认参数
    - 传入的params参数优先级高于配置文件（向后兼容）

    v3.1改进（2025-11-09）：
    - 添加数据质量检查（防止崩溃）
    - 统一降级元数据结构
    """
    # v3.0: 从配置文件读取默认参数
    try:
        config = get_factor_config()
        config_params = config.get_factor_params("S")
        min_data_points = config.get_data_quality_threshold("S", "min_data_points")
    except Exception as e:
        # 配置加载失败时使用硬编码默认值（向后兼容）
        print(f"⚠️ S因子配置加载失败，使用默认值: {e}")
        config_params = {
            "theta": {
                "big": 0.45,
                "small": 0.35,
                "overlay_add": 0.05,
                "new_phaseA_add": 0.10,
                "strong_regime_sub": 0.05
            }
        }
        min_data_points = 10  # 至少需要10个数据点用于zigzag计算

    # 合并配置参数：配置文件 < 传入的params（向后兼容）
    p = dict(config_params)
    if isinstance(params, dict):
        p.update(params)

    # ========== v3.1: 数据质量检查（防止崩溃）==========
    if not c or len(c) < min_data_points:
        return 0, {
            "theta": 0.0,
            "icr": 0.0,
            "retr": 0.0,
            "timing": 0.0,
            "not_over": False,
            "m15_ok": False,
            "penalty": 0.0,
            "interpretation": "数据不足",
            "degradation_reason": "insufficient_data",  # v3.1: 统一字段名
            "min_data_required": min_data_points
        }

    # 检查h、l、c长度一致性
    if len(h) != len(c) or len(l) != len(c):
        return 0, {
            "theta": 0.0,
            "icr": 0.0,
            "retr": 0.0,
            "timing": 0.0,
            "not_over": False,
            "m15_ok": False,
            "penalty": 0.0,
            "interpretation": "数据不一致",
            "degradation_reason": "inconsistent_data_length",  # v3.1: 新增降级原因
            "min_data_required": min_data_points
        }

    # 确保ctx不为None
    if ctx is None:
        ctx = {}

    # theta
    th = _theta(
        p["theta"]["big"], p["theta"]["small"],
        p["theta"]["overlay_add"], p["theta"]["new_phaseA_add"],
        p["theta"]["strong_regime_sub"],
        ctx.get("bigcap",False), ctx.get("overlay",False), ctx.get("phaseA",False), ctx.get("strong",False)
    )
    theta_abs = th*atr_now
    zz = _zigzag_last(h,l,c, theta_abs)

    # sub-scores
    cons=0.5
    if len(zz)>=4:
        kinds=[k for k,_,_ in zz[-4:]]
        if kinds.count("H")>=2 or kinds.count("L")>=2: cons=0.8

    icr=0.5
    if len(zz)>=3:
        a=abs(zz[-1][1]-zz[-2][1]); b=abs(zz[-2][1]-zz[-3][1])
        if b>1e-12: icr = max(0.0, min(1.0, a/b))

    retr=0.5
    if len(zz)>=3:
        rng=abs(zz[-2][1]-zz[-3][1]); ret=abs(zz[-1][1]-zz[-2][1])
        d = abs((ret/max(1e-12,rng))-0.5)
        retr = max(0.0, 1.0 - d/0.12)

    timing=0.5
    if len(zz)>=3:
        dt = zz[-1][2]-zz[-2][2]
        if dt<=0: timing=0.3
        elif dt<4: timing = 0.6
        elif dt<=12: timing = 1.0
        else: timing = max(0.3, 1.2 - dt/12.0)

    over = abs(c[-1]-ema30_last)/max(1e-12, atr_now)
    not_over = 1.0 if over<=0.8 else 0.5

    m15_ok = 1.0 if ctx.get("m15_ok", False) else 0.0

    penalty = 0.0 if over<=0.8 else 0.1

    # 聚合得分（0-1）
    score_raw = max(0.0, min(1.0, 0.22*cons + 0.18*icr + 0.18*retr + 0.14*timing + 0.20*not_over + 0.08*m15_ok - penalty))

    # 转换为中心化值（0.5=中性 → 0，1.0=完美 → +100，0.0=极差 → -100）
    S_raw = (score_raw - 0.5) * 200

    # v2.0合规：应用StandardizationChain（5步稳健化）
    # 输入S_raw，输出标准化后的S_pub（稳健压缩到±100）
    # v3.1: 重新启用StandardizationChain（优化参数：alpha=0.05, lam=3.0）
    chain = _get_structure_chain()
    S_pub, diagnostics = chain.standardize(S_raw)

    # 转换为整数
    S = int(round(S_pub))

    # 解释
    if S >= 40:
        interpretation = "结构完整"
    elif S >= 10:
        interpretation = "结构良好"
    elif S >= -10:
        interpretation = "结构一般"
    elif S >= -40:
        interpretation = "结构较差"
    else:
        interpretation = "结构混乱"

    # v7.4: 导出ZigZag点（用于四步系统Step3风险管理）
    zigzag_points = []
    for kind, price, dt in zz:
        zigzag_points.append({
            "type": kind,           # "H" (高点) or "L" (低点)
            "price": float(price),  # ZigZag点的价格
            "dt": int(dt)           # ZigZag点的时间位置（从0开始）
        })

    return S, {
        "theta":th,
        "icr":icr,
        "retr":retr,
        "timing":timing,
        "not_over":(over<=0.8),
        "m15_ok":bool(ctx.get("m15_ok",False)),
        "penalty":penalty,
        "interpretation": interpretation,
        "zigzag_points": zigzag_points  # v7.4新增：支撑/阻力位识别
    }
