# coding: utf-8
"""
阈值配置加载器（P2.1新增）

统一管理所有信号阈值，避免硬编码

使用方式:
    from ats_core.config.threshold_config import get_thresholds

    thresholds = get_thresholds()
    prime_strength_min = thresholds.get_mature_threshold('prime_strength_min')
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class ThresholdConfig:
    """阈值配置管理器"""

    def __init__(self, config_path: str = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认使用 config/signal_thresholds.json
        """
        if config_path is None:
            # 自动查找配置文件
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / 'config' / 'signal_thresholds.json'

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[ThresholdConfig] 配置文件不存在: {self.config_path}")
            print(f"[ThresholdConfig] 使用默认值")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"[ThresholdConfig] 配置文件格式错误: {e}")
            print(f"[ThresholdConfig] 使用默认值")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """默认配置（硬编码备份）

        v7.2.7修复：默认值应与signal_thresholds.json保持一致
        """
        return {
            "基础分析阈值": {
                "mature_coin": {
                    "prime_strength_min": 35,  # v7.2.7修复：从54改为35
                    "confidence_min": 20,      # v7.2.7修复：从60改为20
                    "edge_min": 0.15,          # v7.2.7修复：从0.48改为0.15
                    "prime_prob_min": 0.45     # v7.2.7修复：从0.68改为0.45
                }
            },
            "v72闸门阈值": {
                "gate2_fund_support": {"F_min": -50},  # v7.2.7修复：从-15改为-50
                "gate4_probability": {"P_min": 0.45}   # v7.2.7修复：从0.50改为0.45
            }
        }

    def get_mature_threshold(self, key: str, default: Any = None) -> Any:
        """获取成熟币种的阈值"""
        return self.config.get("基础分析阈值", {}).get("mature_coin", {}).get(key, default)

    def get_newcoin_threshold(self, phase: str, key: str, default: Any = None) -> Any:
        """
        获取新币的阈值

        Args:
            phase: 'ultra', 'phaseA', 'phaseB'
            key: 阈值名称
            default: 默认值
        """
        phase_key = f"newcoin_{phase}"
        return self.config.get("基础分析阈值", {}).get(phase_key, {}).get(key, default)

    def get_gate_threshold(self, gate_name: str, key: str, default: Any = None) -> Any:
        """
        获取闸门阈值

        Args:
            gate_name: 'gate1_data_quality', 'gate2_fund_support', etc.
            key: 参数名
            default: 默认值
        """
        return self.config.get("v72闸门阈值", {}).get(gate_name, {}).get(key, default)

    def get_calibration_param(self, key: str, default: Any = None) -> Any:
        """获取统计校准参数"""
        return self.config.get("统计校准参数", {}).get(key, default)

    def get_i_factor_param(self, key: str, default: Any = None) -> Any:
        """获取I因子参数"""
        return self.config.get("I因子参数", {}).get(key, default)

    def get_factor_weights(self, group: str = None) -> Dict[str, Any]:
        """
        获取因子分组权重（阶段2.1扩展）

        Args:
            group: 'TC_internal', 'VOM_internal' 或 None（获取全部）

        Returns:
            权重配置字典
        """
        weights = self.config.get("因子分组权重", {})
        if group:
            return weights.get(group, {})
        return weights

    def get_ev_params(self, key: str = None, default: Any = None) -> Any:
        """
        获取EV计算参数（阶段2.1扩展）

        Args:
            key: 参数名（如'spread_bps'）或None（获取全部）
            default: 默认值

        Returns:
            参数值或参数字典
        """
        ev_params = self.config.get("EV计算参数", {})
        if key:
            return ev_params.get(key, default)
        return ev_params

    def get_all(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config


# 全局单例
_threshold_config: ThresholdConfig = None


def get_thresholds() -> ThresholdConfig:
    """
    获取全局阈值配置实例（单例模式）

    Returns:
        ThresholdConfig实例
    """
    global _threshold_config
    if _threshold_config is None:
        _threshold_config = ThresholdConfig()
    return _threshold_config


def reload_thresholds():
    """重新加载配置（用于运行时更新）"""
    global _threshold_config
    _threshold_config = ThresholdConfig()


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("阈值配置测试")
    print("=" * 60)

    config = get_thresholds()

    print("\n成熟币种阈值:")
    print(f"  prime_strength_min: {config.get_mature_threshold('prime_strength_min')}")
    print(f"  confidence_min: {config.get_mature_threshold('confidence_min')}")
    print(f"  edge_min: {config.get_mature_threshold('edge_min')}")

    print("\n新币（PhaseB）阈值:")
    print(f"  prime_strength_min: {config.get_newcoin_threshold('phaseB', 'prime_strength_min')}")

    print("\nv7.2闸门阈值:")
    print(f"  F_min: {config.get_gate_threshold('gate2_fund_support', 'F_min')}")
    print(f"  P_min: {config.get_gate_threshold('gate4_probability', 'P_min')}")

    print("\n统计校准参数:")
    print(f"  calibration_min_samples: {config.get_calibration_param('calibration_min_samples')}")
    print(f"  bootstrap_base_p: {config.get_calibration_param('bootstrap_base_p')}")

    print("\nI因子参数:")
    print(f"  window_hours: {config.get_i_factor_param('window_hours')}")
    print(f"  beta_threshold_high: {config.get_i_factor_param('beta_threshold_high')}")

    print("\n因子分组权重（阶段2.1新增）:")
    weights = config.get_factor_weights()
    print(f"  TC_weight: {weights.get('TC_weight')}")
    print(f"  VOM_weight: {weights.get('VOM_weight')}")
    print(f"  B_weight: {weights.get('B_weight')}")
    tc_internal = config.get_factor_weights('TC_internal')
    print(f"  TC内部: T={tc_internal.get('T_weight')}, C={tc_internal.get('C_weight')}")

    print("\nEV计算参数（阶段2.1新增）:")
    print(f"  spread_bps: {config.get_ev_params('spread_bps')}")
    print(f"  impact_bps: {config.get_ev_params('impact_bps')}")
    print(f"  default_RR: {config.get_ev_params('default_RR')}")

    print("\n" + "=" * 60)
