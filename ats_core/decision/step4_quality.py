"""
v7.4 四步分层决策系统 - Step4: 质量控制层

Purpose:
    四道闸门验证，确保信号质量

Gates:
    - Gate1: 基础筛选（24h成交量）
    - Gate2: 噪声过滤（ATR/Price噪声比）
    - Gate3: 信号强度（Prime Strength门槛）
    - Gate4: 矛盾检测（因子间矛盾、趋势vs时机矛盾）

Functions:
    - check_gate1_volume(): Gate1成交量检查
    - check_gate2_noise(): Gate2噪声检查
    - check_gate3_strength(): Gate3信号强度检查
    - check_gate4_contradiction(): Gate4矛盾检测
    - step4_quality_control(): 主函数

Author: Claude Code (based on Expert Implementation Plan)
Version: v7.4.2
Created: 2025-11-16
"""

from typing import Dict, Any, List, Optional, Tuple
from ats_core.logging import log, warn


def check_gate1_volume(
    klines: List[Dict[str, Any]],
    params: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Gate1: 基础成交量筛选

    Args:
        klines: K线数据（至少24根）
        params: 配置参数

    Returns:
        (pass: bool, reason: str | None)

    v7.4.3更新：
        - 添加enabled开关，默认禁用
        - 选币阶段已通过min_volume_24h_usdt过滤，此处重复检查无意义
    """
    gate1_cfg = params.get("four_step_system", {}).get("step4_quality", {}).get("gate1_volume", {})

    # v7.4.3: 支持enabled开关，默认禁用
    enabled = gate1_cfg.get("enabled", False)
    if not enabled:
        return True, None  # 禁用时直接通过

    min_volume = gate1_cfg.get("min_volume_24h", 1_000_000.0)

    # 计算24h成交量
    if len(klines) < 24:
        return False, f"K线数据不足: {len(klines)} < 24"

    volume_24h = sum(float(k.get("volume", 0.0)) for k in klines[-24:])

    if volume_24h >= min_volume:
        return True, None
    else:
        return False, f"24h成交量不足: {volume_24h:.0f} < {min_volume:.0f}"


def check_gate2_noise(
    symbol: str,
    klines: List[Dict[str, Any]],
    params: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Gate2: 噪声过滤（ATR/Price）

    Logic:
        noise_ratio = ATR / close_price
        若noise_ratio > max_noise_ratio（默认15%），说明波动太大，拒绝
        v7.4.2 P0-6修复：基于资产类别动态调整阈值

    Args:
        symbol: 交易对符号（v7.4.2新增，用于资产分类）
        klines: K线数据
        params: 配置参数

    Returns:
        (pass: bool, reason: str | None)

    P0-6修复说明：
        - 稳定币（USDT等）：max_noise_ratio = 0.05（低波动性）
        - 蓝筹币（BTC/ETH/BNB）：max_noise_ratio = 0.10（中等波动性）
        - 山寨币（其他）：max_noise_ratio = 0.20（高波动性）
    """
    gate2_cfg = params.get("four_step_system", {}).get("step4_quality", {}).get("gate2_noise", {})

    # v7.4.2 P0-6修复：动态阈值逻辑
    enable_dynamic = gate2_cfg.get("enable_dynamic", True)

    if enable_dynamic and "dynamic_thresholds" in gate2_cfg:
        dynamic_cfg = gate2_cfg["dynamic_thresholds"]

        # 判断资产类别
        asset_type = "altcoins"  # 默认山寨币

        if symbol in dynamic_cfg.get("stablecoins", {}).get("symbols", []):
            asset_type = "stablecoins"
        elif symbol in dynamic_cfg.get("blue_chip", {}).get("symbols", []):
            asset_type = "blue_chip"

        # 获取对应类别的阈值
        max_noise = dynamic_cfg.get(asset_type, {}).get("max_noise_ratio", 0.15)
        threshold_source = f"{asset_type}_dynamic"
    else:
        # 降级：使用固定阈值
        max_noise = gate2_cfg.get("max_noise_ratio", 0.15)
        threshold_source = "default"

    if not klines:
        return False, "K线数据为空"

    close_price = float(klines[-1].get("close", 0.0))
    atr = float(klines[-1].get("atr", 0.0))

    if close_price <= 0:
        return False, "价格数据异常"

    noise_ratio = atr / close_price if atr > 0 else 0.0

    if noise_ratio <= max_noise:
        return True, None
    else:
        return False, f"噪声过高[{threshold_source}]: {noise_ratio:.2%} > {max_noise:.2%}"


def check_gate3_strength(
    prime_strength: float,
    params: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Gate3: 信号强度门槛

    Args:
        prime_strength: 主要强度（可以是final_strength from Step1，或其他强度指标）
        params: 配置参数

    Returns:
        (pass: bool, reason: str | None)
    """
    gate3_cfg = params.get("four_step_system", {}).get("step4_quality", {}).get("gate3_strength", {})
    min_strength = gate3_cfg.get("min_prime_strength", 35.0)

    if prime_strength >= min_strength:
        return True, None
    else:
        return False, f"信号强度不足: {prime_strength:.1f} < {min_strength:.1f}"


def check_gate4_contradiction(
    factor_scores: Dict[str, float],
    enhanced_f: float,
    params: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Gate4: 矛盾检测

    Contradictions:
        1. C vs O矛盾：C和O都绝对值>60且方向相反（资金流vs持仓矛盾）
        2. T vs Enhanced_F矛盾：T强趋势(>70)但Enhanced_F很负(<-40)（强趋势但追高）

    Args:
        factor_scores: 因子得分
        enhanced_f: Enhanced F v2得分（从Step2获取）
        params: 配置参数

    Returns:
        (pass: bool, reason: str | None)
    """
    gate4_cfg = params.get("four_step_system", {}).get("step4_quality", {}).get("gate4_contradiction", {})

    c_score = factor_scores.get("C", 0.0)
    o_score = factor_scores.get("O", 0.0)
    t_score = factor_scores.get("T", 0.0)

    # 矛盾1：C vs O
    # v7.6.1修复(M4): 改用联合条件，避免漏检
    c_vs_o_cfg = gate4_cfg.get("c_vs_o", {})
    c_vs_o_enabled = c_vs_o_cfg.get("enabled", True)
    c_vs_o_threshold = c_vs_o_cfg.get("abs_threshold", 50)
    c_vs_o_sum_threshold = c_vs_o_cfg.get("sum_threshold", 100)

    contradiction1 = False
    if c_vs_o_enabled:
        # v7.6.1修复(M4): 两种矛盾条件
        # 条件A: |C| + |O| > sum_threshold 且方向相反
        # 条件B: |C| > abs_threshold 且 |O| > abs_threshold 且方向相反
        opposite_direction = (c_score * o_score) < 0
        sum_condition = (abs(c_score) + abs(o_score) > c_vs_o_sum_threshold)
        both_strong = (abs(c_score) > c_vs_o_threshold and abs(o_score) > c_vs_o_threshold)

        contradiction1 = opposite_direction and (sum_condition or both_strong)

    # 矛盾2：T vs Enhanced_F
    t_vs_f_cfg = gate4_cfg.get("t_vs_enhanced_f", {})
    t_vs_f_enabled = t_vs_f_cfg.get("enabled", True)
    t_strong_threshold = t_vs_f_cfg.get("t_strong_threshold", 70)
    f_chase_threshold = t_vs_f_cfg.get("f_chase_threshold", -40)

    contradiction2 = False
    if t_vs_f_enabled:
        # T强趋势，但Enhanced_F很负（追高）
        contradiction2 = (
            abs(t_score) > t_strong_threshold
            and enhanced_f < f_chase_threshold
        )

    # 判断
    if contradiction1:
        return False, f"C与O因子方向矛盾: C={c_score:.1f}, O={o_score:.1f}"
    elif contradiction2:
        return False, f"趋势与时机矛盾: T={t_score:.1f}, Enhanced_F={enhanced_f:.1f}"
    else:
        return True, None


def step4_quality_control(
    symbol: str,
    klines: List[Dict[str, Any]],
    factor_scores: Dict[str, float],
    prime_strength: float,
    step1_result: Dict[str, Any],
    step2_result: Dict[str, Any],
    step3_result: Dict[str, Any],
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step4质量控制层主函数

    Pipeline:
        Gate1: 24h成交量 → 基础流动性筛选
        Gate2: ATR/Price → 噪声过滤
        Gate3: Prime Strength → 信号强度门槛
        Gate4: 矛盾检测 → 因子间矛盾、趋势vs时机矛盾

    Args:
        symbol: 交易对符号
        klines: K线数据
        factor_scores: 因子得分
        prime_strength: 主要强度（通常使用Step1的final_strength）
        step1_result: Step1结果
        step2_result: Step2结果
        step3_result: Step3结果
        params: 配置参数

    Returns:
        dict: {
            "gate1_pass": bool,
            "gate2_pass": bool,
            "gate3_pass": bool,
            "gate4_pass": bool,
            "all_gates_pass": bool,
            "final_decision": "ACCEPT" / "REJECT",
            "reject_reason": str | None,
            "gates_status": dict  # 详细状态
        }
    """
    # Gate1: 成交量
    gate1_pass, gate1_reason = check_gate1_volume(klines, params)

    # Gate2: 噪声 (v7.4.2 P0-6修复: 添加symbol参数支持动态阈值)
    gate2_pass, gate2_reason = check_gate2_noise(symbol, klines, params)

    # Gate3: 强度
    gate3_pass, gate3_reason = check_gate3_strength(prime_strength, params)

    # Gate4: 矛盾
    enhanced_f = step2_result.get("enhanced_f", 0.0)
    gate4_pass, gate4_reason = check_gate4_contradiction(factor_scores, enhanced_f, params)

    # 汇总
    all_gates_pass = gate1_pass and gate2_pass and gate3_pass and gate4_pass

    if all_gates_pass:
        final_decision = "ACCEPT"
        reject_reason = None
        log(f"✅ {symbol} - Step4通过: 四道闸门全部通过")
    else:
        final_decision = "REJECT"
        # 返回第一个失败的闸门原因
        reject_reason = gate1_reason or gate2_reason or gate3_reason or gate4_reason
        log(f"❌ {symbol} - Step4拒绝: {reject_reason}")

    return {
        "gate1_pass": gate1_pass,
        "gate2_pass": gate2_pass,
        "gate3_pass": gate3_pass,
        "gate4_pass": gate4_pass,
        "all_gates_pass": all_gates_pass,
        "final_decision": final_decision,
        "reject_reason": reject_reason,
        "gates_status": {
            "gate1": {"pass": gate1_pass, "reason": gate1_reason},
            "gate2": {"pass": gate2_pass, "reason": gate2_reason},
            "gate3": {"pass": gate3_pass, "reason": gate3_reason},
            "gate4": {"pass": gate4_pass, "reason": gate4_reason}
        }
    }


# ============ 测试用例 ============

if __name__ == "__main__":
    """
    测试Step4质量控制层

    Usage:
        python3 -m ats_core.decision.step4_quality
    """
    print("=" * 70)
    print("v7.4 Step4质量控制层测试")
    print("=" * 70)

    # 模拟配置
    from ats_core.cfg import CFG
    test_params = CFG.params

    # 确保step4_quality配置存在
    if "four_step_system" not in test_params or "step4_quality" not in test_params["four_step_system"]:
        print("⚠️  配置缺失，使用默认配置")
        test_params["four_step_system"] = test_params.get("four_step_system", {})
        test_params["four_step_system"]["step4_quality"] = {
            "gate1_volume": {"min_volume_24h": 1_000_000},
            "gate2_noise": {"max_noise_ratio": 0.15},
            "gate3_strength": {"min_prime_strength": 35},
            "gate4_contradiction": {
                "c_vs_o": {"enabled": True, "abs_threshold": 60},
                "t_vs_enhanced_f": {
                    "enabled": True,
                    "t_strong_threshold": 70,
                    "f_chase_threshold": -40
                }
            }
        }

    # 模拟K线数据（高成交量，低噪声）
    base_price = 100.0
    klines_good = []
    for i in range(24):
        klines_good.append({
            "open_time": 1700000000000 + i * 3600000,
            "open": base_price + i * 0.1,
            "high": base_price + i * 0.1 + 0.3,
            "low": base_price + i * 0.1 - 0.3,
            "close": base_price + i * 0.1 + 0.1,
            "volume": 100_000.0,  # 24h总量 = 2.4M > 1M
            "atr": 0.5  # 噪声 = 0.5/100 = 0.5% < 15%
        })

    # 模拟Step1/2/3结果
    step1_mock = {
        "direction_score": 75.0,
        "final_strength": 55.0,
        "pass": True
    }

    step2_mock = {
        "enhanced_f": 60.0,
        "timing_quality": "Good",
        "pass": True
    }

    step3_mock = {
        "entry_price": 102.5,
        "stop_loss": 100.0,
        "take_profit": 107.0,
        "risk_reward_ratio": 1.8,
        "pass": True
    }

    # 测试场景1：完美信号（四道闸门全通过）
    print("\n📊 测试场景1：完美信号（四道闸门全通过）")
    print("-" * 70)

    factor_scores_perfect = {
        "T": 70, "M": 20, "C": 80, "V": 65, "O": 75, "B": 60
    }

    result1 = step4_quality_control(
        symbol="ETHUSDT",
        klines=klines_good,
        factor_scores=factor_scores_perfect,
        prime_strength=55.0,
        step1_result=step1_mock,
        step2_result=step2_mock,
        step3_result=step3_mock,
        params=test_params
    )

    print(f"\n结果: {result1['final_decision']}")
    print(f"Gate1 (成交量): {'✅ 通过' if result1['gate1_pass'] else '❌ 失败'}")
    print(f"Gate2 (噪声): {'✅ 通过' if result1['gate2_pass'] else '❌ 失败'}")
    print(f"Gate3 (强度): {'✅ 通过' if result1['gate3_pass'] else '❌ 失败'}")
    print(f"Gate4 (矛盾): {'✅ 通过' if result1['gate4_pass'] else '❌ 失败'}")

    # 测试场景2：Gate1失败（成交量不足）
    print("\n\n📊 测试场景2：Gate1失败（成交量不足）")
    print("-" * 70)

    klines_low_vol = []
    for i in range(24):
        klines_low_vol.append({
            "open_time": 1700000000000 + i * 3600000,
            "open": base_price,
            "high": base_price + 0.5,
            "low": base_price - 0.5,
            "close": base_price,
            "volume": 10_000.0,  # 24h总量 = 240K < 1M
            "atr": 0.5
        })

    result2 = step4_quality_control(
        symbol="LOWVOLCOIN",
        klines=klines_low_vol,
        factor_scores=factor_scores_perfect,
        prime_strength=55.0,
        step1_result=step1_mock,
        step2_result=step2_mock,
        step3_result=step3_mock,
        params=test_params
    )

    print(f"\n结果: {result2['final_decision']}")
    if not result2['all_gates_pass']:
        print(f"拒绝原因: {result2['reject_reason']}")

    # 测试场景3：Gate2失败（噪声过高）
    print("\n\n📊 测试场景3：Gate2失败（噪声过高）")
    print("-" * 70)

    klines_noisy = []
    for i in range(24):
        klines_noisy.append({
            "open_time": 1700000000000 + i * 3600000,
            "open": base_price,
            "high": base_price + 10,
            "low": base_price - 10,
            "close": base_price,
            "volume": 100_000.0,
            "atr": 20.0  # 噪声 = 20/100 = 20% > 15%
        })

    result3 = step4_quality_control(
        symbol="NOISYCOIN",
        klines=klines_noisy,
        factor_scores=factor_scores_perfect,
        prime_strength=55.0,
        step1_result=step1_mock,
        step2_result=step2_mock,
        step3_result=step3_mock,
        params=test_params
    )

    print(f"\n结果: {result3['final_decision']}")
    if not result3['all_gates_pass']:
        print(f"拒绝原因: {result3['reject_reason']}")

    # 测试场景4：Gate3失败（强度不足）
    print("\n\n📊 测试场景4：Gate3失败（强度不足）")
    print("-" * 70)

    result4 = step4_quality_control(
        symbol="WEAKCOIN",
        klines=klines_good,
        factor_scores=factor_scores_perfect,
        prime_strength=25.0,  # < 35
        step1_result=step1_mock,
        step2_result=step2_mock,
        step3_result=step3_mock,
        params=test_params
    )

    print(f"\n结果: {result4['final_decision']}")
    if not result4['all_gates_pass']:
        print(f"拒绝原因: {result4['reject_reason']}")

    # 测试场景5：Gate4失败（C vs O矛盾）
    print("\n\n📊 测试场景5：Gate4失败（C vs O矛盾）")
    print("-" * 70)

    factor_scores_contradictory = {
        "T": 50, "M": 20,
        "C": 80,   # 强正
        "V": 50,
        "O": -75,  # 强负（矛盾）
        "B": 40
    }

    result5 = step4_quality_control(
        symbol="CONTRADICTCOIN",
        klines=klines_good,
        factor_scores=factor_scores_contradictory,
        prime_strength=55.0,
        step1_result=step1_mock,
        step2_result=step2_mock,
        step3_result=step3_mock,
        params=test_params
    )

    print(f"\n结果: {result5['final_decision']}")
    if not result5['all_gates_pass']:
        print(f"拒绝原因: {result5['reject_reason']}")

    # 测试场景6：Gate4失败（T vs F矛盾）
    print("\n\n📊 测试场景6：Gate4失败（T vs F矛盾 - 强趋势但追高）")
    print("-" * 70)

    factor_scores_chase = {
        "T": 85,  # 强趋势
        "M": 30, "C": 60, "V": 50, "O": 55, "B": 40
    }

    step2_chase = {
        "enhanced_f": -50.0,  # 明显追高
        "timing_quality": "Chase",
        "pass": False
    }

    result6 = step4_quality_control(
        symbol="CHASECOIN",
        klines=klines_good,
        factor_scores=factor_scores_chase,
        prime_strength=55.0,
        step1_result=step1_mock,
        step2_result=step2_chase,
        step3_result=step3_mock,
        params=test_params
    )

    print(f"\n结果: {result6['final_decision']}")
    if not result6['all_gates_pass']:
        print(f"拒绝原因: {result6['reject_reason']}")

    print("\n" + "=" * 70)
    print("✅ Step4质量控制层测试完成")
    print("=" * 70)
