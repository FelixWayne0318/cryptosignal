# coding: utf-8
"""
V8 六层架构统一格式转换工具

Purpose:
    提供各层之间的数据格式转换函数，确保数据流转一致性

Standard:
    遵循 config/signal_thresholds.json 中的 unified_formats 配置

Version: v1.0.0
Author: Claude Code
Created: 2025-11-22
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import re


# ============ Symbol 格式转换 ============

def normalize_symbol(symbol: str) -> str:
    """
    将任意格式的交易对转换为标准格式: BTCUSDT

    Args:
        symbol: 原始交易对，如 "BTC-USDT-PERP", "BTC/USDT", "btcusdt"

    Returns:
        标准格式: "BTCUSDT"

    Examples:
        >>> normalize_symbol("BTC-USDT-PERP")
        'BTCUSDT'
        >>> normalize_symbol("BTC/USDT")
        'BTCUSDT'
        >>> normalize_symbol("btcusdt")
        'BTCUSDT'
    """
    if not symbol:
        return ""

    # 转大写，移除分隔符和后缀
    result = symbol.upper()
    result = result.replace("-", "").replace("/", "").replace(":", "")
    result = result.replace("PERP", "").replace("SWAP", "")

    return result


def to_ccxt_symbol(symbol: str) -> str:
    """
    将标准格式转换为CCXT格式: BTC/USDT

    Args:
        symbol: 标准格式，如 "BTCUSDT"

    Returns:
        CCXT格式: "BTC/USDT"

    Examples:
        >>> to_ccxt_symbol("BTCUSDT")
        'BTC/USDT'
        >>> to_ccxt_symbol("ETHUSDT")
        'ETH/USDT'
    """
    if "/" in symbol:
        return symbol.upper()

    # 标准化
    s = normalize_symbol(symbol)

    # 查找USDT/BUSD位置
    for quote in ["USDT", "BUSD", "USDC", "BTC", "ETH"]:
        if s.endswith(quote):
            base = s[:-len(quote)]
            return f"{base}/{quote}"

    # 无法解析，返回原值
    return s


def to_cryptofeed_symbol(symbol: str, exchange: str = "binance_futures") -> str:
    """
    将标准格式转换为Cryptofeed格式: BTC-USDT-PERP

    Args:
        symbol: 标准格式，如 "BTCUSDT"
        exchange: 交易所名称

    Returns:
        Cryptofeed格式: "BTC-USDT-PERP"
    """
    s = normalize_symbol(symbol)

    # 查找USDT位置
    for quote in ["USDT", "BUSD"]:
        if s.endswith(quote):
            base = s[:-len(quote)]
            if "futures" in exchange.lower():
                return f"{base}-{quote}-PERP"
            else:
                return f"{base}-{quote}"

    return s


# ============ 时间戳格式转换 ============

def normalize_timestamp(ts: Any) -> float:
    """
    统一时间戳格式为秒(float)

    Args:
        ts: 原始时间戳，可能是秒(float)或毫秒(int)

    Returns:
        秒格式的浮点数

    Examples:
        >>> normalize_timestamp(1732252800000)  # 毫秒
        1732252800.0
        >>> normalize_timestamp(1732252800.123)  # 秒
        1732252800.123
    """
    if ts is None:
        return 0.0

    ts_float = float(ts)

    # 检测是否为毫秒（大于2286年的秒值）
    if ts_float > 1e11:
        return ts_float / 1000.0

    return ts_float


def to_milliseconds(ts: float) -> int:
    """
    将秒格式转换为毫秒

    Args:
        ts: 秒格式时间戳

    Returns:
        毫秒格式整数
    """
    return int(ts * 1000)


# ============ 决策输出标准化 ============

@dataclass
class DecisionOutput:
    """标准化的决策输出格式"""
    symbol: str
    timestamp: float
    decision: str  # "ACCEPT" | "REJECT"
    action: Optional[str]  # "LONG" | "SHORT" | None

    # 交易参数
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: float = 0.05

    # 风险指标
    risk_pct: Optional[float] = None
    reward_pct: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    # 信心指标
    probability: float = 0.0
    confidence: float = 0.0

    # 四步结果
    step1_result: Dict[str, Any] = field(default_factory=dict)
    step2_result: Dict[str, Any] = field(default_factory=dict)
    step3_result: Dict[str, Any] = field(default_factory=dict)
    step4_result: Dict[str, Any] = field(default_factory=dict)

    # 附加信息
    reject_reason: Optional[str] = None
    factor_scores: Dict[str, float] = field(default_factory=dict)

    @property
    def is_valid_trade(self) -> bool:
        """检查是否为有效的交易信号"""
        return (
            self.decision == "ACCEPT"
            and self.entry_price is not None
            and self.stop_loss is not None
            and self.take_profit is not None
            and self.risk_reward_ratio is not None
            and self.risk_reward_ratio >= 1.0
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


def four_step_to_decision_output(
    result: Dict[str, Any],
    timestamp: Optional[float] = None
) -> DecisionOutput:
    """
    将四步决策系统输出转换为标准DecisionOutput

    Args:
        result: run_four_step_decision() 的返回值
        timestamp: 时间戳（可选，默认使用当前时间）

    Returns:
        标准化的DecisionOutput
    """
    import time

    return DecisionOutput(
        symbol=normalize_symbol(result.get("symbol", "")),
        timestamp=timestamp or time.time(),
        decision=result.get("decision", "REJECT"),
        action=result.get("action"),
        entry_price=result.get("entry_price"),
        stop_loss=result.get("stop_loss"),
        take_profit=result.get("take_profit"),
        risk_pct=result.get("risk_pct"),
        reward_pct=result.get("reward_pct"),
        risk_reward_ratio=result.get("risk_reward_ratio"),
        step1_result=result.get("step1_direction", {}),
        step2_result=result.get("step2_timing", {}),
        step3_result=result.get("step3_risk", {}),
        step4_result=result.get("step4_quality", {}),
        reject_reason=result.get("reject_reason"),
        factor_scores=result.get("factor_scores", {}),
        # 从step1提取置信度
        confidence=result.get("step1_direction", {}).get("direction_confidence", 0.0),
        probability=result.get("step1_direction", {}).get("direction_confidence", 0.0),
    )


# ============ 执行信号转换 ============

@dataclass
class ExecutionSignalStandard:
    """标准化的执行信号格式"""
    exchange: str
    symbol: str  # CCXT格式: BTC/USDT
    side: str  # "buy" | "sell"
    quantity: float
    signal_id: str
    order_type: str = "market"
    price: Optional[float] = None
    leverage: Optional[int] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reduce_only: bool = False
    params: Dict[str, Any] = field(default_factory=dict)


def decision_to_execution_signal(
    decision: DecisionOutput,
    quantity: float,
    exchange: str = "binanceusdm",
    signal_id: Optional[str] = None
) -> ExecutionSignalStandard:
    """
    将决策输出转换为执行信号

    Args:
        decision: 标准化的决策输出
        quantity: 订单数量
        exchange: 交易所ID
        signal_id: 信号ID（可选，默认自动生成）

    Returns:
        标准化的执行信号

    Raises:
        ValueError: 如果决策不是有效交易
    """
    import uuid

    if not decision.is_valid_trade:
        raise ValueError(f"无效的交易决策: {decision.decision}, RR={decision.risk_reward_ratio}")

    return ExecutionSignalStandard(
        exchange=exchange,
        symbol=to_ccxt_symbol(decision.symbol),
        side="buy" if decision.action == "LONG" else "sell",
        quantity=quantity,
        signal_id=signal_id or str(uuid.uuid4())[:8],
        price=decision.entry_price,
        stop_loss=decision.stop_loss,
        take_profit=decision.take_profit,
        params={
            "stopLoss": {"triggerPrice": decision.stop_loss},
            "takeProfit": {"triggerPrice": decision.take_profit},
        }
    )


# ============ Telegram 格式转换 ============

def decision_to_telegram_dict(
    decision: DecisionOutput,
    klines: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    将决策输出转换为Telegram v72格式

    Args:
        decision: 标准化的决策输出
        klines: K线数据（用于成交量检查）

    Returns:
        兼容render_signal_v72的字典
    """
    # 构建v72_enhancements
    v72_enhancements = {
        "P_calibrated": decision.probability,
        "EV_net": (decision.risk_reward_ratio or 1.0) - 1.0,
        "F_v2": decision.factor_scores.get("F", 0),
        "I_v2": decision.factor_scores.get("I", 0),
        "momentum_grading": {
            "level": 0,
            "description": ""
        },
        "I_meta": {
            "beta_btc": 0,
            "beta_eth": 0
        },
        "independence_market_analysis": {
            "market_regime": 0,
            "alignment": "顺势" if decision.action == "LONG" else "逆势",
            "confidence_multiplier": decision.confidence
        },
        "group_scores": {
            "TC": (decision.factor_scores.get("T", 0) + decision.factor_scores.get("C", 0)) / 2,
            "VOM": (decision.factor_scores.get("V", 0) + decision.factor_scores.get("O", 0) + decision.factor_scores.get("M", 0)) / 3,
            "B": decision.factor_scores.get("B", 0)
        },
        "gates": {
            "details": []
        }
    }

    return {
        "symbol": decision.symbol,
        "price": decision.entry_price,
        "side": "long" if decision.action == "LONG" else "short",
        "v72_enhancements": v72_enhancements,
        "scores": {
            k: v for k, v in decision.factor_scores.items()
            if k in ["T", "M", "C", "V", "O", "B"]
        },
        "tp_pct": decision.reward_pct or 0.03,
        "sl_pct": decision.risk_pct or 0.015,
        "position_size": decision.position_size,
        "entry_price": decision.entry_price,
        "stop_loss": decision.stop_loss,
        "take_profit": decision.take_profit,
        "risk_reward_ratio": decision.risk_reward_ratio,
        "klines": klines or [],
    }


