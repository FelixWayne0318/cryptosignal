#!/usr/bin/env python3
"""
修复v7.2路径问题：将相对路径改为绝对路径

问题：
- trade_recorder.py 使用相对路径 "data/trade_history.db"
- analysis_db.py 使用相对路径 "data/analysis.db"
- report_writer.py 使用相对路径计算

解决方案：
- 使用绝对路径，避免工作目录问题
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path("/home/user/cryptosignal")

print("=" * 70)
print("🔧 修复v7.2路径配置")
print("=" * 70)

# 1. 修复 trade_recorder.py
print("\n1️⃣ 修复 trade_recorder.py...")
trade_recorder_file = PROJECT_ROOT / "ats_core/data/trade_recorder.py"

if trade_recorder_file.exists():
    content = trade_recorder_file.read_text()

    # 替换默认路径
    old_line = 'def __init__(self, db_path: str = "data/trade_history.db"):'
    new_line = f'def __init__(self, db_path: str = "{PROJECT_ROOT}/data/trade_history.db"):'

    if old_line in content:
        content = content.replace(old_line, new_line)
        print(f"   ✅ 已修改 __init__ 默认参数")

    old_line2 = 'def get_recorder(db_path: str = "data/trade_history.db") -> TradeRecorder:'
    new_line2 = f'def get_recorder(db_path: str = "{PROJECT_ROOT}/data/trade_history.db") -> TradeRecorder:'

    if old_line2 in content:
        content = content.replace(old_line2, new_line2)
        print(f"   ✅ 已修改 get_recorder 默认参数")

    trade_recorder_file.write_text(content)
    print(f"   📝 已保存更改")
else:
    print(f"   ❌ 文件不存在: {trade_recorder_file}")

# 2. 修复 analysis_db.py
print("\n2️⃣ 修复 analysis_db.py...")
analysis_db_file = PROJECT_ROOT / "ats_core/data/analysis_db.py"

if analysis_db_file.exists():
    content = analysis_db_file.read_text()

    old_line = 'def __init__(self, db_path: str = "data/analysis.db"):'
    new_line = f'def __init__(self, db_path: str = "{PROJECT_ROOT}/data/analysis.db"):'

    if old_line in content:
        content = content.replace(old_line, new_line)
        print(f"   ✅ 已修改 __init__ 默认参数")

    old_line2 = 'def get_analysis_db(db_path: str = "data/analysis.db") -> AnalysisDB:'
    new_line2 = f'def get_analysis_db(db_path: str = "{PROJECT_ROOT}/data/analysis.db") -> AnalysisDB:'

    if old_line2 in content:
        content = content.replace(old_line2, new_line2)
        print(f"   ✅ 已修改 get_analysis_db 默认参数")

    analysis_db_file.write_text(content)
    print(f"   📝 已保存更改")
else:
    print(f"   ❌ 文件不存在: {analysis_db_file}")

# 3. 验证修复
print("\n3️⃣ 验证修复...")
import sys
sys.path.insert(0, str(PROJECT_ROOT))

try:
    # 重新导入（清除缓存）
    if 'ats_core.data.trade_recorder' in sys.modules:
        del sys.modules['ats_core.data.trade_recorder']
    if 'ats_core.data.analysis_db' in sys.modules:
        del sys.modules['ats_core.data.analysis_db']

    from ats_core.data.trade_recorder import get_recorder
    from ats_core.data.analysis_db import get_analysis_db

    recorder = get_recorder()
    analysis_db = get_analysis_db()

    print(f"   TradeRecorder DB路径: {recorder.db_path}")
    print(f"   AnalysisDB DB路径: {analysis_db.db_path}")

    if str(PROJECT_ROOT) in recorder.db_path:
        print(f"   ✅ TradeRecorder使用绝对路径")
    else:
        print(f"   ⚠️  TradeRecorder仍使用相对路径")

    if str(PROJECT_ROOT) in analysis_db.db_path:
        print(f"   ✅ AnalysisDB使用绝对路径")
    else:
        print(f"   ⚠️  AnalysisDB仍使用相对路径")

except Exception as e:
    print(f"   ❌ 验证失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ 修复完成！")
print()
print("💡 下一步:")
print("   1. 重启扫描器: pkill -f realtime_signal_scanner")
print("   2. 运行 setup.sh 或手动启动")
print("   3. 观察日志中的路径是否正确")
print("=" * 70)
