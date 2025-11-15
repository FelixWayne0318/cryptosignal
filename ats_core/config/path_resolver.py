"""
统一配置路径解析器 - v7.3.2

**目的**: 解决P1-4问题 - cfg.py和RuntimeConfig路径解析不一致

**问题背景**:
- cfg.py使用: os.path.join(_REPO_ROOT, "config", "params.json")
- RuntimeConfig使用: Path(__file__).parent.parent.parent / "config"
- 不同环境(开发/Docker/测试)路径可能不同

**解决方案**:
- 统一的路径解析逻辑
- 支持环境变量覆盖 (CRYPTOSIGNAL_CONFIG_ROOT)
- 支持多种回退策略

**使用示例**:
    from ats_core.config.path_resolver import get_config_root

    # 获取配置根目录
    config_root = get_config_root()
    params_path = config_root / "params.json"

    # 设置自定义配置目录
    set_config_root("/custom/path/to/config")

版本: v7.3.2
作者: Claude Code
创建日期: 2025-11-15
参考: /tmp/revised_fix_plan.md#Phase2-3
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 全局配置根目录缓存
_CONFIG_ROOT: Optional[Path] = None


class ConfigPathError(Exception):
    """配置路径错误异常"""
    pass


def get_config_root() -> Path:
    """
    获取配置文件根目录（统一路径解析）

    解析优先级：
    1. 环境变量 CRYPTOSIGNAL_CONFIG_ROOT（最高优先级）
    2. 全局缓存 _CONFIG_ROOT（如果已通过 set_config_root 设置）
    3. 相对于当前文件的路径（默认）

    Returns:
        Path: 配置目录的绝对路径

    Raises:
        ConfigPathError: 如果配置目录不存在或无法找到

    Examples:
        >>> # 默认使用
        >>> config_root = get_config_root()
        >>> print(config_root)
        /home/user/cryptosignal/config

        >>> # 使用环境变量
        >>> os.environ['CRYPTOSIGNAL_CONFIG_ROOT'] = '/custom/config'
        >>> config_root = get_config_root()
        >>> print(config_root)
        /custom/config
    """
    global _CONFIG_ROOT

    # 优先级1: 环境变量
    if 'CRYPTOSIGNAL_CONFIG_ROOT' in os.environ:
        env_path = Path(os.environ['CRYPTOSIGNAL_CONFIG_ROOT']).resolve()
        logger.debug(f"使用环境变量配置路径: {env_path}")

        if not env_path.exists():
            raise ConfigPathError(
                f"环境变量 CRYPTOSIGNAL_CONFIG_ROOT 指向的目录不存在: {env_path}\n"
                f"请检查环境变量设置或创建该目录"
            )

        if not env_path.is_dir():
            raise ConfigPathError(
                f"环境变量 CRYPTOSIGNAL_CONFIG_ROOT 不是目录: {env_path}"
            )

        return env_path

    # 优先级2: 全局缓存（如果已设置）
    if _CONFIG_ROOT is not None:
        logger.debug(f"使用缓存的配置路径: {_CONFIG_ROOT}")
        return _CONFIG_ROOT

    # 优先级3: 相对于当前文件的默认路径
    # ats_core/config/path_resolver.py -> ats_core/config -> ats_core -> project_root -> config
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent  # path_resolver.py -> config -> ats_core -> project_root
    default_config_root = project_root / "config"

    logger.debug(f"当前文件: {current_file}")
    logger.debug(f"项目根目录: {project_root}")
    logger.debug(f"默认配置路径: {default_config_root}")

    if not default_config_root.exists():
        raise ConfigPathError(
            f"无法找到配置目录。\n"
            f"尝试的路径: {default_config_root}\n"
            f"当前文件: {current_file}\n"
            f"项目根目录: {project_root}\n"
            f"\n"
            f"解决方法：\n"
            f"1. 确保 config/ 目录存在于项目根目录\n"
            f"2. 或者设置环境变量: export CRYPTOSIGNAL_CONFIG_ROOT=/path/to/config\n"
            f"3. 或者调用: set_config_root('/path/to/config')"
        )

    if not default_config_root.is_dir():
        raise ConfigPathError(
            f"配置路径不是目录: {default_config_root}"
        )

    # 缓存默认路径
    _CONFIG_ROOT = default_config_root
    logger.info(f"配置根目录设置为: {_CONFIG_ROOT}")

    return _CONFIG_ROOT


def set_config_root(path: str | Path) -> None:
    """
    手动设置配置文件根目录

    Args:
        path: 配置目录路径（字符串或Path对象）

    Raises:
        ConfigPathError: 如果目录不存在或不是目录

    Examples:
        >>> set_config_root("/custom/config")
        >>> config_root = get_config_root()
        >>> print(config_root)
        /custom/config

    Notes:
        - 此设置会覆盖默认路径
        - 但仍会被环境变量 CRYPTOSIGNAL_CONFIG_ROOT 覆盖
        - 通常用于测试或特殊部署场景
    """
    global _CONFIG_ROOT

    config_path = Path(path).resolve()

    if not config_path.exists():
        raise ConfigPathError(
            f"配置目录不存在: {config_path}\n"
            f"请创建该目录或提供有效路径"
        )

    if not config_path.is_dir():
        raise ConfigPathError(
            f"配置路径不是目录: {config_path}"
        )

    _CONFIG_ROOT = config_path
    logger.info(f"配置根目录已手动设置为: {_CONFIG_ROOT}")


def reset_config_root() -> None:
    """
    重置配置根目录缓存（主要用于测试）

    Examples:
        >>> set_config_root("/custom/config")
        >>> reset_config_root()
        >>> # 下次调用 get_config_root() 会重新计算默认路径
    """
    global _CONFIG_ROOT
    _CONFIG_ROOT = None
    logger.debug("配置根目录缓存已重置")


def get_config_file(filename: str) -> Path:
    """
    获取配置文件的完整路径

    Args:
        filename: 配置文件名（如 "params.json"）

    Returns:
        Path: 配置文件的完整路径

    Raises:
        ConfigPathError: 如果配置目录不存在

    Examples:
        >>> params_path = get_config_file("params.json")
        >>> print(params_path)
        /home/user/cryptosignal/config/params.json

        >>> thresholds_path = get_config_file("signal_thresholds.json")
        >>> print(thresholds_path)
        /home/user/cryptosignal/config/signal_thresholds.json
    """
    config_root = get_config_root()
    return config_root / filename


# 便捷函数：获取常用配置文件路径
def get_params_file() -> Path:
    """获取 params.json 路径"""
    return get_config_file("params.json")


def get_thresholds_file() -> Path:
    """获取 signal_thresholds.json 路径"""
    return get_config_file("signal_thresholds.json")


def get_numeric_stability_file() -> Path:
    """获取 numeric_stability.json 路径"""
    return get_config_file("numeric_stability.json")


def get_factor_ranges_file() -> Path:
    """获取 factor_ranges.json 路径"""
    return get_config_file("factor_ranges.json")


def get_factors_unified_file() -> Path:
    """获取 factors_unified.json 路径"""
    return get_config_file("factors_unified.json")


def get_logging_file() -> Path:
    """获取 logging.json 路径"""
    return get_config_file("logging.json")


def get_binance_credentials_file() -> Path:
    """获取 binance_credentials.json 路径"""
    return get_config_file("binance_credentials.json")


def get_telegram_file() -> Path:
    """获取 telegram.json 路径"""
    return get_config_file("telegram.json")


# 导出接口
__all__ = [
    'get_config_root',
    'set_config_root',
    'reset_config_root',
    'get_config_file',
    'get_params_file',
    'get_thresholds_file',
    'get_numeric_stability_file',
    'get_factor_ranges_file',
    'get_factors_unified_file',
    'get_logging_file',
    'get_binance_credentials_file',
    'get_telegram_file',
    'ConfigPathError',
]
