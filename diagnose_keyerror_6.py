#!/usr/bin/env python3
# coding: utf-8
"""
KeyError: 6 诊断脚本
快速定位K线字段访问错误的具体位置

Usage:
    python3 diagnose_keyerror_6.py
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ats_core.backtest.data_loader import HistoricalDataLoader
from ats_core.backtest.engine import BacktestEngine
from ats_core.pipeline.analyze_symbol import analyze_symbol_with_preloaded_klines

print("=" * 70)
print("KeyError: 6 诊断脚本")
print("=" * 70)
print()

# ==================== 测试1: K线数据格式检查 ====================
print("📋 测试1: 检查K线数据格式")
print("-" * 70)

try:
    data_loader = HistoricalDataLoader()

    # 尝试加载一小段K线数据
    end_time = int(datetime(2024, 8, 2).timestamp() * 1000)
    start_time = end_time - (10 * 3600 * 1000)  # 10小时

    print(f"加载测试K线: ETHUSDT 1h")
    print(f"时间范围: {start_time} - {end_time}")

    klines = data_loader.load_klines(
        symbol="ETHUSDT",
        start_time=start_time,
        end_time=end_time,
        interval="1h"
    )

    if klines and len(klines) > 0:
        print(f"✅ 成功加载 {len(klines)} 条K线")
        print()

        # 检查第一条K线的格式
        first_kline = klines[0]
        print(f"第一条K线类型: {type(first_kline)}")
        print(f"第一条K线内容: {first_kline}")
        print()

        if isinstance(first_kline, dict):
            print("✅ K线格式: 字典格式")
            print(f"字段列表: {list(first_kline.keys())}")
        elif isinstance(first_kline, list):
            print("✅ K线格式: 列表格式")
            print(f"字段数量: {len(first_kline)}")
            if len(first_kline) >= 11:
                print("字段映射: [timestamp, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_base, taker_buy_quote]")
        else:
            print(f"⚠️ 未知K线格式: {type(first_kline)}")
    else:
        print("❌ K线加载失败或为空")

except Exception as e:
    print(f"❌ 测试1失败: {e}")
    traceback.print_exc()

print()
print()

# ==================== 测试2: analyze_symbol调用追踪 ====================
print("📋 测试2: 追踪analyze_symbol调用")
print("-" * 70)

try:
    # 准备测试数据
    symbol = "ETHUSDT"

    print(f"测试符号: {symbol}")
    print("准备调用 analyze_symbol_with_preloaded_klines...")
    print()

    # 调用分析函数（这里会触发错误）
    result = analyze_symbol_with_preloaded_klines(
        symbol=symbol,
        k1h=klines,
        k4h=[],
        oi_data=None,
        spot_k1h=None,
        orderbook=None,
        mark_price=None,
        funding_rate=None,
        spot_price=None,
        btc_klines=None,
        eth_klines=None
    )

    print("✅ analyze_symbol调用成功")
    print(f"返回结果类型: {type(result)}")

    if isinstance(result, dict):
        print(f"结果字段: {list(result.keys())[:10]}...")  # 只显示前10个字段

except KeyError as e:
    print(f"❌ 捕获KeyError: {e}")
    print()
    print("完整错误追踪:")
    print("-" * 70)
    traceback.print_exc()
    print("-" * 70)
    print()

    # 分析错误位置
    tb = traceback.extract_tb(sys.exc_info()[2])
    print("错误调用栈分析:")
    for i, frame in enumerate(tb):
        print(f"  {i+1}. {frame.filename}:{frame.lineno} in {frame.name}")
        print(f"     {frame.line}")
    print()

    # 定位关键信息
    error_key = str(e).strip("'\"")
    print(f"⚠️ 尝试访问的键/索引: {error_key}")

    if error_key == "6":
        print()
        print("🔍 错误分析:")
        print("  - 代码尝试访问索引6（对应Binance K线的close_time字段）")
        print("  - 但K线数据可能是字典格式，不支持整数索引")
        print("  - 需要使用 _get_kline_field() 兼容函数")
        print()
        print("📍 可能的错误位置:")
        print("  - ats_core/pipeline/analyze_symbol.py 的 _analyze_symbol_core()")
        print("  - 或其他直接访问 kline[6] 的代码")

except Exception as e:
    print(f"❌ 测试2失败: {e}")
    traceback.print_exc()

print()
print()

# ==================== 测试3: 代码扫描 ====================
print("📋 测试3: 扫描代码中的K线索引访问")
print("-" * 70)

try:
    import re

    # 扫描可能存在问题的文件
    files_to_scan = [
        "ats_core/pipeline/analyze_symbol.py",
        "ats_core/backtest/engine.py",
        "ats_core/utils/factor_history.py"
    ]

    pattern = re.compile(r'\[([0-9]|10)\]')  # 匹配 [0] 到 [10] 的索引访问

    issues_found = []

    for file_path in files_to_scan:
        full_path = project_root / file_path
        if not full_path.exists():
            continue

        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            # 跳过注释行
            if line.strip().startswith('#'):
                continue

            # 检查是否包含数字索引访问
            matches = pattern.findall(line)
            if matches:
                # 检查是否与K线相关（包含kline, k1, k4, btc等关键词）
                if any(keyword in line.lower() for keyword in ['kline', 'k1', 'k4', 'btc', 'candle', '_k']):
                    issues_found.append({
                        'file': file_path,
                        'line': line_num,
                        'code': line.strip(),
                        'indices': matches
                    })

    if issues_found:
        print(f"⚠️ 发现 {len(issues_found)} 处可能的K线索引访问:")
        print()
        for issue in issues_found[:20]:  # 只显示前20个
            print(f"  📁 {issue['file']}:{issue['line']}")
            print(f"     访问索引: {issue['indices']}")
            print(f"     代码: {issue['code'][:80]}")
            print()
    else:
        print("✅ 未发现明显的K线索引访问问题")

except Exception as e:
    print(f"❌ 测试3失败: {e}")
    traceback.print_exc()

print()
print("=" * 70)
print("诊断完成")
print("=" * 70)
print()
print("📝 下一步:")
print("  1. 将以上输出完整复制给我")
print("  2. 特别注意 '错误调用栈分析' 部分")
print("  3. 我会根据具体位置修复代码")
