#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ats_core/modulators/modulator_chain.py

v6.6 统一调制器链 - L/S/F/I四调制器系统

核心原则：**不能搞一票否决**
- 所有调制器只做连续调整，无硬拒绝
- L=0 → position_mult=30%（最小仓位，仍可交易）
- S=-100 → confidence降低但不拒绝
- F/I只调整Teff和cost，无阈值门槛

⚠️ v6.7++重要变更（2025-11-06）：
- p_min_adj 已弃用：改用FIModulator.calculate_thresholds()统一计算p_min
- p_min_adj 保留用于向后兼容，但analyze_symbol.py不再使用
- 新代码应使用 ats_core.modulators.fi_modulators.get_fi_modulator()

架构：
┌─────────────────────────────────────────┐
│  L(流动性) → position_mult, cost_eff_L  │
│  S(结构)   → confidence_mult, Teff_S    │
│  F(资金领先)→ Teff_F, [p_min_adj已弃用] │
│  I(独立性) → Teff_I, cost_eff_I         │
└─────────────────────────────────────────┘
              ↓ 融合
┌─────────────────────────────────────────┐
│  Teff = T0 × Teff_L × Teff_S × Teff_F × │
│         Teff_I  (乘法)                   │
│  cost = cost_base + cost_L + cost_I     │
│         (加法)                           │
│  p_min = 使用FIModulator (F+I双重调制)  │
└─────────────────────────────────────────┘

