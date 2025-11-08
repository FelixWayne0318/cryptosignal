#!/usr/bin/env python3
# coding: utf-8
"""
数据库初始化脚本

功能：
1. 初始化TradeRecorder数据库（data/trade_history.db）
2. 初始化AnalysisDB数据库（data/analysis.db）
3. 验证数据库表结构是否正确

使用场景：
- 首次部署时自动初始化数据库
- 更换服务器时重新创建数据库
- 数据库损坏时重建

执行方式：
- 由 setup.sh 自动调用
- 也可手动执行：python3 scripts/init_databases.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.data.trade_recorder import get_recorder
from ats_core.data.analysis_db import get_analysis_db


def init_trade_recorder():
    """初始化TradeRecorder数据库"""
    print("📊 初始化 TradeRecorder 数据库...")

    try:
        recorder = get_recorder("data/trade_history.db")

        # 验证表是否存在
        stats = recorder.get_statistics()

        print(f"   ✅ trade_history.db 初始化成功")
        print(f"      - 已记录信号: {stats['total_signals']}个")
        print(f"      - 路径: data/trade_history.db")
        return True

    except Exception as e:
        print(f"   ❌ trade_history.db 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_analysis_db():
    """初始化AnalysisDB数据库"""
    print("📊 初始化 AnalysisDB 数据库...")

    try:
        db = get_analysis_db("data/analysis.db")

        # 验证表是否存在（通过查询闸门统计）
        stats = db.get_gate_statistics()

        print(f"   ✅ analysis.db 初始化成功")
        print(f"      - 已记录信号: {stats['total_signals']}个")
        print(f"      - 路径: data/analysis.db")
        print(f"      - 表结构: 6个专业表")
        print(f"        * market_data: 市场原始数据")
        print(f"        * factor_scores: 因子计算结果")
        print(f"        * signal_analysis: 信号分析数据")
        print(f"        * gate_evaluation: 闸门评估结果")
        print(f"        * modulator_effects: 调制器影响")
        print(f"        * signal_outcomes: 实际结果跟踪")
        return True

    except Exception as e:
        print(f"   ❌ analysis.db 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🗄️  CryptoSignal 数据库初始化")
    print("=" * 60)
    print("")

    # 确保data目录存在
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"✅ 数据目录已就绪: {data_dir}")
    print("")

    # 初始化数据库
    results = []

    # 1. TradeRecorder
    results.append(("TradeRecorder", init_trade_recorder()))
    print("")

    # 2. AnalysisDB
    results.append(("AnalysisDB", init_analysis_db()))
    print("")

    # 总结
    print("=" * 60)
    print("📊 初始化结果")
    print("=" * 60)

    all_success = True
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{status}: {name}")
        if not success:
            all_success = False

    print("")

    if all_success:
        print("✅ 所有数据库初始化成功！")
        print("")
        print("📝 数据库文件位置：")
        print("   - data/trade_history.db (TradeRecorder)")
        print("   - data/analysis.db (AnalysisDB)")
        print("")
        print("💡 注意事项：")
        print("   - 数据库文件已加入.gitignore，不会被提交")
        print("   - 更换服务器时会自动重新创建")
        print("   - 数据会持久保存在服务器本地")
        print("")
        return 0
    else:
        print("❌ 部分数据库初始化失败，请检查错误信息")
        return 1


if __name__ == '__main__':
    sys.exit(main())
