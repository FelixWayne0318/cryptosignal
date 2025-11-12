# coding: utf-8
from __future__ import annotations

"""
完整的单币种分析管道（统一±100系统 v6.6 - 6+4因子架构）：
1. 获取市场数据（K线、OI、订单簿、资金费率）
2. 计算6+4维特征（A层6因子: T/M/C/V/O/B + B层4调制器: L/S/F/I）
3. 统一±100评分（正数=看多/好，负数=看空/差）
4. 计算加权分数和置信度（权重百分比系统，A层总和100%）
5. L/S/F/I调制器：调节仓位/置信度/温度/成本，不参与评分
6. 判定发布条件（软约束系统：EV≤0和P<p_min仅标记，不硬拒绝）

核心架构（v6.6 - 软约束+调制器系统）：
- A层6因子: T/M/C/V/O/B（权重百分比，总和100%）
- B层4调制器: L(流动性)/S(结构)/F(资金领先)/I(独立性)（权重=0，仅调制参数）
- 废弃因子: Q(清算密度-数据不可靠), E(环境-低收益), S移至调制器
- 权重配置: T24/M17/C24/V12/O17/B6 (总和100%)
- 软约束: EV≤0和P<p_min不硬拒绝，仅标记soft_filtered=True
- 三层止损: 结构止损(Swing) > 订单簿聚类 > ATR后备

架构分层（v6.6标准配置）：
- Layer 1（价格行为53%）：T(24%) + M(17%) + V(12%)
- Layer 2（资金流41%）：C(24%) + O(17%)
- Layer 3（微观结构6%）：B(6%)
- Layer B（调制器0%）：L/S/F/I(0%)  ← 不参与评分，仅调制执行参数
"""

from typing import Dict, Any, Tuple, List
from statistics import median

from ats_core.cfg import CFG
from ats_core.config.threshold_config import get_thresholds  # v7.2.3: 配置管理器
from ats_core.sources.binance import get_klines, get_open_interest_hist, get_spot_klines
from ats_core.features.cvd import cvd_from_klines, cvd_mix_with_oi_price
from ats_core.scoring.scorecard import scorecard, get_factor_contributions
from ats_core.scoring.probability import map_probability

# ========== 世界顶级优化模块 ==========
from ats_core.scoring.probability_v2 import (
    map_probability_sigmoid,
    get_adaptive_temperature
)
from ats_core.scoring.adaptive_weights import (
    get_regime_weights,
    blend_weights
)

# ========== v6.6 统一调制器系统 ==========
from ats_core.modulators.modulator_chain import ModulatorChain
from ats_core.modulators.fi_modulators import get_fi_modulator  # v6.7: 统一p_min计算
from ats_core.features.multi_timeframe import multi_timeframe_coherence

# ========== v6.6 三层止损系统 ==========
from ats_core.execution.stop_loss_calculator import ThreeTierStopLoss

# ========== v6.6 因子系统（6因子：T/M/C/V/O/B）==========
# P2.5: 使用价格带法替代固定档位数
from ats_core.features.liquidity_priceband import score_liquidity_priceband as calculate_liquidity
from ats_core.factors_v2.basis_funding import calculate_basis_funding
from ats_core.factors_v2.independence import calculate_independence

# ========== P2.1: 蓄势待发检测增强 ==========
from ats_core.features.accumulation_detection import detect_accumulation_v1, detect_accumulation_v2

# ============ 工具函数 ============

