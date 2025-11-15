"""
运行时配置中心 - v7.3.2-Full

职责：
1. 统一管理所有配置文件的加载
2. 提供类型安全的配置访问接口
3. 缓存配置，避免重复读取
4. 配置校验，防止误配置导致系统异常

使用示例：
    from ats_core.config.runtime_config import RuntimeConfig

    # 获取数值稳定性配置
    stability = RuntimeConfig.get_numeric_stability("independence")
    eps_var_min = stability["eps_var_min"]

    # 获取因子范围配置
    i_range = RuntimeConfig.get_factor_range("I")
    i_min = i_range["min"]
    i_neutral = i_range["neutral"]

    # 获取日志格式配置
    fmt = RuntimeConfig.get_logging_float_format()
    decimals = fmt["decimals"]

版本：v7.3.2
作者：Claude Code
日期：2025-11-15
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误异常"""
    pass


class RuntimeConfig:
    """
    运行时配置中心（单例模式）

    设计模式：
    - 单例模式：全局唯一配置实例
    - 懒加载：首次访问时才加载配置
    - 缓存：加载后缓存在内存中
    - 校验：加载时验证配置格式和内容
    """

    # 配置文件根目录
    _config_root: Optional[Path] = None

    # 缓存
    _numeric_stability: Optional[Dict] = None
    _factor_ranges: Optional[Dict] = None
    _logging: Optional[Dict] = None

    @classmethod
    def set_config_root(cls, root_path: str):
        """
        设置配置文件根目录

        Args:
            root_path: 配置目录路径

        Raises:
            ConfigError: 目录不存在时抛出
        """
        cls._config_root = Path(root_path)
        if not cls._config_root.exists():
            raise ConfigError(f"配置目录不存在: {cls._config_root}")
        logger.info(f"配置根目录设置为: {cls._config_root}")

    @classmethod
    def get_config_root(cls) -> Path:
        """
        获取配置文件根目录

        Returns:
            配置目录Path对象

        Raises:
            ConfigError: 无法找到config目录时抛出
        """
        if cls._config_root is None:
            # 默认：从当前文件向上找config目录
            current = Path(__file__).parent.parent.parent  # ats_core/config -> ats_core -> root
            config_dir = current / "config"

            if config_dir.exists():
                cls._config_root = config_dir
                logger.debug(f"自动发现配置目录: {cls._config_root}")
            else:
                raise ConfigError(
                    f"无法找到config目录。\n"
                    f"尝试路径: {config_dir}\n"
                    f"请调用 RuntimeConfig.set_config_root() 手动设置"
                )

        return cls._config_root

    @classmethod
    def _load_json(cls, filename: str) -> Dict:
        """
        加载JSON配置文件

        Args:
            filename: 配置文件名（如 "numeric_stability.json"）

        Returns:
            配置字典

        Raises:
            ConfigError: 文件不存在或格式错误时抛出
        """
        config_path = cls.get_config_root() / filename

        if not config_path.exists():
            raise ConfigError(f"配置文件不存在: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.debug(f"已加载配置文件: {config_path}")
            return config
        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件JSON格式错误 {config_path}: {e}")
        except Exception as e:
            raise ConfigError(f"加载配置文件失败 {config_path}: {e}")

    # ========== 数值稳定性配置 ==========

    @classmethod
    def load_numeric_stability(cls) -> Dict:
        """
        加载数值稳定性配置

        Returns:
            配置字典
        """
        if cls._numeric_stability is None:
            config = cls._load_json("numeric_stability.json")
            cls._validate_numeric_stability(config)
            cls._numeric_stability = config
            logger.info("数值稳定性配置加载完成")
        return cls._numeric_stability

    @classmethod
    def _validate_numeric_stability(cls, config: Dict):
        """
        校验数值稳定性配置

        Args:
            config: 配置字典

        Raises:
            ConfigError: 配置格式错误时抛出
        """
        if "numeric_stability" not in config:
            raise ConfigError("numeric_stability.json缺少'numeric_stability'根节点")

        # 校验independence块
        indep = config["numeric_stability"].get("independence", {})
        required_keys = ["eps_var_min", "eps_log_price", "eps_div_safe", "eps_r2_denominator"]

        for key in required_keys:
            if key not in indep:
                raise ConfigError(f"numeric_stability.independence缺少必需字段: {key}")

            value = indep[key]
            if not isinstance(value, (int, float)) or value <= 0:
                raise ConfigError(
                    f"numeric_stability.independence.{key}必须是正数，当前值: {value}"
                )

        logger.debug("数值稳定性配置校验通过")

    @classmethod
    def get_numeric_stability(cls, scope: str = "independence") -> Dict:
        """
        获取数值稳定性配置

        Args:
            scope: 配置范围，如"independence"、"default"

        Returns:
            配置字典，包含eps_var_min、eps_log_price等

        Example:
            >>> stability = RuntimeConfig.get_numeric_stability("independence")
            >>> eps_var_min = stability["eps_var_min"]  # 1e-12
        """
        config = cls.load_numeric_stability()
        stability = config["numeric_stability"]

        if scope not in stability:
            logger.warning(f"数值稳定性配置不存在scope={scope}，使用default")
            scope = "default"

        result = stability.get(scope, {})
        logger.debug(f"获取数值稳定性配置[{scope}]: {len(result)}个参数")
        return result

    # ========== 因子范围配置 ==========

    @classmethod
    def load_factor_ranges(cls) -> Dict:
        """
        加载因子范围配置

        Returns:
            配置字典
        """
        if cls._factor_ranges is None:
            config = cls._load_json("factor_ranges.json")
            cls._validate_factor_ranges(config)
            cls._factor_ranges = config
            logger.info("因子范围配置加载完成")
        return cls._factor_ranges

    @classmethod
    def _validate_factor_ranges(cls, config: Dict):
        """
        校验因子范围配置

        Args:
            config: 配置字典

        Raises:
            ConfigError: 配置格式错误时抛出
        """
        if "factors" not in config:
            raise ConfigError("factor_ranges.json缺少'factors'根节点")

        # 校验I因子配置
        if "I" not in config["factors"]:
            raise ConfigError("factor_ranges.json缺少因子I的配置")

        i_cfg = config["factors"]["I"]
        required_keys = ["min", "max", "neutral", "split_beta_mid"]

        for key in required_keys:
            if key not in i_cfg:
                raise ConfigError(f"factor_ranges.I缺少必需字段: {key}")

        # 校验范围合理性
        i_min = i_cfg["min"]
        i_max = i_cfg["max"]
        i_neutral = i_cfg["neutral"]
        split_beta = i_cfg["split_beta_mid"]

        if i_min >= i_max:
            raise ConfigError(f"I因子范围错误: min={i_min} >= max={i_max}")

        if not (i_min <= i_neutral <= i_max):
            raise ConfigError(
                f"I因子中性值超出范围: neutral={i_neutral} 不在 [{i_min}, {i_max}]"
            )

        if not (0 < split_beta < 2):
            raise ConfigError(f"β分界线不合理: split_beta_mid={split_beta}")

        logger.debug("因子范围配置校验通过")

    @classmethod
    def get_factor_range(cls, factor_name: str) -> Dict:
        """
        获取因子范围配置

        Args:
            factor_name: 因子名称，如"I"、"T"、"M"

        Returns:
            配置字典，包含min、max、neutral、split_beta_mid等

        Raises:
            ConfigError: 因子配置不存在时抛出

        Example:
            >>> i_range = RuntimeConfig.get_factor_range("I")
            >>> i_min = i_range["min"]        # 0
            >>> i_max = i_range["max"]        # 100
            >>> i_neutral = i_range["neutral"] # 50
        """
        config = cls.load_factor_ranges()
        factors = config["factors"]

        if factor_name not in factors:
            raise ConfigError(f"因子范围配置不存在: {factor_name}")

        result = factors[factor_name]
        logger.debug(f"获取因子范围配置[{factor_name}]: {len(result)}个参数")
        return result

    # ========== 日志配置 ==========

    @classmethod
    def load_logging(cls) -> Dict:
        """
        加载日志配置

        Returns:
            配置字典
        """
        if cls._logging is None:
            config = cls._load_json("logging.json")
            cls._validate_logging(config)
            cls._logging = config
            logger.info("日志配置加载完成")
        return cls._logging

    @classmethod
    def _validate_logging(cls, config: Dict):
        """
        校验日志配置

        Args:
            config: 配置字典

        Raises:
            ConfigError: 配置格式错误时抛出
        """
        if "logging" not in config:
            raise ConfigError("logging.json缺少'logging'根节点")

        float_fmt = config["logging"].get("float_format", {})

        if "decimals" in float_fmt:
            decimals = float_fmt["decimals"]
            if not isinstance(decimals, int) or decimals < 0:
                raise ConfigError(
                    f"logging.float_format.decimals必须是非负整数，当前值: {decimals}"
                )

        logger.debug("日志配置校验通过")

    @classmethod
    def get_logging_float_format(cls) -> Dict:
        """
        获取日志浮点数格式配置

        Returns:
            配置字典，包含decimals、fallback

        Example:
            >>> fmt = RuntimeConfig.get_logging_float_format()
            >>> decimals = fmt["decimals"]  # 2
            >>> fallback = fmt["fallback"]  # "N/A"
        """
        config = cls.load_logging()
        result = config["logging"].get("float_format", {
            "decimals": 2,
            "fallback": "N/A"
        })
        logger.debug(f"获取日志格式配置: decimals={result.get('decimals')}")
        return result

    # ========== 工具方法 ==========

    @classmethod
    def reload_all(cls):
        """
        重新加载所有配置（用于测试或热更新）

        Note:
            清空所有缓存，下次访问时将重新从文件加载
        """
        cls._numeric_stability = None
        cls._factor_ranges = None
        cls._logging = None
        logger.info("所有配置缓存已清空，下次访问将重新加载")

    @classmethod
    def get_all_configs(cls) -> Dict[str, Dict]:
        """
        获取所有配置（用于调试）

        Returns:
            包含所有配置的字典

        Example:
            >>> all_cfg = RuntimeConfig.get_all_configs()
            >>> print(all_cfg.keys())
            dict_keys(['numeric_stability', 'factor_ranges', 'logging'])
        """
        return {
            "numeric_stability": cls.load_numeric_stability(),
            "factor_ranges": cls.load_factor_ranges(),
            "logging": cls.load_logging()
        }

    @classmethod
    def validate_all(cls):
        """
        验证所有配置文件（用于测试或部署前检查）

        Raises:
            ConfigError: 任何配置文件无效时抛出
        """
        try:
            cls.load_numeric_stability()
            cls.load_factor_ranges()
            cls.load_logging()
            logger.info("✅ 所有配置文件验证通过")
        except ConfigError as e:
            logger.error(f"❌ 配置文件验证失败: {e}")
            raise
