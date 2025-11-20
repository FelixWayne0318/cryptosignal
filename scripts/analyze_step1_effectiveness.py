#!/usr/bin/env python3
"""
分析Step1有效性

评估：
1. Step1 final_strength 分布
2. 接受 vs 拒绝信号的对比
3. 不同阈值下的预期效果
"""

import json
import os
import sys

def load_data(result_dir="data/backtest_results"):
    """加载回测数据"""
    signals_file = os.path.join(result_dir, "signals.json")
    rejects_file = os.path.join(result_dir, "rejected_analyses.json")

    signals = []
    rejects = []

    if os.path.exists(signals_file):
        with open(signals_file) as f:
            signals = json.load(f)

    if os.path.exists(rejects_file):
        with open(rejects_file) as f:
            rejects = json.load(f)

    return signals, rejects

def analyze_step1(signals, rejects):
    """分析Step1数据"""

    print("=" * 60)
    print("Step1 有效性分析")
    print("=" * 60)

    # 1. 收集ACCEPT信号的Step1数据
    accept_strengths = []
    accept_pnls = []

    for sig in signals:
        step1 = sig.get('step1_result', {})
        strength = step1.get('final_strength')
        pnl = sig.get('pnl_percent', 0)

        if strength is not None:
            accept_strengths.append(strength)
            accept_pnls.append(pnl)

    # 2. 收集REJECT信号的Step1数据
    reject_strengths = []
    reject_step1_reasons = []

    for rej in rejects:
        step1 = rej.get('step1_result', {})
        strength = step1.get('final_strength')

        if strength is not None:
            reject_strengths.append(strength)

        if rej.get('rejection_step') == 1:
            reason = rej.get('rejection_reason', 'unknown')
            reject_step1_reasons.append(reason)

    # 3. 基本统计
    print(f"\n📊 数据统计:")
    print(f"  ACCEPT信号: {len(accept_strengths)}")
    print(f"  REJECT信号: {len(reject_strengths)} (其中Step1拒绝: {len(reject_step1_reasons)})")

    # 4. ACCEPT信号分析
    if accept_strengths:
        accept_sorted = sorted(accept_strengths)
        print(f"\n📈 ACCEPT信号 final_strength 分布:")
        print(f"  Min: {min(accept_strengths):.2f}")
        print(f"  Max: {max(accept_strengths):.2f}")
        print(f"  Mean: {sum(accept_strengths)/len(accept_strengths):.2f}")
        print(f"  Median: {accept_sorted[len(accept_sorted)//2]:.2f}")

        # 分位数
        p25 = accept_sorted[int(len(accept_sorted)*0.25)]
        p75 = accept_sorted[int(len(accept_sorted)*0.75)]
        print(f"  P25: {p25:.2f}")
        print(f"  P75: {p75:.2f}")

    # 5. REJECT信号分析
    if reject_strengths:
        reject_sorted = sorted(reject_strengths)
        print(f"\n📉 REJECT信号 final_strength 分布:")
        print(f"  Min: {min(reject_strengths):.2f}")
        print(f"  Max: {max(reject_strengths):.2f}")
        print(f"  Mean: {sum(reject_strengths)/len(reject_strengths):.2f}")
        print(f"  Median: {reject_sorted[len(reject_sorted)//2]:.2f}")

    # 6. 关键问题：final_strength 与 PnL 的相关性
    if accept_strengths and accept_pnls:
        print(f"\n🎯 final_strength 与盈亏关系:")

        # 按strength分组
        bins = [(5.0, 6.0), (6.0, 7.0), (7.0, 8.0), (8.0, float('inf'))]

        for low, high in bins:
            bin_pnls = [pnl for s, pnl in zip(accept_strengths, accept_pnls)
                       if low <= s < high]
            if bin_pnls:
                wins = sum(1 for p in bin_pnls if p > 0)
                win_rate = wins / len(bin_pnls) * 100
                avg_pnl = sum(bin_pnls) / len(bin_pnls)
                label = f"[{low}, {high})" if high != float('inf') else f">= {low}"
                print(f"  {label}: n={len(bin_pnls)}, 胜率={win_rate:.1f}%, 平均PnL={avg_pnl:.2f}%")

    # 7. 阈值敏感性分析
    if accept_strengths and accept_pnls:
        print(f"\n📊 阈值敏感性分析:")
        print(f"  (如果使用不同的 min_final_strength 阈值)")

        all_data = list(zip(accept_strengths, accept_pnls))

        for threshold in [4.0, 5.0, 6.0, 7.0, 8.0]:
            filtered = [(s, p) for s, p in all_data if s >= threshold]
            if filtered:
                wins = sum(1 for s, p in filtered if p > 0)
                total = len(filtered)
                win_rate = wins / total * 100
                avg_pnl = sum(p for s, p in filtered) / total
                print(f"  threshold={threshold}: n={total}, 胜率={win_rate:.1f}%, 平均PnL={avg_pnl:.2f}%")

    # 8. 当前配置参考
    print(f"\n📌 当前配置:")
    print(f"  min_final_strength = 5.0")

    # 9. 评估结论
    print(f"\n{'='*60}")
    print("评估结论")
    print(f"{'='*60}")

    if accept_pnls:
        overall_win_rate = sum(1 for p in accept_pnls if p > 0) / len(accept_pnls) * 100
        overall_avg_pnl = sum(accept_pnls) / len(accept_pnls)

        print(f"\n当前系统表现:")
        print(f"  胜率: {overall_win_rate:.1f}%")
        print(f"  平均PnL: {overall_avg_pnl:.2f}%")

        # 与随机对比
        print(f"\n与随机开单对比:")
        if overall_win_rate > 50:
            print(f"  ✅ 胜率 > 50%，优于随机")
        elif overall_win_rate > 33:
            print(f"  ⚠️ 胜率在33-50%，需要靠RR比弥补")
        else:
            print(f"  ❌ 胜率 < 33%，表现较差")

        if overall_avg_pnl > 0:
            print(f"  ✅ 平均PnL > 0，系统盈利")
        else:
            print(f"  ❌ 平均PnL < 0，系统亏损")

if __name__ == "__main__":
    result_dir = sys.argv[1] if len(sys.argv) > 1 else "data/backtest_results"
    signals, rejects = load_data(result_dir)

    if not signals:
        print("❌ 没有找到信号数据")
        sys.exit(1)

    analyze_step1(signals, rejects)