def _get_threshold_by_phase(config, coin_phase: str, key: str, default: Any = None) -> Any:
    """
    根据币种阶段获取对应阈值（统一函数）

    Args:
        config: ThresholdConfig实例
        coin_phase: 币种阶段 (mature/newcoin_ultra/newcoin_phaseA/newcoin_phaseB/等)
        key: 阈值名称
        default: 默认值

    Returns:
        对应阶段的阈值

    Example:
        confidence_min = _get_threshold_by_phase(config, coin_phase, 'confidence_min', 20)
        # coin_phase='mature' → 15
        # coin_phase='newcoin_phaseB' → 60
        # coin_phase='newcoin_phaseA' → 65
        # coin_phase='newcoin_ultra' → 70
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

def _to_f(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _last(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x[-1])
    except Exception:
        return _to_f(x)

def _ema(seq: List[float], n: int) -> List[float]:
    out: List[float] = []
    if not seq or n <= 1: return [_to_f(v) for v in seq]
    k = 2.0/(n+1.0)
    e = None
    for v in seq:
        v = _to_f(v)
        e = v if e is None else (e + k*(v-e))
        out.append(e)
    return out

def _atr(h: List[float], l: List[float], c: List[float], period: int = 14) -> List[float]:
    n = min(len(h), len(l), len(c))
    if n == 0: return []
    tr: List[float] = []
    pc = _to_f(c[0])
    for i in range(n):
        hi = _to_f(h[i]); lo = _to_f(l[i]); ci = _to_f(c[i])
        tr.append(max(hi-lo, abs(hi-pc), abs(lo-pc)))
        pc = ci
    return _ema(tr, period)

def _safe_dict(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}

# ============ 主分析函数 ============

def _analyze_symbol_core(
    symbol: str,
    k1: List,
    k4: List,
    oi_data: List,
    spot_k1: List = None,
    elite_meta: Dict[str, Any] = None,  # 保留参数兼容性，但不再使用
    k15m: List = None,  # MTF优化：15分钟K线
    k1d: List = None,   # MTF优化：1天K线
    orderbook: Dict = None,     # v6.6: 订单簿数据（L - 流动性）
    mark_price: float = None,   # v6.6: 标记价格（B - 基差）
    funding_rate: float = None, # v6.6: 资金费率（B - 基差）
    spot_price: float = None,   # v6.6: 现货价格（B - 基差）
    btc_klines: List = None,    # v6.6: BTC K线（独立性）
    eth_klines: List = None,    # v6.6: ETH K线（独立性）
    kline_cache = None          # v6.6: K线缓存（用于四门DataQual检查）
) -> Dict[str, Any]:
    """
    核心分析逻辑（使用已获取的K线数据）- v6.6

    此函数包含完整的6因子分析逻辑，但不负责获取数据。
    由analyze_symbol()和analyze_symbol_with_preloaded_klines()调用。

    v6.6 因子系统：
    - T (Trend): 趋势因子
    - M (Momentum): 动量因子
    - C (Carry): 持仓成本因子
    - V (Volatility): 波动率因子
    - O (Open Interest): 持仓量因子
    - B (Basis): 基差因子

    Args:
        symbol: 交易对符号
        k1: 1小时K线数据
        k4: 4小时K线数据
        oi_data: OI数据
        spot_k1: 现货K线（可选）
        elite_meta: 已废弃，保留仅为兼容性
        k15m: 15分钟K线（可选，用于MTF）
        k1d: 1天K线（可选，用于MTF）
        orderbook: 订单簿数据（可选，用于流动性分析）
        mark_price: 标记价格（可选，用于基差因子）
        funding_rate: 资金费率（可选，用于基差因子）
        spot_price: 现货价格（可选，用于基差因子）
        btc_klines: BTC K线数据（可选，用于独立性分析）
        eth_klines: ETH K线数据（可选，用于独立性分析）

    Returns:
        分析结果字典
    """
    params = CFG.params or {}

    # v7.2.3: 从配置文件读取阈值（移除硬编码）
    # v7.2.20修复：移除冗余的配置加载（第193行有正确的加载逻辑）
    # 此处不再加载，避免与函数内部的重复导入冲突

    # 移除候选池先验逻辑（已废弃）
    elite_prior = {}
    bayesian_boost = 0.0  # 不再使用贝叶斯先验

    # ---- 新币检测（优先判断，决定数据要求）----
    # 🔧 v6.3.1: 按照 newstandards/NEWCOIN_SPEC.md § 1 规范修改
    new_coin_cfg = params.get("new_coin", {})

    # 计算K线时间戳差值（用于数据受限检测）
    if k1 and len(k1) > 0:
        # K线格式: [timestamp_ms, open, high, low, close, volume, ...]
        first_kline_ts = k1[0][0]  # 第一根K线时间戳（毫秒）
        latest_kline_ts = k1[-1][0]  # 最后一根K线时间戳（毫秒）
        coin_age_ms = latest_kline_ts - first_kline_ts
        coin_age_hours = coin_age_ms / (1000 * 3600)  # 转换为小时
        bars_1h = len(k1)  # K线根数
    else:
        coin_age_hours = 0
        bars_1h = 0

    coin_age_days = coin_age_hours / 24

    # ---- v6.6: DataQual硬门槛检查（唯一硬拒绝）----
    # v7.2.10修复：从配置读取阈值（避免硬编码）
    # v7.2.20修复：使用模块级导入的get_thresholds（第32行），避免重复导入
    config = get_thresholds()
    min_bars_1h = config.config.get('数据质量阈值', {}).get('min_bars_1h', 200)
    data_qual_min = config.config.get('数据质量阈值', {}).get('data_qual_min', 0.90)

    # 计算数据质量分数
    data_qual = min(1.0, bars_1h / min_bars_1h) if bars_1h > 0 else 0.0

    # 硬拒绝：DataQual < data_qual_min
    if data_qual < data_qual_min:
        return {
            "success": False,
            "symbol": symbol,
            "error": f"数据质量不足: DataQual={data_qual:.2f} < {data_qual_min} (bars_1h={bars_1h})",
            "data_qual": data_qual,
            "bars_1h": bars_1h,
            "rejection_type": "hard_gate_dataqual"
        }

    # 🔧 v6.3.1规范符合性修改：按照 NEWCOIN_SPEC.md § 1 标准
    #
    # 规范定义：
    # - 进入新币通道: since_listing < 14d 或 bars_1h < 400 或 !has_OI/funding
    # - 回切标准通道: bars_1h ≥ 400 且 OI/funding连续≥3d，或 since_listing ≥ 14d
    # - 渐变切换: 48h线性混合（权重/温度/门槛/TTL同步过渡）
    #
    # 当前限制（简化实现）：
    # - ⚠️ 无法获取真实since_listing（需集成交易所API）
    # - ⚠️ 使用bars_1h < 400作为主判断条件（符合规范）
    # - ⚠️ coin_age_hours作为辅助（基于K线时间戳差，非真实上币时间）
    # - ⚠️ 暂未实现48h渐变切换（TODO: 需要状态记录机制）
    # - ⚠️ 使用标准1h/4h因子，非新币专用1m/5m/15m因子（需独立新币通道）
    #
    # TODO: 完整新币通道实现需要：
    # 1. 独立pipeline（新币专用因子：T_new/M_new基于ZLEMA_1m/5m）
    # 2. 点火-成势-衰竭模型（非线性联立）
    # 3. 1m/5m/15m数据流（WS实时订阅）
    # 4. 更严执行闸门（impact≤7bps, spread≤35bps, DataQual≥0.90）
    # 5. Prime时间窗口（0-3m冷启动, 3-8m首批, 8-15m主力）

    # 检测数据受限情况
    # 当K线数量接近缓存上限时，无法判断真实币龄，强制视为成熟币
    data_limited = (bars_1h >= 200)  # ≥200根1h K线 ≈ 8.3天，视为数据充足

    # 🔧 规范符合性修改：使用bars_1h < 400作为新币判断标准（NEWCOIN_SPEC.md § 1）
    # 旧阈值（不符合规范）：ultra_new≤24h, phaseA≤7d, phaseB≤30d
    # 新阈值（符合规范）：newcoin < 400 bars (≈16.7天) 或 < 14天
    newcoin_bars_threshold = new_coin_cfg.get("newcoin_bars_threshold", 400)  # 规范值：400根
    newcoin_days_threshold = new_coin_cfg.get("newcoin_days_threshold", 14)   # 规范值：14天

    # 判断是否为新币（按照规范 § 1）
    # v7.2.10修复：从配置读取新币阶段识别阈值（避免硬编码）
    ultra_new_hours = config.config.get('新币阶段识别', {}).get('ultra_new_hours', 24)
    phase_A_hours = config.config.get('新币阶段识别', {}).get('phase_A_hours', 168)
    phase_B_hours = config.config.get('新币阶段识别', {}).get('phase_B_hours', 400)

    if data_limited:
        # 数据受限（≥200根K线），使用coin_age_hours推测币龄并分级
        # 修复：之前强制按mature处理导致bars=300 (12.5天)的币用阈值54（过高）
        # 现在：根据实际币龄使用合理阈值（phaseB用28-40）
        if coin_age_hours < ultra_new_hours:  # 默认 < 24小时
            is_new_coin = True
            coin_phase = "newcoin_ultra(data_limited)"
            is_ultra_new = True
            is_phaseA = False
            is_phaseB = False
        elif coin_age_hours < phase_A_hours:  # 默认 < 168小时（7天）
            is_new_coin = True
            coin_phase = "newcoin_phaseA(data_limited)"
            is_ultra_new = False
            is_phaseA = True
            is_phaseB = False
        elif coin_age_hours < phase_B_hours:  # 默认 < 400小时（16.7天）
            is_new_coin = True
            coin_phase = "newcoin_phaseB(data_limited)"
            is_ultra_new = False
            is_phaseA = False
            is_phaseB = True
        else:
            # 真正的成熟币（>16.7天）
            is_new_coin = False
            coin_phase = "mature(data_limited)"
            is_ultra_new = False
            is_phaseA = False
            is_phaseB = False
    elif bars_1h < newcoin_bars_threshold:
        # 规范条件1: bars_1h < 400 → 新币
        is_new_coin = True
        # 内部细分（用于不同数据要求和阈值）
        if bars_1h < 24:  # < 1天
            coin_phase = "newcoin_ultra"  # 超新币（<24h）
            is_ultra_new = True
            is_phaseA = False
            is_phaseB = False
        elif bars_1h < 168:  # < 7天
            coin_phase = "newcoin_phaseA"  # 新币阶段A（1-7天）
            is_ultra_new = False
            is_phaseA = True
            is_phaseB = False
        else:  # 7天 - 400根（≈16.7天）
            coin_phase = "newcoin_phaseB"  # 新币阶段B（7-16.7天）
            is_ultra_new = False
            is_phaseA = False
            is_phaseB = True
    elif coin_age_days < newcoin_days_threshold:
        # 规范条件2: since_listing < 14d（这里用coin_age_days近似）
        # 注意：这是近似值，真实since_listing需要交易所API
        is_new_coin = True
        coin_phase = "newcoin_phaseB"  # 已有足够K线但仍<14天
        is_ultra_new = False
        is_phaseA = False
        is_phaseB = True
    else:
        # 成熟币：bars_1h ≥ 400 且 since_listing ≥ 14d
        is_new_coin = False
        coin_phase = "mature"
        is_ultra_new = False
        is_phaseA = False
        is_phaseB = False

    # 确定数据要求（coin_phase已在上面设置）
    if is_ultra_new:
        min_data = 10  # 超新币：至少10根1h K线
    elif is_phaseA:
        min_data = 30  # 新币阶段A：至少30根
    elif is_phaseB:
        min_data = 50  # 新币阶段B：至少50根
    else:
        min_data = 50  # 成熟币：至少50根

    # 检查数据是否足够
    if not k1 or len(k1) < min_data:
        return _make_empty_result(symbol, "insufficient_data")

    h = [_to_f(r[2]) for r in k1]
    l = [_to_f(r[3]) for r in k1]
    c = [_to_f(r[4]) for r in k1]
    v = [_to_f(r[5]) for r in k1]  # base volume
    q = [_to_f(r[7]) for r in k1]  # quote volume
    c4 = [_to_f(r[4]) for r in k4] if k4 and len(k4) >= 30 else c

    # 性能监控
    import time
    perf = {}

    # 基础指标
    t0 = time.time()
    ema30 = _ema(c, 30)
    atr_series = _atr(h, l, c, 14)
    atr_now = _last(atr_series)
    close_now = _last(c)
    perf['基础指标'] = time.time() - t0

    # CVD（现货+合约组合，如果有现货数据）
    t0 = time.time()
    cvd_series, cvd_mix = cvd_mix_with_oi_price(k1, oi_data, window=20, spot_klines=spot_k1)
    perf['CVD计算'] = time.time() - t0

    # ---- 2. 计算v6.6因子（6因子 + 4调制器，统一±100系统）----

    # === A层：6个方向因子（参与评分）===

    # 趋势（T）：-100（下跌）到 +100（上涨）
    t0 = time.time()
    T, T_meta = _calc_trend(h, l, c, c4, params.get("trend", {}))
    perf['T趋势'] = time.time() - t0

    # 动量（M）：-100（减速下跌）到 +100（加速上涨）
    t0 = time.time()
    M, M_meta = _calc_momentum(h, l, c, params.get("momentum", {}))
    perf['M动量'] = time.time() - t0

    # CVD资金流（C）：-100（流出）到 +100（流入）
    t0 = time.time()
    C, C_meta = _calc_cvd_flow(cvd_series, c, params.get("cvd_flow", {}), klines=k1)  # v2.5+传入klines用于ADTV_notional归一化
    perf['C资金流'] = time.time() - t0

    # 结构（S）：-100（差）到 +100（好）
    t0 = time.time()
    ctx = {"bigcap": False, "overlay": False, "phaseA": False, "strong": (abs(T) > 75), "m15_ok": False}
    S, S_meta = _calc_structure(h, l, c, _last(ema30), atr_now, params.get("structure", {}), ctx)
    perf['S结构'] = time.time() - t0

    # 量能（V）：-100（缩量）到 +100（放量）
    # v2.0: 传入closes以修复多空对称性
    t0 = time.time()
    V, V_meta = _calc_volume(q, closes=c)
    perf['V量能'] = time.time() - t0

    # 持仓（O）：-100（减少）到 +100（增加）
    t0 = time.time()
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / max(1e-12, abs(close_now)) if len(cvd_series) >= 7 else 0.0
    O, O_meta = _calc_oi(symbol, c, params.get("open_interest", {}), cvd6, oi_data=oi_data)
    perf['O持仓'] = time.time() - t0

    # 基差+资金费（B）：-100（看跌）到 +100（看涨）- 方向维度
    t0 = time.time()
    if mark_price is not None and spot_price is not None and funding_rate is not None:
        try:
            B, B_meta = calculate_basis_funding(
                perp_price=mark_price,
                spot_price=spot_price,
                funding_rate=funding_rate,
                params=params.get("basis_funding", {})
            )
        except Exception as e:
            from ats_core.logging import warn
            warn(f"B因子计算失败: {e}")
            B, B_meta = 0, {"error": str(e)}
    else:
        B, B_meta = 0, {"note": "缺少mark_price/spot_price/funding_rate数据"}
    perf['B基差资金费'] = time.time() - t0

    # v6.6: E环境因子已废弃（不再计算）
    E_meta = {"deprecated": True, "note": "v6.6: 环境因子已废弃"}

    # v6.6: Q因子已完全移除（清算密度数据不可靠且收益低）

    # === B层：4个调制器（不参与评分）===

    # 流动性（L）：-100（差）到 +100（好）
    # v6.2修复：calculate_liquidity已返回标准化后的±100分数，无需再次映射
    t0 = time.time()
    if orderbook is not None:
        try:
            L, L_meta = calculate_liquidity(orderbook, params.get("liquidity", {}))
            # L已经是±100范围，直接使用
        except Exception as e:
            from ats_core.logging import warn
            warn(f"L因子计算失败: {e}")
            L, L_meta = 0, {"error": str(e)}
    else:
        L, L_meta = 0, {"note": "无订单簿数据"}
    perf['L流动性'] = time.time() - t0

    # 结构（S）：-100（差）到 +100（好）
    # v6.6: S因子已在line 323-326计算，此处作为B层调制器使用

    # 独立性（I）：0（完全相关）到 100（完全独立）→ 归一化到 ±100
    # 越独立越好，所以高分=正分，低分=负分
    t0 = time.time()
    if btc_klines and eth_klines and len(c) >= 25:  # 至少需要25个点（默认window=24）
        try:
            # 提取价格数据，确保三个序列长度一致
            # 使用最小长度来避免长度不匹配
            min_len = min(len(c), len(btc_klines), len(eth_klines))
            # 建议使用48小时数据，但至少需要25小时
            use_len = min(min_len, 48) if min_len >= 25 else 0

            if use_len >= 25:
                alt_prices = c[-use_len:]
                btc_prices = [_to_f(k[4]) for k in btc_klines[-use_len:]]  # Close prices
                eth_prices = [_to_f(k[4]) for k in eth_klines[-use_len:]]  # Close prices

                # v6.2修复：calculate_independence已返回标准化后的±100分数
                # (通过StandardizationChain处理，参见independence.py:187-188)
                # 无需再次映射，直接使用
                I_raw, beta_sum, I_meta = calculate_independence(
                    alt_prices=alt_prices,
                    btc_prices=btc_prices,
                    eth_prices=eth_prices,
                    params=params.get("independence", {})
                )

                # v6.6修复：I_raw已经过StandardizationChain输出±100，无需再tanh
                # 之前的tanh(I_raw/50)造成double-tanh bug，将±100压缩到±96
                I = I_raw  # 直接使用StandardizationChain的输出

                # 补充元数据
                I_meta['data_points'] = use_len
                I_meta['note'] = 'v6.6: I_raw直接使用，已移除double-tanh bug'
            else:
                I, I_meta = 0, {"note": f"数据不足（需要25小时，实际{min_len}小时）"}
        except Exception as e:
            from ats_core.logging import warn
            warn(f"I因子计算失败: {e}")
            I, I_meta = 0, {"error": str(e)}
    else:
        I, I_meta = 0, {"note": "缺少BTC/ETH K线数据"}
    perf['I独立性'] = time.time() - t0

    # ---- 2.5. 资金领先性（F调节器）----
    # A1修复：统一使用F_v2（6小时窗口，CVD+OI综合判断）
    # F不参与基础评分，仅用于概率调整和v7.2闸门检查
    t0 = time.time()
    from ats_core.features.fund_leading import score_fund_leading_v2

    F, F_meta = score_fund_leading_v2(
        cvd_series=cvd_series,
        oi_data=oi_data,
        klines=k1,
        atr_now=atr_now,
        params=params.get("fund_leading", {})
    )
    perf['F资金领先'] = time.time() - t0

    # ---- 3. Scorecard（v6.6: 6因子A层 + 4调制器B层）----
    # v6.6架构：L/S/F/I移至B层调制器，不参与方向评分
    # 符合MODULATORS.md § 2.1规范：调制器只调制position/Teff/cost/confidence

    # v6.6基础权重（6因子A层系统：总权重100%）
    # 配置优先级：config/params.json > 硬编码默认值
    base_weights_raw = params.get("weights", {
        # Layer 1: 价格行为层（53%）
        "T": 24.0,  # 趋势（v6.6: +4% from S/Q重分配）
        "M": 17.0,  # 动量（v6.6: +3% from S/Q重分配）
        "V": 12.0,  # 量能（v6.6: +1% from S/Q重分配）
        # Layer 2: 资金流层（41%）
        "C": 24.0,  # CVD资金流（v6.6: +4% from S/Q重分配）
        "O": 17.0,  # OI持仓（v6.6: +3% from S/Q重分配）
        # Layer 3: 微观结构层（6%）
        "B": 6.0,   # 基差+资金费（v6.6: unchanged）
        # B层调制器（不参与评分，权重=0）
        "L": 0.0,   # 流动性调制器（v6.6: moved from A-layer）
        "S": 0.0,   # 结构调制器（v6.6: moved from A-layer）
        "F": 0.0,   # 资金领先调制器（v6.6: already B-layer）
        "I": 0.0,   # 独立性调制器（v6.6: already B-layer）
        # 废弃因子
        "E": 0.0,   # 环境因子（v6.6: deprecated）
    })  # A层6因子总计: 24+17+12+24+17+6 = 100.0 ✓

    # 过滤注释字段（防止传入blend_weights时出现类型错误）
    base_weights = {k: v for k, v in base_weights_raw.items() if not k.startswith('_')}

    # 尝试提前获取市场状态（用于自适应权重）
    try:
        import time
        from ats_core.features.market_regime import calculate_market_regime
        cache_key = f"{int(time.time() // 60)}"
        market_regime_early, _ = calculate_market_regime(cache_key)
    except Exception:
        # 如果获取失败，使用中性值
        market_regime_early = 0

    # 计算当前波动率
    current_volatility = atr_now / close_now if close_now > 0 else 0.02

    # 获取自适应权重
    regime_weights = get_regime_weights(market_regime_early, current_volatility)

    # 平滑混合（70%自适应 + 30%基础）
    weights = blend_weights(regime_weights, base_weights, blend_ratio=0.7)

    # v6.6: 6维方向分数（T/M/C/V/O/B）+ 4维B层调制器（L/S/F/I）
    scores = {
        # A-layer direction factors (6 factors in v6.6)
        "T": T, "M": M, "C": C, "V": V, "O": O, "B": B,
        # v6.6移除: L/S移至B层调制器, Q完全删除, E废弃
    }

    # v2.0合规：因子范围验证（HIGH #2）
    # 所有因子必须在±100范围内（SPEC_DIGEST.md § 1）
    for factor_name, factor_value in scores.items():
        if not (-100 <= factor_value <= 100):
            from ats_core.logging import warn
            warn(f"⚠️  因子{factor_name}超出范围: {factor_value}, 裁剪到±100")
            scores[factor_name] = max(-100, min(100, factor_value))

    # v6.6: B-layer modulation factors (L/S/F/I affect position/Teff/cost/confidence)
    # 调制器不参与评分（权重=0%），仅调整执行参数
    modulation = {
        "L": L,  # Liquidity modulator
        "S": S,  # Structure modulator
        "F": F,  # Funding leading modulator
        "I": I,  # Independence modulator
    }

    # v6.6: 将调制器也加入到scores字典（用于测试和完整性）
    # 注意：调制器在scorecard中权重为0，不影响加权分数
    scores.update(modulation)

    # 计算加权分数（scorecard内部已归一化到±100）
    # 注意：scorecard函数通过 total/weight_sum 自动归一化，无需再除以1.6
    # 注意：scores现在包含L/S/F/I，但它们在weights中权重为0，不影响结果
    weighted_score, confidence, edge = scorecard(scores, weights)

    # 计算每个因子对总分的贡献（用于电报消息显示）
    factor_contributions = get_factor_contributions(scores, weights)

    # 方向判断（根据加权分数符号）
    side_long = (weighted_score > 0)

    # ---- v6.6: 调制器链调用 ----
    # 创建调制器链实例
    modulator_chain = ModulatorChain(params={
        "T0": 2.0,
        "cost_base": 0.0015,
        "L_params": {"min_position": 0.30, "safety_margin": 0.005},
        "S_params": {"confidence_min": 0.70, "confidence_max": 1.30},
        "F_params": {"Teff_min": 0.60, "Teff_max": 1.50},  # v7.2++增强
        "I_params": {"Teff_min": 0.70, "Teff_max": 1.30}   # v7.2++增强
    })

    # 准备L_components（从L_meta提取）
    L_components = {
        "spread_bps": L_meta.get("spread_bps", 10.0),
        "depth_quality": L_meta.get("depth_quality", 50.0),
        "impact_bps": L_meta.get("impact_bps", 5.0),
        "obi": L_meta.get("obi", 0.0)
    }

    # 执行调制器链
    modulator_output = modulator_chain.modulate_all(
        L_score=L,  # L from liquidity.py: [0, 100]
        S_score=S,  # S from structure_sq.py: [-100, +100]
        F_score=F,  # F from fund_leading.py: [-100, +100]
        I_score=I,  # I from independence.py: [-100, +100]
        L_components=L_components,
        confidence_base=confidence,
        symbol=symbol
    )

    # 更新confidence使用调制后的值
    confidence_modulated = modulator_output.confidence_final

    # 元数据
    scores_meta = {
        # 旧因子
        "T": T_meta,
        "M": M_meta,
        "C": C_meta,
        "S": S_meta,
        "V": V_meta,
        "O": O_meta,
        "E": E_meta,
        # 新因子
        "L": L_meta,
        "B": B_meta,
        # v6.6: Q_meta已移除（Q因子完全删除）
        "I": I_meta,
        # 调节器
        "F": F_meta
    }

    # ---- 4. 基础概率计算（🚀 世界顶级优化：Sigmoid映射）----
    prior_up = 0.50  # 中性先验
    quality_score = _calc_quality(scores, len(k1), len(oi_data))

    # v6.3.2新增：新币质量评分补偿
    # 问题：_calc_quality对K线<100的币种惩罚(Q*=0.85)，新币天然数据少被惩罚
    # 解决：给予适度补偿，但仍保留一定惩罚（数据少确实是风险）
    #
    # 补偿策略：
    # - ultra_new: 部分补偿（0.85 → 0.90），仍保留10%惩罚
    # - phaseA: 小幅补偿（0.85 → 0.88），保留12%惩罚
    # - phaseB: 微调补偿（0.85 → 0.87），保留13%惩罚
    # - mature: 无补偿
    if is_new_coin and len(k1) < 100:
        original_quality = quality_score
        # v7.2.10修复：从配置读取质量补偿参数（避免硬编码）
        ultra_new_compensate_from = config.config.get('新币质量补偿', {}).get('ultra_new_compensate_from', 0.85)
        ultra_new_compensate_to = config.config.get('新币质量补偿', {}).get('ultra_new_compensate_to', 0.90)
        if is_ultra_new:
            # 超新币：从0.85补偿到0.90（配置化）
            quality_score = min(1.0, quality_score / ultra_new_compensate_from * ultra_new_compensate_to)
        elif is_phaseA:
            # 阶段A：从0.85补偿到0.88
            quality_score = min(1.0, quality_score / 0.85 * 0.88)
        elif is_phaseB:
            # 阶段B：从0.85补偿到0.87
            quality_score = min(1.0, quality_score / 0.85 * 0.87)
        # 注：补偿不能超过1.0，且仍保留一定惩罚（体现数据少的风险）

    # v6.6: 使用调制器链的Teff（替代get_adaptive_temperature）
    # 调制器已融合了L/S/F/I的温度调整
    temperature = modulator_output.Teff_final

    # 使用Sigmoid概率映射（替代线性映射）
    # v6.6: 使用调制后的temperature和cost
    P_long_base, P_short_base = map_probability_sigmoid(edge, prior_up, quality_score, temperature)
    P_base = P_long_base if side_long else P_short_base

    # 移除贝叶斯先验调整（已废弃候选池机制）

    # ---- 5. 最终概率（v2.0合规：移除F直接调整）----
    # F调制器仅通过Teff/cost调整（在integrated_gates中实现）
    # 不应直接修改概率，避免双重惩罚
    # 符合MODULATORS.md § 2.1规范："F仅调节Teff/cost/thresholds，绝不修改方向分数或概率"
    # v7.2.10修复：从配置读取概率上限（避免硬编码）
    P_long_max = config.config.get('概率计算阈值', {}).get('P_long_max', 0.95)
    P_short_max = config.config.get('概率计算阈值', {}).get('P_short_max', 0.95)
    P_long = min(P_long_max, P_long_base)
    P_short = min(P_short_max, P_short_base)
    P_chosen = P_long if side_long else P_short

    # ---- v6.6: 软约束检查（EV和P门槛）----
    # 获取发布配置
    publish_cfg = params.get("publish", {})

    # 计算EV使用调制后的cost
    # 修复：使用abs(edge)，因为无论做多还是做空，收益都应该是正数
    EV = P_chosen * abs(edge) - (1 - P_chosen) * modulator_output.cost_final

    # 软约束1：EV ≤ 0
    if EV <= 0:
        # 不是硬拒绝，记录为"自然过滤"
        # 返回success=True但publish=False
        pass  # 允许继续，但后续会标记为不发布

    # 软约束2：P < p_min（基于F/I调制器调整）
    # v6.7++修复（2025-11-06）：统一p_min计算到FIModulator
    # 问题：之前使用ModulatorChain.p_min_adj（仅考虑F），现在统一到FIModulator（完整F+I）
    #
    # 归一化F和I到[0, 1]范围（FIModulator需要）
    F_normalized = (F + 100.0) / 200.0  # [-100, 100] → [0, 1]
    I_normalized = (I + 100.0) / 200.0  # [-100, 100] → [0, 1]

    # 使用FIModulator计算完整的p_min（包含F和I双重调制）
    fi_modulator = get_fi_modulator()
    p_min_modulated, delta_p_min, threshold_details = fi_modulator.calculate_thresholds(
        F_raw=F_normalized,
        I_raw=I_normalized,
        symbol=symbol
    )

    # FIModulator公式: p_min = p0 + θF·max(0, gF) + θI·min(0, gI)
    # v7.2.5修复: p0从硬编码0.58改为配置0.45（与prime_prob_min一致）
    # 默认参数: p0=0.45, θF=0.03, θI=-0.02, range=[0.50, 0.75]
    #
    # 为了保持信号量控制，叠加安全边际调整
    safety_margin = modulator_output.L_meta.get("safety_margin", 0.005)
    adjustment = safety_margin / (abs(edge) + 1e-6)
    adjustment = min(adjustment, 0.02)  # 限制最大调整

    # 最终p_min = FIModulator计算值 + 安全边际
    p_min_adjusted = p_min_modulated + adjustment
    # v7.2.10修复：从配置读取p_min调整范围（避免硬编码）
    p_min_range_min = config.config.get('概率计算阈值', {}).get('p_min_range_min', 0.50)
    p_min_range_max = config.config.get('概率计算阈值', {}).get('p_min_range_max', 0.75)
    # 限制在合理范围
    p_min_adjusted = max(p_min_range_min, min(p_min_range_max, p_min_adjusted))

    # 检查P是否低于阈值
    p_below_threshold = P_chosen < p_min_adjusted

    # ---- 6. 发布判定（4级分级标准）----

    # 新币特殊处理：应用分级标准
    # v7.2.6修复：移除所有硬编码，从配置文件读取
    if is_ultra_new:
        # 超新币（1-24小时）：超级谨慎
        prime_prob_min = new_coin_cfg.get("ultra_new_prime_prob_min", 0.70)
        prime_dims_ok_min = new_coin_cfg.get("ultra_new_dims_ok_min", 6)
        prime_dim_threshold = new_coin_cfg.get("ultra_new_prime_dim_threshold", 70)  # v7.2.6修复：从配置读取
        watch_prob_min = new_coin_cfg.get("ultra_new_watch_prob_min", 0.65)  # v7.2.6修复：从配置读取
    elif is_phaseA:
        # 阶段A（1-7天）：极度谨慎
        prime_prob_min = new_coin_cfg.get("phaseA_prime_prob_min", 0.65)
        prime_dims_ok_min = new_coin_cfg.get("phaseA_dims_ok_min", 5)
        # v7.2.7修复：优先从signal_thresholds.json读取，回退到params.json
        prime_dim_threshold = config.get_newcoin_threshold('phaseA', 'prime_dim_threshold', 65) if config else 65
        watch_prob_min = new_coin_cfg.get("phaseA_watch_prob_min", 0.60)  # v7.2.6修复：从配置读取
    elif is_phaseB:
        # 阶段B（7-30天）：谨慎
        prime_prob_min = new_coin_cfg.get("phaseB_prime_prob_min", 0.63)
        prime_dims_ok_min = new_coin_cfg.get("phaseB_dims_ok_min", 4)
        # v7.2.7修复：优先从signal_thresholds.json读取，回退到params.json
        prime_dim_threshold = config.get_newcoin_threshold('phaseB', 'prime_dim_threshold', 65) if config else 65
        watch_prob_min = new_coin_cfg.get("phaseB_watch_prob_min", 0.60)  # v7.2.6修复：从配置读取
    else:
        # 成熟币种：正常标准
        # v7.2.7修复：统一使用signal_thresholds.json，移除params.json依赖
        # 修复前：使用params.json的publish配置（prime_prob_min=0.68）
        # 修复后：使用signal_thresholds.json的mature_coin配置（prime_prob_min=0.45）
        if config:
            prime_prob_min = config.get_mature_threshold('prime_prob_min', 0.45)  # v7.2.7修复
            prime_dims_ok_min = config.get_mature_threshold('dims_ok_min', 3)
            prime_dim_threshold = config.get_mature_threshold('prime_dim_threshold', 50)
            # watch功能已废弃，但保留兼容性
            watch_prob_min = 0.65  # 保持原值，watch信号不再发送
        else:
            # 配置加载失败时使用默认值
            prime_prob_min = 0.45
            prime_dims_ok_min = 3
            prime_dim_threshold = 50
            watch_prob_min = 0.65

    # ---- Prime评分系统（v4.0 - 基于10维因子系统）----
    # 重大改进：使用10维综合评分替代4维独立评分
    #
    # 旧逻辑问题：
    # - 只用了概率(40) + C(20) + V(20) + O(20) = 100分
    # - 新增的L（流动性）和B（基差+资金费）完全没有参与
    # - 导致低流动性或极端资金费的币种仍能获得高分
    #
    # 新逻辑：
    # - 基础强度（60分）= confidence（10维加权分数的绝对值）× 0.6
    # - 概率加成（40分）= 基于P_chosen的额外奖励
    # - 总分 0-100，所有10维因子都参与
    #
    # 目标：prime_strength >= 35 → is_prime (v6.0权重百分比系统)
    # 注：从65调整为35，因为权重从180-base改为100-base（65×100/180≈36）

    # ---- 四门调节：计算部分（v6.6完整集成）----
    # 四门：DataQual / EV / Execution / Probability
    # 这些值将影响Prime强度的最终得分（通过乘法调节）

    # Gate 1: DataQual - 数据质量（基于缓存新鲜度）
    gates_data_qual = 1.0  # 默认值
    if kline_cache is not None:
        try:
            from ats_core.data.quality import DataQualMonitor
            dataqual_monitor = DataQualMonitor()
            can_publish, gates_data_qual, reason = dataqual_monitor.can_publish_prime(
                symbol,
                kline_cache=kline_cache
            )
            # DataQual会在下面影响prime_strength
        except Exception as e:
            from ats_core.logging import warn
            warn(f"DataQual检查失败 ({symbol}): {e}")
            gates_data_qual = 1.0

    # Gate 2: EV - 期望值（基于概率和成本）
    # 修复：使用实际edge而不是假设edge=1.0
    # EV = P * abs(edge) - (1-P) * cost
    # 使用调制器输出的最终成本
    # 负值表示不利，会额外惩罚Prime强度
    gates_ev = P_chosen * abs(edge) - (1 - P_chosen) * modulator_output.cost_final

    # Gate 3: Execution - 执行质量（基于流动性L）
    # L范围-100到+100，映射到execution 0.0-1.0
    # L=0 → execution=0.5（中性）
    # L=100 → execution=1.0（优秀）
    # L=-100 → execution=0.0（极差）
    gates_execution = 0.5 + L / 200.0  # L已在上面计算得到

    # Gate 4: Probability - 概率门（基于P_chosen）
    # P=0.5 → 0（中性）
    # P=0.75 → 0.5（良好）
    # P=1.0 → 1.0（优秀）
    # P<0.5 → 负值（不利）
    gates_probability = 2 * P_chosen - 1

    prime_strength = 0.0

    # 1. 基础强度：基于v6.6综合评分（60分）
    # confidence = abs(weighted_score)，已包含6个核心因子T/M/C/V/O/B
    # 范围：0-100 → 映射到 0-60分
    base_strength = confidence * 0.6
    prime_strength += base_strength

    # 2. 概率加成（40分）- 2025-11-04审计优化：降低阈值从0.60到0.30
    # v7.2.10修复：从配置读取概率加成阈值（避免硬编码）
    P_chosen_bonus_threshold = config.config.get('概率计算阈值', {}).get('P_chosen_bonus_threshold', 0.30)
    # 30%→0分, 60%→40分, >60%截断
    # 原因：熊市时P_chosen普遍在0.32-0.44范围，0.60阈值过高导致无法获得加成
    prob_bonus = 0.0
    if P_chosen >= P_chosen_bonus_threshold:
        prob_bonus = min(40.0, (P_chosen - P_chosen_bonus_threshold) / P_chosen_bonus_threshold * 40.0)
        prime_strength += prob_bonus

    # 3. ✅ 四门调节影响（乘法调节，可降低0-50%）
    # 这是v6.6完整集成的关键：让四门真正影响Prime强度
    gate_multiplier = 1.0

    # DataQual影响（30%权重）
    # DataQual=1.0 → *1.0（无影响）
    # DataQual=0.9 → *0.97（-3%）
    # DataQual=0.8 → *0.94（-6%）
    # DataQual=0.5 → *0.85（-15%）
    gate_multiplier *= (0.7 + 0.3 * gates_data_qual)

    # Execution影响（40%权重）
    # Execution=1.0 → *1.0（无影响）
    # Execution=0.5 → *0.8（-20%）
    # Execution=0.0 → *0.6（-40%）
    gate_multiplier *= (0.6 + 0.4 * gates_execution)

    # EV负值时额外惩罚（最多-30%）
    if gates_ev < 0:
        ev_penalty = max(0.7, 1.0 + gates_ev * 0.3)  # ev=-1 → *0.7
        gate_multiplier *= ev_penalty

    # Probability负值时额外惩罚（最多-20%）
    if gates_probability < 0:
        prob_penalty = max(0.8, 1.0 + gates_probability * 0.2)  # P=0 → *0.8
        gate_multiplier *= prob_penalty

    # 应用四门调节
    prime_strength_before_gates = prime_strength  # 记录调整前的值
    prime_strength *= gate_multiplier

    # 记录各部分得分（用于调试）
    prime_breakdown = {
        'base_strength': round(base_strength, 1),
        'prob_bonus': round(prob_bonus, 1),
        'confidence': confidence,
        'P_chosen': round(P_chosen, 4),
        # v6.6新增：四门调节信息
        'gate_multiplier': round(gate_multiplier, 3),
        'strength_before_gates': round(prime_strength_before_gates, 1),
        'strength_after_gates': round(prime_strength, 1)
    }

    # ---- 🚀 世界顶级优化：多时间框架协同验证（缓存版，零API调用）----
    # 性能优化：使用预加载的K线数据，零API调用
    # 从20-40秒/币种 降至 <0.01秒/币种
    mtf_result = None
    mtf_coherence = 100.0  # 默认值

    try:
        from ats_core.features.multi_timeframe import multi_timeframe_coherence_cached

        # 使用缓存版MTF（零API调用）
        mtf_result = multi_timeframe_coherence_cached(
            symbol=symbol,
            k15m=k15m,  # 预加载的15m K线
            k1h=k1,     # 预加载的1h K线
            k4h=k4,     # 预加载的4h K线
            k1d=k1d,    # 预加载的1d K线
            verbose=False
        )
        mtf_coherence = mtf_result['coherence_score']

        # v7.2.10修复：从配置读取多时间框架一致性阈值（避免硬编码）
        mtf_coherence_min = config.config.get('多维度一致性', {}).get('mtf_coherence_min', 60)
        mtf_coherence_penalty = config.config.get('多维度一致性', {}).get('mtf_coherence_penalty', 0.90)

        # 一致性过滤: <阈值惩罚
        if mtf_coherence < mtf_coherence_min:
            # 时间框架不一致，降低概率和Prime评分
            P_chosen *= 0.85  # 惩罚15%
            prime_strength *= mtf_coherence_penalty  # Prime评分降低（配置化）

            # 更新对应方向的概率
            if side_long:
                P_long = P_chosen
            else:
                P_short = P_chosen
    except Exception as e:
        # MTF验证失败，不影响主流程
        from ats_core.logging import warn
        warn(f"[MTF-Cached] {symbol}: 多时间框架验证失败 - {e}")

    # 计算达标维度数（使用币种特定的阈值）
    dims_ok = sum(1 for s in scores.values() if abs(s) >= prime_dim_threshold)

    # v6.3.2修复：Prime判定应用币种特定阈值
    # 问题：之前所有币种都用固定25分，新币专用阈值(prime_prob_min等)未生效
    # 修复：新币使用更严格的prime_strength阈值，体现高风险需要高确定性
    #
    # 原因分析：
    # - 新币数据少、流动性差、波动大 → 需要更高确定性
    # - 成熟币数据充足、流动性好 → 可以适当放宽
    # - 当前用标准因子（1h/4h）而非新币专用因子（1m/5m）→ 需补偿性提高阈值
    #
    # 阈值设计（基于prime_strength）：
    # - ultra_new: 35分（数据最少，风险最高）
    # - phaseA: 32分（仍然高风险）
    # - phaseB: 28分（过渡阶段）
    # - mature: 25分（标准阈值）
    if is_ultra_new:
        prime_strength_threshold = new_coin_cfg.get("ultra_new_prime_strength_min", 35)
    elif is_phaseA:
        prime_strength_threshold = new_coin_cfg.get("phaseA_prime_strength_min", 32)
    elif is_phaseB:
        prime_strength_threshold = new_coin_cfg.get("phaseB_prime_strength_min", 28)
    else:
        # v7.2.3修复：从配置文件读取，移除硬编码54
        # 基于实际分布：Prime强度中位=36, P75=45, Max=59
        # 阈值35（配置文件默认值）接近中位数，合理
        if config:
            prime_strength_threshold = config.get_mature_threshold('prime_strength_min', 35)
        else:
            prime_strength_threshold = 35  # 配置加载失败时的默认值

    # v6.7新增：蓄势待发检测（F优先通道）
    # P2.1增强：使用detect_accumulation_v2，带veto条件
    # 目标：在价格上涨前捕捉信号，而非等趋势确立后才发现
    # 特征：资金强势流入(C高) + 资金领先价格(F高) + 但趋势未确立(T低)

    # 构建因子字典和元数据（用于accumulation detection）
    accumulation_cfg = params.get("factor_optimization_v2", {}).get("accumulation_detection", {})
    accumulation_version = accumulation_cfg.get("version", "v1")

    factors_dict = {
        "T": T, "M": M, "C": C, "V": V, "O": O, "B": B,
        "F": F, "L": L, "S": S, "I": I
    }

    meta_dict = {
        "T": T_meta, "M": M_meta, "C": C_meta, "V": V_meta,
        "O": O_meta, "B": B_meta, "F": F_meta, "L": L_meta,
        "S": S_meta, "I": I_meta
    }

    # 调用对应版本的检测函数
    try:
        if accumulation_version == "v2":
            is_accumulating, accumulating_reason, adjusted_threshold = detect_accumulation_v2(
                factors_dict, meta_dict, accumulation_cfg.get("v2", {})
            )
        else:
            is_accumulating, accumulating_reason, adjusted_threshold = detect_accumulation_v1(
                factors_dict, meta_dict, accumulation_cfg.get("v1", {})
            )

        # 应用调整后的阈值
        if is_accumulating:
            prime_strength_threshold = adjusted_threshold

    except Exception as e:
        # 降级到原有逻辑（向后兼容）
        from ats_core.logging import warn
        warn(f"蓄势检测失败，使用原有逻辑: {e}")
        is_accumulating = False
        accumulating_reason = ""

        # v7.2.10修复：从配置读取蓄势检测阈值（避免硬编码）
        strong_acc_cfg = config.config.get('蓄势检测阈值', {}).get('strong_accumulation', {})
        moderate_acc_cfg = config.config.get('蓄势检测阈值', {}).get('moderate_accumulation', {})

        F_min_strong = strong_acc_cfg.get('F_min', 90)
        C_min_strong = strong_acc_cfg.get('C_min', 60)
        T_max_strong = strong_acc_cfg.get('T_max', 40)
        strength_threshold_strong = strong_acc_cfg.get('strength_threshold', 35)

        F_min_moderate = moderate_acc_cfg.get('F_min', 85)
        C_min_moderate = moderate_acc_cfg.get('C_min', 70)
        T_max_moderate = moderate_acc_cfg.get('T_max', 30)
        V_max_moderate = moderate_acc_cfg.get('V_max', 0)
        strength_threshold_moderate = moderate_acc_cfg.get('strength_threshold', 38)

        if F >= F_min_strong and C >= C_min_strong and T < T_max_strong:
            # 强烈蓄势特征：资金大量流入，但价格还在横盘/初期
            is_accumulating = True
            accumulating_reason = f"强势蓄势(F≥{F_min_strong}+C≥{C_min_strong}+T<{T_max_strong})"
            prime_strength_threshold = strength_threshold_strong  # 降低阈值，允许早期捕捉
        elif F >= F_min_moderate and C >= C_min_moderate and T < T_max_moderate and V < V_max_moderate:
            # 深度蓄势特征：资金流入 + 量能萎缩（洗盘完成）+ 价格横盘
            is_accumulating = True
            accumulating_reason = f"深度蓄势(F≥{F_min_moderate}+C≥{C_min_moderate}+V<{V_max_moderate}+T<{T_max_moderate})"
            prime_strength_threshold = strength_threshold_moderate  # 稍微提高一点要求（配置化）

    # Prime判定：使用币种特定阈值（可能被蓄势通道降低）+ P值硬约束
    # P2.5+信号过滤：加入P值硬约束，必须P>=p_min_adjusted才能发布
    # P2.5++修复（2025-11-05）：添加更多质量门槛，减少80%信号

    # 质量门槛1：基础概率和Prime强度
    quality_check_1 = (prime_strength >= prime_strength_threshold) and (P_chosen >= p_min_adjusted)

    # 质量门槛2：综合置信度（A层6因子加权）
    # v7.2.3修复：从配置文件读取，移除硬编码
    # v7.2.30修复：使用币种阶段特定阈值（新币使用更严格的阈值）
    confidence_threshold = _get_threshold_by_phase(config, coin_phase, 'confidence_min', 20)

    quality_check_2 = confidence >= confidence_threshold

    # 质量门槛3：四门槛综合质量（gate_multiplier）
    # v7.2.4修复：从配置文件读取，移除硬编码0.84
    # v7.2.30修复：使用币种阶段特定阈值
    gate_multiplier_threshold = _get_threshold_by_phase(config, coin_phase, 'gate_multiplier_min', 0.84)

    quality_check_3 = gate_multiplier >= gate_multiplier_threshold

    # 质量门槛4：edge优势边际
    # v7.2.4修复：从配置文件读取，移除硬编码0.48
    # v7.2.30修复：使用币种阶段特定阈值（新币要求更高edge）
    # 实际数据分布：Edge P75=0.14, 中位=0.07, Max=0.31
    edge_threshold = _get_threshold_by_phase(config, coin_phase, 'edge_min', 0.15)

    quality_check_4 = abs(edge) >= edge_threshold

    # 综合判定：所有质量门槛都要通过
    is_prime = quality_check_1 and quality_check_2 and quality_check_3 and quality_check_4
    is_watch = False  # 不再发布Watch信号

    # v6.3新增：拒绝原因跟踪（专家建议 #5）
    # v6.3.2修复：使用币种特定的prime_strength_threshold
    # P2.5++修复（2025-11-05）：增加新质量门槛的拒绝原因
    # v7.2.4修复：移除硬编码，使用配置文件阈值
    # v7.2.30修复：使用币种阶段特定阈值

    # 获取base_strength_min阈值（用于拒绝原因显示）
    base_strength_threshold = _get_threshold_by_phase(config, coin_phase, 'base_strength_min', 30)

    rejection_reason = []
    if not is_prime:
        # 检查质量门槛1：Prime强度和概率
        if not quality_check_1:
            if prime_strength < prime_strength_threshold:
                rejection_reason.append(f"❌ Prime强度不足({prime_strength:.1f} < {prime_strength_threshold})")
                if base_strength < base_strength_threshold:
                    rejection_reason.append(f"  - 基础强度过低({base_strength:.1f}/60)")
                if confidence < confidence_threshold:
                    rejection_reason.append(f"  - 综合置信度低({confidence:.1f}/{confidence_threshold})")
                if prob_bonus < 10:
                    rejection_reason.append(f"  - 概率加成不足({prob_bonus:.1f}/40, P={P_chosen:.3f})")
            if P_chosen < p_min_adjusted:
                rejection_reason.append(f"❌ 概率过低({P_chosen:.3f} < {p_min_adjusted:.3f})")

        # 检查质量门槛2：综合置信度
        if not quality_check_2:
            rejection_reason.append(f"❌ 置信度不足({confidence:.1f} < {confidence_threshold})")

        # 检查质量门槛3：gate_multiplier
        if not quality_check_3:
            rejection_reason.append(f"❌ 四门槛质量不足(gate_mult={gate_multiplier:.3f} < {gate_multiplier_threshold:.2f})")
            # 详细说明哪些门槛拖后腿
            # v7.2.10修复：从配置读取新币闸门阈值（避免硬编码）
            data_qual_newcoin_min = config.config.get('数据质量阈值', {}).get('data_qual_newcoin_min', 0.95)
            execution_gate_min = config.config.get('执行闸门阈值', {}).get('execution_gate_min', 0.70)

            gates_data_qual = _get(r, "gates.data_qual", 1.0) if 'r' in locals() else 1.0
            gates_execution = 0.5 + L / 200.0 if L else 0.5
            if gates_data_qual < data_qual_newcoin_min:
                rejection_reason.append(f"  - DataQual低({gates_data_qual:.2%} < {data_qual_newcoin_min})")
            if gates_execution < execution_gate_min:
                rejection_reason.append(f"  - 执行质量差({gates_execution:.2f} < {execution_gate_min}, L={L})")

        # 检查质量门槛4：edge
        if not quality_check_4:
            rejection_reason.append(f"❌ Edge不足({abs(edge):.2f} < {edge_threshold:.2f})")
    else:
        rejection_reason = [f"✅ 通过所有质量门槛(P={P_chosen:.3f}, Prime={prime_strength:.1f}, Conf={confidence:.1f}, GM={gate_multiplier:.3f}, Edge={abs(edge):.2f})"]

    # ---- 6. BTC/ETH市场过滤器（方案B - 独立过滤 + 避免双重惩罚）----
    # 计算市场大盘趋势，避免逆势做单
    import time
    cache_key = f"{int(time.time() // 60)}"  # 按分钟缓存

    try:
        from ats_core.features.market_regime import calculate_market_regime, apply_market_filter

        # 计算市场趋势
        market_regime, market_meta = calculate_market_regime(cache_key)

        # 应用市场过滤（逆势惩罚）
        P_chosen_filtered, prime_strength_filtered, market_adjustment_reason = apply_market_filter(
            "long" if side_long else "short",
            P_chosen,
            prime_strength,
            market_regime
        )

        # v6.2：直接应用市场过滤器结果
        # F调节器已移除（v2.0合规），无需担心双重惩罚
        if market_adjustment_reason:
            # 应用市场过滤（奖励或惩罚）
            P_chosen = P_chosen_filtered
            # 更新对应方向的概率
            if side_long:
                P_long = P_chosen
            else:
                P_short = P_chosen

            prime_strength = prime_strength_filtered
            # P2.5+: 重新判定is_prime，加入P值硬约束
            is_prime = (prime_strength >= prime_strength_threshold) and (P_chosen >= p_min_adjusted)

        penalty_reason = market_adjustment_reason

    except Exception as e:
        # 市场过滤器失败时不影响主流程
        market_regime = 0
        market_meta = {"error": str(e), "btc_trend": 0, "eth_trend": 0, "regime_desc": "计算失败"}
        penalty_reason = ""

    # ---- 7. 15分钟微确认 ----
    m15_ok = _check_microconfirm_15m(symbol, side_long, params.get("microconfirm_15m", {}), atr_now)

    # ---- v6.6: 三层止损计算 ----
    # 为所有信号计算止损（不限于Prime）
    stop_loss_calculator = ThreeTierStopLoss(params=params.get("stop_loss", {}))

    direction = "LONG" if side_long else "SHORT"
    stop_loss_result = stop_loss_calculator.calculate_stop_loss(
        direction=direction,
        current_price=close_now,
        highs=h,
        lows=l,
        orderbook=orderbook,
        atr=atr_now
    )

    # 计算止盈（简化版：基于edge和RR比）
    # v6.6: 使用调制后的edge和止损距离计算止盈
    target_rr_ratio = 2.0  # 目标盈亏比2:1
    take_profit_distance = stop_loss_result.distance_pct * target_rr_ratio

    if direction == "LONG":
        take_profit_price = close_now * (1 + take_profit_distance)
    else:
        take_profit_price = close_now * (1 - take_profit_distance)

    # 旧版给价计划（兼容性保留）
    pricing = None
    if is_prime:
        pricing = _calc_pricing(h, l, c, atr_now, params.get("pricing", {}), side_long)

    # ---- v6.6: 详细因子输出日志（用于测试和调试）----
    from ats_core.logging import log as _log
    # 详细输出策略：只对Prime/Watch信号或测试模式显示详细因子分析
    # 环境变量VERBOSE_FACTOR_LOG=1可强制所有币种详细输出（用于测试）
    import os
    force_verbose = os.environ.get('VERBOSE_FACTOR_LOG', '0') == '1'
    _VERBOSE_FACTOR_LOG = force_verbose or is_prime or is_watch
    if _VERBOSE_FACTOR_LOG:
        # 6个核心因子详情
        core_factors = ['T', 'M', 'C', 'V', 'O', 'B']
        factor_details = []
        for f in core_factors:
            val = scores.get(f, 0)
            wt = weights.get(f, 0)  # 使用自适应权重
            contrib = val * wt / 100.0 if wt > 0 else 0
            sign = '+' if val >= 0 else ''
            factor_details.append(f"{f}={sign}{val:.1f}({wt:.0f}%→{sign}{contrib:.1f})")

        # 4个调制器详情
        modulators = ['L', 'S', 'F', 'I']
        mod_details = []
        for m in modulators:
            val = modulation.get(m, 0)
            sign = '+' if val >= 0 else ''
            mod_details.append(f"{m}={sign}{val:.1f}")

        # 软约束检查
        soft_warnings = []
        if EV <= 0:
            soft_warnings.append(f"EV={EV:.4f}≤0")
        if p_below_threshold:
            soft_warnings.append(f"P={P_chosen:.3f}<{p_min_adjusted:.3f}")

        soft_status = "⚠️ " + ", ".join(soft_warnings) if soft_warnings else "✅ 通过"

        # 使用系统日志函数输出到stdout
        _log(f"📊 [{symbol}] v6.6因子详细分析:")
        _log(f"   A层-核心因子(6): {', '.join(factor_details)}")
        _log(f"   B层-调制器(4):   {', '.join(mod_details)}")
        _log(f"   加权总分: {weighted_score:+.2f} | 置信度: {confidence:.1f} | Edge: {edge:+.4f}")
        _log(f"   方向: {'LONG' if side_long else 'SHORT'} | P={P_chosen:.3f} | Prime强度: {prime_strength:.1f}/{prime_strength_threshold:.1f}")
        _log(f"   调制链输出: 仓位倍数={modulator_output.position_mult:.2f}, Teff={modulator_output.Teff_final:.1f}h, Cost={modulator_output.cost_final:.4f}")
        _log(f"   软约束: {soft_status}")
        _log(f"   发布状态: {'🟢 Prime' if is_prime else '🟡 Watch' if is_watch else '⚪ 不发布'}")
        if rejection_reason and not is_prime:
            _log(f"   拒绝原因: {', '.join(rejection_reason)}")

    # ---- 8. 组装结果（统一±100系统）----
    result = {
        "success": True,  # P2.1修复：添加success标识
        "symbol": symbol,
        "price": close_now,
        "ema30": _last(ema30),
        "atr_now": atr_now,

        # 性能分析（用于调试）
        "perf": perf,

        # 10维分数（统一±100，v2.0合规版：F已移除）
        "scores": scores,
        "scores_meta": scores_meta,

        # B-layer调节因子（v2.0新增：F不参与评分，仅用于Teff/cost调节）
        "modulation": modulation,

        # v6.6: 调制器输出（L/S/F/I调制链结果）
        "modulator_output": modulator_output.to_dict(),
        "position_mult": modulator_output.position_mult,  # 仓位倍数 [0.30, 1.00]
        "Teff_final": modulator_output.Teff_final,  # 最终温度（融合后）
        "cost_modulated": modulator_output.cost_final,  # 调制后成本

        # v6.7++: FIModulator阈值计算（统一p_min）
        "fi_thresholds": {
            "p_min_base": threshold_details.get("p_min", 0.0),  # FIModulator基础p_min
            "p_min_adjusted": p_min_adjusted,  # 加上安全边际后的最终p_min
            "delta_p_min": delta_p_min,
            "F_normalized": F_normalized,
            "I_normalized": I_normalized,
            "g_F": threshold_details.get("g_F", 0.0),
            "g_I": threshold_details.get("g_I", 0.0),
            "adj_F": threshold_details.get("adj_F", 0.0),  # F的调整量
            "adj_I": threshold_details.get("adj_I", 0.0),  # I的调整量
            "safety_adjustment": adjustment  # 安全边际调整
        },

        # Scorecard结果（阶段1.4：标记为deprecated，将被v7.2层的因子分组替代）
        "weighted_score": weighted_score,  # -100 到 +100 [DEPRECATED: 使用v7.2层的分组加权]
        "confidence": confidence,  # 0-100（绝对值）[DEPRECATED: 使用v7.2层的confidence_v72]
        "edge": edge,  # -1.0 到 +1.0 [保留：仍然有用]
        "_scorecard_deprecation": "weighted_score/confidence使用基础权重（T24/M17/C24/V12/O17/B6），v7.2层使用分组权重（TC50/VOM35/B15）",

        # 方向
        "side": "long" if side_long else "short",
        "side_long": side_long,

        # 概率（阶段2.3：标记为DEPRECATED，v7.2层使用统计校准概率）
        "P_long": P_long,  # DEPRECATED: 使用v7.2层的P_calibrated
        "P_short": P_short,  # DEPRECATED: 使用v7.2层的P_calibrated
        "probability": P_chosen,  # DEPRECATED: 使用v7.2层的P_calibrated
        "P_base": P_base,  # 基础概率（调整前）[DEPRECATED]
        "_probability_deprecation": "基础层使用sigmoid映射，v7.2层使用统计校准（EmpiricalCalibrator）。生产环境应使用v7.2层的P_calibrated",
        "F_score": F,  # F分数（-100到+100）
        "F_adjustment": 1.0,  # 调整系数（v6.2: F调节器已移除，固定为1.0）
        "prior_up": prior_up,
        "quality_score": quality_score,  # 质量系数（0.6-1.0）

        # 发布（阶段1.2b：标记为deprecated，最终判定应由v7.2层完成）
        "publish": {
            "prime": is_prime,  # DEPRECATED: 使用intermediate_data.diagnostic_result.base_is_prime
            "_deprecated_notice": "publish.prime将由v7.2层统一判定，请使用v7.2增强层的最终判定结果",
            "watch": is_watch,
            "dims_ok": dims_ok,
            "prime_strength": int(prime_strength),  # Prime评分（0-100）
            "prime_strength_threshold": prime_strength_threshold,  # v6.3.2新增：币种特定阈值
            "prime_breakdown": prime_breakdown,  # Prime评分详细分解（v4.0新增）
            "rejection_reason": rejection_reason,  # v6.3新增：拒绝原因跟踪
            "ttl_h": 8,
            # v6.6软约束（不硬拒绝，仅标记）
            # 阶段2.4：标记EV为DEPRECATED，v7.2层使用ATR-based EV计算
            "EV": EV,  # DEPRECATED: 使用v7.2层的EV_net
            "EV_positive": EV > 0,  # DEPRECATED: 使用v7.2层的EV_net > 0
            "_EV_deprecation": "基础层使用P*edge-(1-P)*cost，v7.2层使用ATR-based计算。生产环境应使用v7.2层的EV_net",
            "P_threshold": p_min_adjusted,
            "P_above_threshold": not p_below_threshold,
            "soft_filtered": (EV <= 0) or p_below_threshold,  # DEPRECATED: 使用v7.2层的pass_gates
            "soft_filter_reason": "EV≤0" if EV <= 0 else ("P<p_min" if p_below_threshold else None),
            # v6.7新增：蓄势待发标识
            "is_accumulating": is_accumulating,
            "accumulating_reason": accumulating_reason
        },

        # ===== L1修复：添加中间数据（供v7.2判定层使用）=====
        # 目的：避免v7.2层重复计算CVD、ATR等数据
        # 重构阶段1.2a完成日期：2025-11-09
        # 重构阶段1.2b扩展日期：2025-11-09（添加诊断结果）
        "intermediate_data": {
            # 原始数据（L1修复）
            "cvd_series": cvd_series,  # CVD序列（完整）
            "klines": k1,  # K线数据（供v7.2使用）
            "oi_data": oi_data,  # OI数据（供v7.2使用）
            "atr_now": atr_now,  # 当前ATR
            "close_now": close_now,  # 当前收盘价

            # 质量检查结果（阶段1.2b：详细诊断信息）
            "quality_checks": {
                "check_1_strength_prob": quality_check_1,
                "check_2_confidence": quality_check_2,
                "check_3_gate_multiplier": quality_check_3,
                "check_4_edge": quality_check_4,
                "gate_multiplier": gate_multiplier,
                "edge_value": edge
            },

            # 诊断结果（阶段1.2b：基础层的质量评估，供v7.2层参考）
            # 注意：这不是最终判定，最终判定应在v7.2层完成
            "diagnostic_result": {
                "base_is_prime": is_prime,  # 基础层的prime判定（诊断用）
                "base_prime_strength": prime_strength,
                "base_confidence": confidence,
                "base_probability": P_chosen,
                "base_edge": edge,
                "quality_checks_passed": {
                    "strength_prob": quality_check_1,
                    "confidence": quality_check_2,
                    "gate_multiplier": quality_check_3,
                    "edge": quality_check_4
                },
                "rejection_reason": rejection_reason,
                "deprecation_notice": "基础层的prime判定仅供诊断，最终判定应由v7.2层完成"
            }
        },

        # 新币信息（嵌套格式，匹配scanner读取）
        "new_coin": {
            "is_new": is_new_coin,
            "phase": coin_phase,
            "age_days": round(coin_age_days, 1)
        },
        # 向后兼容（保留旧键名）
        "coin_age_days": round(coin_age_days, 1),
        "coin_age_hours": round(coin_age_hours, 1),  # v6.8: 添加以支持统计分析
        "bars": bars_1h,  # v6.8: 添加以支持统计分析
        "coin_phase": coin_phase,
        "is_new_coin": is_new_coin,

        # 微确认
        "m15_ok": m15_ok,

        # 给价
        "pricing": pricing,

        # v6.6: 三层止损止盈
        "stop_loss": stop_loss_result.to_dict(),
        "take_profit": {
            "price": take_profit_price,
            "distance_pct": take_profit_distance,
            "distance_usdt": take_profit_distance * 1000,
            "method": "rr_based",
            "method_cn": f"盈亏比 (RR={target_rr_ratio:.1f})",
            "rr_ratio": target_rr_ratio
        },

        # CVD
        "cvd_z20": _zscore_last(cvd_series, 20) if cvd_series else 0.0,
        "cvd_mix_abs_per_h": abs(_last(cvd_mix)) if cvd_mix else 0.0,

        # 市场过滤器（BTC/ETH大盘趋势）
        "market_regime": market_regime,
        "market_meta": market_meta,
        "market_penalty": penalty_reason if penalty_reason else None,

        # F调节器否决警告（v6.2: F调节器已移除，固定为None）
        "f_veto_warning": None,

        # v6.6完整版：四门系统（已集成到Prime强度计算）
        # 这些门现在真正影响Prime强度（通过gate_multiplier）
        "gates": {
            # Gate 1: DataQual - 数据质量（基于缓存新鲜度，REST模式）
            # 1.0 = 最新（<30s）, 0.9 = 良好（<3min）, 0.7 = 陈旧（>5min）
            "data_qual": round(gates_data_qual, 3),

            # Gate 2: EV - 期望值（基于概率和成本）
            # EV = P*abs(edge) - (1-P)*cost, 正值=有利，负值=不利
            # 负值会额外惩罚Prime强度（最多-30%）
            "ev_gate": round(gates_ev, 3),

            # Gate 3: Execution - 执行质量（基于流动性L）
            # 0.0-1.0 范围，L=-100→0.0, L=0→0.5, L=100→1.0
            # 影响Prime强度（最多-40%）
            "execution": round(gates_execution, 3),

            # Gate 4: Probability - 概率门（基于P_chosen）
            # -1.0到+1.0范围，P=0.5→0, P=0.75→0.5, P=1.0→1.0
            # 负值会额外惩罚Prime强度（最多-20%）
            "probability": round(gates_probability, 3),

            # v6.6新增：四门综合影响
            "gate_multiplier": round(gate_multiplier, 3),  # Prime强度调节系数（0.6-1.0）
        },

        # 🚀 世界顶级优化模块元数据
        "optimization_meta": {
            # Sigmoid概率映射
            "probability_method": "sigmoid",
            "temperature": temperature,
            "volatility": current_volatility,

            # 自适应权重
            "weights_method": "regime_dependent",
            "base_weights": base_weights,
            "regime_weights": regime_weights,
            "final_weights": weights,
            "blend_ratio": 0.7,

            # 多时间框架
            "mtf_coherence": mtf_coherence,
            "mtf_result": mtf_result,
        },

        # 因子贡献详情（用于电报消息显示）
        "factor_contributions": factor_contributions,
    }

    # 兼容旧版 telegram_fmt.py：将分数直接放在顶层
    # 注意：scores现在包含所有10个因子（T/M/C/V/O/B + L/S/F/I）
    result.update(scores)

    return result


def analyze_symbol(symbol: str) -> Dict[str, Any]:
    """
    完整分析单个交易对（数据获取 + 分析）

    🔧 Phase 2重构（v6.4）：
    - 阶段0: 快速预判是否为新币（数据获取前）
    - 阶段1: 根据预判结果分别获取数据（新币: 1m/5m/15m/1h，成熟币: 1h/4h）
    - 阶段2: 精准判断（基于实际K线数量）
    - 阶段3-4: 因子计算和判定（Phase 3实现新币专用因子）

    此函数负责：
    1. 从API获取K线和OI数据
    2. 调用_analyze_symbol_core()进行分析

    返回：
    - 8维分数（T/M/C/S/V/O/E/F，统一±100系统）
    - scorecard结果（weighted_score/confidence/edge）
    - 概率（P_long/P_short/probability）
    - 发布判定（prime/watch）
    - 给价计划（入场/止损/止盈）
    - 元数据

    统一±100系统：
    - 所有分数：-100（看空/差）到 +100（看多/好）
    - weighted_score > 0 → 看多，< 0 → 看空
    - confidence = abs(weighted_score)

    Args:
        symbol: 交易对符号
    """
    from ats_core.logging import log, warn
    from ats_core.data_feeds import (
        quick_newcoin_check,
        fetch_newcoin_data,
        fetch_standard_data,
    )

    # ---- 阶段0: 快速预判（数据获取前）----
    # 🔧 Phase 2新增：在数据获取前判断是否为新币
    is_new_coin_likely, listing_time_ms, bars_1h_approx = quick_newcoin_check(symbol)

    # ---- 阶段1: 分别获取数据 ----
    newcoin_data = None  # 新币专用数据（k1m/k5m/k15m/avwap）

    if is_new_coin_likely:
        # 新币通道：获取1m/5m/15m/1h数据
        log(f"🔧 Phase 2: {symbol} 预判为新币，使用新币数据流（1m/5m/15m/1h）")
        newcoin_data = fetch_newcoin_data(symbol, listing_time_ms)

        # 从新币数据中提取标准K线（兼容现有_analyze_symbol_core）
        k1 = newcoin_data["k1h"]  # 使用1h K线作为k1
        k4 = get_klines(symbol, "4h", 200)  # 仍需4h K线（Phase 3后可能移除）
        k15m = newcoin_data["k15m"]  # 15m K线（用于MTF）

    else:
        # 成熟币通道：获取1h/4h数据
        log(f"成熟币通道: {symbol} 使用标准数据流（1h/4h）")
        standard_data = fetch_standard_data(symbol)
        k1 = standard_data["k1h"]
        k4 = standard_data["k4h"]
        k15m = None  # 成熟币暂不使用15m数据

    # ---- 继续获取其他数据（通用部分）----
    oi_data = get_open_interest_hist(symbol, "1h", 300)

    # 尝试获取现货K线（用于CVD组合计算）
    # 如果失败（某些币只有合约），cvd_mix_with_oi_price会自动降级到只用合约CVD
    try:
        spot_k1 = get_spot_klines(symbol, "1h", 300)
    except Exception:
        spot_k1 = None

    # v6.6 因子系统：获取L/B/I因子所需数据
    from ats_core.sources.binance import (
        get_orderbook_snapshot,
        get_mark_price,
        get_funding_rate,
        get_spot_price
    )

    # 获取订单簿数据（L因子）
    # 注：后续将实现价格带法（±bps聚合）替代固定档位数
    try:
        orderbook = get_orderbook_snapshot(symbol, limit=100)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取{symbol}订单簿失败: {e}")
        orderbook = None

    # 获取标记价格（B因子）
    try:
        mark_price = get_mark_price(symbol)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取{symbol}标记价格失败: {e}")
        mark_price = None

    # 获取资金费率（B因子）
    try:
        funding_rate = get_funding_rate(symbol)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取{symbol}资金费率失败: {e}")
        funding_rate = None

    # 获取现货价格（B因子）
    try:
        spot_price = get_spot_price(symbol)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取{symbol}现货价格失败: {e}")
        spot_price = None

    # 获取BTC/ETH K线数据（独立性分析）
    # 注意：只需要获取一次，不需要每个币种都获取
    # 但为了保持analyze_symbol()的独立性，这里还是获取
    try:
        btc_klines = get_klines('BTCUSDT', '1h', 48)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取BTC K线失败: {e}")
        btc_klines = []

    try:
        eth_klines = get_klines('ETHUSDT', '1h', 48)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取ETH K线失败: {e}")
        eth_klines = []

    # ---- 2. 调用核心分析函数 ----
    result = _analyze_symbol_core(
        symbol=symbol,
        k1=k1,
        k4=k4,
        oi_data=oi_data,
        spot_k1=spot_k1,
        elite_meta=None,  # 不再使用候选池元数据
        k15m=k15m,                   # 15m K线（新币/MTF）
        orderbook=orderbook,         # L（流动性）
        mark_price=mark_price,       # B（基差+资金费）
        funding_rate=funding_rate,   # B（基差+资金费）
        spot_price=spot_price,       # B（基差+资金费）
        btc_klines=btc_klines,       # 独立性分析
        eth_klines=eth_klines        # 独立性分析
    )

    # ---- 3. 添加新币数据元信息（Phase 2）----
    # 为Phase 3准备：将新币专用数据存储在metadata中
    if newcoin_data:
        if "metadata" not in result:
            result["metadata"] = {}

        result["metadata"]["newcoin_data"] = {
            "is_new_coin": True,
            "listing_time": listing_time_ms,
            "bars_1h": newcoin_data["bars_1h"],
            "avwap": newcoin_data["avwap"],
            "avwap_meta": newcoin_data["avwap_meta"],
            # K线数据量统计
            "k1m_count": len(newcoin_data["k1m"]),
            "k5m_count": len(newcoin_data["k5m"]),
            "k15m_count": len(newcoin_data["k15m"]),
            # Phase 3待实现: T_new/M_new/S_new因子将使用这些数据
            "phase2_note": "新币数据已获取，Phase 3将实现专用因子",
        }
    else:
        if "metadata" not in result:
            result["metadata"] = {}
        result["metadata"]["newcoin_data"] = {
            "is_new_coin": False,
            "phase2_note": "成熟币使用标准数据流",
        }

    return result


# ============ 特征计算辅助函数 ============

def _calc_trend(h, l, c, c4, cfg):
    """趋势打分（±100系统）

    v3.1: 更新以支持新的 score_trend 返回格式 (T, metadata)
    """
    try:
        from ats_core.features.trend import score_trend
        # v3.1: score_trend 现在返回 (T, metadata) 而不是 (T, Tm)
        T, meta = score_trend(h, l, c, c4, cfg)
        return int(T), meta
    except Exception:
        return 0, {"Tm": 0, "slopeATR": 0.0, "emaOrder": 0, "degradation_reason": "calculation_error"}

def _calc_accel(c, cvd_series, cfg):
    """加速度打分（旧版，保留用于兼容）"""
    try:
        from ats_core.features.accel import score_accel
        A, meta = score_accel(c, cvd_series, cfg)
        return int(A), meta
    except Exception:
        return 50, {"dslope30": 0.0, "cvd6": 0.0, "weak_ok": False}

def _calc_momentum(h, l, c, cfg):
    """动量打分（±100系统）"""
    try:
        from ats_core.features.momentum import score_momentum
        M, meta = score_momentum(h, l, c, cfg)
        return int(M), meta
    except Exception as e:
        from ats_core.logging import warn
        warn(f"⚠️  M因子计算异常: {e}")
        return 0, {"slope_now": 0.0, "accel": 0.0, "error": str(e)}

def _calc_cvd_flow(cvd_series, c, cfg, klines=None):
    """
    CVD资金流打分（±100系统）

    Args:
        cvd_series: CVD序列
        c: 收盘价序列
        cfg: 配置参数
        klines: K线数据（v2.5+用于ADTV_notional归一化）
    """
    try:
        from ats_core.features.cvd_flow import score_cvd_flow
        C, meta = score_cvd_flow(cvd_series, c, False, cfg, klines=klines)  # v2.5+传入klines
        return int(C), meta
    except Exception:
        return 0, {"cvd6": 0.0, "cvd_score": 0}

def _calc_structure(h, l, c, ema30_last, atr_now, cfg, ctx):
    """结构打分"""
    try:
        from ats_core.features.structure_sq import score_structure
        S, meta = score_structure(h, l, c, ema30_last, atr_now, cfg, ctx)
        return int(S), meta
    except Exception:
        return 50, {"theta": 0.4, "icr": 0.5, "retr": 0.5}

def _calc_volume(vol, closes=None):
    """量能打分（±100系统，v2.0修复多空对称性）"""
    try:
        from ats_core.features.volume import score_volume
        V, meta = score_volume(vol, closes=closes)
        return int(V), meta
    except Exception as e:
        from ats_core.logging import warn
        warn(f"⚠️  V因子计算异常: {e}")
        return 0, {"v5v20": 1.0, "vroc_abs": 0.0, "error": str(e)}

def _calc_oi(symbol, closes, cfg, cvd6_fallback, oi_data=None):
    """持仓打分（±100系统）"""
    try:
        from ats_core.features.open_interest import score_open_interest
        O, meta = score_open_interest(symbol, closes, cfg, cvd6_fallback, oi_data=oi_data)
        return int(O), meta
    except Exception:
        return 0, {"oi1h_pct": None, "oi24h_pct": None}

def _calc_environment(h, l, c, atr_now, cfg):
    """环境打分（±100系统）"""
    try:
        from ats_core.features.environment import environment_score
        E, meta = environment_score(h, l, c, atr_now, cfg)
        return int(E), meta
    except Exception:
        return 0, {"chop": 50.0, "room": 0.5}

# A1修复：_calc_fund_leading函数已废弃（2025-11-09）
# 原因：基础分析层已统一使用score_fund_leading_v2
# 旧版本使用5个分散参数，新版本直接使用cvd_series/oi_data/klines/atr_now

def _calc_quality(scores: Dict, n_klines: int, n_oi: int) -> float:
    """
    质量系数 Q ∈ [0.6, 1.0]
    考虑：样本完备性、不过度、非拥挤等

    统一±100系统：使用绝对值判断强度
    """
    Q = 1.0

    # v7.2.10修复：从配置读取因子质量检查阈值（避免硬编码）
    # v7.2.20修复：使用模块级导入的get_thresholds（第32行），避免重复导入
    config = get_thresholds()
    factor_quality_cfg = config.config.get('因子质量检查', {})
    n_klines_min = factor_quality_cfg.get('n_klines_min', 100)
    n_oi_min = factor_quality_cfg.get('n_oi_min', 50)
    weak_dim_threshold = factor_quality_cfg.get('weak_dim_threshold', 40)
    weak_dims_max = factor_quality_cfg.get('weak_dims_max', 3)
    quality_penalty = factor_quality_cfg.get('quality_penalty', 0.90)

    # 样本不足
    if n_klines < n_klines_min:
        Q *= 0.85
    if n_oi < n_oi_min:
        Q *= quality_penalty

    # 维度弱证据过多（绝对值<阈值的维度）
    weak_dims = sum(1 for s in scores.values() if abs(s) < weak_dim_threshold)
    if weak_dims >= weak_dims_max:
        Q *= 0.85

    return max(0.6, min(1.0, Q))

def _check_microconfirm_15m(symbol: str, side_long: bool, params: Dict, atr1h: float) -> bool:
    """15分钟微确认"""
    try:
        from ats_core.features.microconfirm_15m import check_microconfirm_15m
        result = check_microconfirm_15m(symbol, side_long, params, atr1h)
        return result.get("ok", False)
    except Exception:
        return False

def _calc_pricing(h, l, c, atr_now, cfg, side_long):
    """给价计划"""
    try:
        from ats_core.features.pricing import price_plan
        return price_plan(h, l, c, atr_now, cfg, side_long)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"pricing计算失败: {e}, cfg={cfg}")
        return None

def _zscore_last(series, window):
    """计算最后一个值的z-score"""
    if not series or len(series) < window:
        return 0.0
    tail = series[-window:]
    med = median(tail)
    mad = median([abs(x - med) for x in tail]) or 1e-9
    return (series[-1] - med) / (1.4826 * mad)

def _make_empty_result(symbol: str, reason: str):
    """数据不足时的空结果（统一±100系统）"""
    return {
        "symbol": symbol,
        "error": reason,
        "scores": {"T": 0, "M": 0, "C": 0, "S": 0, "V": 0, "O": 0, "E": 0},
        "weighted_score": 0,  # -100到+100
        "confidence": 0,  # 0-100
        "edge": 0.0,  # -1.0到+1.0
        "probability": 0.5,
        "publish": {"prime": False, "watch": False, "dims_ok": 0, "ttl_h": 0},
        "side": "neutral",
        "side_long": False,
        "m15_ok": False,
        "pricing": None,
        "P_long": 0.5,
        "P_short": 0.5,
        "F_score": 0
    }


# ============ 批量扫描优化：支持预加载K线 ============

def analyze_symbol_with_preloaded_klines(
    symbol: str,
    k1h: List,
    k4h: List,
    oi_data: List = None,
    spot_k1h: List = None,
    elite_meta: Dict = None,
    k15m: List = None,  # MTF优化：15分钟K线
    k1d: List = None,   # MTF优化：1天K线
    orderbook: Dict = None,     # v6.6: 订单簿数据（L - 流动性）
    mark_price: float = None,   # v6.6: 标记价格（B - 基差）
    funding_rate: float = None, # v6.6: 资金费率（B - 基差）
    spot_price: float = None,   # v6.6: 现货价格（B - 基差）
    btc_klines: List = None,    # v6.6: BTC K线（独立性）
    eth_klines: List = None,    # v6.6: ETH K线（独立性）
    kline_cache = None          # v6.6: K线缓存（用于四门DataQual检查）
) -> Dict[str, Any]:
    """
    使用预加载的K线数据分析币种（用于批量扫描优化）- v6.6

    v6.6 因子系统（6因子）：T/M/C/V/O/B

    Args:
        symbol: 交易对符号
        k1h: 1小时K线数据（300根）
        k4h: 4小时K线数据（200根）
        oi_data: OI数据（可选）
        spot_k1h: 现货1小时K线（可选，用于CVD）
        elite_meta: Elite Universe元数据（可选）
        k15m: 15分钟K线（可选，用于MTF）
        k1d: 1天K线（可选，用于MTF）
        orderbook: 订单簿数据（可选，用于流动性分析）
        mark_price: 标记价格（可选，用于基差因子）
        funding_rate: 资金费率（可选，用于基差因子）
        spot_price: 现货价格（可选，用于基差因子）
        btc_klines: BTC K线数据（可选，用于独立性分析）
        eth_klines: ETH K线数据（可选，用于独立性分析）

    Returns:
        分析结果字典（格式与analyze_symbol相同）

    使用场景:
        批量扫描时从WebSocket缓存读取K线，避免重复API调用

    注意:
        这个函数不会自动获取K线数据，调用者必须提供
    """
    # 使用预加载的数据调用核心分析函数（v6.6）
    # 如果oi_data为None，使用空列表避免NoneType错误
    return _analyze_symbol_core(
        symbol=symbol,
        k1=k1h,
        k4=k4h,
        oi_data=oi_data if oi_data is not None else [],
        spot_k1=spot_k1h,
        elite_meta=elite_meta,
        k15m=k15m,  # 传递15m K线
        k1d=k1d,    # 传递1d K线
        orderbook=orderbook,         # 传递订单簿（L）
        mark_price=mark_price,       # 传递标记价格（B）
        funding_rate=funding_rate,   # 传递资金费率（B）
        spot_price=spot_price,       # 传递现货价格（B）
        btc_klines=btc_klines,       # 传递BTC K线（独立性）
        eth_klines=eth_klines,       # 传递ETH K线（独立性）
        kline_cache=kline_cache      # 传递K线缓存（四门DataQual）
    )
