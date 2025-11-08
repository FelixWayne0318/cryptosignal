# coding: utf-8
"""
交易记录器 - v7.2阶段2数据采集模块

功能：
1. 记录信号发布时的完整快照
2. 记录实际执行数据（如果有交易）
3. 记录交易最终结果

数据用途：
- 统计校准表优化
- 闸门阈值调整
- 成本模型精细化
"""

import sqlite3
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path


class TradeRecorder:
    """交易记录器 - 采集真实交易数据"""

    def __init__(self, db_path: str = None):
        """
        初始化交易记录器

        Args:
            db_path: SQLite数据库路径（默认为项目根目录下的data/trade_history.db）
        """
        if db_path is None:
            # 自动检测项目根目录
            import os
            project_root = os.path.expanduser("~/cryptosignal")
            db_path = os.path.join(project_root, "data", "trade_history.db")

        self.db_path = db_path

        # 确保data目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 表1: 信号快照
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_snapshots (
            signal_id TEXT PRIMARY KEY,
            timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            confidence REAL,

            -- v7.2因子（JSON存储）
            factors TEXT,
            v72_enhancements TEXT,

            -- 市场状态
            price REAL,
            atr REAL,
            independence REAL,
            market_regime REAL,

            -- 预测值
            predicted_p REAL,
            predicted_ev REAL,
            tp_target REAL,
            sl_target REAL,

            -- 闸门结果
            gate_results TEXT,
            all_gates_passed INTEGER,

            -- 索引
            UNIQUE(signal_id)
        )
        """)

        # 创建索引
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON signal_snapshots(timestamp)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_symbol ON signal_snapshots(symbol)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_side ON signal_snapshots(side)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_confidence ON signal_snapshots(confidence)
        """)

        # 表2: 执行记录（可选，如果有交易）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            actual_entry_price REAL,
            actual_fill_time INTEGER,
            actual_cost_bps REAL,
            cost_breakdown TEXT,

            FOREIGN KEY (signal_id) REFERENCES signal_snapshots(signal_id)
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_exec_signal_id ON execution_records(signal_id)
        """)

        # 表3: 交易结果（可选，如果有交易）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            outcome TEXT,
            exit_price REAL,
            exit_reason TEXT,
            hold_duration_hours REAL,
            pnl_pct REAL,
            pnl_usdt REAL,
            total_cost_bps REAL,
            funding_cost_bps REAL,

            FOREIGN KEY (signal_id) REFERENCES signal_snapshots(signal_id)
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_result_signal_id ON trade_results(signal_id)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_result_outcome ON trade_results(outcome)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_result_timestamp ON trade_results(timestamp)
        """)

        conn.commit()
        conn.close()

    def record_signal_snapshot(self, signal_data: Dict[str, Any]) -> str:
        """
        记录信号发布时的完整快照

        Args:
            signal_data: 信号数据（来自analyze_with_v72_enhancements）

        Returns:
            signal_id: 生成的信号ID
        """
        # 生成signal_id
        timestamp = signal_data.get('timestamp') or int(time.time() * 1000)
        symbol = signal_data.get('symbol', 'UNKNOWN')
        signal_id = f"{symbol}_{timestamp}"

        # 提取核心字段
        side = signal_data.get('side', 'unknown')
        confidence = signal_data.get('weighted_score', 0)

        # v7.2因子
        scores = signal_data.get('scores', {})
        v72_enhancements = signal_data.get('v72_enhancements', {})

        # 市场状态
        price = signal_data.get('price', 0)
        atr = signal_data.get('atr', 0)
        independence = scores.get('I', 50)
        market_regime = signal_data.get('market_regime', 0)

        # 预测值
        predicted_p = v72_enhancements.get('P_calibrated', signal_data.get('probability', 0.5))
        predicted_ev = v72_enhancements.get('EV_net', signal_data.get('expected_value', 0))
        tp_target = signal_data.get('tp_pct', 0.03)
        sl_target = signal_data.get('sl_pct', 0.015)

        # 闸门结果
        gate_results = v72_enhancements.get('gate_results', {})
        all_gates_passed = 1 if v72_enhancements.get('all_gates_passed', False) else 0

        # 插入数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO signal_snapshots (
                signal_id, timestamp, symbol, side, confidence,
                factors, v72_enhancements,
                price, atr, independence, market_regime,
                predicted_p, predicted_ev, tp_target, sl_target,
                gate_results, all_gates_passed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id, timestamp, symbol, side, confidence,
                json.dumps(scores), json.dumps(v72_enhancements),
                price, atr, independence, market_regime,
                predicted_p, predicted_ev, tp_target, sl_target,
                json.dumps(gate_results), all_gates_passed
            ))

            conn.commit()
            print(f"[TradeRecorder] 记录信号快照: {signal_id}")

        except sqlite3.IntegrityError:
            # 信号已存在，跳过
            print(f"[TradeRecorder] 信号已存在: {signal_id}")
            pass

        finally:
            conn.close()

        return signal_id

    def record_execution(self, signal_id: str, execution_data: Dict[str, Any]):
        """
        记录实际执行数据（可选，如果有交易）

        Args:
            signal_id: 信号ID
            execution_data: 执行数据
        """
        timestamp = int(time.time() * 1000)
        actual_entry_price = execution_data.get('fill_price', 0)
        actual_fill_time = execution_data.get('fill_time', timestamp)
        actual_cost_bps = execution_data.get('actual_cost_bps', 0)
        cost_breakdown = execution_data.get('cost_breakdown', {})

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO execution_records (
                signal_id, timestamp, actual_entry_price, actual_fill_time,
                actual_cost_bps, cost_breakdown
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                signal_id, timestamp, actual_entry_price, actual_fill_time,
                actual_cost_bps, json.dumps(cost_breakdown)
            ))

            conn.commit()
            print(f"[TradeRecorder] 记录执行数据: {signal_id}")

        finally:
            conn.close()

    def record_trade_result(self, signal_id: str, result_data: Dict[str, Any]):
        """
        记录交易最终结果（可选，如果有交易）

        Args:
            signal_id: 信号ID
            result_data: 交易结果数据
        """
        timestamp = int(time.time() * 1000)
        outcome = result_data.get('outcome', 'unknown')  # "win", "loss", "breakeven"
        exit_price = result_data.get('exit_price', 0)
        exit_reason = result_data.get('exit_reason', 'unknown')  # "TP", "SL", "timeout"
        hold_duration_hours = result_data.get('hold_duration_hours', 0)
        pnl_pct = result_data.get('pnl_pct', 0)
        pnl_usdt = result_data.get('pnl_usdt', 0)
        total_cost_bps = result_data.get('total_cost_bps', 0)
        funding_cost_bps = result_data.get('funding_cost_bps', 0)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO trade_results (
                signal_id, timestamp, outcome, exit_price, exit_reason,
                hold_duration_hours, pnl_pct, pnl_usdt, total_cost_bps, funding_cost_bps
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id, timestamp, outcome, exit_price, exit_reason,
                hold_duration_hours, pnl_pct, pnl_usdt, total_cost_bps, funding_cost_bps
            ))

            conn.commit()
            print(f"[TradeRecorder] 记录交易结果: {signal_id} - {outcome}")

        finally:
            conn.close()

    def get_signal_count(self) -> int:
        """获取已记录的信号总数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM signal_snapshots")
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def get_recent_signals(self, limit: int = 10) -> list:
        """获取最近的信号记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        SELECT signal_id, timestamp, symbol, side, confidence, predicted_p, predicted_ev, all_gates_passed
        FROM signal_snapshots
        ORDER BY timestamp DESC
        LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "signal_id": row[0],
                "timestamp": row[1],
                "symbol": row[2],
                "side": row[3],
                "confidence": row[4],
                "predicted_p": row[5],
                "predicted_ev": row[6],
                "all_gates_passed": bool(row[7])
            })

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 总信号数
            cursor.execute("SELECT COUNT(*) FROM signal_snapshots")
            total_signals = cursor.fetchone()[0]
        except sqlite3.OperationalError as e:
            # 表不存在，重新初始化数据库
            conn.close()
            self._init_database()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM signal_snapshots")
            total_signals = cursor.fetchone()[0]

        # 通过闸门的信号数
        cursor.execute("SELECT COUNT(*) FROM signal_snapshots WHERE all_gates_passed = 1")
        gates_passed = cursor.fetchone()[0]

        # 平均置信度
        cursor.execute("SELECT AVG(confidence) FROM signal_snapshots WHERE all_gates_passed = 1")
        avg_confidence = cursor.fetchone()[0] or 0

        # 平均预测概率
        cursor.execute("SELECT AVG(predicted_p) FROM signal_snapshots WHERE all_gates_passed = 1")
        avg_predicted_p = cursor.fetchone()[0] or 0

        # 平均预测EV
        cursor.execute("SELECT AVG(predicted_ev) FROM signal_snapshots WHERE all_gates_passed = 1")
        avg_predicted_ev = cursor.fetchone()[0] or 0

        # 多空分布
        cursor.execute("SELECT side, COUNT(*) FROM signal_snapshots WHERE all_gates_passed = 1 GROUP BY side")
        side_distribution = {}
        for row in cursor.fetchall():
            side_distribution[row[0]] = row[1]

        # 交易结果统计（如果有）
        cursor.execute("SELECT COUNT(*) FROM trade_results")
        total_trades = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trade_results WHERE outcome = 'win'")
        wins = cursor.fetchone()[0]

        conn.close()

        return {
            "total_signals": total_signals,
            "gates_passed": gates_passed,
            "gates_pass_rate": gates_passed / total_signals if total_signals > 0 else 0,
            "avg_confidence": avg_confidence,
            "avg_predicted_p": avg_predicted_p,
            "avg_predicted_ev": avg_predicted_ev,
            "side_distribution": side_distribution,
            "total_trades": total_trades,
            "wins": wins,
            "winrate": wins / total_trades if total_trades > 0 else 0
        }


# 全局单例
_recorder_instance = None


def get_recorder(db_path: str = None) -> TradeRecorder:
    """获取TradeRecorder单例"""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = TradeRecorder(db_path)
    return _recorder_instance
