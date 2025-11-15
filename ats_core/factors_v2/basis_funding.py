# coding: utf-8
"""
B 因子: Basis + Funding（基差+资金费）

整合 #5 基差与资金费率

理论基础:
1. 基差（Basis）= (永续价格 - 现货价格) / 现货价格
   - 正基差：市场看涨，多头愿意支付溢价
   - 负基差：市场看跌，空头愿意支付溢价

2. 资金费率（Funding Rate）：
   - 正费率：多头支付空头（市场过热）
   - 负费率：空头支付多头（市场恐慌）

评分逻辑:
- 基差和资金费率都归一化到±100
- 正值表示看涨情绪，负值表示看跌情绪
- 加权融合：60%基差 + 40%资金费

Range: -100 到 +100
"""

from __future__ import annotations
from typing import Tuple, Dict, Any, Optional
import numpy as np
from ats_core.scoring.scoring_utils import StandardizationChain
from ats_core.config.factor_config import get_factor_config

# P3修复: 从配置读取StandardizationChain参数，消除硬编码
_basis_chain = None  # 延迟初始化

def _get_basis_chain() -> StandardizationChain:
    """获取StandardizationChain实例（延迟初始化，从配置读取）"""
    global _basis_chain

    if _basis_chain is None:
        try:
            config = get_factor_config()
            std_params = config.get_standardization_params("B")

            _basis_chain = StandardizationChain(
                alpha=std_params.get('alpha', 0.15),
                tau=std_params.get('tau', 3.0),
                z0=std_params.get('z0', 2.5),
                zmax=std_params.get('zmax', 6.0),
                lam=std_params.get('lam', 1.5)
            )
        except Exception as e:
            # 配置加载失败时使用默认参数（向后兼容）
            print(f"⚠️ B因子StandardizationChain配置加载失败，使用默认参数: {e}")
            _basis_chain = StandardizationChain(
                alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5
            )

    return _basis_chain


def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except Exception:
        return 0.0


def get_adaptive_basis_thresholds(
    basis_history: list,
    mode: str = 'hybrid',
    min_data_points: int = 50
) -> Tuple[float, float]:
    """
    计算自适应基差阈值（P0.1修复）

    Args:
        basis_history: 历史基差数据（bps）
        mode: 'adaptive' | 'legacy' | 'hybrid'
        min_data_points: 最小数据点数（默认50）

    Returns:
        (neutral_bps, extreme_bps)
    """
    # Legacy模式或数据不足时使用固定阈值
    if mode == 'legacy' or len(basis_history) < min_data_points:
        return 50.0, 100.0

    # 计算滚动百分位
    basis_array = np.array(basis_history)
    neutral_bps = float(np.percentile(np.abs(basis_array), 50))  # 中位数
    extreme_bps = float(np.percentile(np.abs(basis_array), 90))  # 90分位

    # 边界保护（防止极端市场）
    neutral_bps = np.clip(neutral_bps, 20.0, 200.0)
    extreme_bps = np.clip(extreme_bps, 50.0, 300.0)

    # 确保extreme > neutral
    if extreme_bps <= neutral_bps:
        extreme_bps = neutral_bps * 1.5

    return neutral_bps, extreme_bps


def get_adaptive_funding_thresholds(
    funding_history: list,
    mode: str = 'hybrid',
    min_data_points: int = 50
) -> Tuple[float, float]:
    """
    计算自适应资金费率阈值（P0.1修复）

    Args:
        funding_history: 历史资金费率数据
        mode: 'adaptive' | 'legacy' | 'hybrid'
        min_data_points: 最小数据点数（默认50）

    Returns:
        (neutral_rate, extreme_rate)
    """
    # Legacy模式或数据不足时使用固定阈值
    if mode == 'legacy' or len(funding_history) < min_data_points:
        return 0.001, 0.002

    # 计算滚动百分位
    funding_array = np.array(funding_history)
    neutral_rate = float(np.percentile(np.abs(funding_array), 50))
    extreme_rate = float(np.percentile(np.abs(funding_array), 90))

    # 边界保护
    neutral_rate = np.clip(neutral_rate, 0.0001, 0.005)
    extreme_rate = np.clip(extreme_rate, 0.0005, 0.01)

    # 确保extreme > neutral
    if extreme_rate <= neutral_rate:
        extreme_rate = neutral_rate * 1.5

    return neutral_rate, extreme_rate


