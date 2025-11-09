# coding: utf-8
"""
配置文件验证器（v3.0）

验证factors_unified.json的完整性和正确性
确保所有必需参数存在且类型正确

Author: CryptoSignal v7.2 Config Management Team
Date: 2025-11-09
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Any
import json


class ConfigValidator:
    """配置文件验证器"""

    # StandardizationChain参数规范
    STANDARDIZATION_SPECS = {
        'alpha': {'type': (int, float), 'range': (0.01, 1.0)},
        'tau': {'type': (int, float), 'range': (0.5, 10.0)},
        'z0': {'type': (int, float), 'range': (0.5, 5.0)},
        'zmax': {'type': (int, float), 'range': (2.0, 10.0)},
        'lam': {'type': (int, float), 'range': (1.0, 3.0)},
    }

    # 因子参数规范（基础验证）
    FACTOR_PARAM_SPECS = {
        'M': {
            'ema_fast': {'type': int, 'range': (1, 10)},
            'ema_slow': {'type': int, 'range': (3, 20)},
            'slope_lookback': {'type': int, 'range': (3, 20)},
            'slope_scale': {'type': (int, float), 'range': (0.1, 10.0)},
            'accel_scale': {'type': (int, float), 'range': (0.1, 10.0)},
        },
        'T': {
            'ema_order_min_bars': {'type': int, 'range': (3, 20)},
            'slope_lookback': {'type': int, 'range': (5, 30)},
            'atr_period': {'type': int, 'range': (7, 30)},
        },
        'C+': {
            'lookback_hours': {'type': int, 'range': (3, 24)},
            'cvd_scale': {'type': (int, float), 'range': (0.01, 1.0)},
        },
        'V+': {
            'vlevel_short': {'type': int, 'range': (3, 10)},
            'vlevel_long': {'type': int, 'range': (10, 50)},
            'vlevel_scale': {'type': (int, float), 'range': (0.1, 5.0)},
        },
        'O+': {
            'min_oi_samples': {'type': int, 'range': (10, 100)},
            'oi24_scale': {'type': (int, float), 'range': (0.01, 1.0)},
        },
    }

    def __init__(self, config: Dict[str, Any]):
        """
        初始化验证器

        Args:
            config: 配置字典（已加载的JSON）
        """
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        执行完整验证

        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # 1. 验证基本结构
        self._validate_structure()

        # 2. 验证全局配置（v3.0新增）
        if 'global' in self.config:
            self._validate_global_config()
        else:
            self.warnings.append("配置文件缺少'global'配置（v3.0新增），将使用默认值")

        # 3. 验证因子配置
        self._validate_factors()

        # 4. 验证一致性
        self._validate_consistency()

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_structure(self):
        """验证基本结构"""
        required_keys = ['version', 'updated_at', 'factors', 'weights_config', 'thresholds']

        for key in required_keys:
            if key not in self.config:
                self.errors.append(f"缺少必需的顶层键: '{key}'")

        # 验证版本号
        version = self.config.get('version', '')
        if not version.startswith('3.0'):
            self.warnings.append(f"配置文件版本 {version}，建议升级到v3.0")

    def _validate_global_config(self):
        """验证全局配置（v3.0）"""
        global_config = self.config.get('global', {})

        # 验证standardization配置
        if 'standardization' in global_config:
            std_config = global_config['standardization']

            # 验证default_params
            if 'default_params' in std_config:
                params = std_config['default_params']
                for param_name, spec in self.STANDARDIZATION_SPECS.items():
                    if param_name not in params:
                        self.warnings.append(
                            f"global.standardization.default_params缺少参数: '{param_name}'"
                        )
                    else:
                        value = params[param_name]
                        # 类型检查
                        if not isinstance(value, spec['type']):
                            self.errors.append(
                                f"global.standardization.default_params.{param_name} "
                                f"类型错误: 期望{spec['type']}，实际{type(value)}"
                            )
                        # 范围检查
                        elif 'range' in spec:
                            min_val, max_val = spec['range']
                            if not (min_val <= value <= max_val):
                                self.warnings.append(
                                    f"global.standardization.default_params.{param_name} "
                                    f"值{value}超出建议范围[{min_val}, {max_val}]"
                                )

            # 验证factor_overrides
            if 'factor_overrides' in std_config:
                overrides = std_config['factor_overrides']
                for factor_name, override_params in overrides.items():
                    for param_name in override_params:
                        if param_name not in self.STANDARDIZATION_SPECS and param_name not in ['enabled', 'comment']:
                            self.warnings.append(
                                f"global.standardization.factor_overrides.{factor_name} "
                                f"包含未知参数: '{param_name}'"
                            )

        # 验证data_quality配置
        if 'data_quality' in global_config:
            dq_config = global_config['data_quality']

            for threshold_type in ['min_data_points', 'historical_lookback']:
                if threshold_type not in dq_config:
                    self.warnings.append(f"global.data_quality缺少配置: '{threshold_type}'")

        # 验证degradation配置
        if 'degradation' in global_config:
            deg_config = global_config['degradation']

            if 'fallback_strategy' not in deg_config:
                self.warnings.append("global.degradation缺少'fallback_strategy'配置")

    def _validate_factors(self):
        """验证因子配置"""
        if 'factors' not in self.config:
            self.errors.append("配置文件缺少'factors'配置")
            return

        factors = self.config['factors']

        # 验证每个因子
        for factor_name, factor_config in factors.items():
            # 验证基本键
            required_keys = ['name', 'layer', 'weight', 'enabled', 'params']
            for key in required_keys:
                if key not in factor_config:
                    self.errors.append(f"因子'{factor_name}'缺少必需键: '{key}'")

            # 验证权重
            weight = factor_config.get('weight', 0)
            if not isinstance(weight, (int, float)) or weight < 0:
                self.errors.append(f"因子'{factor_name}'的权重无效: {weight}")

            # 验证参数（如果有规范）
            if factor_name in self.FACTOR_PARAM_SPECS:
                self._validate_factor_params(factor_name, factor_config.get('params', {}))

    def _validate_factor_params(self, factor_name: str, params: Dict[str, Any]):
        """验证因子参数"""
        spec = self.FACTOR_PARAM_SPECS[factor_name]

        for param_name, param_spec in spec.items():
            if param_name not in params:
                self.warnings.append(f"因子'{factor_name}'缺少参数: '{param_name}'")
            else:
                value = params[param_name]

                # 类型检查
                expected_type = param_spec['type']
                if not isinstance(value, expected_type):
                    self.errors.append(
                        f"因子'{factor_name}'.params.{param_name} "
                        f"类型错误: 期望{expected_type}，实际{type(value)}"
                    )

                # 范围检查
                if 'range' in param_spec and isinstance(value, (int, float)):
                    min_val, max_val = param_spec['range']
                    if not (min_val <= value <= max_val):
                        self.warnings.append(
                            f"因子'{factor_name}'.params.{param_name} "
                            f"值{value}超出建议范围[{min_val}, {max_val}]"
                        )

    def _validate_consistency(self):
        """验证一致性"""
        # 验证权重总和
        if 'factors' in self.config and 'weights_config' in self.config:
            factors = self.config['factors']
            weights_config = self.config['weights_config']

            # 计算启用因子的权重总和（排除调节器）
            total_weight = 0
            for factor_name, factor_config in factors.items():
                if factor_config.get('enabled', False) and factor_config.get('type') != 'regulator':
                    total_weight += factor_config.get('weight', 0)

            # 与配置的总权重对比
            expected_total = weights_config.get('total_weight', 160)
            if abs(total_weight - expected_total) > 5:
                self.warnings.append(
                    f"权重总和不一致: 实际{total_weight}，配置{expected_total}"
                )

    def print_report(self):
        """打印验证报告"""
        print("=" * 60)
        print("配置文件验证报告")
        print("=" * 60)

        if not self.errors and not self.warnings:
            print("✅ 配置文件验证通过，无错误和警告")
        else:
            if self.errors:
                print(f"\n❌ 发现{len(self.errors)}个错误:")
                for i, error in enumerate(self.errors, 1):
                    print(f"  {i}. {error}")

            if self.warnings:
                print(f"\n⚠️  发现{len(self.warnings)}个警告:")
                for i, warning in enumerate(self.warnings, 1):
                    print(f"  {i}. {warning}")

        print("=" * 60)


def validate_config_file(config_path: str) -> Tuple[bool, List[str], List[str]]:
    """
    验证配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        (is_valid, errors, warnings)
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        validator = ConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        validator.print_report()

        return is_valid, errors, warnings

    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {config_path}")
        return False, [f"文件不存在: {config_path}"], []
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件JSON格式错误: {e}")
        return False, [f"JSON格式错误: {e}"], []
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return False, [f"验证错误: {e}"], []


# ========== 测试代码 ==========

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 默认配置文件路径
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config" / "factors_unified.json"

    # 允许命令行指定配置文件
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])

    print(f"验证配置文件: {config_path}\n")
    is_valid, errors, warnings = validate_config_file(str(config_path))

    # 退出码：0=成功，1=有错误
    sys.exit(0 if is_valid else 1)
