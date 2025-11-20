#!/usr/bin/env python3
"""
分析Step2 enhanced_f_final分布

用于诊断Step2通过率100%的问题
"""
import json
import sys

def analyze_enhanced_f_distribution(signals, rejects):
    """分析Step2 enhanced_f_final分布"""

    print(f"Signals (ACCEPT): {len(signals)}")
    print(f"Rejected analyses: {len(rejects)}")

    # 收集所有进入Step2的样本的enhanced_f_final
    enhanced_f_values = []
    stage_counts = {"early": 0, "mid": 0, "late": 0, "blowoff": 0, "unknown": 0}

    # 从ACCEPT信号中提取
    for sig in signals:
        step2 = sig.get('step2_result', {})
        ef = step2.get('enhanced_f_final', step2.get('enhanced_f'))
        stage = step2.get('trend_stage', 'unknown')
        if ef is not None:
            enhanced_f_values.append(ef)
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

    # 从REJECT分析中提取 (只有通过Step1的才有Step2结果)
    for rej in rejects:
        if rej.get('step1_passed', False):  # 通过了Step1
            step2 = rej.get('step2_result', {})
            if step2:
                ef = step2.get('enhanced_f_final', step2.get('enhanced_f'))
                stage = step2.get('trend_stage', 'unknown')
                if ef is not None:
                    enhanced_f_values.append(ef)
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1

    if not enhanced_f_values:
        print("\n❌ 没有找到enhanced_f_final数据!")
        return

    print("\n" + "="*60)
    print("Enhanced_F_Final 分布统计")
    print("="*60)

    # 基本统计
    arr = sorted(enhanced_f_values)
    n = len(arr)

    print(f"\n📊 基本统计:")
    print(f"   样本数: {n}")
    print(f"   Min: {min(arr):.1f}")
    print(f"   Max: {max(arr):.1f}")
    print(f"   Mean: {sum(arr)/n:.1f}")

    # 分位数
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f)

    print(f"\n📈 分位数:")
    print(f"   25%: {percentile(arr, 25):.1f}")
    print(f"   50%: {percentile(arr, 50):.1f}")
    print(f"   75%: {percentile(arr, 75):.1f}")

    print(f"\n📉 区间分布:")
    bins = [
        (-float('inf'), -60, "< -60 (Chase)"),
        (-60, -30, "[-60, -30) (Poor)"),
        (-30, 0, "[-30, 0) (Mediocre-)"),
        (0, 30, "[0, 30) (Mediocre+)"),
        (30, 60, "[30, 60) (Good)"),
        (60, float('inf'), ">= 60 (Excellent)")
    ]

    for low, high, label in bins:
        count = sum(1 for x in arr if low <= x < high)
        pct = count / n * 100
        print(f"   {label}: {count} ({pct:.1f}%)")

    print(f"\n🎯 TrendStage分布:")
    total_stages = sum(stage_counts.values())
    for stage in ["early", "mid", "late", "blowoff", "unknown"]:
        count = stage_counts.get(stage, 0)
        if count > 0:
            pct = count / total_stages * 100 if total_stages > 0 else 0
            print(f"   {stage}: {count} ({pct:.1f}%)")

    # 诊断结论
    print("\n" + "="*60)
    print("诊断结论")
    print("="*60)

    below_minus30 = sum(1 for x in arr if x < -30)
    if below_minus30 == 0:
        print("\n✅ 没有样本落在 < -30 区间")
        print("   → Step2的100%通过率是因为所有样本的enhanced_f_final >= -30")
        print("   → 建议: 提高min_threshold (如从-30改为0)")
    else:
        print(f"\n⚠️  有 {below_minus30} 个样本在 < -30 区间，但Step2仍然100%通过")
        print("   → 可能是闸门接线问题，请检查回测引擎")

if __name__ == "__main__":
    # 默认读取回测结果目录
    import os
    result_dir = sys.argv[1] if len(sys.argv) > 1 else "data/backtest_results"

    # 支持两种格式：单文件或目录
    if os.path.isdir(result_dir):
        # 新格式：signals.json + rejected_analyses.json
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

        data = {"signals": signals, "rejected_analyses": rejects}
        print(f"从目录加载: {result_dir}")
        print(f"  - {len(signals)} 信号")
        print(f"  - {len(rejects)} REJECT记录")
    else:
        # 旧格式：单个JSON文件
        with open(result_dir) as f:
            data = json.load(f)
        signals = data.get('signals', [])
        rejects = data.get('rejected_analyses', [])

    analyze_enhanced_f_distribution(signals, rejects)