def _normalize_basis(
    basis_bps: float,
    neutral_bps: float,
    extreme_bps: float
) -> float:
    """
    归一化基差到±100

    Args:
        basis_bps: 基差（基点）
        neutral_bps: 中性基差阈值
        extreme_bps: 极端基差阈值

    Returns:
        归一化评分 (-100 到 +100)
    """
    if abs(basis_bps) <= neutral_bps:
        # 中性区域：线性映射到±33
        return (basis_bps / neutral_bps) * 33.0
    else:
        # 极端区域：映射到±33到±100
        if basis_bps > 0:
            # 正基差（看涨）
            excess = basis_bps - neutral_bps
            ratio = min(1.0, excess / (extreme_bps - neutral_bps))
            return 33.0 + ratio * 67.0
        else:
            # 负基差（看跌）
            excess = abs(basis_bps) - neutral_bps
            ratio = min(1.0, excess / (extreme_bps - neutral_bps))
            return -33.0 - ratio * 67.0


def _normalize_funding(
    funding_rate: float,
    neutral_rate: float,
    extreme_rate: float
) -> float:
    """
    归一化资金费率到±100

    Args:
        funding_rate: 资金费率
        neutral_rate: 中性费率阈值
        extreme_rate: 极端费率阈值

    Returns:
        归一化评分 (-100 到 +100)
    """
    if abs(funding_rate) <= neutral_rate:
        # 中性区域：线性映射到±33
        return (funding_rate / neutral_rate) * 33.0
    else:
        # 极端区域：映射到±33到±100
        if funding_rate > 0:
            # 正费率（多头支付，看涨情绪）
            excess = funding_rate - neutral_rate
            ratio = min(1.0, excess / (extreme_rate - neutral_rate))
            return 33.0 + ratio * 67.0
        else:
            # 负费率（空头支付，看跌情绪）
            excess = abs(funding_rate) - neutral_rate
            ratio = min(1.0, excess / (extreme_rate - neutral_rate))
            return -33.0 - ratio * 67.0