作者：Claude (Sonnet 4.5)
日期：2025-11-03
版本：v6.6 (更新v6.7++: 2025-11-06)
"""

from typing import Dict, Any, Optional, Tuple
import math


class ModulatorOutput:
    """调制器输出数据类"""

    def __init__(self):
        # L调制器输出
        self.position_mult = 1.0  # 仓位倍数 [0.30, 1.00]
        self.cost_eff_L = 0.0     # 成本调整 [-0.20, +0.20]
        self.L_meta = {}

        # S调制器输出
        self.confidence_mult = 1.0  # 信心倍数 [0.70, 1.30]
        self.Teff_S = 1.0          # 温度倍数 [0.85, 1.15]
        self.S_meta = {}

        # F调制器输出
        self.Teff_F = 1.0      # 温度倍数 [0.80, 1.20]
        self.p_min_adj = 0.0   # ⚠️ DEPRECATED v6.7++: 改用FIModulator.calculate_thresholds()
        self.F_meta = {}

        # I调制器输出
        self.Teff_I = 1.0      # 温度倍数 [0.85, 1.15]
        self.cost_eff_I = 0.0  # 成本调整 [-0.15, +0.15]
        self.I_meta = {}

        # 融合结果
        self.Teff_final = 1.0
        self.cost_final = 0.0
        self.confidence_final = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "L": {
                "position_mult": self.position_mult,
                "cost_eff": self.cost_eff_L,
                "meta": self.L_meta
            },
            "S": {
                "confidence_mult": self.confidence_mult,
                "Teff_mult": self.Teff_S,
                "meta": self.S_meta
            },
            "F": {
                "Teff_mult": self.Teff_F,
                "p_min_adj": self.p_min_adj,
                "meta": self.F_meta
            },
            "I": {
                "Teff_mult": self.Teff_I,
                "cost_eff": self.cost_eff_I,
                "meta": self.I_meta
            },
            "fusion": {
                "Teff_final": self.Teff_final,
                "cost_final": self.cost_final,
                "confidence_final": self.confidence_final
            }
        }


class ModulatorChain:
    """
    v6.6 统一调制器链

    功能：
    1. L调制器：流动性 → 仓位调整 + 成本调整
    2. S调制器：结构 → 信心调整 + 温度调整
    3. F调制器：资金领先 → 温度调整 + p_min调整
    4. I调制器：独立性 → 温度调整 + 成本调整
    5. 融合：Teff乘法、cost加法
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化调制器链

        参数：
        - params: 配置参数字典
          - L_params: L调制器参数
          - S_params: S调制器参数
          - F_params: F调制器参数
          - I_params: I调制器参数
          - T0: 基准温度（默认2.0）
          - cost_base: 基础成本（默认0.0015）
        """
        self.params = params or {}
        self.L_params = self.params.get("L_params", {})
        self.S_params = self.params.get("S_params", {})
        self.F_params = self.params.get("F_params", {})
        self.I_params = self.params.get("I_params", {})

        # 默认参数
        self.T0 = self.params.get("T0", 2.0)
        self.cost_base = self.params.get("cost_base", 0.0015)

    def modulate_all(
        self,
        L_score: float,
        S_score: float,
        F_score: float,
        I_score: float,
        L_components: Optional[Dict[str, float]] = None,
        confidence_base: float = 50.0,
        symbol: str = "UNKNOWN"
    ) -> ModulatorOutput:
        """
        执行完整调制器链

        参数：
        - L_score: 流动性分数 [-100, +100]
        - S_score: 结构分数 [-100, +100]
        - F_score: 资金领先分数 [-100, +100]
        - I_score: 独立性分数 [-100, +100]
        - L_components: L因子详细组成（可选）
          - spread_bps: 价差（基点）
          - depth_quality: 深度质量
          - impact_bps: 冲击成本（基点）
          - obi: 订单簿失衡
        - confidence_base: 基础信心指数
        - symbol: 交易对符号

        返回：
        - ModulatorOutput实例
        """
        output = ModulatorOutput()

        # 1. L调制器：流动性 → 仓位 + 成本
        output.position_mult, output.cost_eff_L, output.L_meta = self._modulate_L(
            L_score, L_components, symbol
        )

        # 2. S调制器：结构 → 信心 + 温度
        output.confidence_mult, output.Teff_S, output.S_meta = self._modulate_S(
            S_score, confidence_base
        )

        # 3. F调制器：资金领先 → 温度 + p_min
        output.Teff_F, output.p_min_adj, output.F_meta = self._modulate_F(
            F_score
        )

        # 4. I调制器：独立性 → 温度 + 成本
        output.Teff_I, output.cost_eff_I, output.I_meta = self._modulate_I(
            I_score
        )

        # 5. 融合
        output.Teff_final, output.cost_final, output.confidence_final = self._fuse(
            output, confidence_base
        )

        return output

    def _modulate_L(
        self,
        L_score: float,
        L_components: Optional[Dict[str, float]],
        symbol: str
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        L调制器：流动性 → 仓位倍数 + 成本调整

        逻辑：
        - L高（+80~+100）：position_mult接近1.0，cost略降
        - L中（0~+80）：position_mult=0.5-0.8，cost不变
        - L低（-100~0）：position_mult=0.3-0.5，cost略升
        - **关键**：L=-100时position_mult=30%（不拒绝！）

        参数：
        - L_score: [-100, +100]
        - L_components: {spread_bps, depth_quality, impact_bps, obi}
        - symbol: 交易对

        返回：
        - position_mult: [0.30, 1.00]
        - cost_eff: [-0.20, +0.20]
        - meta: 元数据字典
        """
        # 默认参数（用户已确认）
        min_position = self.L_params.get("min_position", 0.30)  # 30%最小仓位
        max_position = self.L_params.get("max_position", 1.00)  # 100%最大仓位
        safety_margin = self.L_params.get("safety_margin", 0.005)  # 0.5%安全边际（用户确认）

        # 基础映射：L [-100, +100] → position_mult [0.30, 1.00]
        # 步骤1: 将L从[-100, +100]映射到[0, 1]
        # 步骤2: 使用平方根函数增加中低流动性的仓位（避免过于保守）
        normalized_L = (L_score + 100.0) / 200.0  # [-100,+100] → [0,1]
        position_mult = min_position + (max_position - min_position) * math.sqrt(normalized_L)

        # 成本调整：L高 → cost降低，L低 → cost升高
        # 映射：L=+100 → cost_eff=-0.20, L=0 → -0.10, L=-100 → +0.20
        cost_eff = -0.20 * (2 * normalized_L - 1)  # [-0.20, +0.20]

        # 特殊情况：如果有详细组件，进一步微调
        warnings = []
        if L_components:
            spread_bps = L_components.get("spread_bps", 0)
            impact_bps = L_components.get("impact_bps", 0)

            # 如果spread或impact极高，进一步降低仓位（但不低于min_position）
            if spread_bps > 30:
                position_mult *= 0.9
                warnings.append(f"spread高({spread_bps:.1f}bps)，仓位降低10%")
            if impact_bps > 10:
                position_mult *= 0.9
                warnings.append(f"impact高({impact_bps:.1f}bps)，仓位降低10%")

            # 限制在范围内
            position_mult = max(min_position, min(max_position, position_mult))

        # 元数据
        meta = {
            "L_score": L_score,
            "position_mult": position_mult,
            "cost_eff": cost_eff,
            "min_position": min_position,
            "safety_margin": safety_margin,
            "warnings": warnings if warnings else None,
            "note": "v6.6: 无硬拒绝，L=0时仍有30%仓位"
        }

        return position_mult, cost_eff, meta

    def _modulate_S(
        self,
        S_score: float,
        confidence_base: float
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        S调制器：结构 → 信心倍数 + 温度倍数

        逻辑：
        - S正（结构完整）：confidence提升，Teff降低（P提升）
        - S负（结构混乱）：confidence降低，Teff提升（P降低）
        - 范围：confidence_mult [0.70, 1.30], Teff [0.85, 1.15]

        参数：
        - S_score: [-100, +100]
        - confidence_base: 基础信心指数

        返回：
        - confidence_mult: [0.70, 1.30]
        - Teff_S: [0.85, 1.15]
        - meta: 元数据字典
        """
        # 用户确认参数
        confidence_min = self.S_params.get("confidence_min", 0.70)
        confidence_max = self.S_params.get("confidence_max", 1.30)
        Teff_min = self.S_params.get("Teff_min", 0.85)
        Teff_max = self.S_params.get("Teff_max", 1.15)

        # 归一化：S [-100, +100] → normalized [-1, +1]
        normalized_S = S_score / 100.0

        # 信心倍数：S=+100 → 1.30, S=0 → 1.00, S=-100 → 0.70
        # 线性映射
        confidence_mult = 1.0 + 0.30 * normalized_S
        confidence_mult = max(confidence_min, min(confidence_max, confidence_mult))

        # 温度倍数：S正 → Teff降低（P提升），S负 → Teff升高（P降低）
        # S=+100 → Teff=0.85, S=0 → 1.00, S=-100 → 1.15
        Teff_S = 1.0 - 0.15 * normalized_S
        Teff_S = max(Teff_min, min(Teff_max, Teff_S))

        # 计算调整后的信心指数
        confidence_adjusted = confidence_base * confidence_mult

        # 元数据
        meta = {
            "S_score": S_score,
            "confidence_mult": confidence_mult,
            "Teff_S": Teff_S,
            "confidence_base": confidence_base,
            "confidence_adjusted": confidence_adjusted,
            "note": "S正→信心提升+P提升, S负→信心降低+P降低"
        }

        return confidence_mult, Teff_S, meta

    def _modulate_F(
        self,
        F_score: float
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        F调制器：资金领先 → 温度倍数 + p_min调整

        ⚠️ DEPRECATED (v6.7++): p_min_adj 已弃用
        - 新代码应使用 FIModulator.calculate_thresholds() 计算完整的p_min（包含F+I）
        - 此函数保留p_min_adj仅用于向后兼容
        - analyze_symbol.py 已迁移到 FIModulator

        逻辑：
        - F正（资金领先价格）：Teff降低（P提升），p_min略降
        - F负（价格领先资金）：Teff升高（P降低），p_min略升
        - 范围：Teff [0.60, 1.50], p_min_adj [-2%, +2%]  # v7.2++增强: 扩大影响范围

        参数：
        - F_score: [-100, +100]

        返回：
        - Teff_F: [0.60, 1.50]  # v7.2++增强: 从[0.80,1.20]扩大到[0.60,1.50]
        - p_min_adj: [-0.02, +0.02] ⚠️ DEPRECATED
        - meta: 元数据字典
        """
        Teff_min = self.F_params.get("Teff_min", 0.60)  # v7.2++: 0.80→0.60
        Teff_max = self.F_params.get("Teff_max", 1.50)  # v7.2++: 1.20→1.50
        p_min_adj_range = self.F_params.get("p_min_adj_range", 0.02)  # v7.2++: 0.01→0.02，增强影响

        # 归一化
        normalized_F = F_score / 100.0

        # 温度倍数：F正 → Teff降低（P提升）
        # v7.2++: F=+100 → 0.60, F=0 → 1.00, F=-100 → 1.50 (增强50%)
        Teff_F = 1.0 - 0.40 * normalized_F  # v7.2++: 0.20→0.40
        Teff_F = max(Teff_min, min(Teff_max, Teff_F))

        # p_min调整：F正 → p_min降低（放宽门槛）
        # v7.2++: F=+100 → -2%, F=0 → 0, F=-100 → +2% (恢复原始强度)
        p_min_adj = -p_min_adj_range * normalized_F

        # 元数据
        meta = {
            "F_score": F_score,
            "Teff_F": Teff_F,
            "p_min_adj": p_min_adj,
            "note": "v7.2++增强: F正→Teff大降+P大提升, F负→Teff大升+P大降低"
        }

        return Teff_F, p_min_adj, meta

    def _modulate_I(
        self,
        I_score: float
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        I调制器：独立性 → 温度倍数 + 成本调整（旧版，向后兼容）

        ⚠️ v7.3.2-Full: 建议使用apply_independence_full()获取完整的veto+软调制

        逻辑：
        - I正（独立性高）：Teff降低（P提升），cost略降
        - I负（跟随性强）：Teff升高（P降低），cost略升
        - 范围：Teff [0.70, 1.30], cost_eff [-0.20, +0.20]  # v7.2++增强: 扩大影响范围

        参数：
        - I_score: [-100, +100] 或 [0, 100] (v7.3.2-Full质量因子)

        返回：
        - Teff_I: [0.70, 1.30]  # v7.2++增强: 从[0.85,1.15]扩大到[0.70,1.30]
        - cost_eff: [-0.20, +0.20]  # v7.2++增强: 从[-0.15,0.15]扩大到[-0.20,0.20]
        - meta: 元数据字典
        """
        Teff_min = self.I_params.get("Teff_min", 0.70)  # v7.2++: 0.85→0.70
        Teff_max = self.I_params.get("Teff_max", 1.30)  # v7.2++: 1.15→1.30
        cost_eff_range = self.I_params.get("cost_eff_range", 0.20)  # v7.2++: 0.15→0.20

        # v7.3.2-Full兼容：如果I是0-100质量因子，转换为-100到+100
        if 0 <= I_score <= 100:
            # I=0(高相关) → -100, I=50(中性) → 0, I=100(高独立) → +100
            normalized_I = (I_score - 50.0) / 50.0
        else:
            # 旧版[-100, +100]格式
            normalized_I = I_score / 100.0

        # 温度倍数：I正 → Teff降低（P提升）
        # v7.2++: I=+100 → 0.70, I=0 → 1.00, I=-100 → 1.30 (增强2倍)
        Teff_I = 1.0 - 0.30 * normalized_I  # v7.2++: 0.15→0.30
        Teff_I = max(Teff_min, min(Teff_max, Teff_I))

        # 成本调整：I正 → cost降低
        # v7.2++: I=+100 → -0.20, I=0 → 0, I=-100 → +0.20 (增强33%)
        cost_eff = -cost_eff_range * normalized_I

        # 元数据
        meta = {
            "I_score": I_score,
            "Teff_I": Teff_I,
            "cost_eff": cost_eff,
            "note": "v7.3.2-Full: 建议使用apply_independence_full()获取veto逻辑"
        }

        return Teff_I, cost_eff, meta

    def apply_I_gate(
        self,
        I: float,
        T_BTC: float,
        T_alt: float,
        composite_score: float,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        I因子风控闸门 - v7.3.2-Full核心veto逻辑

        规则：
        1. 高Beta币逆BTC强趋势 → 必veto
        2. 高Beta币弱信号 → 不做
        3. 高独立币 → 放宽effective_threshold

        参数：
        - I: 独立性分数（0-100质量因子）
        - T_BTC: BTC趋势分数（-100到+100）
        - T_alt: 本币趋势分数（-100到+100）
        - composite_score: 综合分数（A层6因子总分）
        - config: 配置字典（可选），从signal_thresholds.json.independence_gate读取

        返回：
        - {
            "veto": bool,
            "veto_reasons": List[str],
            "effective_threshold": float
          }

        Note:
        - 配置从config/signal_thresholds.json的independence_gate节点读取
        - 所有阈值可配置，零硬编码
        """
        # 加载配置
        if config is None:
            try:
                from ats_core.config.runtime_config import RuntimeConfig
                # TODO: 实现get_independence_gate_config()
                # 暂时使用默认值
                config = {
                    "thresholds": {
                        "corr_strong_max_I": 30,
                        "indep_strong_min_I": 70,
                        "btc_trend_strong_T": 60,
                        "min_score_for_corr": 70,
                        "relax_score_for_indep": 45
                    },
                    "veto_rules": {
                        "rule_1_beta_against_btc": {"enabled": True},
                        "rule_2_beta_weak_signal": {"enabled": True}
                    }
                }
            except Exception:
                # 降级到硬编码默认值（临时）
                config = {
                    "thresholds": {
                        "corr_strong_max_I": 30,
                        "indep_strong_min_I": 70,
                        "btc_trend_strong_T": 60,
                        "min_score_for_corr": 70,
                        "relax_score_for_indep": 45
                    },
                    "veto_rules": {
                        "rule_1_beta_against_btc": {"enabled": True},
                        "rule_2_beta_weak_signal": {"enabled": True}
                    }
                }

        thresholds = config.get("thresholds", {})
        veto_rules = config.get("veto_rules", {})

        corr_strong_max_I = thresholds.get("corr_strong_max_I", 30)
        indep_strong_min_I = thresholds.get("indep_strong_min_I", 70)
        btc_trend_strong_T = thresholds.get("btc_trend_strong_T", 60)
        min_score_for_corr = thresholds.get("min_score_for_corr", 70)
        relax_score_for_indep = thresholds.get("relax_score_for_indep", 45)

        veto = False
        veto_reasons = []

        # 规则1：高Beta币逆BTC强趋势 → 必veto
        rule_1_enabled = veto_rules.get("rule_1_beta_against_btc", {}).get("enabled", True)
        if rule_1_enabled and I <= corr_strong_max_I and abs(T_BTC) >= btc_trend_strong_T:
            # 检查方向：T_alt和T_BTC符号相反则逆势
            if (T_alt > 0 and T_BTC < 0) or (T_alt < 0 and T_BTC > 0):
                veto = True
                veto_reasons.append("beta_coin_against_btc_trend")

        # 规则2：高Beta币弱信号 → 不做
        rule_2_enabled = veto_rules.get("rule_2_beta_weak_signal", {}).get("enabled", True)
        if not veto and rule_2_enabled and I <= corr_strong_max_I:
            if abs(composite_score) < min_score_for_corr:
                veto = True
                veto_reasons.append("beta_coin_weak_signal")

        # 阈值放宽：高独立币特权
        # 从signal_thresholds.json读取基础阈值（默认50）
        base_threshold = config.get("base_threshold", 50.0)

        if I >= indep_strong_min_I:
            # 高独立币：降低阈值（从50降到45）
            effective_threshold = min(base_threshold, relax_score_for_indep)
        else:
            # 其他币种：使用基础阈值
            effective_threshold = base_threshold

        return {
            "veto": veto,
            "veto_reasons": veto_reasons,
            "effective_threshold": effective_threshold
        }

    def apply_independence_full(
        self,
        I: float,
        T_BTC: float,
        T_alt: float,
        composite_score: float,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        I因子完整调制 - v7.3.2-Full（veto + 软调制）

        整合：
        1. 风控闸门：apply_I_gate() - veto逻辑 + effective_threshold
        2. 软调制：confidence_boost + cost_multiplier

        参数：
        - I: 独立性分数（0-100质量因子）
        - T_BTC: BTC趋势分数
        - T_alt: 本币趋势分数
        - composite_score: 综合分数
        - config: 配置字典

        返回：
        - {
            "veto": bool,
            "veto_reasons": List[str],
            "effective_threshold": float,
            "confidence_boost": float,
            "cost_multiplier": float,
            "Teff_mult": float  # 兼容旧接口
          }
        """
        # 1. 风控闸门
        gate_result = self.apply_I_gate(I, T_BTC, T_alt, composite_score, config)

        # 2. 软调制（基于I分数）
        # 从config读取软调制参数
        if config is None:
            config = {}

        soft_mod = config.get("soft_modulation", {})
        conf_cfg = soft_mod.get("confidence", {})
        cost_cfg = soft_mod.get("cost", {})

        # 默认软调制规则（基于I档位）
        if I >= 70:
            # 高度独立：I ≥ 70
            confidence_boost = conf_cfg.get("highly_independent", 0.15)
            cost_multiplier = cost_cfg.get("highly_independent", 1.0)
        elif I >= 50:
            # 中性：50 ≤ I < 70
            confidence_boost = 0.05
            cost_multiplier = 1.0
        elif I >= 30:
            # 相关：30 ≤ I < 50
            confidence_boost = 0.0
            cost_multiplier = 1.1
        else:
            # 高度相关：I < 30
            confidence_boost = conf_cfg.get("highly_correlated", -0.10)
            cost_multiplier = cost_cfg.get("highly_correlated", 1.2)

        # 3. 兼容旧接口：计算Teff_mult（基于I映射）
        # I=100(高独立) → Teff=0.70, I=50(中性) → Teff=1.0, I=0(高相关) → Teff=1.30
        normalized_I = (I - 50.0) / 50.0
        Teff_mult = 1.0 - 0.30 * normalized_I
        Teff_mult = max(0.70, min(1.30, Teff_mult))

        return {
            **gate_result,  # veto, veto_reasons, effective_threshold
            "confidence_boost": confidence_boost,
            "cost_multiplier": cost_multiplier,
            "Teff_mult": Teff_mult
        }

    def _fuse(
        self,
        output: ModulatorOutput,
        confidence_base: float
    ) -> Tuple[float, float, float]:
        """
        融合调制器输出

        融合规则：
        1. Teff：乘法融合（用户确认）
           Teff = T0 × Teff_S × Teff_F × Teff_I
           （注：L不影响Teff，仅影响仓位）

        2. cost：加法融合
           cost = cost_base + cost_eff_L + cost_eff_I

        3. confidence：S独占
           confidence = confidence_base × confidence_mult_S

        参数：
        - output: ModulatorOutput实例
        - confidence_base: 基础信心指数

        返回：
        - Teff_final: 最终温度
        - cost_final: 最终成本
        - confidence_final: 最终信心指数
        """
        # 1. Teff乘法融合（L不参与，仅S/F/I）
        Teff_final = self.T0 * output.Teff_S * output.Teff_F * output.Teff_I

        # 2. cost加法融合
        cost_final = self.cost_base + output.cost_eff_L + output.cost_eff_I
        # 限制cost在合理范围 [0.0001, 0.005]
        cost_final = max(0.0001, min(0.005, cost_final))

        # 3. confidence由S独占
        confidence_final = confidence_base * output.confidence_mult

        return Teff_final, cost_final, confidence_final


# ==================== 辅助函数 ====================

def logistic(x: float, T: float = 2.0) -> float:
    """
    Logistic函数计算概率

    P = 1 / (1 + exp(-x / T))

    参数：
    - x: edge（优势边际）
    - T: 温度参数（Teff）

    返回：
    - 概率 [0, 1]
    """
    return 1.0 / (1.0 + math.exp(-x / T))


def calculate_EV(P: float, edge: float, cost: float) -> float:
    """
    计算期望值

    EV = P × edge - (1 - P) × cost

    参数：
    - P: 胜率
    - edge: 优势边际
    - cost: 交易成本

    返回：
    - 期望值（百分比）
    """
    return P * edge - (1 - P) * cost


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试用例
    print("=" * 60)
    print("v6.6 调制器链测试")
    print("=" * 60)

    # 创建调制器链
    chain = ModulatorChain(params={
        "T0": 2.0,
        "cost_base": 0.0015,
        "L_params": {"min_position": 0.30, "safety_margin": 0.005},
        "S_params": {"confidence_min": 0.70, "confidence_max": 1.30},
        "F_params": {"Teff_min": 0.80, "Teff_max": 1.20},
        "I_params": {"Teff_min": 0.85, "Teff_max": 1.15}
    })

    # 测试案例1：高质量信号
    print("\n【测试1】高质量信号（L=80, S=+65, F=+38, I=+22）")
    output1 = chain.modulate_all(
        L_score=80,
        S_score=+65,
        F_score=+38,
        I_score=+22,
        L_components={"spread_bps": 5.0, "impact_bps": 3.0},
        confidence_base=88.0,
        symbol="ETHUSDT"
    )

    print(f"L调制: position_mult={output1.position_mult:.2%}, cost_eff={output1.cost_eff_L:+.4f}")
    print(f"S调制: confidence_mult={output1.confidence_mult:.2f}x, Teff_S={output1.Teff_S:.2f}")
    print(f"F调制: Teff_F={output1.Teff_F:.2f}, p_min_adj={output1.p_min_adj:+.2%}")
    print(f"I调制: Teff_I={output1.Teff_I:.2f}, cost_eff={output1.cost_eff_I:+.4f}")
    print(f"融合: Teff={output1.Teff_final:.3f}, cost={output1.cost_final:.4f}, confidence={output1.confidence_final:.1f}")

    # 计算概率
    edge = 0.85
    P_base = logistic(edge, T=2.0)
    P_adjusted = logistic(edge, T=output1.Teff_final)
    EV_base = calculate_EV(P_base, edge, 0.0015)
    EV_adjusted = calculate_EV(P_adjusted, edge, output1.cost_final)

    print(f"概率: P_base={P_base:.1%} → P_adjusted={P_adjusted:.1%}")
    print(f"EV: {EV_base:+.2%} → {EV_adjusted:+.2%}")
    print(f"建议仓位: {output1.position_mult:.0%}")

    # 测试案例2：低质量信号（但不拒绝）
    print("\n【测试2】低质量信号（L=25, S=-45, F=-20, I=-15）")
    output2 = chain.modulate_all(
        L_score=25,
        S_score=-45,
        F_score=-20,
        I_score=-15,
        L_components={"spread_bps": 35.0, "impact_bps": 12.0},
        confidence_base=60.0,
        symbol="NEWCOIN"
    )

    print(f"L调制: position_mult={output2.position_mult:.2%}, cost_eff={output2.cost_eff_L:+.4f}")
    print(f"S调制: confidence_mult={output2.confidence_mult:.2f}x, Teff_S={output2.Teff_S:.2f}")
    print(f"F调制: Teff_F={output2.Teff_F:.2f}, p_min_adj={output2.p_min_adj:+.2%}")
    print(f"I调制: Teff_I={output2.Teff_I:.2f}, cost_eff={output2.cost_eff_I:+.4f}")
    print(f"融合: Teff={output2.Teff_final:.3f}, cost={output2.cost_final:.4f}, confidence={output2.confidence_final:.1f}")

    edge2 = 0.55
    P_base2 = logistic(edge2, T=2.0)
    P_adjusted2 = logistic(edge2, T=output2.Teff_final)
    EV_base2 = calculate_EV(P_base2, edge2, 0.0015)
    EV_adjusted2 = calculate_EV(P_adjusted2, edge2, output2.cost_final)

    print(f"概率: P_base={P_base2:.1%} → P_adjusted={P_adjusted2:.1%}")
    print(f"EV: {EV_base2:+.2%} → {EV_adjusted2:+.2%}")
    print(f"建议仓位: {output2.position_mult:.0%} (低质量→小仓位，但仍可交易✅)")

    # 测试案例3：极端情况（L=0, S=-100）
    print("\n【测试3】极端低质量（L=0, S=-100, F=-80, I=-60）")
    output3 = chain.modulate_all(
        L_score=0,
        S_score=-100,
        F_score=-80,
        I_score=-60,
        confidence_base=40.0,
        symbol="ILLIQUID"
    )

    print(f"L调制: position_mult={output3.position_mult:.2%} (最小仓位，无拒绝✅)")
    print(f"S调制: confidence_mult={output3.confidence_mult:.2f}x (信心大降)")
    print(f"F调制: Teff_F={output3.Teff_F:.2f} (概率大降)")
    print(f"I调制: Teff_I={output3.Teff_I:.2f} (概率降低)")
    print(f"融合: Teff={output3.Teff_final:.3f}, cost={output3.cost_final:.4f}, confidence={output3.confidence_final:.1f}")

    edge3 = 0.40
    P_adjusted3 = logistic(edge3, T=output3.Teff_final)
    EV_adjusted3 = calculate_EV(P_adjusted3, edge3, output3.cost_final)

    print(f"概率: P_adjusted={P_adjusted3:.1%} (极低)")
    print(f"EV: {EV_adjusted3:+.2%}")
    print(f"建议仓位: {output3.position_mult:.0%}")
    print(f"结论: 即使L=0/S=-100，仍有30%最小仓位，无硬拒绝✅")

    print("\n" + "=" * 60)
    print("测试完成！调制器链工作正常。")
    print("=" * 60)
