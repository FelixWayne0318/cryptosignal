#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一风险管理模块

功能：
- 固定风险比例（0.5% per trade）
- Phase差异化乘数（新币降低暴露）
- 单笔风险上限（$6 USDT）
- 冷却时间机制（止损8h，止盈3h）

规范：
- 借鉴外部方案 risk.py 的固定R值思想
- 结合当前系统的 newcoin_phase 分类

使用：
    from ats_core.risk.risk_manager import calculate_position_size, check_cooldown

    size = calculate_position_size(
        account_equity=10000.0,
        atr=2.5,
        tick_value=1.0,
        newcoin_phase='ultra_new_1',
        is_overlay=False
    )
"""
from __future__ import annotations
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

# ==================== 风险参数配置 ====================

# 固定风险比例（每笔交易占账户权益的百分比）
RISK_PCT = 0.005  # 0.5%

# 单笔风险上限（USDT）
RISK_USDT_CAP = 6.0

# Phase差异化乘数（新币风险降低）
PHASE_MULTIPLIER = {
    'ultra_new_0': 0.3,  # 0-3min: 极度保守（强制WATCH，理论上不会下单）
    'ultra_new_1': 0.5,  # 3-8min: 保守
    'ultra_new_2': 0.7,  # 8-15min: 中性
    'mature': 1.0,       # >15min or >7d: 正常
    'fully_mature': 1.0  # >12d: 完全成熟（如启用）
}

# Overlay池乘数（重叠池降低暴露）
OVERLAY_MULTIPLIER = 0.7

# 冷却时间（秒）
COOL_DOWN_SECONDS = {
    'stop_loss': 8 * 3600,    # 止损后8小时
    'take_profit': 3 * 3600,  # 止盈后3小时
    'manual_close': 1 * 3600  # 手动平仓后1小时
}

# 最大并发持仓数
MAX_CONCURRENT_POSITIONS = 3

# 总成本上限（进场费用+滑点，以R计）
MAX_TOTAL_COST_R = 0.12


# ==================== 数据结构 ====================

@dataclass
class PositionCloseRecord:
    """持仓平仓记录"""
    symbol: str
    close_time: int  # 时间戳（秒）
    close_type: str  # 'stop_loss', 'take_profit', 'manual_close'
    pnl_r: float     # 盈亏（以R计）


class RiskManager:
    """风险管理器（单例）"""

    def __init__(self):
        # 平仓记录（symbol → 最近平仓记录）
        self.close_records: Dict[str, PositionCloseRecord] = {}

        # 当前持仓计数
        self.current_positions = 0

    def record_close(
        self,
        symbol: str,
        close_type: str,
        pnl_r: float
    ) -> None:
        """
        记录平仓事件

        Args:
            symbol: 交易对
            close_type: 平仓类型 ('stop_loss', 'take_profit', 'manual_close')
            pnl_r: 盈亏（以R计）
        """
        self.close_records[symbol] = PositionCloseRecord(
            symbol=symbol,
            close_time=int(time.time()),
            close_type=close_type,
            pnl_r=pnl_r
        )

    def check_cooldown(
        self,
        symbol: str,
        now_ts: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        检查冷却时间

        Args:
            symbol: 交易对
            now_ts: 当前时间戳（秒），None则使用当前时间

        Returns:
            (in_cooldown, reason):
                - in_cooldown: True表示在冷却期内
                - reason: 冷却原因（用于日志）
        """
        if now_ts is None:
            now_ts = int(time.time())

        if symbol not in self.close_records:
            return False, ""

        record = self.close_records[symbol]
        elapsed = now_ts - record.close_time
        cooldown_duration = COOL_DOWN_SECONDS.get(record.close_type, 0)

        if elapsed < cooldown_duration:
            remaining = cooldown_duration - elapsed
            remaining_minutes = remaining // 60
            return True, f"冷却期内（{record.close_type}，剩余{remaining_minutes}分钟）"

        return False, ""

    def can_open_position(
        self,
        symbol: str,
        now_ts: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        判断是否可以开仓

        Returns:
            (can_open, reason):
                - can_open: True表示可以开仓
                - reason: 拒绝原因（如果不能开仓）
        """
        # 检查并发持仓数
        if self.current_positions >= MAX_CONCURRENT_POSITIONS:
            return False, f"并发持仓数已达上限({MAX_CONCURRENT_POSITIONS})"

        # 检查冷却时间
        in_cooldown, cooldown_reason = self.check_cooldown(symbol, now_ts)
        if in_cooldown:
            return False, cooldown_reason

        return True, ""


# ==================== 全局单例 ====================
_risk_manager_instance: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    """获取风险管理器单例"""
    global _risk_manager_instance
    if _risk_manager_instance is None:
        _risk_manager_instance = RiskManager()
    return _risk_manager_instance


# ==================== 仓位计算 ====================

def calculate_position_size(
    account_equity: float,
    atr: float,
    tick_value: float,
    newcoin_phase: str = 'mature',
    is_overlay: bool = False,
    risk_pct: float = RISK_PCT,
    risk_cap: float = RISK_USDT_CAP
) -> float:
    """
    计算仓位大小（以R为单位的固定风险）

    Args:
        account_equity: 账户权益（USDT）
        atr: ATR值（用于计算止损距离）
        tick_value: 每tick价值（USDT）
        newcoin_phase: 新币阶段 ('ultra_new_0/1/2', 'mature', 'fully_mature')
        is_overlay: 是否为重叠池
        risk_pct: 风险比例（默认0.005 = 0.5%）
        risk_cap: 单笔风险上限（USDT，默认6.0）

    Returns:
        position_size: 仓位数量（合约张数）

    公式：
        R_dollar = min(account_equity * risk_pct, risk_cap)
        position_size = (R_dollar * phase_mult * overlay_mult) / (atr * tick_value)

    示例：
        >>> calculate_position_size(
        ...     account_equity=10000.0,
        ...     atr=2.5,
        ...     tick_value=1.0,
        ...     newcoin_phase='ultra_new_1',
        ...     is_overlay=False
        ... )
        10.0  # (min(50, 6) * 0.5 * 1.0) / (2.5 * 1.0) = 3.0 / 2.5 = 1.2
    """
    # 计算基础风险金额
    r_dollar = min(float(account_equity) * risk_pct, risk_cap)

    # Phase调整
    phase_mult = PHASE_MULTIPLIER.get(newcoin_phase, 1.0)

    # Overlay调整
    overlay_mult = OVERLAY_MULTIPLIER if is_overlay else 1.0

    # 计算数量（避免除零）
    denominator = max(float(atr) * float(tick_value), 1e-9)
    qty = (r_dollar * phase_mult * overlay_mult) / denominator

    return max(float(qty), 0.0)


def estimate_total_cost_r(
    fee_rate: float = 0.0004,  # Binance Maker 0.02% * 2
    estimated_slippage_bps: float = 3.0  # 预估滑点 3bps
) -> float:
    """
    估算总成本（以R计）

    Args:
        fee_rate: 手续费率（进场+出场）
        estimated_slippage_bps: 预估滑点（bps）

    Returns:
        total_cost_r: 总成本（以R计）

    公式：
        fee_r = fee_rate (e.g., 0.0004 for 0.04%)
        slip_r = estimated_slippage_bps / 10000
        total = fee_r + slip_r

    说明：
        1R = ATR，成本以R为单位便于风险管理
    """
    fee_r = fee_rate
    slip_r = estimated_slippage_bps / 10000.0
    return fee_r + slip_r


def validate_cost_constraint(
    fee_r: float,
    slip_r: float,
    max_cost_r: float = MAX_TOTAL_COST_R
) -> Tuple[bool, str]:
    """
    验证成本约束

    Args:
        fee_r: 手续费（以R计）
        slip_r: 滑点（以R计）
        max_cost_r: 最大总成本（默认0.12R）

    Returns:
        (valid, reason):
            - valid: True表示成本可接受
            - reason: 拒绝原因（如果超限）
    """
    total_cost = fee_r + slip_r

    if total_cost > max_cost_r:
        return False, f"总成本过高: {total_cost:.4f}R > {max_cost_r}R"

    return True, ""


# ==================== 便捷函数 ====================

def check_cooldown(symbol: str) -> Tuple[bool, str]:
    """
    便捷函数：检查冷却时间

    Returns:
        (in_cooldown, reason)
    """
    manager = get_risk_manager()
    return manager.check_cooldown(symbol)


def record_trade_close(symbol: str, close_type: str, pnl_r: float) -> None:
    """
    便捷函数：记录平仓

    Args:
        symbol: 交易对
        close_type: 'stop_loss', 'take_profit', 'manual_close'
        pnl_r: 盈亏（以R计）
    """
    manager = get_risk_manager()
    manager.record_close(symbol, close_type, pnl_r)


def can_open_position(symbol: str) -> Tuple[bool, str]:
    """
    便捷函数：判断是否可以开仓

    Returns:
        (can_open, reason)
    """
    manager = get_risk_manager()
    return manager.can_open_position(symbol)