# ============ 存储格式转换 ============

@dataclass
class StoragePayload:
    """标准化的存储数据格式"""
    timestamp: float
    symbol: str
    category: str  # "trade", "orderbook", "factor", "signal", "decision", "execution"
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.timestamp,
            "symbol": self.symbol,
            "category": self.category,
            "payload": self.data
        }


def decision_to_storage_payload(decision: DecisionOutput) -> StoragePayload:
    """
    将决策输出转换为存储格式

    Args:
        decision: 标准化的决策输出

    Returns:
        存储格式的数据
    """
    return StoragePayload(
        timestamp=decision.timestamp,
        symbol=decision.symbol,
        category="decision",
        data={
            "decision": decision.decision,
            "action": decision.action,
            "probability": decision.probability,
            "confidence": decision.confidence,
            "entry_price": decision.entry_price,
            "stop_loss": decision.stop_loss,
            "take_profit": decision.take_profit,
            "position_size": decision.position_size,
            "risk_reward_ratio": decision.risk_reward_ratio,
            "factor_scores": decision.factor_scores,
            "reject_reason": decision.reject_reason,
        }
    )


# ============ 实时因子映射 ============

def realtime_factors_to_scores(
    cvd_z: float,
    obi: float,
    trade_intensity: float,
    spread_bps: float
) -> Dict[str, float]:
    """
    将实时因子映射到标准因子分数（估算）

    注意：这是简化映射，完整映射需要K线数据

    Args:
        cvd_z: CVD Z-score (-3 to 3)
        obi: 订单簿失衡 (-1 to 1)
        trade_intensity: 交易强度
        spread_bps: 点差（基点）

    Returns:
        估算的因子分数 {"C": float, "V": float, "L": float, ...}
    """
    # CVD → C (资金流向)
    c_score = min(100, max(-100, cvd_z * 33))

    # OBI → L (流动性方向)
    l_score = min(100, max(-100, obi * 100))

    # Trade Intensity → V (量能)
    # 需要归一化，假设正常范围是0-1000
    v_score = min(100, trade_intensity / 10)

    # Spread → 流动性质量（低spread = 高流动性）
    # 典型spread: 1-10 bps
    liquidity_quality = max(0, 100 - spread_bps * 10)

    return {
        "C": c_score,
        "V": v_score,
        "L": l_score,
        "T": 0,  # 需要K线计算
        "M": 0,  # 需要K线计算
        "O": 0,  # 需要持仓数据
        "B": 0,  # 需要资金费率
        "S": 0,  # 需要结构分析
        "I": 0,  # 需要相关性分析
        "F": c_score,  # CVD近似F因子
        "_liquidity_quality": liquidity_quality,
        "_source": "realtime_estimation"
    }


