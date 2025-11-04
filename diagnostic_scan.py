#!/usr/bin/env python3
# coding: utf-8
"""
全面诊断脚本 - 检测信号产生率为0的问题
运行方式: python3 diagnostic_scan.py > diagnostic_report.txt 2>&1
"""

import sys
import os
import json
import subprocess
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("🔍 CryptoSignal 系统诊断工具 v1.0")
print("=" * 80)
print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# 第一部分：版本和配置检查
# ============================================================================

print("\n" + "=" * 80)
print("📋 第一部分：版本和配置检查")
print("=" * 80)

# 1.1 Git版本检查
print("\n1.1 Git版本信息:")
try:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    commit_msg = subprocess.check_output(["git", "log", "-1", "--pretty=%B"]).decode().strip()
    print(f"   分支: {branch}")
    print(f"   Commit: {commit[:8]}")
    print(f"   最新提交: {commit_msg.split()[0][:50]}")
except Exception as e:
    print(f"   ❌ Git检查失败: {e}")

# 1.2 关键文件版本检查
print("\n1.2 关键代码检查:")

# 检查 realtime_signal_scanner.py 的 Anti-Jitter 配置
print("\n   A. Anti-Jitter 配置 (realtime_signal_scanner.py):")
try:
    with open("scripts/realtime_signal_scanner.py", "r") as f:
        content = f.read()

    # 检查 prime_entry_threshold
    if "prime_entry_threshold=0.55" in content:
        print("      ✅ prime_entry_threshold = 0.55 (正确)")
    elif "prime_entry_threshold=0.65" in content:
        print("      ❌ prime_entry_threshold = 0.65 (旧版，应为0.55)")
    else:
        print("      ⚠️  找不到 prime_entry_threshold 配置")

    # 检查 prime_maintain_threshold
    if "prime_maintain_threshold=0.52" in content:
        print("      ✅ prime_maintain_threshold = 0.52 (正确)")
    elif "prime_maintain_threshold=0.58" in content:
        print("      ❌ prime_maintain_threshold = 0.58 (旧版，应为0.52)")
    else:
        print("      ⚠️  找不到 prime_maintain_threshold 配置")

    # 检查 EV 字段读取
    if "publish_info.get('EV', 0.0)" in content:
        print("      ✅ EV字段读取使用大写 'EV' (正确)")
    elif "publish_info.get('ev', 0.0)" in content:
        print("      ❌ EV字段读取使用小写 'ev' (错误，应为'EV')")
    else:
        print("      ⚠️  找不到 EV 字段读取代码")

except Exception as e:
    print(f"      ❌ 文件检查失败: {e}")

# 检查 analyze_symbol.py 的 EV 计算
print("\n   B. EV 计算 (analyze_symbol.py):")
try:
    with open("ats_core/pipeline/analyze_symbol.py", "r") as f:
        content = f.read()

    # 检查 EV 计算是否使用 abs(edge)
    if "P_chosen * abs(edge)" in content:
        print("      ✅ EV计算使用 abs(edge) (正确)")
    elif "P_chosen * edge - (1 - P_chosen)" in content and "abs" not in content.split("P_chosen * edge")[0][-50:]:
        print("      ❌ EV计算使用有符号edge (错误)")

    # 检查 p_min adjustment 限制
    if "adjustment = min(adjustment, 0.02)" in content:
        print("      ✅ p_min adjustment 限制为 0.02 (正确)")
    else:
        print("      ⚠️  找不到 p_min adjustment 限制")

    # 检查 publish 字典中的 EV 字段（大写）
    if '"EV": EV' in content:
        print("      ✅ publish字典使用大写 'EV' (正确)")
    elif '"ev": EV' in content:
        print("      ❌ publish字典使用小写 'ev' (错误)")

except Exception as e:
    print(f"      ❌ 文件检查失败: {e}")

# ============================================================================
# 第二部分：运行实际扫描测试
# ============================================================================

print("\n" + "=" * 80)
print("🧪 第二部分：运行测试扫描 (10个币种)")
print("=" * 80)

