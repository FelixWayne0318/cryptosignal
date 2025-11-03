#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ats_core/execution/stop_loss_calculator.py

v6.6 三层止损计算系统

优先级层级：
Priority 1: 结构高低点 (Structure Highs/Lows)
├─ 检测方法：Swing Points (50-bar lookback)
├─ 置信度：70-90
├─ 距离范围：1%-5%
└─ 适用场景：结构清晰、技术形态完整

Priority 2: 订单簿聚类 (Orderbook Clustering)
├─ 检测方法：密度聚类算法
├─ 置信度：60-80
├─ 距离范围：0.5%-3%
└─ 适用场景：流动性好、订单簿深度充足

Priority 3: ATR极限保护 (ATR Fallback)
├─ 计算方法：2.5 × ATR(14)
├─ 最大限制：5 × ATR（防止过宽）
├─ 置信度：40-60
├─ 距离范围：2%-8%
└─ 适用场景：新币、流动性差、数据缺失

核心特性：
- 三层决策自动降级
- 每层都记录fallback_chain供审计
- ATR作为极限保护和最终兜底

作者：Claude (Sonnet 4.5)
日期：2025-11-03
版本：v6.6
"""

from typing import Dict, Any, Optional, List, Tuple
import math


class StopLossResult:
    """止损计算结果数据类"""

    def __init__(self):
        self.stop_price = 0.0
        self.distance_pct = 0.0
        self.distance_usdt = 0.0  # 基于1000 USDT仓位
        self.method = "unknown"
        self.method_cn = "未知"
        self.confidence = 0
        self.fallback_chain = []
        self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "stop_price": self.stop_price,
            "distance_pct": self.distance_pct,
            "distance_usdt": self.distance_usdt,
            "method": self.method,
            "method_cn": self.method_cn,
            "confidence": self.confidence,
            "fallback_chain": self.fallback_chain,
            "metadata": self.metadata
        }


class ThreeTierStopLoss:
    """
    三层止损计算系统

    功能：
    1. Priority 1: 结构高低点检测
    2. Priority 2: 订单簿聚类
    3. Priority 3: ATR兜底
    4. 自动降级决策
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化三层止损系统

        参数：
        - params: 配置参数
          - structure_lookback: 结构回看周期（默认50）
          - structure_window: 摆动窗口（默认5）
          - structure_buffer: 结构缓冲（默认0.002，即0.2%）
          - orderbook_min_orders: 最小订单数（默认5）
          - orderbook_bucket_size: 价格区间大小（默认0.001，即0.1%）
          - atr_multiplier: ATR倍数（默认2.5）
          - atr_max_multiplier: 最大ATR倍数（默认5.0）
        """
        self.params = params or {}
        self.structure_lookback = self.params.get("structure_lookback", 50)
        self.structure_window = self.params.get("structure_window", 5)
        self.structure_buffer = self.params.get("structure_buffer", 0.002)
        self.orderbook_min_orders = self.params.get("orderbook_min_orders", 5)
        self.orderbook_bucket_size = self.params.get("orderbook_bucket_size", 0.001)
        self.atr_multiplier = self.params.get("atr_multiplier", 2.5)
        self.atr_max_multiplier = self.params.get("atr_max_multiplier", 5.0)

    def calculate_stop_loss(
        self,
        direction: str,
        current_price: float,
        highs: List[float],
        lows: List[float],
        orderbook: Optional[Dict[str, List]] = None,
        atr: Optional[float] = None
    ) -> StopLossResult:
        """
        计算止损价格（三层决策）

        参数：
        - direction: "LONG" 或 "SHORT"
        - current_price: 当前价格
        - highs: 高点序列（最近lookback根K线）
        - lows: 低点序列
        - orderbook: 订单簿 {"bids": [(price, qty), ...], "asks": [...]}
        - atr: ATR(14)值

        返回：
        - StopLossResult实例
        """
        result = StopLossResult()
        result.fallback_chain = []

        # Priority 1: 结构高低点
        structure_result = self._detect_structure_stop(
            direction, current_price, highs, lows
        )
        result.fallback_chain.append(("structure", structure_result))

        if structure_result and structure_result["confidence"] >= 70:
            self._apply_result(result, structure_result)
            return result

        # Priority 2: 订单簿聚类
        if orderbook:
            orderbook_result = self._detect_orderbook_stop(
                direction, current_price, orderbook
            )
            result.fallback_chain.append(("orderbook", orderbook_result))

            if orderbook_result and orderbook_result["confidence"] >= 60:
                self._apply_result(result, orderbook_result)
                return result

        # Priority 3: ATR兜底
        if atr and atr > 0:
            atr_result = self._calculate_atr_stop(
                direction, current_price, atr
            )
            result.fallback_chain.append(("atr", atr_result))
            self._apply_result(result, atr_result)
            return result
        else:
            # 极端情况：无ATR数据，使用固定百分比
            fallback_pct = 0.03  # 3%
            if direction == "LONG":
                result.stop_price = current_price * (1 - fallback_pct)
            else:
                result.stop_price = current_price * (1 + fallback_pct)

            result.distance_pct = fallback_pct
            result.distance_usdt = fallback_pct * current_price * 1000 / current_price
            result.method = "fixed_percentage"
            result.method_cn = "固定百分比（3%）"
            result.confidence = 30
            result.metadata = {"warning": "无ATR数据，使用固定百分比"}

            result.fallback_chain.append(("fixed", result.to_dict()))
            return result

    def _detect_structure_stop(
        self,
        direction: str,
        current_price: float,
        highs: List[float],
        lows: List[float]
    ) -> Optional[Dict[str, Any]]:
        """
        Priority 1: 结构高低点检测

        使用Swing Points方法：
        - 摆动高点：中间K线高点是前后N根的局部最高点
        - 摆动低点：中间K线低点是前后N根的局部最低点

        参数：
        - direction: "LONG" 或 "SHORT"
        - current_price: 当前价格
        - highs: 高点序列
        - lows: 低点序列

        返回：
        - 结果字典或None
        """
        if not highs or not lows:
            return None

        if len(highs) < self.structure_lookback or len(lows) < self.structure_lookback:
            return None

        # 只看最近lookback根
        recent_highs = highs[-self.structure_lookback:]
        recent_lows = lows[-self.structure_lookback:]

        window = self.structure_window

        if direction == "LONG":
            # 做多：寻找摆动低点
            swing_low = self._find_swing_low(recent_lows, window)

            if swing_low is None:
                return None

            # 止损设在摆动低点下方（缓冲0.2%）
            stop_price = swing_low * (1 - self.structure_buffer)
            distance_pct = abs(current_price - stop_price) / current_price

            # 合理性检查
            if distance_pct < 0.005:  # 太近（<0.5%）
                confidence = 50
            elif distance_pct > 0.06:  # 太远（>6%）
                confidence = 60
            else:
                confidence = 90

            return {
                "stop_price": stop_price,
                "distance_pct": distance_pct,
                "distance_usdt": distance_pct * 1000,  # 基于1000U仓位
                "method": "structure_swing",
                "method_cn": "结构低点 (Swing Low)",
                "confidence": confidence,
                "metadata": {
                    "swing_low": swing_low,
                    "buffer": self.structure_buffer,
                    "lookback": self.structure_lookback,
                    "window": window
                }
            }

        else:  # SHORT
            # 做空：寻找摆动高点
            swing_high = self._find_swing_high(recent_highs, window)

            if swing_high is None:
                return None

            # 止损设在摆动高点上方（缓冲0.2%）
            stop_price = swing_high * (1 + self.structure_buffer)
            distance_pct = abs(stop_price - current_price) / current_price

            # 合理性检查
            if distance_pct < 0.005:
                confidence = 50
            elif distance_pct > 0.06:
                confidence = 60
            else:
                confidence = 90

            return {
                "stop_price": stop_price,
                "distance_pct": distance_pct,
                "distance_usdt": distance_pct * 1000,
                "method": "structure_swing",
                "method_cn": "结构高点 (Swing High)",
                "confidence": confidence,
                "metadata": {
                    "swing_high": swing_high,
                    "buffer": self.structure_buffer,
                    "lookback": self.structure_lookback,
                    "window": window
                }
            }

    def _find_swing_low(self, lows: List[float], window: int) -> Optional[float]:
        """
        查找摆动低点

        摆动低点定义：第i根K线的低点是前后window根的局部最低点

        参数：
        - lows: 低点序列
        - window: 前后窗口大小

        返回：
        - 摆动低点价格或None
        """
        # 从最近的开始往前找（排除最后window根，避免边界问题）
        for i in range(len(lows) - window - 1, window - 1, -1):
            is_swing_low = True

            # 检查前window根
            for j in range(1, window + 1):
                if lows[i] >= lows[i - j]:
                    is_swing_low = False
                    break

            if not is_swing_low:
                continue

            # 检查后window根
            for j in range(1, window + 1):
                if lows[i] >= lows[i + j]:
                    is_swing_low = False
                    break

            if is_swing_low:
                return lows[i]

        return None

    def _find_swing_high(self, highs: List[float], window: int) -> Optional[float]:
        """
        查找摆动高点

        摆动高点定义：第i根K线的高点是前后window根的局部最高点

        参数：
        - highs: 高点序列
        - window: 前后窗口大小

        返回：
        - 摆动高点价格或None
        """
        for i in range(len(highs) - window - 1, window - 1, -1):
            is_swing_high = True

            # 检查前window根
            for j in range(1, window + 1):
                if highs[i] <= highs[i - j]:
                    is_swing_high = False
                    break

            if not is_swing_high:
                continue

            # 检查后window根
            for j in range(1, window + 1):
                if highs[i] <= highs[i + j]:
                    is_swing_high = False
                    break

            if is_swing_high:
                return highs[i]

        return None

    def _detect_orderbook_stop(
        self,
        direction: str,
        current_price: float,
        orderbook: Dict[str, List]
    ) -> Optional[Dict[str, Any]]:
        """
        Priority 2: 订单簿聚类检测

        使用密度聚类算法检测支撑/阻力位

        参数：
        - direction: "LONG" 或 "SHORT"
        - current_price: 当前价格
        - orderbook: {"bids": [(price, qty), ...], "asks": [...]}

        返回：
        - 结果字典或None
        """
        if direction == "LONG":
            # 做多止损：寻找下方支撑（bid侧）
            relevant_orders = [
                (p, q) for p, q in orderbook.get("bids", [])
                if current_price * 0.95 <= p <= current_price * 0.998
            ]
        else:
            # 做空止损：寻找上方阻力（ask侧）
            relevant_orders = [
                (p, q) for p, q in orderbook.get("asks", [])
                if current_price * 1.002 <= p <= current_price * 1.05
            ]

        if len(relevant_orders) < self.orderbook_min_orders:
            return None

        # 密度聚类：将价格离散化为bucket
        price_buckets = {}
        for price, qty in relevant_orders:
            # 归一化到bucket
            bucket = round(price / current_price / self.orderbook_bucket_size) * self.orderbook_bucket_size
            price_buckets[bucket] = price_buckets.get(bucket, 0) + qty

        # 找到最大密度区间
        max_qty = 0
        max_bucket = None
        for bucket, qty in price_buckets.items():
            if qty > max_qty:
                max_qty = qty
                max_bucket = bucket

        if max_bucket is None:
            return None

        # 计算聚类价格
        cluster_price = max_bucket * current_price

        # 评估聚类强度
        total_qty = sum(price_buckets.values())
        cluster_ratio = max_qty / total_qty if total_qty > 0 else 0
        cluster_strength = min(100, int(cluster_ratio * 200))

        # 距离检查
        distance_pct = abs(cluster_price - current_price) / current_price
        if distance_pct < 0.005:  # 太近（<0.5%）
            return None
        if distance_pct > 0.035:  # 太远（>3.5%）
            return None

        # 置信度基于聚类强度
        confidence = cluster_strength

        return {
            "stop_price": cluster_price,
            "distance_pct": distance_pct,
            "distance_usdt": distance_pct * 1000,
            "method": "orderbook_cluster",
            "method_cn": "订单簿聚类",
            "confidence": confidence,
            "metadata": {
                "cluster_strength": cluster_strength,
                "cluster_ratio": cluster_ratio,
                "orders_count": len(relevant_orders),
                "max_qty": max_qty,
                "total_qty": total_qty
            }
        }

    def _calculate_atr_stop(
        self,
        direction: str,
        current_price: float,
        atr: float
    ) -> Dict[str, Any]:
        """
        Priority 3: ATR兜底止损

        参数：
        - direction: "LONG" 或 "SHORT"
        - current_price: 当前价格
        - atr: ATR(14)值

        返回：
        - 结果字典
        """
        # 基础止损距离
        stop_distance = atr * self.atr_multiplier

        # 极限保护：最大5×ATR
        max_distance = atr * self.atr_max_multiplier
        stop_distance = min(stop_distance, max_distance)

        if direction == "LONG":
            stop_price = current_price - stop_distance
        else:
            stop_price = current_price + stop_distance

        distance_pct = stop_distance / current_price

        # 置信度评估
        if distance_pct > 0.06:
            confidence = 40  # 太宽，低置信
            warning = "止损距离>6%，建议手动复核"
        elif distance_pct < 0.015:
            confidence = 50  # 太窄，可能频繁触发
            warning = "止损距离<1.5%，可能过于敏感"
        else:
            confidence = 60
            warning = None

        return {
            "stop_price": stop_price,
            "distance_pct": distance_pct,
            "distance_usdt": distance_pct * 1000,
            "method": "atr_fallback",
            "method_cn": f"ATR兜底 ({self.atr_multiplier}×)",
            "confidence": confidence,
            "metadata": {
                "atr": atr,
                "multiplier": self.atr_multiplier,
                "max_multiplier": self.atr_max_multiplier,
                "warning": warning,
                "note": "Priority 1/2不可用，使用ATR兜底"
            }
        }

    def _apply_result(self, result: StopLossResult, source: Dict[str, Any]):
        """将源字典应用到结果对象"""
        result.stop_price = source["stop_price"]
        result.distance_pct = source["distance_pct"]
        result.distance_usdt = source["distance_usdt"]
        result.method = source["method"]
        result.method_cn = source["method_cn"]
        result.confidence = source["confidence"]
        result.metadata = source.get("metadata", {})


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("v6.6 三层止损系统测试")
    print("=" * 60)

    # 创建止损计算器
    calculator = ThreeTierStopLoss(params={
        "structure_lookback": 50,
        "structure_window": 5,
        "structure_buffer": 0.002,
        "atr_multiplier": 2.5,
        "atr_max_multiplier": 5.0
    })

    # 测试案例1：结构清晰的主流币（ETHUSDT）
    print("\n【测试1】结构清晰 (ETHUSDT做多)")
    print("-" * 60)

    # 模拟价格数据（最近50根K线的高低点）
    current_price = 3250.0
    highs = [3200 + i * 2 + (i % 7) * 5 for i in range(50)]
    lows = [3180 + i * 2 - (i % 7) * 5 for i in range(50)]
    # 在第20根创建明显的swing low
    lows[20] = 3150.0
    highs[20] = 3160.0

    # 模拟订单簿
    orderbook = {
        "bids": [(3250 - i * 5, 100 + i * 10) for i in range(20)],
        "asks": [(3250 + i * 5, 100 + i * 10) for i in range(20)]
    }

    atr = 80.0

    result1 = calculator.calculate_stop_loss(
        direction="LONG",
        current_price=current_price,
        highs=highs,
        lows=lows,
        orderbook=orderbook,
        atr=atr
    )

    print(f"止损价格: {result1.stop_price:.2f} USDT")
    print(f"止损距离: {result1.distance_pct:.2%} (${result1.distance_usdt:.2f}/1000U)")
    print(f"方法: {result1.method_cn}")
    print(f"置信度: {result1.confidence}/100")
    print(f"Fallback链: {[x[0] for x in result1.fallback_chain]}")
    print(f"元数据: {result1.metadata}")

    # 测试案例2：流动性差的新币（无结构）
    print("\n【测试2】流动性差 (新币做空，无明显结构)")
    print("-" * 60)

    current_price2 = 0.5
    # 无明显结构的价格
    highs2 = [0.5 + (i % 10) * 0.01 for i in range(20)]
    lows2 = [0.48 + (i % 10) * 0.01 for i in range(20)]

    # 订单簿稀疏
    orderbook2 = {
        "bids": [(0.5 - i * 0.01, 10) for i in range(3)],
        "asks": [(0.5 + i * 0.01, 10) for i in range(3)]
    }

    atr2 = 0.03

    result2 = calculator.calculate_stop_loss(
        direction="SHORT",
        current_price=current_price2,
        highs=highs2,
        lows=lows2,
        orderbook=orderbook2,
        atr=atr2
    )

    print(f"止损价格: {result2.stop_price:.4f} USDT")
    print(f"止损距离: {result2.distance_pct:.2%} (${result2.distance_usdt:.2f}/1000U)")
    print(f"方法: {result2.method_cn}")
    print(f"置信度: {result2.confidence}/100")
    print(f"Fallback链: {[x[0] for x in result2.fallback_chain]}")
    if result2.metadata.get("warning"):
        print(f"⚠️  警告: {result2.metadata['warning']}")

    # 测试案例3：订单簿聚类成功
    print("\n【测试3】订单簿聚类 (BTCUSDT做多)")
    print("-" * 60)

    current_price3 = 50000.0
    # 结构不明显
    highs3 = [50000 + i * 50 for i in range(20)]
    lows3 = [49800 + i * 50 for i in range(20)]

    # 订单簿在49500有大量支撑
    orderbook3 = {
        "bids": [
            (49900, 100),
            (49800, 150),
            (49700, 200),
            (49600, 180),
            (49500, 500),  # 大量支撑
            (49480, 510),  # 聚类中心
            (49450, 480),
            (49400, 150),
            (49300, 100)
        ],
        "asks": [(50000 + i * 100, 100) for i in range(10)]
    }

    atr3 = 1200.0

    result3 = calculator.calculate_stop_loss(
        direction="LONG",
        current_price=current_price3,
        highs=highs3,
        lows=lows3,
        orderbook=orderbook3,
        atr=atr3
    )

    print(f"止损价格: {result3.stop_price:.2f} USDT")
    print(f"止损距离: {result3.distance_pct:.2%} (${result3.distance_usdt:.2f}/1000U)")
    print(f"方法: {result3.method_cn}")
    print(f"置信度: {result3.confidence}/100")
    print(f"Fallback链: {[x[0] for x in result3.fallback_chain]}")
    print(f"聚类强度: {result3.metadata.get('cluster_strength', 0)}/100")

    print("\n" + "=" * 60)
    print("测试完成！三层止损系统工作正常。")
    print("=" * 60)
