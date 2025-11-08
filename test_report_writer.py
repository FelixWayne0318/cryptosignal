#!/usr/bin/env python3
"""
测试报告写入功能

验证：
1. 目录权限是否正常
2. 写入功能是否正常
3. JSON序列化是否正常
4. 文件是否创建成功
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_report_writer():
    """测试报告写入器"""
    print("=" * 60)
    print("🧪 测试报告写入功能")
    print("=" * 60)

    # 1. 测试导入
    print("\n1️⃣ 测试导入模块...")
    try:
        from ats_core.analysis.report_writer import ReportWriter
        from ats_core.analysis.scan_statistics import ScanStatistics
        print("   ✅ 模块导入成功")
    except Exception as e:
        print(f"   ❌ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. 测试目录权限
    print("\n2️⃣ 测试目录权限...")
    reports_dir = Path(__file__).parent / "reports"
    print(f"   检查目录: {reports_dir}")

    if not reports_dir.exists():
        print(f"   ❌ 目录不存在: {reports_dir}")
        return False

    # 测试写入权限
    test_file = reports_dir / "test_permission.txt"
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        test_file.unlink()
        print("   ✅ 目录可写")
    except Exception as e:
        print(f"   ❌ 目录不可写: {e}")
        return False

    # 3. 测试ReportWriter初始化
    print("\n3️⃣ 测试ReportWriter初始化...")
    try:
        writer = ReportWriter()
        print(f"   基础目录: {writer.base_dir}")
        print(f"   latest目录: {writer.latest_dir}")
        print(f"   history目录: {writer.history_dir}")
        print("   ✅ 初始化成功")
    except Exception as e:
        print(f"   ❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. 测试写入模拟数据
    print("\n4️⃣ 测试写入模拟数据...")

    # 模拟统计数据
    summary_data = {
        "timestamp": "2025-11-07T01:50:00",
        "scan_info": {
            "total_symbols": 10,
            "signals_found": 2,
            "filtered": 8
        },
        "signals": [
            {
                "symbol": "BTCUSDT",
                "edge": 0.65,
                "confidence": 78.5,
                "prime_strength": 85.2,
                "P_chosen": 0.820
            }
        ],
        "rejection_reasons": {
            "Edge不足": 5,
            "置信度不足": 3
        },
        "market_stats": {
            "avg_edge": 0.35,
            "avg_confidence": 42.1
        },
        "performance": {
            "total_time_sec": 25.5,
            "speed_coins_per_sec": 0.39
        }
    }

    detail_data = {
        "timestamp": "2025-11-07T01:50:00",
        "total_symbols": 10,
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "edge": 0.65,
                "confidence": 78.5,
                "T": 85,
                "M": 72
            }
        ]
    }

    text_report = """
==================================================
📊 测试扫描报告
==================================================
🕐 时间: 2025-11-07 01:50:00
📈 扫描币种: 10 个
✅ 信号数量: 2 个
📉 过滤数量: 8 个

🎯 【发出的信号】
  BTCUSDT: Edge=0.65, Conf=78.5, Prime=85.2

❌ 【拒绝原因分布】
  ❌ Edge不足: 5个 (50.0%)
  ❌ 置信度不足: 3个 (30.0%)
==================================================
    """

    try:
        files = writer.write_scan_report(
            summary=summary_data,
            detail=detail_data,
            text_report=text_report
        )

        print("   ✅ 写入成功！")
        print("\n   📁 生成的文件:")
        for key, path in files.items():
            file_path = Path(path)
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"      ✅ {key}: {path} ({size} bytes)")
            else:
                print(f"      ❌ {key}: {path} (不存在)")

    except Exception as e:
        print(f"   ❌ 写入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. 验证文件内容
    print("\n5️⃣ 验证文件内容...")

    # 检查summary JSON
    summary_file = writer.latest_dir / "scan_summary.json"
    try:
        import json
        with open(summary_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        print(f"   ✅ scan_summary.json 可读")
        print(f"      - signals_found: {loaded['scan_info']['signals_found']}")
    except Exception as e:
        print(f"   ❌ scan_summary.json 读取失败: {e}")
        return False

    # 检查Markdown
    md_file = writer.latest_dir / "scan_summary.md"
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"   ✅ scan_summary.md 可读 ({len(content)} 字符)")
    except Exception as e:
        print(f"   ❌ scan_summary.md 读取失败: {e}")
        return False

    # 6. 测试趋势文件
    print("\n6️⃣ 检查趋势文件...")
    trends_file = writer.base_dir / "trends.json"
    if trends_file.exists():
        try:
            with open(trends_file, 'r', encoding='utf-8') as f:
                trends = json.load(f)
            print(f"   ✅ trends.json 存在")
            print(f"      - 历史记录数: {len(trends.get('signals_count', []))}")
        except Exception as e:
            print(f"   ⚠️ trends.json 读取失败: {e}")
    else:
        print(f"   ⚠️ trends.json 不存在（首次运行正常）")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_report_writer()
    sys.exit(0 if success else 1)
