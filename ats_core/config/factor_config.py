# coding: utf-8
"""
统一因子配置管理器

功能:
1. 加载统一配置文件（factors_unified.json）
2. 提供因子参数访问接口
3. 支持自适应权重
4. 版本控制
"""

from __future__ import annotations
import json
import os
from typing import Dict, Any, Optional, List


class FactorConfig:
    """统一因子配置管理器"""

    def __init__(self, config_path: str = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为 config/factors_unified.json
        """
        if config_path is None:
            # 默认路径：项目根目录/config/factors_unified.json
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(project_root, "config", "factors_unified.json")

        self.config_path = config_path
        self.config = self._load_config()

        # 快速访问属性
        self.version = self.config['version']
        self.factors = self.config['factors']
        self.thresholds = self.config['thresholds']
        self.risk_management = self.config['risk_management']
        self.weights_config = self.config['weights_config']
        self.adaptive_weights_config = self.config['adaptive_weights']

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ 配置加载成功: {self.config_path} (v{config['version']})")
            return config
        except Exception as e:
            print(f"❌ 配置加载失败: {e}")
            raise

    def reload(self):
        """重新加载配置（用于动态更新）"""
        self.config = self._load_config()
        self.version = self.config['version']
        self.factors = self.config['factors']
        self.thresholds = self.config['thresholds']
        print(f"🔄 配置已重新加载: v{self.version}")

    # ========== 因子相关方法 ==========

    def get_factor_params(self, factor_name: str) -> Dict[str, Any]:
        """
        获取因子参数

        Args:
            factor_name: 因子名称 (T, M, C+, S, V+, O+, L, B, Q, I, F)

        Returns:
            因子参数字典

        Raises:
            ValueError: 未知因子名称
        """
        if factor_name not in self.factors:
            raise ValueError(f"Unknown factor: {factor_name}")

        return self.factors[factor_name]['params']

    def get_fallback_params(self, factor_name: str) -> Dict[str, Any]:
        """
        获取因子降级参数（v7.3.4新增）

        当配置加载失败时使用的默认参数

        Args:
            factor_name: 因子名称 (T, M, C+, S, V+, O+, L, B, Q, I, F)

        Returns:
            降级参数字典

        Raises:
            ValueError: 未知因子名称或无降级参数
        """
        if factor_name not in self.factors:
            raise ValueError(f"Unknown factor: {factor_name}")

        fallback = self.factors[factor_name].get('fallback_params', {})
        if not fallback:
            # 如果没有fallback_params，返回params作为降级（向后兼容）
            return self.factors[factor_name]['params']

        return fallback

    def get_factor_weight(self, factor_name: str) -> int:
        """
        获取因子权重

        Args:
            factor_name: 因子名称

        Returns:
            权重值
        """
        if factor_name not in self.factors:
            raise ValueError(f"Unknown factor: {factor_name}")

        return self.factors[factor_name].get('weight', 0)

    def is_factor_enabled(self, factor_name: str) -> bool:
        """
        检查因子是否启用

        Args:
            factor_name: 因子名称

        Returns:
            True if enabled, False otherwise
        """
        if factor_name not in self.factors:
            return False

        return self.factors[factor_name].get('enabled', False)

    def get_all_weights(self, exclude_regulators: bool = True) -> Dict[str, int]:
        """
        获取所有因子权重

        Args:
            exclude_regulators: 是否排除调节器（如F）

        Returns:
            {factor_name: weight, ...}
        """
        weights = {}

        for name, config in self.factors.items():
            # 跳过未启用的因子
            if not config.get('enabled', False):
                continue

            # 跳过调节器
            if exclude_regulators and config.get('type') == 'regulator':
                continue

            weights[name] = config.get('weight', 0)

        return weights

    def get_weights_dict(self) -> Dict[str, float]:
        """
        获取权重字典（兼容analyze_symbol.py格式）

        v7.3.4新增：配置统一方案，从factors_unified.json读取权重

        Returns:
            {factor_name: weight, ...}
            - 使用简化命名（C而非C+, V而非V+, O而非O+）
            - 返回float类型（兼容analyze_symbol.py）
            - 包含A层评分因子（T/M/C/V/O/B）和B层调制器（L/S/F/I）
            - B层调制器权重为0.0

        Note:
            本方法是配置统一方案的核心，替代CFG.params["weights"]
        """
        weights = {}

        # 命名映射：factors_unified.json命名 → analyze_symbol.py命名
        name_mapping = {
            'C+': 'C',  # CVD因子
            'V+': 'V',  # 量能因子
            'O+': 'O'   # 持仓量因子
        }

        for name, config in self.factors.items():
            # 跳过未启用的因子
            if not config.get('enabled', False):
                continue

            # 转换命名以兼容现有代码
            key = name_mapping.get(name, name)

            # 转换为float（analyze_symbol.py期望float类型）
            weights[key] = float(config.get('weight', 0))

        return weights

    def get_enabled_factors(self) -> List[str]:
        """
        获取所有启用的因子名称

        Returns:
            因子名称列表
        """
        return [
            name for name, config in self.factors.items()
            if config.get('enabled', False)
        ]

    # ========== 自适应权重 ==========

    def get_adaptive_weights(
        self,
        market_regime: float,
        volatility: float
    ) -> Dict[str, int]:
        """
        获取自适应权重（基于市场体制）

        Args:
            market_regime: 市场体制评分 (-100 到 +100)
            volatility: 波动率 (如 0.05 表示5%日波动)

        Returns:
            调整后的权重字典
        """
        # 如果未启用自适应权重，返回默认权重
        if not self.adaptive_weights_config.get('enabled', False):
            return self.get_all_weights()

        regimes = self.adaptive_weights_config['regimes']
        base_weights = self.get_all_weights()
        adjusted_weights = base_weights.copy()

        # 检测市场体制并应用相应权重
        for regime_name, regime_config in regimes.items():
            condition = regime_config['condition']

            # 评估条件
            if self._evaluate_regime_condition(condition, market_regime, volatility):
                # 应用权重调整
                regime_weights = regime_config['weight_adjustments']
                blend_ratio = self.adaptive_weights_config.get('blend_ratio', 0.7)

                # 混合权重（70%体制权重 + 30%基础权重）
                for factor_name in base_weights.keys():
                    if factor_name in regime_weights:
                        adjusted_weights[factor_name] = int(
                            regime_weights[factor_name] * blend_ratio +
                            base_weights[factor_name] * (1 - blend_ratio)
                        )

                print(f"🔄 应用自适应权重: {regime_name} ({regime_config['description']})")
                break

        return adjusted_weights

    def _evaluate_regime_condition(
        self,
        condition: str,
        market_regime: float,
        volatility: float
    ) -> bool:
        """
        评估体制条件

        Args:
            condition: 条件字符串（如 "abs(market_regime) > 60"）
            market_regime: 市场体制值
            volatility: 波动率

        Returns:
            True if condition met, False otherwise
        """
        try:
            # 安全评估条件（只允许特定变量）
            allowed_vars = {
                'market_regime': market_regime,
                'volatility': volatility,
                'abs': abs
            }
            return eval(condition, {"__builtins__": {}}, allowed_vars)
        except Exception as e:
            print(f"⚠️ 条件评估失败: {condition}, 错误: {e}")
            return False

    # ========== 阈值相关方法 ==========

    def get_threshold(self, threshold_name: str) -> Any:
        """
        获取阈值

        Args:
            threshold_name: 阈值名称

        Returns:
            阈值值
        """
        # 支持嵌套访问（如 "filters.liquidity_min"）
        keys = threshold_name.split('.')
        value = self.thresholds

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise KeyError(f"Threshold not found: {threshold_name}")

        return value

    def get_risk_param(self, param_path: str) -> Any:
        """
        获取风险管理参数

        Args:
            param_path: 参数路径（如 "stop_loss.base_atr_multiplier"）

        Returns:
            参数值
        """
        keys = param_path.split('.')
        value = self.risk_management

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise KeyError(f"Risk param not found: {param_path}")

        return value

    # ========== v3.0新增：配置管理优化方法 ==========

    def get_standardization_params(self, factor_name: str) -> Dict[str, Any]:
        """
        获取StandardizationChain参数（v3.0新增）

        Args:
            factor_name: 因子名称 (T, M, C+, S, V+, O+, etc.)

        Returns:
            StandardizationChain参数字典 (alpha, tau, z0, zmax, lam, enabled)

        Raises:
            KeyError: 配置文件中没有global.standardization配置
        """
        if 'global' not in self.config or 'standardization' not in self.config['global']:
            # 向后兼容：如果没有global配置，返回默认值
            print(f"⚠️ 配置文件缺少global.standardization，使用默认值")
            return {
                'alpha': 0.25,
                'tau': 5.0,
                'z0': 3.0,
                'zmax': 6.0,
                'lam': 1.5,
                'enabled': True
            }

        std_config = self.config['global']['standardization']
        default_params = std_config.get('default_params', {})

        # 检查是否有因子级覆盖
        overrides = std_config.get('factor_overrides', {})
        if factor_name in overrides:
            # 合并默认参数和覆盖参数
            params = dict(default_params)
            params.update(overrides[factor_name])
            return params
        else:
            # 使用默认参数
            return dict(default_params)

    def get_data_quality_threshold(
        self,
        factor_name: str,
        threshold_type: str = 'min_data_points'
    ) -> Any:
        """
        获取数据质量阈值（v3.0新增）

        Args:
            factor_name: 因子名称 (T, M, C+, etc.)
            threshold_type: 阈值类型 ('min_data_points', 'historical_lookback', 'data_freshness_seconds')

        Returns:
            阈值值（int or float）

        Raises:
            KeyError: 配置文件中没有global.data_quality配置
        """
        if 'global' not in self.config or 'data_quality' not in self.config['global']:
            # 向后兼容：返回合理的默认值
            defaults = {
                'min_data_points': 20,
                'historical_lookback': 50,
                'data_freshness_seconds': 3600
            }
            return defaults.get(threshold_type, 20)

        data_quality = self.config['global']['data_quality']

        if threshold_type not in data_quality:
            raise KeyError(f"Unknown threshold type: {threshold_type}")

        thresholds = data_quality[threshold_type]

        # 检查是否有因子级配置
        if factor_name in thresholds:
            return thresholds[factor_name]
        else:
            # 使用默认值
            return thresholds.get('default', 20)

    def get_degradation_strategy(self) -> str:
        """
        获取降级策略（v3.0新增）

        Returns:
            降级策略 ('zero_score', 'partial_data', etc.)
        """
        if 'global' not in self.config or 'degradation' not in self.config['global']:
            return 'zero_score'  # 默认策略

        return self.config['global']['degradation'].get('fallback_strategy', 'zero_score')

    def should_log_degradation(self) -> bool:
        """
        是否记录降级事件（v3.0新增）

        Returns:
            True if should log, False otherwise
        """
        if 'global' not in self.config or 'degradation' not in self.config['global']:
            return True  # 默认记录

        return self.config['global']['degradation'].get('log_degradation_events', True)

    def get_confidence_penalty(self, degradation_reason: str) -> float:
        """
        获取降级置信度惩罚系数（v3.0新增）

        Args:
            degradation_reason: 降级原因 ('missing_data', 'stale_data', 'partial_data')

        Returns:
            惩罚系数 (0.0-1.0)
        """
        if 'global' not in self.config or 'degradation' not in self.config['global']:
            defaults = {
                'missing_data': 0.5,
                'stale_data': 0.7,
                'partial_data': 0.8
            }
            return defaults.get(degradation_reason, 0.5)

        degradation = self.config['global']['degradation']
        confidence_penalty = degradation.get('confidence_penalty', {})
        return confidence_penalty.get(degradation_reason, 0.5)

    def get_factor_config_full(self, factor_name: str) -> Dict[str, Any]:
        """
        获取因子的完整配置（v3.0新增）

        包含：
        - 基本信息 (name, layer, weight, enabled)
        - 算法参数 (params)
        - StandardizationChain参数
        - 数据质量阈值

        Args:
            factor_name: 因子名称

        Returns:
            完整配置字典

        Raises:
            ValueError: 未知因子名称
        """
        if factor_name not in self.factors:
            raise ValueError(f"Unknown factor: {factor_name}")

        config = dict(self.factors[factor_name])

        # 添加StandardizationChain配置
        config['standardization'] = self.get_standardization_params(factor_name)

        # 添加数据质量阈值
        config['data_quality'] = {
            'min_data_points': self.get_data_quality_threshold(factor_name, 'min_data_points'),
            'historical_lookback': self.get_data_quality_threshold(factor_name, 'historical_lookback'),
        }

        return config

    # ========== 工具方法 ==========

    def normalize_score(self, weighted_sum: float) -> float:
        """
        归一化加权分数到±100

        Args:
            weighted_sum: 加权总分 (-100 到 +100) (v6.0: 100%系统)

        Returns:
            归一化分数 (-100 到 +100)
        """
        norm_factor = self.weights_config['normalization_factor']
        return weighted_sum / norm_factor

    def get_layer_weights(self) -> Dict[str, int]:
        """
        获取各层权重分配

        Returns:
            {layer_name: total_weight, ...}
        """
        return self.weights_config['layer_distribution']

    def summary(self) -> str:
        """
        获取配置摘要

        Returns:
            配置摘要字符串
        """
        enabled_factors = self.get_enabled_factors()
        weights = self.get_all_weights()

        summary = f"""
========== 因子配置摘要 ==========
版本: {self.version}
更新时间: {self.config['updated_at']}

启用因子: {len(enabled_factors)}个
{', '.join(enabled_factors)}

权重分配:
"""
        for factor_name in enabled_factors:
            if factor_name in weights:
                weight = weights[factor_name]
                layer = self.factors[factor_name]['layer']
                summary += f"  {factor_name}: {weight} ({layer})\n"

        summary += f"\n总权重: {sum(weights.values())}\n"
        summary += f"自适应权重: {'启用' if self.adaptive_weights_config['enabled'] else '禁用'}\n"
        summary += "=" * 35

        return summary


# ========== 全局单例 ==========

_config_instance: Optional[FactorConfig] = None


def get_factor_config(config_path: str = None) -> FactorConfig:
    """
    获取全局因子配置实例（单例模式）

    Args:
        config_path: 可选的配置文件路径

    Returns:
        FactorConfig实例
    """
    global _config_instance

    if _config_instance is None or config_path is not None:
        _config_instance = FactorConfig(config_path)

    return _config_instance


def reload_config():
    """重新加载配置"""
    global _config_instance
    if _config_instance is not None:
        _config_instance.reload()


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("因子配置管理器测试")
    print("=" * 60)

    # 创建配置管理器
    config = get_factor_config()

    # 打印摘要
    print(config.summary())

    # 测试获取参数
    print("\n[测试] 获取T因子参数:")
    t_params = config.get_factor_params('T')
    print(f"  EMA Short: {t_params['ema_short']}")
    print(f"  EMA Long: {t_params['ema_long']}")

    # 测试获取权重
    print("\n[测试] 所有因子权重:")
    weights = config.get_all_weights()
    for name, weight in weights.items():
        print(f"  {name}: {weight}")

    # 测试自适应权重
    print("\n[测试] 自适应权重（强趋势市场）:")
    adaptive_weights = config.get_adaptive_weights(market_regime=70, volatility=0.03)
    for name, weight in adaptive_weights.items():
        print(f"  {name}: {weight}")

    # 测试阈值
    print("\n[测试] 获取阈值:")
    print(f"  Prime强度最小值: {config.get_threshold('prime_strength_min')}")
    print(f"  流动性最小值: {config.get_threshold('filters.liquidity_min')}")

    # 测试风险参数
    print("\n[测试] 风险管理参数:")
    print(f"  止损ATR倍数: {config.get_risk_param('stop_loss.base_atr_multiplier')}")
    print(f"  止盈ATR倍数: {config.get_risk_param('take_profit.base_atr_multiplier')}")

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