# ============ 测试 ============

if __name__ == "__main__":
    print("=" * 60)
    print("V8 格式转换工具测试")
    print("=" * 60)

    # 测试Symbol转换
    print("\n1. Symbol转换测试:")
    test_symbols = ["BTC-USDT-PERP", "BTC/USDT", "btcusdt", "ETHUSDT"]
    for s in test_symbols:
        print(f"  {s:20} → normalize: {normalize_symbol(s):10} → ccxt: {to_ccxt_symbol(s)}")

    # 测试时间戳转换
    print("\n2. 时间戳转换测试:")
    test_ts = [1732252800000, 1732252800.123, 1732252800]
    for ts in test_ts:
        print(f"  {ts:20} → {normalize_timestamp(ts):.3f} 秒")

    # 测试DecisionOutput
    print("\n3. DecisionOutput测试:")
    decision = DecisionOutput(
        symbol="BTCUSDT",
        timestamp=1732252800.0,
        decision="ACCEPT",
        action="LONG",
        entry_price=95000.0,
        stop_loss=94000.0,
        take_profit=97000.0,
        risk_reward_ratio=2.0,
        probability=0.65,
        confidence=0.8
    )
    print(f"  is_valid_trade: {decision.is_valid_trade}")

    # 测试执行信号转换
    print("\n4. 执行信号转换测试:")
    exec_signal = decision_to_execution_signal(decision, quantity=0.01)
    print(f"  symbol: {exec_signal.symbol}")
    print(f"  side: {exec_signal.side}")
    print(f"  quantity: {exec_signal.quantity}")

    print("\n" + "=" * 60)
    print("✅ 格式转换工具测试完成")
    print("=" * 60)
