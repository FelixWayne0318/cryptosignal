# coding: utf-8
"""
StateManager - 状态持久化和恢复

职责：
- 定期保存Broker状态到文件
- 支持从崩溃恢复
- 记录交易日志用于审计

状态文件格式：
{
    "version": "1.0",
    "timestamp": 1234567890000,
    "broker_state": {...},
    "data_feed_state": {...}
}

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StateManager:
    """
    状态管理器

    配置从config/params.json的paper_trading.reporting读取
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化StateManager

        Args:
            config: 报告配置（paper_trading.reporting）
        """
        # 配置参数
        self.save_interval = config.get("save_state_interval", 300)  # 秒
        self.state_file = config.get("state_file", "data/paper_state.json")
        self.log_interval = config.get("log_interval_minutes", 60)

        # 确保目录存在
        state_dir = os.path.dirname(self.state_file)
        if state_dir:
            os.makedirs(state_dir, exist_ok=True)

        # 交易日志文件
        self.trade_log_file = self.state_file.replace(".json", "_trades.jsonl")

        # 状态
        self._last_save_time = 0
        self._last_log_time = 0

        logger.info(
            f"StateManager初始化: "
            f"state_file={self.state_file}, "
            f"save_interval={self.save_interval}s"
        )

    def save_state(self, broker_state: Dict[str, Any], force: bool = False) -> bool:
        """
        保存状态

        Args:
            broker_state: Broker状态数据
            force: 强制保存（忽略间隔）

        Returns:
            是否保存成功
        """
        current_time = time.time()

        # 检查保存间隔
        if not force and (current_time - self._last_save_time) < self.save_interval:
            return False

        try:
            state = {
                "version": "1.0",
                "timestamp": int(current_time * 1000),
                "saved_at": datetime.now().isoformat(),
                "broker_state": broker_state,
            }

            # 写入临时文件再重命名（原子操作）
            temp_file = self.state_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            os.replace(temp_file, self.state_file)

            self._last_save_time = current_time
            logger.debug(f"状态保存成功: {self.state_file}")
            return True

        except Exception as e:
            logger.error(f"状态保存失败: {e}")
            return False

    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        加载状态

        Returns:
            状态数据或None
        """
        if not os.path.exists(self.state_file):
            logger.info(f"状态文件不存在: {self.state_file}")
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            version = state.get("version", "unknown")
            timestamp = state.get("timestamp", 0)
            saved_at = state.get("saved_at", "unknown")

            logger.info(
                f"状态加载成功: version={version}, "
                f"saved_at={saved_at}"
            )

            return state.get("broker_state")

        except Exception as e:
            logger.error(f"状态加载失败: {e}")
            return None

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        记录交易日志（追加模式）

        Args:
            trade_data: 交易数据
        """
        try:
            trade_data["logged_at"] = datetime.now().isoformat()

            with open(self.trade_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trade_data, ensure_ascii=False) + "\n")

            logger.debug(f"交易日志记录: {trade_data.get('id', 'unknown')}")

        except Exception as e:
            logger.error(f"交易日志记录失败: {e}")

    def log_position_open(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录开仓

        Args:
            position_id: 持仓ID
            symbol: 交易对
            direction: 方向
            entry_price: 入场价
            quantity: 数量
            stop_loss: 止损价
            take_profit: 止盈价
            metadata: 额外元数据
        """
        trade_data = {
            "type": "POSITION_OPEN",
            "id": position_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "timestamp": int(time.time() * 1000),
        }

        if metadata:
            trade_data["metadata"] = metadata

        self.log_trade(trade_data)

    def log_position_close(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        realized_pnl: float,
        realized_pnl_pct: float,
        exit_reason: str,
        holding_minutes: Optional[float] = None
    ) -> None:
        """
        记录平仓

        Args:
            position_id: 持仓ID
            symbol: 交易对
            direction: 方向
            entry_price: 入场价
            exit_price: 出场价
            quantity: 数量
            realized_pnl: 已实现盈亏（USDT）
            realized_pnl_pct: 已实现盈亏（%）
            exit_reason: 退出原因
            holding_minutes: 持仓时长
        """
        trade_data = {
            "type": "POSITION_CLOSE",
            "id": position_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": realized_pnl_pct,
            "exit_reason": exit_reason,
            "holding_minutes": holding_minutes,
            "timestamp": int(time.time() * 1000),
        }

        self.log_trade(trade_data)

    def get_trade_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取交易历史

        Args:
            limit: 返回数量限制

        Returns:
            交易记录列表
        """
        if not os.path.exists(self.trade_log_file):
            return []

        trades = []
        try:
            with open(self.trade_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        trades.append(json.loads(line))

            if limit:
                trades = trades[-limit:]

            return trades

        except Exception as e:
            logger.error(f"读取交易历史失败: {e}")
            return []

    def should_log_status(self) -> bool:
        """
        检查是否应该记录状态日志

        Returns:
            是否应该记录
        """
        current_time = time.time()
        interval_seconds = self.log_interval * 60

        if (current_time - self._last_log_time) >= interval_seconds:
            self._last_log_time = current_time
            return True

        return False

    def clear_state(self) -> None:
        """清除状态文件（用于重置）"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
            logger.info(f"状态文件已删除: {self.state_file}")

        if os.path.exists(self.trade_log_file):
            os.remove(self.trade_log_file)
            logger.info(f"交易日志已删除: {self.trade_log_file}")

    def get_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要

        Returns:
            状态摘要
        """
        trades = self.get_trade_history()

        # 统计
        total_trades = len([t for t in trades if t.get("type") == "POSITION_CLOSE"])
        wins = len([
            t for t in trades
            if t.get("type") == "POSITION_CLOSE" and t.get("realized_pnl", 0) > 0
        ])
        losses = len([
            t for t in trades
            if t.get("type") == "POSITION_CLOSE" and t.get("realized_pnl", 0) <= 0
        ])

        total_pnl = sum([
            t.get("realized_pnl", 0)
            for t in trades
            if t.get("type") == "POSITION_CLOSE"
        ])

        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / total_trades if total_trades > 0 else 0,
            "total_pnl": total_pnl,
            "state_file": self.state_file,
            "trade_log_file": self.trade_log_file,
        }
