# coding: utf-8
"""
analyze_symbol_v3.py - 统一因子系统 v3.0（10+1维有机整合）

架构：
┌─────────────────────────────────────────────────────────┐
│           10+1维因子体系（世界顶级架构）                  │
├─────────────────────────────────────────────────────────┤
│ Layer 1: 价格行为层 (65分)                              │
│   - T: Trend (25)                                       │
│   - M: Momentum (15)                                    │
│   - S: Structure (10)                                   │
│   - V+: Volume+Trigger (15)                            │
├─────────────────────────────────────────────────────────┤
│ Layer 2: 资金流层 (40分)                                │
│   - C+: Enhanced CVD (20)                              │
│   - O+: OI Regime (20)                                 │
│   - F: Fund Leading (调节器)                            │
├─────────────────────────────────────────────────────────┤
│ Layer 3: 微观结构层 (45分)                              │
│   - L: Liquidity (20) ⭐⭐⭐⭐⭐                      │
│   - B: Basis+Funding (15) ⭐⭐⭐⭐                   │
│   - Q: Liquidation (10) ⭐⭐⭐⭐                     │
├─────────────────────────────────────────────────────────┤
│ Layer 4: 市场环境层 (10分)                              │
│   - I: Independence (10) ⭐⭐⭐⭐                    │
├─────────────────────────────────────────────────────────┤
│ 总权重: 160分 → 归一化到±100                            │
└─────────────────────────────────────────────────────────┘

作者: Claude (世界顶级量化架构师)
日期: 2025-10-27
版本: 3.0.0
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import json
import time
import statistics

# ========== 核心依赖 ==========
from ats_core.cfg import CFG
from ats_core.sources.binance import (
    get_klines,
    get_open_interest_hist,
    get_spot_klines,
    get_orderbook_snapshot,
    get_mark_price,
    get_funding_rate,
    get_liquidations
)

# ========== 旧因子（保留T/M） ==========
from ats_core.features.trend import score_trend
from ats_core.features.momentum import score_momentum

# ========== 新因子系统 v2（已启用） ==========
from ats_core.factors_v2 import (
    calculate_oi_regime,
    calculate_volume_trigger,
    calculate_liquidity,
    calculate_basis_funding,
    calculate_liquidation,
    calculate_independence,
    calculate_cvd_enhanced
)

# ========== 评分系统 ==========
from ats_core.scoring.probability_v2 import (
    map_probability_sigmoid,
    get_adaptive_temperature
)

# ========== 工具函数 ==========
from ats_core.logging import log, warn, error


def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except:
        return 0.0


def _last(x):
    """安全获取最后一个元素"""
    return x[-1] if x and len(x) > 0 else None


def _safe_dict(obj) -> Dict:
    """确保返回字典"""
    return obj if isinstance(obj, dict) else {}


# ========== 核心分析函数 ==========

def analyze_symbol_v3(symbol: str) -> Dict[str, Any]:
    """
    统一因子系统 v3.0 - 完整分析单个交易对
    
    10+1维因子体系：
    - Layer 1 (价格行为): T, M, S, V+
    - Layer 2 (资金流): C+, O+, F
    - Layer 3 (微观结构): L, B, Q
    - Layer 4 (市场环境): I
    
    Args:
        symbol: 交易对符号
        
    Returns:
        完整分析结果字典
    """
    start_time = time.time()
    
    # ========== 1. 加载配置 ==========
    try:
        with open('config/factors_unified.json', 'r') as f:
            unified_config = json.load(f)
    except Exception as e:
        warn(f"加载统一配置失败: {e}，使用默认配置")
        unified_config = _get_default_config()
    
    factors_config = unified_config.get('factors', {})
    thresholds = unified_config.get('thresholds', {})
    
    # ========== 2. 获取数据 ==========
    try:
        k1 = get_klines(symbol, "1h", 300)
        k4 = get_klines(symbol, "4h", 200)
        oi_hist = get_open_interest_hist(symbol, "1h", 300)
        
        # 可选：现货K线
        try:
            spot_k1 = get_spot_klines(symbol, "1h", 300)
        except:
            spot_k1 = None
            
    except Exception as e:
        error(f"{symbol} 数据获取失败: {e}")
        return {
            'symbol': symbol,
            'error': str(e),
            'timestamp': int(time.time())
        }
    
    # 数据验证
    if not k1 or len(k1) < 50:
        return {'symbol': symbol, 'error': 'insufficient 1h data'}
    if not k4 or len(k4) < 30:
        k4 = k1  # 降级使用1h数据
    if not oi_hist or len(oi_hist) < 50:
        return {'symbol': symbol, 'error': 'insufficient OI data'}
    
    # 提取价格序列
    close_1h = [_to_f(k[4]) for k in k1]
    close_4h = [_to_f(k[4]) for k in k4]
    oi_values = [_to_f(x.get('sumOpenInterest', 0)) for x in oi_hist]
    
    # ========== 3. Layer 1: 价格行为层 (65分) ==========
    scores = {}
    metadata = {}
    
    # T: Trend (25分)
    if factors_config.get('T', {}).get('enabled', True):
        try:
            T_score = score_trend(k1, k4)
            scores['T'] = T_score
            metadata['T'] = {'score': T_score, 'weight': 25}
        except Exception as e:
            warn(f"T因子计算失败: {e}")
            scores['T'] = 0

    # M: Momentum (15分)
    if factors_config.get('M', {}).get('enabled', True):
        try:
            M_score = score_momentum(k1)
            scores['M'] = M_score
            metadata['M'] = {'score': M_score, 'weight': 15}
        except Exception as e:
            warn(f"M因子计算失败: {e}")
            scores['M'] = 0

    # S: Structure (10分) - 暂时使用简化版
    scores['S'] = 50  # 默认中性
    metadata['S'] = {'status': 'simplified', 'weight': 10}

    # V+: Volume+Trigger (15分) - 增强版
    if factors_config.get('V+', {}).get('enabled', True):
        try:
            v_result = calculate_volume_trigger(k1, factors_config.get('V+', {}))
            scores['V+'] = v_result['score']
            metadata['V+'] = {
                'score': v_result['score'],
                'trigger_detected': v_result.get('trigger_detected', False),
                'trigger_strength': v_result.get('trigger_strength', 0),
                'weight': 15
            }
        except Exception as e:
            warn(f"V+因子计算失败: {e}")
            scores['V+'] = 50
    else:
        scores['V+'] = 50
    
    # ========== 4. Layer 2: 资金流层 (40分) ==========

    # C+: Enhanced CVD (20分) - 增强版
    if factors_config.get('C+', {}).get('enabled', True):
        try:
            c_result = calculate_cvd_enhanced(k1, spot_k1, factors_config.get('C+', {}))
            scores['C+'] = c_result['score']
            metadata['C+'] = {
                'score': c_result['score'],
                'cvd_signal': c_result.get('cvd_signal', 0),
                'flow_pressure': c_result.get('flow_pressure', 0),
                'weight': 20
            }
        except Exception as e:
            warn(f"C+因子计算失败: {e}")
            scores['C+'] = 0
    else:
        scores['C+'] = 0

    # O+: OI Regime (20分) - 增强版（四象限）
    if factors_config.get('O+', {}).get('enabled', True):
        try:
            o_result = calculate_oi_regime(oi_hist, k1, factors_config.get('O+', {}))
            scores['O+'] = o_result['score']
            metadata['O+'] = {
                'score': o_result['score'],
                'regime': o_result.get('regime', 'unknown'),
                'oi_change': o_result.get('oi_change_pct', 0),
                'weight': 20
            }
        except Exception as e:
            warn(f"O+因子计算失败: {e}")
            scores['O+'] = 0
    else:
        scores['O+'] = 0
    
    # ========== 5. Layer 3: 微观结构层 (45分) ==========

    # L: Liquidity (20分) ⭐⭐⭐⭐⭐
    if factors_config.get('L', {}).get('enabled', True):
        try:
            orderbook = get_orderbook_snapshot(symbol, limit=50)
            l_result = calculate_liquidity(orderbook, k1, factors_config.get('L', {}))
            scores['L'] = l_result['score']
            metadata['L'] = {
                'score': l_result['score'],
                'spread_bps': l_result.get('spread_bps', 0),
                'depth_score': l_result.get('depth_score', 0),
                'impact_score': l_result.get('impact_score', 0),
                'weight': 20
            }
        except Exception as e:
            warn(f"L因子计算失败: {e}")
            scores['L'] = 70  # 默认良好流动性
            metadata['L'] = {'status': 'error', 'error': str(e), 'weight': 20}
    else:
        scores['L'] = 70

    # B: Basis+Funding (15分) ⭐⭐⭐⭐
    if factors_config.get('B', {}).get('enabled', True):
        try:
            mark_price = get_mark_price(symbol)
            funding_rate = get_funding_rate(symbol)
            b_result = calculate_basis_funding(
                spot_k1 if spot_k1 else k1,
                k1,
                mark_price,
                funding_rate,
                factors_config.get('B', {})
            )
            scores['B'] = b_result['score']
            metadata['B'] = {
                'score': b_result['score'],
                'basis_bps': b_result.get('basis_bps', 0),
                'funding_rate': b_result.get('funding_rate', 0),
                'sentiment': b_result.get('sentiment', 'neutral'),
                'weight': 15
            }
        except Exception as e:
            warn(f"B因子计算失败: {e}")
            scores['B'] = 0  # 中性
            metadata['B'] = {'status': 'error', 'error': str(e), 'weight': 15}
    else:
        scores['B'] = 0

    # Q: Liquidation (10分) ⭐⭐⭐⭐
    if factors_config.get('Q', {}).get('enabled', True):
        try:
            liquidations = get_liquidations(symbol, interval='1h', limit=200)
            q_result = calculate_liquidation(liquidations, k1, factors_config.get('Q', {}))
            scores['Q'] = q_result['score']
            metadata['Q'] = {
                'score': q_result['score'],
                'long_liq_ratio': q_result.get('long_liq_ratio', 0.5),
                'short_liq_ratio': q_result.get('short_liq_ratio', 0.5),
                'liq_pressure': q_result.get('liq_pressure', 0),
                'weight': 10
            }
        except Exception as e:
            warn(f"Q因子计算失败: {e}")
            scores['Q'] = 0  # 中性
            metadata['Q'] = {'status': 'error', 'error': str(e), 'weight': 10}
    else:
        scores['Q'] = 0
    
    # ========== 6. Layer 4: 市场环境层 (10分) ==========

    # I: Independence (10分) - 独立性评估
    if factors_config.get('I', {}).get('enabled', True):
        try:
            # 获取BTC和ETH的K线作为市场基准
            btc_k1 = get_klines('BTCUSDT', '1h', 200)
            eth_k1 = get_klines('ETHUSDT', '1h', 200)
            i_result = calculate_independence(k1, btc_k1, eth_k1, factors_config.get('I', {}))
            scores['I'] = i_result['score']
            metadata['I'] = {
                'score': i_result['score'],
                'btc_beta': i_result.get('btc_beta', 1.0),
                'eth_beta': i_result.get('eth_beta', 1.0),
                'independence_level': i_result.get('independence_level', 'normal'),
                'weight': 10
            }
        except Exception as e:
            warn(f"I因子计算失败: {e}")
            scores['I'] = 50  # 默认中性
            metadata['I'] = {'status': 'error', 'error': str(e), 'weight': 10}
    else:
        scores['I'] = 50
    
    # ========== 7. 加权计算 ==========
    
    weights = {
        'T': 25, 'M': 15, 'S': 10, 'V+': 15,
        'C+': 20, 'O+': 20,
        'L': 20, 'B': 15, 'Q': 10,
        'I': 10
    }
    
    weighted_sum = 0.0
    total_weight = 0.0
    
    for factor, score in scores.items():
        if factor in weights:
            w = weights[factor]
            weighted_sum += score * w / 100.0  # 归一化
            total_weight += w
    
    # 归一化到±100
    edge = weighted_sum / 1.6  # 总权重160 / 100 = 1.6
    confidence = abs(edge)
    side_long = edge > 0
    
    # ========== 8. F调节器 (概率调整) ==========
    
    C_score = scores.get('C+', 0)
    F_aligned = C_score if side_long else -C_score
    
    # F调节系数
    if abs(F_aligned) >= 70:
        F_adjustment = 1.15
    elif abs(F_aligned) >= 50:
        F_adjustment = 1.00
    elif abs(F_aligned) >= 30:
        F_adjustment = 0.90
    else:
        F_adjustment = 0.70
    
    # ========== 9. Sigmoid概率映射 ==========
    
    prior_up = 0.5
    Q = 1.0
    temperature = 40.0
    
    P_long_base, P_short_base = map_probability_sigmoid(edge, prior_up, Q, temperature)
    P_base = P_long_base if side_long else P_short_base
    
    # F调节
    P_final = min(0.90, P_base * F_adjustment)
    
    # ========== 10. Prime评分 ==========
    
    # 概率得分
    prob_score = min(40, P_final * 40)
    
    # CVD得分
    cvd_score = min(20, abs(C_score) / 100.0 * 20)
    
    # 量能得分
    vol_score = min(20, abs(scores.get('V+', 0)) / 100.0 * 20)
    
    # 持仓得分
    oi_score = min(20, abs(scores.get('O+', 0)) / 100.0 * 20)
    
    prime_strength = prob_score + cvd_score + vol_score + oi_score
    
    # ========== 11. 发布过滤 ==========
    
    filters = thresholds.get('filters', {})
    
    # 基础判定
    is_prime = (
        prime_strength >= thresholds.get('prime_strength_min', 78) and
        P_final >= thresholds.get('prime_prob_min', 0.62)
    )
    
    is_watch = prime_strength >= thresholds.get('watch_strength_min', 65)
    
    # 流动性过滤
    L_score = scores.get('L', 0)
    if L_score < filters.get('liquidity_min', 60):
        is_prime = False
        metadata['filter_reason'] = f'low_liquidity_{L_score}'
    
    # 基差极值过滤
    B_meta = metadata.get('B', {})
    basis_bps = abs(B_meta.get('basis_bps', 0))
    if basis_bps > filters.get('basis_extreme_bps', 100):
        is_prime = False
        metadata['filter_reason'] = f'extreme_basis_{basis_bps:.0f}bp'
    
    # 资金费极值调整
    funding_rate = abs(B_meta.get('funding_rate', 0))
    if funding_rate > filters.get('funding_extreme_rate', 0.002):
        P_final *= 0.85
        prime_strength *= 0.9
    
    # ========== 12. 风险管理参数 ==========
    
    current_price = close_1h[-1]
    atr = _calculate_atr(k1)
    
    # 动态止损（基于流动性）
    if L_score < 60:
        sl_mult = 2.5
    elif L_score < 80:
        sl_mult = 2.0
    else:
        sl_mult = 1.8
    
    if side_long:
        stop_loss = current_price - atr * sl_mult
        take_profit_1 = current_price + atr * 2.5
    else:
        stop_loss = current_price + atr * sl_mult
        take_profit_1 = current_price - atr * 2.5
    
    # ========== 13. 返回结果 ==========
    
    elapsed = time.time() - start_time
    
    return {
        'symbol': symbol,
        'timestamp': int(time.time()),
        'version': '3.0.0',
        'elapsed_ms': round(elapsed * 1000, 2),
        
        # 因子分数
        'scores': scores,
        'metadata': metadata,
        
        # 加权结果
        'weighted_sum': round(weighted_sum, 2),
        'edge': round(edge, 2),
        'confidence': round(confidence, 2),
        
        # 方向和概率
        'side': 'LONG' if side_long else 'SHORT',
        'side_long': side_long,
        'probability': round(P_final, 4),
        'P_long': round(P_long_base, 4),
        'P_short': round(P_short_base, 4),
        
        # F调节器
        'F_adjustment': round(F_adjustment, 2),
        'F_score': round(F_aligned, 2),
        
        # Prime评分
        'prime_strength': round(prime_strength, 1),
        'prime_breakdown': {
            'prob': round(prob_score, 1),
            'cvd': round(cvd_score, 1),
            'vol': round(vol_score, 1),
            'oi': round(oi_score, 1)
        },
        
        # 发布
        'publish': {
            'prime': is_prime,
            'watch': is_watch
        },
        
        # 风险管理
        'risk': {
            'entry': round(current_price, 8),
            'stop_loss': round(stop_loss, 8),
            'take_profit_1': round(take_profit_1, 8),
            'take_profit_2': round(take_profit_1 * 1.5, 8) if side_long else round(take_profit_1 * 0.5, 8),
            'atr': round(atr, 8),
            'sl_multiplier': sl_mult
        }
    }


def _calculate_atr(klines: List, period: int = 14) -> float:
    """计算ATR"""
    if len(klines) < period + 1:
        return 0.0
    
    trs = []
    for i in range(1, len(klines)):
        h = _to_f(klines[i][2])
        l = _to_f(klines[i][3])
        c_prev = _to_f(klines[i-1][4])
        
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    
    if len(trs) < period:
        return 0.0
    
    return statistics.mean(trs[-period:])


def _get_default_config() -> Dict:
    """默认配置（如果文件加载失败）"""
    return {
        'factors': {
            'T': {'enabled': True, 'params': {}},
            'M': {'enabled': True, 'params': {}},
            'S': {'enabled': True, 'params': {}},
            'V+': {'enabled': True, 'params': {}},
            'C+': {'enabled': True, 'params': {}},
            'O+': {'enabled': True, 'params': {}},
            'L': {'enabled': True, 'params': {}},
            'B': {'enabled': True, 'params': {}},
            'Q': {'enabled': True, 'params': {}},
            'I': {'enabled': True, 'params': {}},
        },
        'thresholds': {
            'prime_strength_min': 78,
            'prime_prob_min': 0.62,
            'watch_strength_min': 65,
            'filters': {
                'liquidity_min': 60,
                'basis_extreme_bps': 100,
                'funding_extreme_rate': 0.002
            }
        }
    }


# ========== 测试代码 ==========

if __name__ == "__main__":
    import sys
    
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    
    print(f"\n{'='*60}")
    print(f"测试 analyze_symbol_v3 - {symbol}")
    print(f"{'='*60}\n")
    
    result = analyze_symbol_v3(symbol)
    
    if 'error' in result:
        print(f"❌ 错误: {result['error']}")
    else:
        print(f"✅ 分析完成 ({result['elapsed_ms']}ms)\n")
        print(f"方向: {result['side']}")
        print(f"概率: {result['probability']:.1%}")
        print(f"Prime强度: {result['prime_strength']:.0f}/100")
        print(f"Edge: {result['edge']:.1f}\n")
        
        print("因子分数（10+1维）：")
        scores = result['scores']
        for factor in ['T', 'M', 'S', 'V+', 'C+', 'O+', 'L', 'B', 'Q', 'I']:
            if factor in scores:
                score = scores[factor]
                meta = result['metadata'].get(factor, {})
                weight = meta.get('weight', 0)
                print(f"  {factor:3s}: {score:>5.0f} (权重={weight})")
        
        print(f"\nF调节器: {result['F_score']:.0f} → ×{result['F_adjustment']:.2f}")
        
        pub = result['publish']
        print(f"\n发布: Prime={'✅' if pub['prime'] else '❌'}, Watch={'✅' if pub['watch'] else '❌'}")
