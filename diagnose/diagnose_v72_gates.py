# coding: utf-8
"""
v7.2信号过滤诊断工具

用途：分析为什么候选信号被v7.2五道闸门拒绝

运行方法：
cd ~/cryptosignal
python3 scripts/diagnose_v72_gates.py
"""

import sys
import json
from pathlib import Path
from collections import Counter

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("🔍 v7.2五道闸门诊断")
print("=" * 70)

# 读取最新扫描摘要
summary_file = project_root / 'reports' / 'latest' / 'scan_summary.json'
if not summary_file.exists():
    print(f"\n❌ 扫描摘要文件不存在: {summary_file}")
    sys.exit(1)

with open(summary_file, 'r') as f:
    summary = json.load(f)

# 读取详细数据
detail_file = project_root / 'reports' / 'latest' / 'scan_detail.json'
if detail_file.exists():
    with open(detail_file, 'r') as f:
        detail = json.load(f)
else:
    detail = None

# 读取当前阈值配置
config_file = project_root / 'config' / 'signal_thresholds.json'
with open(config_file, 'r') as f:
    thresholds = json.load(f)

gates_config = thresholds.get('v72闸门阈值', {})

print(f"\n📋 当前v7.2闸门阈值配置:")
print(f"   Gate1 (数据质量): min_klines >= {gates_config.get('gate1_data_quality', {}).get('min_klines', 100)}")
print(f"   Gate2 (资金支撑): F >= {gates_config.get('gate2_fund_support', {}).get('F_min', -15)}")
print(f"   Gate3 (期望值): EV >= {gates_config.get('gate3_ev', {}).get('EV_min', 0.0)}")
print(f"   Gate4 (概率): P >= {gates_config.get('gate4_probability', {}).get('P_min', 0.50)}")
print(f"   Gate5 (独立性): I >= {gates_config.get('gate5_independence_market', {}).get('I_min', 30)}")

# 分析扫描结果
scan_info = summary.get('scan_info', {})
total_symbols = scan_info.get('total_symbols', 0)
signals_found = scan_info.get('signals_found', 0)

print(f"\n📊 扫描结果统计:")
print(f"   扫描币种: {total_symbols}")
print(f"   候选信号（基础层）: {signals_found}")

# 如果有详细数据，分析拒绝原因
if detail and 'symbols' in detail:
    symbols_data = detail['symbols']

    # 统计拒绝原因
    rejection_counter = Counter()
    prime_signals = []
    rejected_signals = []

    for symbol_data in symbols_data:
        symbol = symbol_data.get('symbol')
        is_prime = symbol_data.get('is_prime', False)
        rejection_reasons = symbol_data.get('rejection_reason', [])

        if is_prime:
            prime_signals.append(symbol_data)
        else:
            rejected_signals.append(symbol_data)
            # 统计拒绝原因
            for reason in rejection_reasons:
                # 提取关键原因（去掉具体数值）
                if "概率过低" in reason:
                    rejection_counter["概率过低 (P < P_min)"] += 1
                elif "置信度不足" in reason:
                    rejection_counter["置信度不足 (Conf < min)"] += 1
                elif "Edge不足" in reason:
                    rejection_counter["Edge不足 (Edge < min)"] += 1
                elif "Prime强度不足" in reason:
                    rejection_counter["Prime强度不足"] += 1

    print(f"\n🎯 信号质量分布:")
    print(f"   ✅ Prime信号: {len(prime_signals)}")
    print(f"   ❌ 被拒绝: {len(rejected_signals)}")

    if rejection_counter:
        print(f"\n📉 拒绝原因TOP 5:")
        for reason, count in rejection_counter.most_common(5):
            pct = count / len(rejected_signals) * 100
            print(f"   {reason}: {count}个 ({pct:.1f}%)")

    # 分析接近阈值的币种（差一点就能通过）
    near_threshold = []
    P_min = gates_config.get('gate4_probability', {}).get('P_min', 0.50)
    F_min = gates_config.get('gate2_fund_support', {}).get('F_min', -15)

    for symbol_data in rejected_signals:
        P = symbol_data.get('P_chosen', 0)
        confidence = symbol_data.get('confidence', 0)

        # 检查是否接近阈值（差5%以内）
        if P >= P_min * 0.95 and P < P_min:
            near_threshold.append({
                'symbol': symbol_data['symbol'],
                'P': P,
                'P_gap': P_min - P,
                'confidence': confidence
            })

    if near_threshold:
        print(f"\n⚠️  接近阈值的币种（差一点就通过）: {len(near_threshold)}个")
        print(f"   这些币种如果降低阈值可能通过：")
        for item in sorted(near_threshold, key=lambda x: -x['P'])[:5]:
            print(f"   - {item['symbol']}: P={item['P']:.3f} (差{item['P_gap']:.3f}), Conf={item['confidence']:.0f}")

    # 分析Prime信号的特征
    if prime_signals:
        print(f"\n✅ Prime信号特征分析:")
        P_values = [s.get('P_chosen', 0) for s in prime_signals]
        conf_values = [s.get('confidence', 0) for s in prime_signals]
        edge_values = [abs(s.get('edge', 0)) for s in prime_signals]

        print(f"   概率范围: {min(P_values):.3f} ~ {max(P_values):.3f}")
        print(f"   置信度范围: {min(conf_values):.0f} ~ {max(conf_values):.0f}")
        print(f"   Edge范围: {min(edge_values):.2f} ~ {max(edge_values):.2f}")

        # 显示Top 5 Prime信号
        print(f"\n   Top 5 Prime信号:")
        sorted_prime = sorted(prime_signals, key=lambda x: x.get('confidence', 0), reverse=True)
        for i, s in enumerate(sorted_prime[:5], 1):
            print(f"   {i}. {s['symbol']}: Conf={s.get('confidence', 0):.0f}, P={s.get('P_chosen', 0):.3f}, Edge={abs(s.get('edge', 0)):.2f}")

