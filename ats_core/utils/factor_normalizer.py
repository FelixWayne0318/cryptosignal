# coding: utf-8
"""
ats_core/utils/factor_normalizer.py

统一因子归一化框架（P1.1）

目标：
- 解决10个因子使用不同归一化方法导致的跨币种、跨regime比较失真问题
- 提供统一的zscore → tanh映射接口
- 支持hybrid模式（数据充足用zscore，不足用legacy）

作者：Claude (Sonnet 4.5)
日期：2025-11-05
版本：P1.1
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np


class FactorNormalizer:
    """
    统一因子归一化框架

    支持3种模式：
    - 'zscore': 基于历史均值和标准差的Z-score归一化
    - 'percentile': 基于历史百分位的归一化
    - 'legacy': 使用固定阈值的传统归一化（兼容模式）
    - 'hybrid': 数据充足时用zscore，不足时用legacy（推荐）

    核心理念：
    所有因子最终统一映射到[-100, +100]区间，便于：
    1. 跨币种比较（BTC vs 山寨币）
    2. 跨regime比较（牛市 vs 熊市）
    3. 跨时间比较（不同市场环境）

    示例：
        normalizer = FactorNormalizer(window_size=100, mode='hybrid')

        # T因子示例
        T_norm, meta = normalizer.normalize(
            value=slope,
            history_window=slope_history[-100:],
            fixed_neutral=0.0,
            fixed_extreme=0.02
        )

        # 保留现有的R²加权
        T_final = T_norm * r_squared_confidence
    """

    def __init__(
        self,
        window_size: int = 100,
        mode: str = 'hybrid',
        tanh_scale: float = 2.0
    ):
        """
        初始化归一化器

        Args:
            window_size: 历史数据窗口大小（默认100）
            mode: 归一化模式 'zscore' | 'percentile' | 'legacy' | 'hybrid'
            tanh_scale: tanh映射的缩放系数（默认2.0，使3σ → ±95分）
        """
        self.window_size = window_size
        self.mode = mode
        self.tanh_scale = tanh_scale

    def normalize(
        self,
        value: float,
        history_window: List[float],
        fixed_neutral: Optional[float] = None,
        fixed_extreme: Optional[float] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        统一归一化接口

        Args:
            value: 当前值
            history_window: 历史数据窗口
            fixed_neutral: 固定中性阈值（legacy模式必需）
            fixed_extreme: 固定极端阈值（legacy模式必需）

        Returns:
            (normalized_value, metadata)
            - normalized_value: [-100, +100]
            - metadata: {method, mean, std, z_score, ...}
        """
        # Hybrid模式：根据数据量自动选择
        if self.mode == 'hybrid':
            if len(history_window) >= self.window_size:
                return self._zscore_normalize(value, history_window)
            else:
                if fixed_neutral is None or fixed_extreme is None:
                    raise ValueError("Hybrid模式fallback到legacy时需要提供fixed_neutral和fixed_extreme")
                return self._legacy_normalize(value, fixed_neutral, fixed_extreme)

        elif self.mode == 'zscore':
            return self._zscore_normalize(value, history_window)

        elif self.mode == 'percentile':
            return self._percentile_normalize(value, history_window)

        elif self.mode == 'legacy':
            if fixed_neutral is None or fixed_extreme is None:
                raise ValueError("Legacy模式需要提供fixed_neutral和fixed_extreme")
            return self._legacy_normalize(value, fixed_neutral, fixed_extreme)

        else:
            raise ValueError(f"不支持的模式: {self.mode}")

    def _zscore_normalize(
        self,
        value: float,
        window: List[float]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Z-score归一化 → tanh映射

        公式：
        1. z = (value - μ) / σ
        2. normalized = 100 * tanh(z / tanh_scale)

        优点：
        - 自动适应不同币种和市场环境
        - 标准化后可比性强
        - 对异常值鲁棒

        Args:
            value: 当前值
            window: 历史数据窗口

        Returns:
            (normalized_value, metadata)
        """
        if len(window) < 10:
            raise ValueError(f"数据不足：需要至少10个历史数据点，当前{len(window)}个")

        window_array = np.array(window)
        mean = float(np.mean(window_array))
        std = float(np.std(window_array))

        # 标准差过小检查
        if std < 1e-6:
            # 数据基本不变，返回中性值
            return 0.0, {
                'method': 'zscore',
                'mean': mean,
                'std': std,
                'std_too_small': True,
                'note': '标准差过小，数据基本恒定'
            }

        # 计算Z-score
        z = (value - mean) / std

        # tanh映射到[-100, +100]
        # tanh_scale=2.0时：z=±4 → ±98分，z=±2 → ±76分
        normalized = 100.0 * np.tanh(z / self.tanh_scale)

        metadata = {
            'method': 'zscore',
            'mean': round(mean, 6),
            'std': round(std, 6),
            'z_score': round(z, 3),
            'normalized': round(normalized, 2),
            'window_size': len(window),
            'tanh_scale': self.tanh_scale,
            'note': f'z/{self.tanh_scale}使3σ → ±95分'
        }

        return normalized, metadata

    def _percentile_normalize(
        self,
        value: float,
        window: List[float]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        百分位归一化

        公式：
        1. 计算value在window中的百分位 p ∈ [0, 100]
        2. normalized = (p - 50) * 2  # 映射到[-100, +100]

        优点：
        - 非参数方法，不假设分布
        - 对异常值极其鲁棒

        缺点：
        - 离散性较强
        - 不考虑值的绝对大小

        Args:
            value: 当前值
            window: 历史数据窗口

        Returns:
            (normalized_value, metadata)
        """
        if len(window) < 10:
            raise ValueError(f"数据不足：需要至少10个历史数据点，当前{len(window)}个")

        window_sorted = np.sort(window)

        # 计算百分位（使用linear插值）
        percentile = float(np.searchsorted(window_sorted, value) / len(window) * 100)

        # 映射到[-100, +100]
        # percentile=50 → 0, percentile=90 → +80, percentile=10 → -80
        normalized = (percentile - 50.0) * 2.0
        normalized = np.clip(normalized, -100.0, 100.0)

        metadata = {
            'method': 'percentile',
            'percentile': round(percentile, 2),
            'normalized': round(normalized, 2),
            'window_size': len(window),
            'note': 'percentile-50 × 2 映射到±100'
        }

        return normalized, metadata

    def _legacy_normalize(
        self,
        value: float,
        neutral: float,
        extreme: float
    ) -> Tuple[float, Dict[str, Any]]:
        """
        固定阈值归一化（兼容现有逻辑）

        公式：
        - value < neutral → 0
        - value ∈ [neutral, extreme] → [0, 100] 线性插值
        - value > extreme → 100

        优点：
        - 简单直观
        - 兼容现有代码
        - 新币冷启动友好

        缺点：
        - 需要手动设定阈值
        - 不同市场环境下阈值可能失效

        Args:
            value: 当前值
            neutral: 中性阈值
            extreme: 极端阈值

        Returns:
            (normalized_value, metadata)
        """
        # 处理正负值（支持带符号的因子）
        sign = 1.0 if value >= 0 else -1.0
        value_abs = abs(value)
        neutral_abs = abs(neutral)
        extreme_abs = abs(extreme)

        # 线性映射
        if value_abs <= neutral_abs:
            normalized = value_abs / max(neutral_abs, 1e-6) * 33.0  # 中性区域映射到[0, 33]
        elif value_abs >= extreme_abs:
            normalized = 100.0  # 极端区域饱和在100
        else:
            # 线性插值 [neutral, extreme] → [33, 100]
            ratio = (value_abs - neutral_abs) / max(extreme_abs - neutral_abs, 1e-6)
            normalized = 33.0 + ratio * 67.0

        # 恢复符号
        normalized *= sign

        metadata = {
            'method': 'legacy',
            'neutral': neutral,
            'extreme': extreme,
            'normalized': round(normalized, 2),
            'note': '固定阈值映射'
        }

        return normalized, metadata

    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置

        Returns:
            配置字典
        """
        return {
            'window_size': self.window_size,
            'mode': self.mode,
            'tanh_scale': self.tanh_scale
        }

    def __repr__(self) -> str:
        return f"FactorNormalizer(window_size={self.window_size}, mode='{self.mode}', tanh_scale={self.tanh_scale})"


# ========== 工具函数 ==========

def normalize_factor(
    value: float,
    history_window: List[float],
    mode: str = 'hybrid',
    window_size: int = 100,
    fixed_neutral: Optional[float] = None,
    fixed_extreme: Optional[float] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    便捷函数：快速归一化单个因子值

    Args:
        value: 当前值
        history_window: 历史数据窗口
        mode: 归一化模式
        window_size: 窗口大小
        fixed_neutral: 固定中性阈值（legacy/hybrid模式需要）
        fixed_extreme: 固定极端阈值（legacy/hybrid模式需要）

    Returns:
        (normalized_value, metadata)

    示例：
        T_norm, meta = normalize_factor(
            value=0.025,
            history_window=slope_history[-100:],
            mode='hybrid',
            fixed_neutral=0.0,
            fixed_extreme=0.02
        )
    """
    normalizer = FactorNormalizer(window_size=window_size, mode=mode)
    return normalizer.normalize(value, history_window, fixed_neutral, fixed_extreme)


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("FactorNormalizer 测试")
    print("=" * 60)

    # 模拟历史数据（正态分布，μ=0.01, σ=0.005）
    np.random.seed(42)
    history = list(np.random.normal(0.01, 0.005, 100))

    normalizer = FactorNormalizer(window_size=100, mode='hybrid')

    # 测试用例
    test_cases = [
        ("中性值", 0.01),  # 均值附近
        ("正1σ", 0.015),   # +1σ
        ("正2σ", 0.020),   # +2σ
        ("正3σ", 0.025),   # +3σ
        ("负1σ", 0.005),   # -1σ
        ("负2σ", 0.000),   # -2σ
    ]

    print("\n[Zscore模式测试]")
    for label, value in test_cases:
        norm, meta = normalizer.normalize(
            value=value,
            history_window=history,
            fixed_neutral=0.0,
            fixed_extreme=0.02
        )
        print(f"{label:8s}: value={value:.4f}, z={meta['z_score']:+.2f}, norm={norm:+6.1f}")

    # 测试数据不足时的fallback
    print("\n[Hybrid模式 - Fallback到Legacy]")
    short_history = history[:30]  # 只有30个数据点
    norm, meta = normalizer.normalize(
        value=0.025,
        history_window=short_history,
        fixed_neutral=0.0,
        fixed_extreme=0.02
    )
    print(f"数据不足({len(short_history)}个)，fallback到legacy")
    print(f"value=0.025, norm={norm:+6.1f}, method={meta['method']}")

    # 测试Legacy模式
    print("\n[Legacy模式测试]")
    normalizer_legacy = FactorNormalizer(mode='legacy')
    for label, value in [("neutral", 0.0), ("half", 0.01), ("extreme", 0.02), ("超extreme", 0.03)]:
        norm, meta = normalizer_legacy.normalize(
            value=value,
            history_window=[],  # legacy不需要历史数据
            fixed_neutral=0.0,
            fixed_extreme=0.02
        )
        print(f"{label:10s}: value={value:.3f}, norm={norm:+6.1f}")

    print("\n" + "=" * 60)
    print("✅ FactorNormalizer测试完成")
    print("=" * 60)
