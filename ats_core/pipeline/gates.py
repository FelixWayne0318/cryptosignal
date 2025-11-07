# coding: utf-8
"""
四道闸门过滤器（v7.2阶段1）

设计理念：
- 硬过滤：任何一道门不通过，信号直接拒绝
- 分层清晰：数据质量 → 资金支撑 → 系统风险 → 执行成本
- 可审计：每道门都有明确的拒绝原因

四道门：
1. 数据质量门：K线数量、数据完整性
2. F闸门：资金支撑检查（F_dir < -15 → 否决）
3. 市场闸门：系统性风险检查（低独立性+逆势 → 否决）
4. 成本闸门：期望值检查（EV ≤ 0 → 否决）
"""

from typing import Dict, Any, Tuple


class FourGatesFilter:
    """
    四道硬闸门过滤器

    使用方式：
        gates = FourGatesFilter(params)
        pass_all, reason, details = gates.check_all(signal_data)
        if not pass_all:
            print(f"拒绝: {reason}")
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化闸门过滤器

        Args:
            params: 参数配置，包含各个闸门的阈值
        """
        self.params = params or {}

        # 默认参数
        self.defaults = {
            # Gate 1: 数据质量
            "min_bars": 100,                # 最少K线数量

            # Gate 2: F闸门
            "F_threshold": -15,             # F方向值阈值（比v7.1的-20更宽松）

            # Gate 3: 市场闸门
            "I_threshold": 30,              # 独立性阈值
            "market_threshold": 30,         # 市场趋势阈值（±30为强势）

            # Gate 4: 成本闸门
            "min_EV": 0.0,                  # 最小期望值
        }

        self.gate_results = []

    def check_all(self, signal_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        依次检查四道门

        Args:
            signal_data: 信号数据字典，包含：
                - bars: K线数量
                - F_score: F因子分数
                - side_long: 是否做多
                - independence (I): 独立性分数
                - market_regime: 市场趋势
                - EV_net: 净期望值

        Returns:
            (pass: bool, reason: str, gate_details: dict)
        """
        self.gate_results = []

        # Gate 1: 数据质量
        pass_g1, reason_g1 = self._gate_data_quality(signal_data)
        self.gate_results.append({"gate": 1, "name": "data_quality", "pass": pass_g1, "reason": reason_g1})
        if not pass_g1:
            return False, reason_g1, {"failed_gate": 1, "gate_name": "data_quality", "details": self.gate_results}

        # Gate 2: F闸门（资金支撑）
        pass_g2, reason_g2 = self._gate_fund_support(signal_data)
        self.gate_results.append({"gate": 2, "name": "fund_support", "pass": pass_g2, "reason": reason_g2})
        if not pass_g2:
            return False, reason_g2, {"failed_gate": 2, "gate_name": "fund_support", "details": self.gate_results}

        # Gate 3: 市场闸门（系统风险）
        pass_g3, reason_g3 = self._gate_market_risk(signal_data)
        self.gate_results.append({"gate": 3, "name": "market_risk", "pass": pass_g3, "reason": reason_g3})
        if not pass_g3:
            return False, reason_g3, {"failed_gate": 3, "gate_name": "market_risk", "details": self.gate_results}

        # Gate 4: 成本闸门（可执行性）
        pass_g4, reason_g4 = self._gate_execution_cost(signal_data)
        self.gate_results.append({"gate": 4, "name": "execution_cost", "pass": pass_g4, "reason": reason_g4})
        if not pass_g4:
            return False, reason_g4, {"failed_gate": 4, "gate_name": "execution_cost", "details": self.gate_results}

        # 全部通过
        return True, "all_gates_passed", {
            "all_pass": True,
            "details": self.gate_results
        }

    def _gate_data_quality(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Gate 1: 数据质量门

        检查：
        - K线数量是否足够
        - 数据完整性
        """
        min_bars = self.params.get("min_bars", self.defaults["min_bars"])

        bars = data.get('bars', 0)
        if bars < min_bars:
            return False, f"insufficient_bars({bars}<{min_bars})"

        # 可以添加更多数据质量检查
        # 例如：缺口率、延迟等

        return True, f"data_quality_ok(bars={bars})"

    def _gate_fund_support(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Gate 2: F闸门（资金支撑）

        理论：价格运动必须有资金支撑

        检查：
        - 做多时：F_dir < threshold → 拒绝（价格领先资金，追涨）
        - 做空时：F_dir < threshold → 拒绝（价格领先资金，追跌）

        其中 F_dir = F × (1 if 做多 else -1)
        """
        F = data.get('F_score', 0)
        side_long = data.get('side_long', True)

        # 方向相关的F
        F_directional = F if side_long else -F

        # 阈值（可配置）
        F_threshold = self.params.get("F_threshold", self.defaults["F_threshold"])

        if F_directional < F_threshold:
            direction = "做多" if side_long else "做空"
            return False, f"fund_lagging({direction}, F_dir={F_directional:.1f}<{F_threshold})"

        return True, f"fund_ok(F_dir={F_directional:.1f})"

    def _gate_market_risk(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Gate 3: 市场闸门（系统性风险）

        理论：
        - 高独立性币种：可以逆势
        - 低独立性币种：不能逆势（会跟随大盘）

        检查：
        - I < threshold 且 逆势 → 拒绝
        """
        I = data.get('independence', 50)
        market_regime = data.get('market_regime', 0)
        side_long = data.get('side_long', True)

        # 阈值
        I_threshold = self.params.get("I_threshold", self.defaults["I_threshold"])
        market_threshold = self.params.get("market_threshold", self.defaults["market_threshold"])

        # 判断是否逆势
        # 做多 & 市场 < -30 → 逆势
        # 做空 & 市场 > +30 → 逆势
        adverse = (market_regime < -market_threshold and side_long) or \
                  (market_regime > +market_threshold and not side_long)

        # 低独立性 + 逆势 → 拒绝
        if I < I_threshold and adverse:
            direction = "做多" if side_long else "做空"
            return False, f"low_independence_adverse({direction}, I={I:.0f}<{I_threshold}, market={market_regime:.0f})"

        # 通过
        if adverse:
            return True, f"market_ok(逆势但高独立性, I={I:.0f})"
        else:
            return True, f"market_ok(顺势, market={market_regime:.0f})"

    def _gate_execution_cost(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Gate 4: 成本闸门（可执行性）

        理论：只做正期望值的交易

        检查：
        - EV_net ≤ 0 → 拒绝
        """
        EV = data.get('EV_net', 0)
        min_EV = self.params.get("min_EV", self.defaults["min_EV"])

        if EV <= min_EV:
            return False, f"negative_EV({EV:.4f}≤{min_EV})"

        return True, f"EV_ok({EV:.4f})"

    def get_last_results(self) -> list:
        """获取最后一次检查的详细结果"""
        return self.gate_results


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("四道闸门测试")
    print("=" * 60)

    gates = FourGatesFilter()

    # 测试1：正常信号（应通过）
    signal1 = {
        "bars": 150,
        "F_score": 35,
        "side_long": True,
        "independence": 60,
        "market_regime": -20,
        "EV_net": 0.015
    }

    pass1, reason1, details1 = gates.check_all(signal1)
    print(f"\n测试1（正常信号）: {'✅ 通过' if pass1 else '❌ 拒绝'}")
    print(f"  原因: {reason1}")
    print(f"  详情: {details1}")

    # 测试2：F不通过
    signal2 = {
        "bars": 150,
        "F_score": -25,  # F_dir = -25（做多但F负，追涨）
        "side_long": True,
        "independence": 60,
        "market_regime": -20,
        "EV_net": 0.015
    }

    pass2, reason2, details2 = gates.check_all(signal2)
    print(f"\n测试2（F不通过）: {'✅ 通过' if pass2 else '❌ 拒绝'}")
    print(f"  原因: {reason2}")

    # 测试3：市场风险不通过
    signal3 = {
        "bars": 150,
        "F_score": 35,
        "side_long": True,
        "independence": 20,  # 低独立性
        "market_regime": -50,  # 强势熊市
        "EV_net": 0.015
    }

    pass3, reason3, details3 = gates.check_all(signal3)
    print(f"\n测试3（市场风险）: {'✅ 通过' if pass3 else '❌ 拒绝'}")
    print(f"  原因: {reason3}")

    # 测试4：EV不通过
    signal4 = {
        "bars": 150,
        "F_score": 35,
        "side_long": True,
        "independence": 60,
        "market_regime": -20,
        "EV_net": -0.005  # 负EV
    }

    pass4, reason4, details4 = gates.check_all(signal4)
    print(f"\n测试4（负EV）: {'✅ 通过' if pass4 else '❌ 拒绝'}")
    print(f"  原因: {reason4}")

    print("\n" + "=" * 60)