else:
    print(f"\n⚠️  没有详细数据文件，无法分析拒绝原因")

# 读取v7.2增强的数据库记录（如果有）
try:
    from ats_core.data.analysis_db import get_analysis_db
    db = get_analysis_db()

    # 查询最近的v7.2分析记录
    recent_records = db.query_recent_signals(limit=100)

    if recent_records:
        print(f"\n🗄️  v7.2数据库记录分析:")
        print(f"   最近100条记录中:")

        gate_failures = {
            'gate1': 0,
            'gate2': 0,
            'gate3': 0,
            'gate4': 0,
            'gate5': 0
        }

        for record in recent_records:
            gate_results = record.get('gate_results', {})
            if gate_results:
                details = gate_results.get('details', [])
                for gate_detail in details:
                    gate_num = gate_detail.get('gate')
                    passed = gate_detail.get('pass', False)
                    if not passed:
                        gate_failures[f'gate{gate_num}'] += 1

        print(f"   闸门失败统计:")
        for gate_name, failures in gate_failures.items():
            if failures > 0:
                pct = failures / len(recent_records) * 100
                print(f"   {gate_name}: {failures}次失败 ({pct:.1f}%)")

except Exception as e:
    print(f"\n⚠️  无法读取数据库: {e}")

print("\n" + "=" * 70)
print("💡 建议:")
print("=" * 70)

# 根据分析给出建议
if detail and rejection_counter:
    top_reason = rejection_counter.most_common(1)[0] if rejection_counter else None

    if top_reason and top_reason[0] == "概率过低 (P < P_min)":
        current_P_min = gates_config.get('gate4_probability', {}).get('P_min', 0.50)
        print(f"1. 当前主要问题：概率阈值过高")
        print(f"   当前阈值: P >= {current_P_min}")
        print(f"   建议: 进一步降低到 P >= 0.40")
        print(f"   编辑: config/signal_thresholds.json")

    if near_threshold:
        print(f"\n2. 有 {len(near_threshold)} 个币种接近阈值")
        print(f"   建议: 微调阈值可增加信号")
        print(f"   差值范围: {min(item['P_gap'] for item in near_threshold):.3f} ~ {max(item['P_gap'] for item in near_threshold):.3f}")

print(f"\n3. Top 1策略：")
print(f"   当前策略: 每次扫描只发送Top 1信号")
print(f"   如需发送更多: 修改 scripts/realtime_signal_scanner.py:372")
print(f"   建议: 保持Top 1，避免信息过载")

print("\n" + "=" * 70)
print("✅ 诊断完成")
print("=" * 70)