def score_basis_funding(
    perp_price: float,
    spot_price: float,
    funding_rate: float,
    funding_history: Optional[list] = None,
    basis_history: Optional[list] = None,
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    计算基差+资金费评分（P1修复：统一命名规范score_*，P2修复：返回int）

    Args:
        perp_price: 永续合约价格
        spot_price: 现货价格
        funding_rate: 当前资金费率（如0.001表示0.1%）
        funding_history: 资金费率历史（可选，用于FWI增强和自适应阈值）
        basis_history: 基差历史（可选，用于自适应阈值，P0.1新增）
        params: 参数字典，包含:
            - basis_neutral_bps: 中性基差（默认50 bps）
            - basis_extreme_bps: 极端基差（默认100 bps）
            - funding_neutral_rate: 中性费率（默认0.001）
            - funding_extreme_rate: 极端费率（默认0.002）
            - basis_weight: 基差权重（默认0.6）
            - funding_weight: 资金费权重（默认0.4）
            - fwi_enabled: 是否启用FWI增强（默认False）
            - adaptive_threshold_mode: 'adaptive' | 'legacy' | 'hybrid'（默认'hybrid'）

    Returns:
        (score, metadata)
        - score: -100 到 +100（正值看涨，负值看跌）
        - metadata: 详细信息
    """
    if params is None:
        params = {}

    # P0.1: 自适应阈值模式
    adaptive_mode = params.get('adaptive_threshold_mode', 'hybrid')

    # 计算自适应阈值（如果启用且有历史数据）
    if adaptive_mode != 'legacy' and basis_history and len(basis_history) >= 50:
        basis_neutral, basis_extreme = get_adaptive_basis_thresholds(
            basis_history, mode=adaptive_mode
        )
        threshold_source = 'adaptive'
    else:
        # Fallback到固定阈值
        basis_neutral = params.get('basis_neutral_bps', 50)
        basis_extreme = params.get('basis_extreme_bps', 100)
        threshold_source = 'legacy'

    if adaptive_mode != 'legacy' and funding_history and len(funding_history) >= 50:
        funding_neutral, funding_extreme = get_adaptive_funding_thresholds(
            funding_history, mode=adaptive_mode
        )
    else:
        funding_neutral = params.get('funding_neutral_rate', 0.001)
        funding_extreme = params.get('funding_extreme_rate', 0.002)

    basis_weight = params.get('basis_weight', 0.6)
    funding_weight = params.get('funding_weight', 0.4)
    fwi_enabled = params.get('fwi_enabled', False)

    # === 1. 计算基差 ===
    perp_price = _to_f(perp_price)
    spot_price = _to_f(spot_price)

    if spot_price == 0:
        return 0.0, {'error': 'Invalid spot price'}

    # 基差（百分比）
    basis_pct = (perp_price - spot_price) / spot_price

    # 转换为基点（1 bps = 0.01%）
    basis_bps = basis_pct * 10000

    # 归一化基差
    basis_score = _normalize_basis(basis_bps, basis_neutral, basis_extreme)

    # === 2. 归一化资金费率 ===
    funding_rate = _to_f(funding_rate)
    funding_score = _normalize_funding(funding_rate, funding_neutral, funding_extreme)

    # === 3. FWI增强（可选）===
    fwi_boost = 0.0
    fwi_active = False

    if fwi_enabled and funding_history and len(funding_history) >= 2:
        # Funding Window Impact (#6因子的可选增强)
        # 检测资金费率的快速变化
        fwi_window = params.get('fwi_window_minutes', 30)
        fwi_boost_max = params.get('fwi_boost_max', 20)

        # 最近30分钟内的费率变化
        recent_funding = funding_history[-fwi_window:] if len(funding_history) > fwi_window else funding_history

        if len(recent_funding) >= 2:
            funding_start = _to_f(recent_funding[0])
            funding_end = _to_f(recent_funding[-1])

            # 计算变化率
            if funding_start != 0:
                funding_change_pct = abs(funding_end - funding_start) / abs(funding_start)
            else:
                funding_change_pct = 0.0

            # 如果费率快速上升（>50%），给予增强
            if funding_change_pct > 0.5:
                fwi_boost = min(fwi_boost_max, funding_change_pct * fwi_boost_max)
                fwi_active = True

                # 增强方向：如果费率上升，增强看涨信号
                if funding_end > funding_start:
                    fwi_boost = abs(fwi_boost)
                else:
                    fwi_boost = -abs(fwi_boost)

    # === 4. 融合评分 ===
    raw_score = basis_score * basis_weight + funding_score * funding_weight

    # 应用FWI增强
    if fwi_active:
        raw_score += fwi_boost

    # v2.0合规：应用StandardizationChain（P3修复：从配置读取参数）
    score_pub, diagnostics = _get_basis_chain().standardize(raw_score)
    final_score = int(round(score_pub))

    # === 5. 情绪等级 ===
    if final_score > 66:
        sentiment = 'very_bullish'
        interpretation = 'Strong bullish sentiment (high premium)'
    elif final_score > 33:
        sentiment = 'bullish'
        interpretation = 'Bullish sentiment'
    elif final_score > -33:
        sentiment = 'neutral'
        interpretation = 'Neutral sentiment'
    elif final_score > -66:
        sentiment = 'bearish'
        interpretation = 'Bearish sentiment'
    else:
        sentiment = 'very_bearish'
        interpretation = 'Strong bearish sentiment (high discount)'

    # === 6. 元数据 ===
    metadata = {
        'basis_pct': basis_pct,
        'basis_bps': basis_bps,
        'basis_score': basis_score,
        'funding_rate': funding_rate,
        'funding_score': funding_score,
        'fwi_boost': fwi_boost,
        'fwi_active': fwi_active,
        'final_score': final_score,
        'sentiment': sentiment,
        'interpretation': interpretation,
        # P0.1: 自适应阈值信息
        'threshold_source': threshold_source,
        'basis_neutral_bps': basis_neutral,
        'basis_extreme_bps': basis_extreme,
        'funding_neutral_rate': funding_neutral,
        'funding_extreme_rate': funding_extreme
    }

    return final_score, metadata


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("B 因子测试 - Basis + Funding（基差+资金费）")
    print("=" * 60)

    # 场景1: 正基差 + 正资金费（强烈看涨）
    print("\n[场景1] 强烈看涨（高溢价+多头支付）")
    score_1, meta_1 = score_basis_funding(
        perp_price=50500,  # 永续价格
        spot_price=50000,  # 现货价格
        funding_rate=0.0015  # 0.15% 资金费
    )
    print(f"  永续价格: $50,500")
    print(f"  现货价格: $50,000")
    print(f"  基差: {meta_1['basis_bps']:.1f} bps ({meta_1['basis_pct']:.3%})")
    print(f"  资金费率: {meta_1['funding_rate']:.4%}")
    print(f"  基差评分: {meta_1['basis_score']:.1f}")
    print(f"  资金费评分: {meta_1['funding_score']:.1f}")
    print(f"  最终评分: {score_1:.1f}")
    print(f"  情绪: {meta_1['sentiment']}")
    print(f"  解读: {meta_1['interpretation']}")

    # 场景2: 负基差 + 负资金费（强烈看跌）
    print("\n[场景2] 强烈看跌（折价+空头支付）")
    score_2, meta_2 = score_basis_funding(
        perp_price=49500,  # 永续价格
        spot_price=50000,  # 现货价格
        funding_rate=-0.0018  # -0.18% 资金费
    )
    print(f"  永续价格: $49,500")
    print(f"  现货价格: $50,000")
    print(f"  基差: {meta_2['basis_bps']:.1f} bps ({meta_2['basis_pct']:.3%})")
    print(f"  资金费率: {meta_2['funding_rate']:.4%}")
    print(f"  基差评分: {meta_2['basis_score']:.1f}")
    print(f"  资金费评分: {meta_2['funding_score']:.1f}")
    print(f"  最终评分: {score_2:.1f}")
    print(f"  情绪: {meta_2['sentiment']}")
    print(f"  解读: {meta_2['interpretation']}")

    # 场景3: 中性基差 + 中性资金费
    print("\n[场景3] 中性市场（平衡）")
    score_3, meta_3 = score_basis_funding(
        perp_price=50025,  # 永续价格
        spot_price=50000,  # 现货价格
        funding_rate=0.0005  # 0.05% 资金费
    )
    print(f"  永续价格: $50,025")
    print(f"  现货价格: $50,000")
    print(f"  基差: {meta_3['basis_bps']:.1f} bps ({meta_3['basis_pct']:.3%})")
    print(f"  资金费率: {meta_3['funding_rate']:.4%}")
    print(f"  基差评分: {meta_3['basis_score']:.1f}")
    print(f"  资金费评分: {meta_3['funding_score']:.1f}")
    print(f"  最终评分: {score_3:.1f}")
    print(f"  情绪: {meta_3['sentiment']}")
    print(f"  解读: {meta_3['interpretation']}")

    # 场景4: FWI增强（资金费快速上升）
    print("\n[场景4] FWI增强（资金费快速上升）")
    funding_hist = [0.0005 + i * 0.0001 for i in range(30)]  # 费率快速上升
    score_4, meta_4 = score_basis_funding(
        perp_price=50100,
        spot_price=50000,
        funding_rate=0.0034,
        funding_history=funding_hist,
        params={'fwi_enabled': True}
    )
    print(f"  永续价格: $50,100")
    print(f"  现货价格: $50,000")
    print(f"  基差: {meta_4['basis_bps']:.1f} bps")
    print(f"  资金费率: {meta_4['funding_rate']:.4%}")
    print(f"  FWI增强: {meta_4['fwi_boost']:.1f} (Active: {meta_4['fwi_active']})")
    print(f"  最终评分: {score_4:.1f}")
    print(f"  情绪: {meta_4['sentiment']}")

    print("\n" + "=" * 60)
    print("✅ Basis + Funding因子测试完成")
    print("=" * 60)
