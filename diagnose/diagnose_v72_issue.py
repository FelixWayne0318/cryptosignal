#!/usr/bin/env python3
"""
v7.2数据持久化问题诊断脚本

检查:
1. 工作目录
2. 数据库路径
3. 报告文件路径
4. 路径计算逻辑
"""

import os
import sys
from pathlib import Path

print("=" * 70)
print("🔍 v7.2数据持久化问题诊断")
print("=" * 70)

# 1. 当前工作目录
print("\n1️⃣ 工作目录检查:")
print(f"   当前工作目录: {os.getcwd()}")
print(f"   预期工作目录: /home/user/cryptosignal")
if os.getcwd() != "/home/user/cryptosignal":
    print(f"   ❌ 工作目录不正确！")
else:
    print(f"   ✅ 工作目录正确")

# 2. 相对路径检查
print("\n2️⃣ 相对路径检查:")
data_dir = Path("data")
trade_db = Path("data/trade_history.db")
analysis_db = Path("data/analysis.db")
reports_dir = Path("reports")

print(f"   data/ 存在: {data_dir.exists()}")
print(f"   data/trade_history.db 存在: {trade_db.exists()}")
print(f"   data/analysis.db 存在: {analysis_db.exists()}")
print(f"   reports/ 存在: {reports_dir.exists()}")

if not data_dir.exists():
    print(f"   ❌ data目录不存在，相对路径会失败！")
    print(f"   当前目录结构: {list(Path('.').iterdir())[:10]}")

# 3. 模拟report_writer路径计算
print("\n3️⃣ ReportWriter路径计算:")
report_writer_file = "/home/user/cryptosignal/ats_core/analysis/report_writer.py"
if Path(report_writer_file).exists():
    p = Path(report_writer_file)
    project_root = p.parent.parent.parent
    print(f"   __file__: {report_writer_file}")
    print(f"   计算的project_root: {project_root}")
    print(f"   计算的reports目录: {project_root / 'reports'}")

    expected_path = "/home/user/cryptosignal/reports/latest/scan_summary.json"
    calculated_path = str(project_root / "reports" / "latest" / "scan_summary.json")

    print(f"\n   预期路径: {expected_path}")
    print(f"   计算路径: {calculated_path}")

    if expected_path == calculated_path:
        print(f"   ✅ 路径计算正确")
    else:
        print(f"   ❌ 路径计算错误！")

# 4. 检查实际数据库内容
print("\n4️⃣ 数据库内容检查:")
sys.path.insert(0, '/home/user/cryptosignal')

try:
    from ats_core.data.trade_recorder import get_recorder
    from ats_core.data.analysis_db import get_analysis_db

    recorder = get_recorder()
    analysis_db_obj = get_analysis_db()

    print(f"   TradeRecorder路径: {recorder.db_path}")
    print(f"   TradeRecorder绝对路径: {Path(recorder.db_path).resolve()}")

    print(f"   AnalysisDB路径: {analysis_db_obj.db_path}")
    print(f"   AnalysisDB绝对路径: {Path(analysis_db_obj.db_path).resolve()}")

    stats = recorder.get_statistics()
    print(f"\n   TradeRecorder信号数: {stats['total_signals']}")
    print(f"   通过闸门: {stats['gates_passed']}")

    if stats['total_signals'] == 0:
        print(f"   ⚠️  数据库是空的，可能数据写入到了错误的位置！")

except Exception as e:
    print(f"   ❌ 加载模块失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 检查文件时间戳
print("\n5️⃣ 报告文件时间戳:")
report_files = [
    "/home/user/cryptosignal/reports/latest/scan_summary.json",
    "/home/user/cryptosignal/reports/latest/scan_summary.md",
    "/home/user/cryptosignal/reports/latest/scan_detail.json"
]

for f in report_files:
    if Path(f).exists():
        mtime = Path(f).stat().st_mtime
        import datetime
        dt = datetime.datetime.fromtimestamp(mtime)
        print(f"   {Path(f).name}: {dt}")
    else:
        print(f"   {Path(f).name}: 不存在")

# 6. 寻找可能的错误路径
print("\n6️⃣ 寻找可能的错误写入位置:")
possible_wrong_paths = [
    "/home/cryptosignal/cryptosignal",
    "/home/cryptosignal",
    os.path.expanduser("~/cryptosignal/cryptosignal"),
]

for wrong_path in possible_wrong_paths:
    if Path(wrong_path).exists():
        print(f"   ⚠️  发现可疑目录: {wrong_path}")
        reports = Path(wrong_path) / "reports"
        data = Path(wrong_path) / "data"
        if reports.exists():
            print(f"      - 包含reports目录")
        if data.exists():
            print(f"      - 包含data目录")
    else:
        print(f"   ✅ {wrong_path} 不存在（正常）")

# 7. 总结和建议
print("\n" + "=" * 70)
print("📋 诊断总结:")
print("=" * 70)

issues = []

if os.getcwd() != "/home/user/cryptosignal":
    issues.append("工作目录不正确")

if not data_dir.exists():
    issues.append("data目录相对路径无法访问")

if stats.get('total_signals', 0) == 0:
    issues.append("数据库中无数据（可能写入到错误位置）")

if issues:
    print("❌ 发现问题:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")

    print("\n💡 解决方案:")
    print("   1. 确保脚本在正确的工作目录运行：")
    print("      cd ~/cryptosignal")
    print("      python3 scripts/realtime_signal_scanner_v72.py --interval 300")
    print()
    print("   2. 或者修改代码使用绝对路径而非相对路径")
    print("      例如：db_path = '/home/user/cryptosignal/data/trade_history.db'")
else:
    print("✅ 未发现明显问题")
    print("   请运行一次扫描并查看输出的路径是否正确")

print("=" * 70)
