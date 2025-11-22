# cs_ext/storage/cryptostore_adapter.py
"""
Cryptostore 数据落盘适配层（轻量骨架版）

设计目标：
- 为 CryptoSignal 提供统一的 "StorageAdapter" 接口
- 可以选择简单本地文件存储（Parquet/CSV/JSON）
- 预留将来与 cryptostore 的深度集成接口

注意：
- 真正的 cryptostore 通常通过独立配置文件和进程运行（配合 cryptofeed）
- 这里不强行直接操作 cryptostore，而是提供一个可演进的适配层
"""

import os
import json
import threading
from dataclasses import dataclass, asdict
from typing import Optional, List, Literal, Dict, Any

import datetime

# 格式转换工具
try:
    from ats_core.utils.format_converter import normalize_symbol, DecisionOutput
    FORMAT_CONVERTER_AVAILABLE = True
except ImportError:
    FORMAT_CONVERTER_AVAILABLE = False
    def normalize_symbol(s): return s


@dataclass
class StorageEvent:
    """
    通用存储事件结构，可以用于：
    - TradeEvent
    - OrderBookEvent
    - 因子快照
    等等
    """
    ts: float
    category: str          # "trade" / "orderbook" / "factor" / "signal" 等
    symbol: str
    payload: dict          # 任意 JSON 可序列化内容


class SimpleFileStorageAdapter:
    """
    一个简单的文件落盘实现：
    - 线程安全
    - 支持 JSON 行格式，便于后续用 pandas / spark / clickhouse 导入
    """

    def __init__(self, base_dir: str = "data/storage", file_format: Literal["jsonl"] = "jsonl"):
        self.base_dir = base_dir
        self.file_format = file_format
        self._lock = threading.Lock()
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_file_path(self, date: datetime.date, category: str) -> str:
        """
        不同日期 + 不同类别存不同文件。
        例如：data/storage/2025-11-22/trade.jsonl
        """
        date_str = date.isoformat()
        dir_path = os.path.join(self.base_dir, date_str)
        os.makedirs(dir_path, exist_ok=True)
        filename = f"{category}.{self.file_format}"
        return os.path.join(dir_path, filename)

    def append_event(self, event: StorageEvent):
        """
        追加事件到对应文件。
        当前实现为 JSON Lines 格式：一行一个 JSON。
        """
        date = datetime.date.fromtimestamp(event.ts)
        file_path = self._get_file_path(date, event.category)

        line = json.dumps(asdict(event), ensure_ascii=False)

        with self._lock:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")


class CryptostoreAdapter:
    """
    未来与 cryptostore 深度集成的占位类。

    当前仅包装 SimpleFileStorageAdapter。
    你可以在后期：
    - 新增与 cryptostore 的队列/redis/kafka 通信
    - 或根据 cryptostore 的 config 生成对应的订阅 & 落盘规则
    """

    def __init__(self, backend: Optional[SimpleFileStorageAdapter] = None):
        if backend is None:
            backend = SimpleFileStorageAdapter()
        self._backend = backend

    def store_trade(self, ts: float, symbol: str, price: float, size: float, side: str):
        event = StorageEvent(
            ts=ts,
            category="trade",
            symbol=symbol,
            payload={
                "price": price,
                "size": size,
                "side": side,
            },
        )
        self._backend.append_event(event)

    def store_orderbook(self, ts: float, symbol: str, bids, asks):
        event = StorageEvent(
            ts=ts,
            category="orderbook",
            symbol=symbol,
            payload={
                "bids": bids,
                "asks": asks,
            },
        )
        self._backend.append_event(event)

    def store_factor_snapshot(self, ts: float, symbol: str, factors: dict):
        """
        factors: 因子名称 -> 因子数值
        """
        event = StorageEvent(
            ts=ts,
            category="factor",
            symbol=symbol,
            payload=factors,
        )
        self._backend.append_event(event)

    def store_signal(self, ts: float, symbol: str, direction: str, strength: float, probability: float, extra: Optional[dict] = None):
        payload = {
            "direction": direction,
            "strength": strength,
            "probability": probability,
        }
        if extra:
            payload.update(extra)

        event = StorageEvent(
            ts=ts,
            category="signal",
            symbol=symbol,
            payload=payload,
        )
        self._backend.append_event(event)

    def store_decision(self, decision: Any):
        """
        存储标准化的四步决策结果

        Args:
            decision: DecisionOutput 或包含标准字段的字典

        使用统一格式标准存储决策，包含：
        - 决策结果 (ACCEPT/REJECT)
        - 交易方向和参数
        - 风险指标
        - 因子分数
        """
        # 从DecisionOutput或dict提取数据
        if FORMAT_CONVERTER_AVAILABLE and hasattr(decision, 'to_dict'):
            data = decision.to_dict()
            ts = decision.timestamp
            symbol = normalize_symbol(decision.symbol)
        elif isinstance(decision, dict):
            data = decision
            ts = decision.get('timestamp', datetime.datetime.now().timestamp())
            symbol = normalize_symbol(decision.get('symbol', 'UNKNOWN'))
        else:
            raise ValueError(f"不支持的决策类型: {type(decision)}")

        # 构建标准payload
        payload = {
            "decision": data.get("decision", "UNKNOWN"),
            "action": data.get("action"),
            "probability": data.get("probability", 0),
            "confidence": data.get("confidence", 0),
            "entry_price": data.get("entry_price"),
            "stop_loss": data.get("stop_loss"),
            "take_profit": data.get("take_profit"),
            "position_size": data.get("position_size", 0.05),
            "risk_reward_ratio": data.get("risk_reward_ratio"),
            "factor_scores": data.get("factor_scores", {}),
            "reject_reason": data.get("reject_reason"),
        }

        event = StorageEvent(
            ts=ts,
            category="decision",
            symbol=symbol,
            payload=payload,
        )
        self._backend.append_event(event)