try:
    from ats_core.pipeline.batch_scan_optimized import batch_scan_optimized
    from ats_core.publishing.anti_jitter import AntiJitter

    print("\n正在扫描...")

    # 运行扫描（限制10个币种以加快速度）
    result = batch_scan_optimized(
        symbols=None,  # 自动获取
        max_symbols=10,  # 只扫描10个币种用于诊断
        interval='1h',
        log=True
    )

    signals = result.get('signals', [])

    print(f"\n扫描完成:")
    print(f"   总币种数: {result.get('total_symbols', 0)}")
    print(f"   发现信号: {len(signals)}")
    print(f"   耗时: {result.get('elapsed_seconds', 0):.1f}秒")

    # ============================================================================
    # 第三部分：详细分析每个信号
    # ============================================================================

    print("\n" + "=" * 80)
    print("📊 第三部分：信号详细分析")
    print("=" * 80)

    if not signals:
        print("\n❌ 没有发现任何信号！")
        print("\n可能原因:")
        print("   1. 市场条件不满足（所有币种都不符合Prime条件）")
        print("   2. 数据获取失败")
        print("   3. 评分系统问题")
    else:
        # 创建 Anti-Jitter 实例用于测试
        anti_jitter = AntiJitter(
            prime_entry_threshold=0.55,
            prime_maintain_threshold=0.52,
            watch_entry_threshold=0.50,
            watch_maintain_threshold=0.45,
            confirmation_bars=1,
            total_bars=2,
            cooldown_seconds=60
        )

        print(f"\n发现 {len(signals)} 个信号，详细分析:\n")

        prime_count = 0
        watch_count = 0
        failed_ev = 0
        failed_prob = 0
        failed_antijitter = 0

        for i, signal in enumerate(signals[:10], 1):  # 只显示前10个
            symbol = signal.get('symbol', 'UNKNOWN')
            probability = signal.get('probability', 0)

            # 获取 publish 信息
            publish_info = signal.get('publish', {})
            is_prime = publish_info.get('prime', False)
            soft_filtered = publish_info.get('soft_filtered', False)
            EV = publish_info.get('EV', 0.0)
            EV_positive = publish_info.get('EV_positive', False)
            P_above_threshold = publish_info.get('P_above_threshold', True)
            rejection_reason = publish_info.get('rejection_reason', [])

            print(f"\n{'─' * 80}")
            print(f"信号 #{i}: {symbol}")
            print(f"{'─' * 80}")

            # 基础信息
            print(f"   概率 (P):        {probability:.4f} ({probability*100:.2f}%)")
            print(f"   期望值 (EV):     {EV:.4f}")
            print(f"   Prime状态:       {'✅ Prime' if is_prime else '❌ 非Prime'}")
            print(f"   软约束过滤:      {'❌ 是' if soft_filtered else '✅ 否'}")
            print(f"   EV > 0:          {'✅ 是' if EV_positive else f'❌ 否 (EV={EV:.4f})'}")
            print(f"   P > 阈值:        {'✅ 是' if P_above_threshold else '❌ 否'}")

            # 拒绝原因
            if rejection_reason:
                if rejection_reason == ["通过(Prime)"]:
                    print(f"   拒绝原因:        ✅ {rejection_reason[0]}")
                else:
                    print(f"   拒绝原因:        ❌ {'; '.join(rejection_reason)}")

            # Anti-Jitter 测试
            print(f"\n   Anti-Jitter 测试:")
            print(f"      配置阈值:")
            print(f"         prime_entry:    0.55 ({0.55*100:.0f}%)")
            print(f"         prime_maintain: 0.52 ({0.52*100:.0f}%)")

            # 模拟 anti-jitter 检查
            constraints_passed = not soft_filtered

            new_level, should_publish = anti_jitter.update(
                symbol=symbol,
                probability=probability,
                ev=EV,
                gates_passed=constraints_passed
            )

            print(f"      检查结果:")
            print(f"         constraints_passed: {constraints_passed}")
            print(f"         EV > 0:             {EV > 0} (EV={EV:.4f})")
            print(f"         P >= 0.55:          {probability >= 0.55} (P={probability:.4f})")
            print(f"         new_level:          {new_level}")
            print(f"         should_publish:     {should_publish}")

            # 发布条件检查
            would_publish = constraints_passed and should_publish and new_level == 'PRIME'
            print(f"\n   最终发布判定:")
            print(f"      条件1 - constraints_passed: {constraints_passed}")
            print(f"      条件2 - should_publish:     {should_publish}")
            print(f"      条件3 - new_level==PRIME:   {new_level == 'PRIME'}")
            print(f"      → 会发布: {'✅ 是' if would_publish else '❌ 否'}")

            # 统计
            if new_level == 'PRIME':
                prime_count += 1
            elif new_level == 'WATCH':
                watch_count += 1

            if EV <= 0:
                failed_ev += 1
            if probability < 0.55:
                failed_prob += 1
            if new_level != 'PRIME':
                failed_antijitter += 1

        # ============================================================================
        # 第四部分：统计汇总
        # ============================================================================

        print("\n" + "=" * 80)
        print("📈 第四部分：统计汇总")
        print("=" * 80)

        print(f"\n信号级别分布:")
        print(f"   PRIME 级别:  {prime_count} / {len(signals)} ({prime_count/len(signals)*100:.1f}%)")
        print(f"   WATCH 级别:  {watch_count} / {len(signals)} ({watch_count/len(signals)*100:.1f}%)")
        print(f"   其他:        {len(signals) - prime_count - watch_count} / {len(signals)}")

        print(f"\n失败原因统计:")
        print(f"   EV ≤ 0:           {failed_ev} / {len(signals)} ({failed_ev/len(signals)*100:.1f}%)")
        print(f"   P < 0.55:         {failed_prob} / {len(signals)} ({failed_prob/len(signals)*100:.1f}%)")
        print(f"   Anti-Jitter拒绝: {failed_antijitter} / {len(signals)} ({failed_antijitter/len(signals)*100:.1f}%)")

        # 概率分布统计
        probs = [s.get('probability', 0) for s in signals]
        evs = [s.get('publish', {}).get('EV', 0) for s in signals]

        if probs:
            print(f"\n概率分布:")
            print(f"   最小值: {min(probs):.4f} ({min(probs)*100:.2f}%)")
            print(f"   最大值: {max(probs):.4f} ({max(probs)*100:.2f}%)")
            print(f"   平均值: {sum(probs)/len(probs):.4f} ({sum(probs)/len(probs)*100:.2f}%)")
            print(f"   中位数: {sorted(probs)[len(probs)//2]:.4f} ({sorted(probs)[len(probs)//2]*100:.2f}%)")

        if evs:
            print(f"\nEV分布:")
            print(f"   最小值: {min(evs):.4f}")
            print(f"   最大值: {max(evs):.4f}")
            print(f"   平均值: {sum(evs)/len(evs):.4f}")
            print(f"   EV>0数量: {sum(1 for ev in evs if ev > 0)} / {len(evs)}")

except Exception as e:
    print(f"\n❌ 扫描测试失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 第五部分：诊断结论和建议
# ============================================================================

print("\n" + "=" * 80)
print("💡 第五部分：诊断结论")
print("=" * 80)

print("""
根据以上诊断结果，请检查:

1. 代码版本问题
   - 确认 git commit 是 42a1596 或更新
   - 确认分支是 claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8

2. 配置问题
   - Anti-Jitter 阈值应为 0.55/0.52 (不是 0.65/0.58)
   - EV 字段读取应使用大写 'EV' (不是小写 'ev')

3. 数据问题
   - 检查信号的实际概率值是否太低 (< 0.55)
   - 检查 EV 值是否都 ≤ 0
   - 检查 soft_filtered 标记是否都为 True

4. Anti-Jitter 状态
   - 检查 new_level 是否都不是 'PRIME'
   - 确认 should_publish 的值

如果所有配置都正确但仍无信号，可能是：
   - 市场条件确实不满足（所有币种评分都太低）
   - 需要进一步降低阈值（如 0.50）或调整 Sigmoid 温度参数
""")

print("\n" + "=" * 80)
print("✅ 诊断完成")
print("=" * 80)
print(f"\n报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\n请将完整输出发送给开发者分析\n")
