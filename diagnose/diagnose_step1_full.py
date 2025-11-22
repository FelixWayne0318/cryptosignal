#!/usr/bin/env python3
"""
Step1 完整诊断脚本

详细追踪Step1从数据获取到交接Step2的完整流程：
1. 原始因子得分 (T/M/C/V/O/B)
2. A层加权合成
3. 方向强度计算
4. 置信度映射
5. BTC对齐因子
6. 最终强度计算
7. 与实际盈亏的关系

用于专家分析Step1评分系统是否合理
"""

import json
import os
import sys
from collections import defaultdict

def load_data(result_path="data/backtest_results"):
    """加载回测数据"""
    signals = []
    rejects = []

    if os.path.isdir(result_path):
        signals_file = os.path.join(result_path, "signals.json")
        rejects_file = os.path.join(result_path, "rejected_analyses.json")

        if os.path.exists(signals_file):
            with open(signals_file) as f:
                signals = json.load(f)

        if os.path.exists(rejects_file):
            with open(rejects_file) as f:
                rejects = json.load(f)
    else:
        if os.path.exists(result_path):
            with open(result_path) as f:
                data = json.load(f)
            signals = data.get('signals', [])
            rejects = data.get('rejected_analyses', [])

    return signals, rejects

def diagnose_step1(signals, rejects):
    """完整诊断Step1"""

    print("=" * 80)
    print("Step1 完整诊断报告")
    print("=" * 80)

    # ========== 1. 数据概览 ==========
    print("\n" + "=" * 80)
    print("1. 数据概览")
    print("=" * 80)

    print(f"\nACCEPT信号: {len(signals)}")
    print(f"REJECT信号: {len(rejects)}")

    # ========== 2. 因子得分分布 ==========
    print("\n" + "=" * 80)
    print("2. 原始因子得分分布 (A层6因子)")
    print("=" * 80)

    # 收集所有信号的因子得分
    factor_scores = defaultdict(list)
    factor_names = ['T', 'M', 'C', 'V', 'O', 'B']

    for sig in signals:
        scores = sig.get('factor_scores', {})
        for f in factor_names:
            if f in scores:
                factor_scores[f].append(scores[f])

    print("\n因子 | 最小值 | 最大值 | 平均值 | 中位数")
    print("-" * 50)

    for f in factor_names:
        values = factor_scores[f]
        if values:
            sorted_vals = sorted(values)
            min_v = min(values)
            max_v = max(values)
            mean_v = sum(values) / len(values)
            median_v = sorted_vals[len(sorted_vals)//2]
            print(f"  {f}  | {min_v:7.1f} | {max_v:7.1f} | {mean_v:7.1f} | {median_v:7.1f}")

    # ========== 3. Step1计算过程分解 ==========
    print("\n" + "=" * 80)
    print("3. Step1计算过程分解")
    print("=" * 80)

    # 收集Step1各中间变量
    direction_scores = []
    direction_strengths = []
    raw_strengths = []          # v7.5.0新增
    prime_strengths = []        # v7.5.0新增
    t_overheat_factors = []     # v7.5.0新增
    direction_confidences = []
    btc_alignments = []
    final_strengths = []
    pnls = []
    i_scores = []

    weights_sample = None

    for sig in signals:
        step1 = sig.get('step1_result', {})
        meta = step1.get('metadata', {})

        ds = step1.get('direction_score')
        dst = step1.get('direction_strength')
        raw_s = step1.get('raw_strength')           # v7.5.0
        prime_s = step1.get('prime_strength')       # v7.5.0
        t_oh = step1.get('t_overheat_factor')       # v7.5.0
        dc = step1.get('direction_confidence')
        ba = step1.get('btc_alignment')
        fs = step1.get('final_strength')
        pnl = sig.get('pnl_percent', 0)
        i_score = meta.get('I_score')

        if ds is not None:
            direction_scores.append(ds)
        if dst is not None:
            direction_strengths.append(dst)
        if raw_s is not None:
            raw_strengths.append(raw_s)
        if prime_s is not None:
            prime_strengths.append(prime_s)
        if t_oh is not None:
            t_overheat_factors.append(t_oh)
        if dc is not None:
            direction_confidences.append(dc)
        if ba is not None:
            btc_alignments.append(ba)
        if fs is not None:
            final_strengths.append(fs)
            pnls.append(pnl)
        if i_score is not None:
            i_scores.append(i_score)

        if weights_sample is None:
            weights_sample = meta.get('weights', {})

    # 打印权重配置
    if weights_sample:
        print("\n📌 A层因子权重配置:")
        for f, w in weights_sample.items():
            if f != '_comment':
                print(f"  {f}: {w}")

    # 打印各变量分布
    def print_dist(name, values):
        if not values:
            print(f"\n{name}: 无数据")
            return
        sorted_vals = sorted(values)
        n = len(values)
        print(f"\n{name} (n={n}):")
        print(f"  范围: [{min(values):.2f}, {max(values):.2f}]")
        print(f"  平均: {sum(values)/n:.2f}")
        print(f"  中位: {sorted_vals[n//2]:.2f}")
        print(f"  P25: {sorted_vals[int(n*0.25)]:.2f}")
        print(f"  P75: {sorted_vals[int(n*0.75)]:.2f}")

    print_dist("direction_score (A层加权合成)", direction_scores)
    print_dist("direction_strength (|direction_score|)", direction_strengths)
    print_dist("raw_strength (v7.5.0: 原始强度)", raw_strengths)
    print_dist("prime_strength (v7.5.0: 映射后强度)", prime_strengths)
    print_dist("t_overheat_factor (v7.5.0: T过热因子)", t_overheat_factors)
    print_dist("direction_confidence (置信度映射)", direction_confidences)
    print_dist("btc_alignment (BTC对齐因子)", btc_alignments)
    print_dist("I_score (独立性因子)", i_scores)
    print_dist("final_strength (最终强度)", final_strengths)

    # ========== 4. 计算公式验证 ==========
    print("\n" + "=" * 80)
    print("4. 计算公式验证")
    print("=" * 80)

    print("\n理论公式 (v7.5.0):")
    print("  final_strength = prime_strength × direction_confidence × btc_alignment")

    # 验证几个样本
    print("\n验证样本 (前5个信号):")
    for i, sig in enumerate(signals[:5]):
        step1 = sig.get('step1_result', {})
        dst = step1.get('direction_strength', 0)
        raw_s = step1.get('raw_strength', dst)  # 兼容旧版本
        prime_s = step1.get('prime_strength', dst)  # 兼容旧版本
        t_oh = step1.get('t_overheat_factor', 1.0)  # 兼容旧版本
        dc = step1.get('direction_confidence', 0)
        ba = step1.get('btc_alignment', 0)
        fs = step1.get('final_strength', 0)
        calculated = prime_s * dc * ba

        print(f"\n  信号 {i+1}:")
        print(f"    raw_strength = {raw_s:.2f}")
        print(f"    prime_strength = {prime_s:.2f} (t_overheat={t_oh:.2f})")
        print(f"    direction_confidence = {dc:.3f}")
        print(f"    btc_alignment = {ba:.3f}")
        print(f"    计算值 = {prime_s:.2f} × {dc:.3f} × {ba:.3f} = {calculated:.2f}")
        print(f"    实际值 = {fs:.2f}")
        print(f"    差异 = {abs(calculated - fs):.4f}")

    # ========== 5. 关键问题：各变量与盈亏的相关性 ==========
    print("\n" + "=" * 80)
    print("5. 各变量与盈亏的相关性分析")
    print("=" * 80)

    # 按final_strength分组
    print("\n5.1 final_strength 与盈亏:")
    bins = [(5, 6), (6, 7), (7, 8), (8, 10), (10, 15), (15, 30)]
    for low, high in bins:
        bin_data = [(fs, pnl) for fs, pnl in zip(final_strengths, pnls) if low <= fs < high]
        if bin_data:
            wins = sum(1 for _, pnl in bin_data if pnl > 0)
            losses = sum(1 for _, pnl in bin_data if pnl < 0)
            avg_pnl = sum(pnl for _, pnl in bin_data) / len(bin_data)
            win_rate = wins / len(bin_data) * 100
            print(f"  [{low}, {high}): n={len(bin_data):3d}, W={wins:2d}, L={losses:2d}, "
                  f"胜率={win_rate:5.1f}%, 平均PnL={avg_pnl:+.2f}%")

    # 按direction_confidence分组
    print("\n5.2 direction_confidence 与盈亏:")
    # 重新收集配对数据
    conf_pnl_pairs = []
    for sig in signals:
        step1 = sig.get('step1_result', {})
        dc = step1.get('direction_confidence')
        pnl = sig.get('pnl_percent', 0)
        if dc is not None:
            conf_pnl_pairs.append((dc, pnl))

    bins = [(0.9, 0.95), (0.95, 0.98), (0.98, 1.0)]
    for low, high in bins:
        bin_data = [(dc, pnl) for dc, pnl in conf_pnl_pairs if low <= dc < high]
        if bin_data:
            wins = sum(1 for _, pnl in bin_data if pnl > 0)
            avg_pnl = sum(pnl for _, pnl in bin_data) / len(bin_data)
            win_rate = wins / len(bin_data) * 100
            print(f"  [{low}, {high}): n={len(bin_data):3d}, 胜率={win_rate:5.1f}%, 平均PnL={avg_pnl:+.2f}%")

    # 按btc_alignment分组
    print("\n5.3 btc_alignment 与盈亏:")
    ba_pnl_pairs = []
    for sig in signals:
        step1 = sig.get('step1_result', {})
        ba = step1.get('btc_alignment')
        pnl = sig.get('pnl_percent', 0)
        if ba is not None:
            ba_pnl_pairs.append((ba, pnl))

    bins = [(0.5, 0.7), (0.7, 0.85), (0.85, 1.0)]
    for low, high in bins:
        bin_data = [(ba, pnl) for ba, pnl in ba_pnl_pairs if low <= ba < high]
        if bin_data:
            wins = sum(1 for _, pnl in bin_data if pnl > 0)
            avg_pnl = sum(pnl for _, pnl in bin_data) / len(bin_data)
            win_rate = wins / len(bin_data) * 100
            print(f"  [{low}, {high}): n={len(bin_data):3d}, 胜率={win_rate:5.1f}%, 平均PnL={avg_pnl:+.2f}%")

    # 按direction_strength分组
    print("\n5.4 direction_strength (|合成分|) 与盈亏:")
    ds_pnl_pairs = []
    for sig in signals:
        step1 = sig.get('step1_result', {})
        ds = step1.get('direction_strength')
        pnl = sig.get('pnl_percent', 0)
        if ds is not None:
            ds_pnl_pairs.append((ds, pnl))

    bins = [(5, 10), (10, 15), (15, 20), (20, 30)]
    for low, high in bins:
        bin_data = [(ds, pnl) for ds, pnl in ds_pnl_pairs if low <= ds < high]
        if bin_data:
            wins = sum(1 for _, pnl in bin_data if pnl > 0)
            avg_pnl = sum(pnl for _, pnl in bin_data) / len(bin_data)
            win_rate = wins / len(bin_data) * 100
            print(f"  [{low}, {high}): n={len(bin_data):3d}, 胜率={win_rate:5.1f}%, 平均PnL={avg_pnl:+.2f}%")

    # ========== 6. 单因子与盈亏的相关性 ==========
    print("\n" + "=" * 80)
    print("6. 单因子与盈亏的相关性")
    print("=" * 80)

    # 收集因子-PnL配对
    factor_pnl = defaultdict(list)
    for sig in signals:
        scores = sig.get('factor_scores', {})
        pnl = sig.get('pnl_percent', 0)
        for f in factor_names:
            if f in scores:
                factor_pnl[f].append((scores[f], pnl))

    for f in factor_names:
        pairs = factor_pnl[f]
        if not pairs:
            continue

        print(f"\n{f}因子:")
        # 按因子值分组
        bins = [(-100, -50), (-50, 0), (0, 50), (50, 100)]
        for low, high in bins:
            bin_data = [(v, pnl) for v, pnl in pairs if low <= v < high]
            if bin_data:
                wins = sum(1 for _, pnl in bin_data if pnl > 0)
                avg_pnl = sum(pnl for _, pnl in bin_data) / len(bin_data)
                win_rate = wins / len(bin_data) * 100
                print(f"  [{low:4d}, {high:4d}): n={len(bin_data):3d}, "
                      f"胜率={win_rate:5.1f}%, 平均PnL={avg_pnl:+.2f}%")

    # ========== 7. 典型样本详细分析 ==========
    print("\n" + "=" * 80)
    print("7. 典型样本详细分析")
    print("=" * 80)

    # 找出高强度低盈利和低强度高盈利的样本
    samples_with_data = []
    for sig in signals:
        step1 = sig.get('step1_result', {})
        fs = step1.get('final_strength')
        pnl = sig.get('pnl_percent', 0)
        if fs is not None:
            samples_with_data.append((sig, fs, pnl))

    # 排序找极端样本
    samples_with_data.sort(key=lambda x: x[1], reverse=True)  # 按final_strength降序

    print("\n7.1 高强度但亏损的样本 (前3个):")
    count = 0
    for sig, fs, pnl in samples_with_data:
        if pnl < 0 and count < 3:
            print_sample_detail(sig, fs, pnl, count + 1)
            count += 1

    print("\n7.2 低强度但盈利的样本 (前3个):")
    samples_with_data.sort(key=lambda x: x[1])  # 按final_strength升序
    count = 0
    for sig, fs, pnl in samples_with_data:
        if pnl > 0 and count < 3:
            print_sample_detail(sig, fs, pnl, count + 1)
            count += 1

    # ========== 8. 诊断结论 ==========
    print("\n" + "=" * 80)
    print("8. 诊断结论与建议")
    print("=" * 80)

    # 检查是否存在负相关
    if final_strengths and pnls:
        # 简单相关性检查
        high_strength = [(fs, pnl) for fs, pnl in zip(final_strengths, pnls) if fs >= 8]
        low_strength = [(fs, pnl) for fs, pnl in zip(final_strengths, pnls) if fs < 8]

        if high_strength and low_strength:
            high_win_rate = sum(1 for _, pnl in high_strength if pnl > 0) / len(high_strength) * 100
            low_win_rate = sum(1 for _, pnl in low_strength if pnl > 0) / len(low_strength) * 100

            print(f"\n关键发现:")
            print(f"  高强度信号 (>=8): n={len(high_strength)}, 胜率={high_win_rate:.1f}%")
            print(f"  低强度信号 (<8): n={len(low_strength)}, 胜率={low_win_rate:.1f}%")

            if high_win_rate < low_win_rate:
                print(f"\n⚠️  警告: final_strength与胜率呈负相关!")
                print(f"  差异: {low_win_rate - high_win_rate:.1f}%")
                print("\n可能原因:")
                print("  1. 过高的方向强度可能意味着过度拥挤的交易")
                print("  2. BTC对齐因子可能在错误的时机增强信号")
                print("  3. 置信度映射曲线可能需要调整")
                print("  4. 因子权重组合可能不合理")
            else:
                print(f"\n✅ final_strength与胜率正相关，评分系统正常")

def print_sample_detail(sig, fs, pnl, idx):
    """打印样本详细信息"""
    step1 = sig.get('step1_result', {})
    meta = step1.get('metadata', {})
    scores = sig.get('factor_scores', {})

    print(f"\n  样本 {idx}:")
    print(f"    final_strength: {fs:.2f}")
    print(f"    PnL: {pnl:+.2f}%")
    print(f"    方向: {sig.get('side', 'unknown')}")

    print(f"    计算分解:")
    print(f"      direction_score: {step1.get('direction_score', 0):.2f}")
    print(f"      direction_strength: {step1.get('direction_strength', 0):.2f}")
    print(f"      direction_confidence: {step1.get('direction_confidence', 0):.3f}")
    print(f"      btc_alignment: {step1.get('btc_alignment', 0):.3f}")

    print(f"    原始因子:")
    for f in ['T', 'M', 'C', 'V', 'O', 'B']:
        if f in scores:
            print(f"      {f}: {scores[f]:.1f}")

    print(f"    其他:")
    print(f"      I_score: {meta.get('I_score', 'N/A')}")
    print(f"      hard_veto: {step1.get('hard_veto', False)}")

if __name__ == "__main__":
    result_path = sys.argv[1] if len(sys.argv) > 1 else "data/backtest_results"
    signals, rejects = load_data(result_path)

    if not signals:
        print("❌ 没有找到信号数据")
        sys.exit(1)

    diagnose_step1(signals, rejects)
