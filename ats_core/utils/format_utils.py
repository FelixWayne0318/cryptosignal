"""
格式化工具函数 - v7.3.2-Full

职责：
1. 安全的浮点数格式化（用于日志输出）
2. 防止日志输出导致系统异常
3. 统一的格式化标准

版本：v7.3.2
作者：Claude Code
日期：2025-11-15
"""

import math
from typing import Union, Any
from ats_core.config.runtime_config import RuntimeConfig


def format_float_safe(value: Any) -> str:
    """
    安全的浮点数格式化（用于日志输出）

    v7.3.2-Full改进：
    - decimals和fallback从RuntimeConfig.get_logging_float_format()读取
    - 不再硬编码默认值
    - 处理各种异常情况（None、NaN、字符串等）

    Args:
        value: 要格式化的值（任意类型）

    Returns:
        格式化后的字符串

    Examples:
        >>> format_float_safe(1.23456)
        '1.23'

        >>> format_float_safe(None)
        'N/A'

        >>> format_float_safe("invalid")
        'N/A'

        >>> format_float_safe(float('nan'))
        'N/A'

        >>> format_float_safe(float('inf'))
        'N/A'

    Note:
        - 配置文件：config/logging.json
        - 可修改decimals（小数位数）和fallback（回退文本）
        - 修改配置后需调用 RuntimeConfig.reload_all() 重新加载
    """
    # 从配置读取格式化参数
    try:
        fmt_cfg = RuntimeConfig.get_logging_float_format()
        decimals = fmt_cfg.get("decimals", 2)
        fallback = fmt_cfg.get("fallback", "N/A")
    except Exception:
        # 配置加载失败时的降级处理
        decimals = 2
        fallback = "N/A"

    # 检查是否为有效数值
    if isinstance(value, (int, float)):
        # 检查NaN和Inf
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return fallback

        # 格式化为指定精度
        try:
            return f"{value:.{decimals}f}"
        except (ValueError, TypeError):
            return fallback

    # 非数值类型
    return fallback


def format_percentage_safe(value: Any, multiply_100: bool = True) -> str:
    """
    安全的百分比格式化（用于日志输出）

    Args:
        value: 要格式化的值（0.0-1.0或0-100）
        multiply_100: 是否乘以100（value为0-1时设为True）

    Returns:
        格式化后的百分比字符串（如 "12.34%"）

    Examples:
        >>> format_percentage_safe(0.1234, multiply_100=True)
        '12.34%'

        >>> format_percentage_safe(12.34, multiply_100=False)
        '12.34%'

        >>> format_percentage_safe(None)
        'N/A'
    """
    if not isinstance(value, (int, float)):
        try:
            fmt_cfg = RuntimeConfig.get_logging_float_format()
            fallback = fmt_cfg.get("fallback", "N/A")
        except Exception:
            fallback = "N/A"
        return fallback

    # 检查NaN和Inf
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            try:
                fmt_cfg = RuntimeConfig.get_logging_float_format()
                fallback = fmt_cfg.get("fallback", "N/A")
            except Exception:
                fallback = "N/A"
            return fallback

    try:
        # 转换为百分比
        pct_value = value * 100 if multiply_100 else value

        # 获取小数位数配置
        fmt_cfg = RuntimeConfig.get_logging_float_format()
        decimals = fmt_cfg.get("decimals", 2)

        return f"{pct_value:.{decimals}f}%"

    except Exception:
        try:
            fmt_cfg = RuntimeConfig.get_logging_float_format()
            fallback = fmt_cfg.get("fallback", "N/A")
        except Exception:
            fallback = "N/A"
        return fallback


def format_integer_safe(value: Any) -> str:
    """
    安全的整数格式化（用于日志输出）

    Args:
        value: 要格式化的值

    Returns:
        格式化后的整数字符串

    Examples:
        >>> format_integer_safe(123.456)
        '123'

        >>> format_integer_safe(None)
        'N/A'
    """
    if isinstance(value, (int, float)):
        # 检查NaN和Inf
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                try:
                    fmt_cfg = RuntimeConfig.get_logging_float_format()
                    fallback = fmt_cfg.get("fallback", "N/A")
                except Exception:
                    fallback = "N/A"
                return fallback

        # 格式化为整数
        try:
            return f"{int(value)}"
        except (ValueError, TypeError, OverflowError):
            pass

    # 非数值类型或转换失败
    try:
        fmt_cfg = RuntimeConfig.get_logging_float_format()
        fallback = fmt_cfg.get("fallback", "N/A")
    except Exception:
        fallback = "N/A"
    return fallback


# 兼容性别名（向后兼容）
safe_float = format_float_safe
safe_percentage = format_percentage_safe
safe_int = format_integer_safe
