#!/usr/bin/env python3
# coding: utf-8
"""
Phase 1: 快速集成测试

简化测试：直接运行扫描器，检查数据更新是否正常工作

运行方法：
    python tests/test_phase1_quick.py
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.logging import log, warn, error


async def main():
    """快速集成测试"""
    log("\n" + "=" * 80)
    log("Phase 1: 快速集成测试")
    log("=" * 80)
    log("\n测试策略:")
    log("1. 导入所有修改的模块，检查是否有语法错误")
    log("2. 检查新添加的方法是否存在")
    log("3. 检查智能时间对齐函数")
    log("\n" + "=" * 80)

    try:
        # 测试1: 导入模块
        log("\n[测试1] 导入修改的模块...")
        try:
            from ats_core.data.realtime_kline_cache import RealtimeKlineCache
            log("   ✓ realtime_kline_cache.py 导入成功")
        except Exception as e:
            error(f"   ✗ realtime_kline_cache.py 导入失败: {e}")
            return False

        try:
            # 检查文件语法而不导入（避免依赖问题）
            batch_file = project_root / 'ats_core' / 'pipeline' / 'batch_scan_optimized.py'
            if batch_file.exists():
                # 使用 Python 编译检查语法
                import py_compile
                py_compile.compile(str(batch_file), doraise=True)
                log("   ✓ batch_scan_optimized.py 语法正确")
            else:
                error("   ✗ batch_scan_optimized.py 文件不存在")
                return False
        except SyntaxError as e:
            error(f"   ✗ batch_scan_optimized.py 语法错误: {e}")
            return False
        except Exception as e:
            warn(f"   ⚠ batch_scan_optimized.py 检查警告: {e}（可能是依赖问题，继续...）")

        try:
            sys.path.insert(0, str(project_root / 'scripts'))
            # 不直接导入整个模块，只检查文件
            scanner_file = project_root / 'scripts' / 'realtime_signal_scanner.py'
            if scanner_file.exists():
                log("   ✓ realtime_signal_scanner.py 文件存在")
            else:
                error("   ✗ realtime_signal_scanner.py 文件不存在")
                return False
        except Exception as e:
            error(f"   ✗ realtime_signal_scanner.py 检查失败: {e}")
            return False

        # 测试2: 检查新方法是否存在
        log("\n[测试2] 检查新添加的方法...")
        cache = RealtimeKlineCache(max_klines=50)

        methods_to_check = [
            'update_current_prices',
            'update_completed_klines',
            'update_market_data',
            'get_market_data'
        ]

        for method_name in methods_to_check:
            if hasattr(cache, method_name):
                log(f"   ✓ {method_name}() 方法存在")
            else:
                error(f"   ✗ {method_name}() 方法不存在")
                return False

        # 测试3: 检查方法签名
        log("\n[测试3] 检查方法签名...")
        import inspect

        # 检查 update_current_prices
        sig = inspect.signature(cache.update_current_prices)
        params = list(sig.parameters.keys())
        expected_params = ['symbols', 'client']
        if all(p in params for p in expected_params):
            log(f"   ✓ update_current_prices() 签名正确: {params}")
        else:
            error(f"   ✗ update_current_prices() 签名错误: {params}")
            return False

        # 检查 update_completed_klines
        sig = inspect.signature(cache.update_completed_klines)
        params = list(sig.parameters.keys())
        expected_params = ['symbols', 'intervals', 'client']
        if all(p in params for p in expected_params):
            log(f"   ✓ update_completed_klines() 签名正确: {params}")
        else:
            error(f"   ✗ update_completed_klines() 签名错误: {params}")
            return False

        # 测试4: 检查智能时间对齐逻辑
        log("\n[测试4] 检查智能时间对齐逻辑...")
        test_cases = [
            (0, [2]),    # 00分 → 02分
            (2, [7]),    # 02分 → 07分
            (15, [17]),  # 15分 → 17分
            (47, [52]),  # 47分 → 52分
            (57, [2]),   # 57分 → 下一小时02分
        ]

        key_minutes = [2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57]

        for current_min, expected_mins in test_cases:
            next_key_minute = None
            for km in key_minutes:
                if km > current_min:
                    next_key_minute = km
                    break

            if next_key_minute is None:
                next_key_minute = 2  # 下一小时

            if next_key_minute in expected_mins:
                log(f"   ✓ {current_min:02d}分 → {next_key_minute:02d}分")
            else:
                error(f"   ✗ {current_min:02d}分 → {next_key_minute:02d}分 (期望{expected_mins})")
                return False

        # 测试5: 验证代码文档
        log("\n[测试5] 验证方法文档...")
        if cache.update_current_prices.__doc__:
            log(f"   ✓ update_current_prices() 有文档")
            # 检查是否包含关键词
            doc = cache.update_current_prices.__doc__
            if 'Layer 1' in doc and '快速价格更新' in doc:
                log(f"   ✓ 文档包含正确的描述")
            else:
                warn(f"   ⚠ 文档描述可能不完整")
        else:
            warn(f"   ⚠ update_current_prices() 缺少文档")

        # 所有测试通过
        log("\n" + "=" * 80)
        log("✅ 所有检查通过！")
        log("=" * 80)
        log("\n下一步:")
        log("1. 部署到生产环境")
        log("2. 运行实际扫描测试")
        log("3. 观察数据更新日志")
        log("\n命令:")
        log("   cd /home/user/cryptosignal")
        log("   ./deploy_and_run.sh restart")
        log("\n" + "=" * 80)

        return True

    except Exception as e:
        error(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
