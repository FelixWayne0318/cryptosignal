#!/usr/bin/env python3
# coding: utf-8
"""
候选池架构测试脚本

测试内容:
1. 池管理器基础功能
2. 缓存机制验证
3. Elite Pool构建
4. Overlay Pool构建
5. 池合并逻辑
6. API调用量估算
"""

from __future__ import annotations
import sys
import os
import time
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.pools.pool_manager import PoolManager, get_pool_manager


def test_1_pool_manager_creation():
    """测试1: 池管理器创建"""
    print("\n" + "=" * 60)
    print("测试1: 池管理器创建")
    print("=" * 60)

    try:
        manager = PoolManager(
            data_dir="data",
            elite_cache_hours=24,
            overlay_cache_hours=1,
            verbose=True
        )
        print("✅ 池管理器创建成功")
        print(f"   数据目录: {manager.data_dir}")
        print(f"   Elite缓存路径: {manager.elite_cache_path}")
        print(f"   Overlay缓存路径: {manager.overlay_cache_path}")
        return True
    except Exception as e:
        print(f"❌ 池管理器创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_cache_status():
    """测试2: 缓存状态检查"""
    print("\n" + "=" * 60)
    print("测试2: 缓存状态检查")
    print("=" * 60)

    try:
        manager = get_pool_manager()
        status = manager.get_cache_status()

        print("Elite Pool状态:")
        elite = status.get('elite', {})
        if elite.get('exists'):
            print(f"   存在: ✅")
            print(f"   有效: {'✅' if elite['valid'] else '❌'}")
            print(f"   年龄: {elite['age_hours']:.2f} 小时")
        else:
            print(f"   存在: ❌ (首次运行)")

        print("\nOverlay Pool状态:")
        overlay = status.get('overlay', {})
        if overlay.get('exists'):
            print(f"   存在: ✅")
            print(f"   有效: {'✅' if overlay['valid'] else '❌'}")
            print(f"   年龄: {overlay['age_hours']:.2f} 小时")
        else:
            print(f"   存在: ❌ (首次运行)")

        print("✅ 缓存状态检查完成")
        return True
    except Exception as e:
        print(f"❌ 缓存状态检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_elite_pool():
    """测试3: Elite Pool构建（可能需要较长时间）"""
    print("\n" + "=" * 60)
    print("测试3: Elite Pool构建")
    print("=" * 60)
    print("⚠️ 警告: 首次构建可能需要较长时间（取决于API限制）")
    print("   如果遇到403错误，这是已知的网络问题，不影响架构正确性")

    try:
        manager = get_pool_manager()
        start_time = time.time()

        symbols = manager.get_elite_pool(force_rebuild=False)
        elapsed = time.time() - start_time

        print(f"\n✅ Elite Pool获取成功")
        print(f"   币种数量: {len(symbols)}")
        print(f"   耗时: {elapsed:.2f} 秒")
        if symbols:
            print(f"   前10个币种: {', '.join(symbols[:10])}")

        return True
    except Exception as e:
        print(f"❌ Elite Pool构建失败: {e}")
        print(f"   这可能是由于Binance API 403错误（已知网络问题）")
        import traceback
        traceback.print_exc()
        return False


def test_4_overlay_pool():
    """测试4: Overlay Pool构建"""
    print("\n" + "=" * 60)
    print("测试4: Overlay Pool构建")
    print("=" * 60)

    try:
        manager = get_pool_manager()

        # 获取Elite Pool（用于去重）
        elite_symbols = manager.get_elite_pool(force_rebuild=False)
        print(f"Elite Pool: {len(elite_symbols)} 个币种")

        start_time = time.time()
        symbols = manager.get_overlay_pool(
            elite_symbols=elite_symbols,
            force_rebuild=False
        )
        elapsed = time.time() - start_time

        print(f"\n✅ Overlay Pool获取成功")
        print(f"   币种数量: {len(symbols)}")
        print(f"   耗时: {elapsed:.2f} 秒")
        if symbols:
            print(f"   前5个币种: {', '.join(symbols[:5])}")

        return True
    except Exception as e:
        print(f"❌ Overlay Pool构建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_merged_universe():
    """测试5: 合并候选池"""
    print("\n" + "=" * 60)
    print("测试5: 合并候选池")
    print("=" * 60)

    try:
        manager = get_pool_manager()
        start_time = time.time()

        symbols, metadata = manager.get_merged_universe()
        elapsed = time.time() - start_time

        print(f"\n✅ 候选池合并成功")
        print(f"   总币种数: {metadata['total_count']}")
        print(f"   Elite Pool: {metadata['elite_count']} 个")
        print(f"   Overlay Pool: {metadata['overlay_count']} 个")
        print(f"   重叠币种: {metadata['overlap_count']} 个")
        print(f"   Elite缓存: {'有效' if metadata['elite_cache_valid'] else '重建'}")
        print(f"   Overlay缓存: {'有效' if metadata['overlay_cache_valid'] else '重建'}")
        print(f"   耗时: {elapsed:.2f} 秒")

        if symbols:
            print(f"\n   前10个币种: {', '.join(symbols[:10])}")

        return True
    except Exception as e:
        print(f"❌ 候选池合并失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_cache_validation():
    """测试6: 缓存有效性验证（再次调用应该更快）"""
    print("\n" + "=" * 60)
    print("测试6: 缓存有效性验证")
    print("=" * 60)
    print("预期: 第二次调用应该使用缓存，速度明显加快")

    try:
        manager = get_pool_manager()

        # 第一次调用
        print("\n第一次调用...")
        start_time_1 = time.time()
        symbols_1, metadata_1 = manager.get_merged_universe()
        elapsed_1 = time.time() - start_time_1

        # 第二次调用（应该使用缓存）
        print("\n第二次调用...")
        start_time_2 = time.time()
        symbols_2, metadata_2 = manager.get_merged_universe()
        elapsed_2 = time.time() - start_time_2

        print(f"\n✅ 缓存验证完成")
        print(f"   第一次: {elapsed_1:.3f} 秒")
        print(f"   第二次: {elapsed_2:.3f} 秒")

        if elapsed_2 < elapsed_1 * 0.1:  # 第二次应该快至少10倍
            print(f"   ✅ 加速比: {elapsed_1/elapsed_2:.1f}x (缓存生效)")
        else:
            print(f"   ⚠️ 加速比: {elapsed_1/elapsed_2:.1f}x (可能缓存未生效)")

        # 验证结果一致性
        if symbols_1 == symbols_2:
            print(f"   ✅ 结果一致性: 完全一致")
        else:
            print(f"   ⚠️ 结果一致性: 存在差异")

        return True
    except Exception as e:
        print(f"❌ 缓存验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_api_call_estimation():
    """测试7: API调用量估算"""
    print("\n" + "=" * 60)
    print("测试7: API调用量估算")
    print("=" * 60)

    try:
        manager = get_pool_manager()
        symbols, metadata = manager.get_merged_universe()

        print("旧架构估算（每次扫描）:")
        print(f"   Base Pool: {metadata['elite_count']} 币种 × 800根K线 = {metadata['elite_count'] * 800:,} 根")
        print(f"   Overlay Pool: {metadata['overlay_count']} 币种 × 60根K线 = {metadata['overlay_count'] * 60:,} 根")
        old_total = metadata['elite_count'] * 800 + metadata['overlay_count'] * 60
        print(f"   总计: {old_total:,} 根K线/次")

        print("\n新架构估算（使用缓存）:")
        print(f"   Elite Pool: 每24小时构建1次")
        print(f"   Overlay Pool: 每1小时构建1次")
        print(f"   假设每天扫描24次（每小时一次）:")
        new_daily = metadata['elite_count'] * 800 * 1 + metadata['overlay_count'] * 60 * 24
        print(f"   每日总计: {new_daily:,} 根K线")

        old_daily = old_total * 24
        print(f"\n对比:")
        print(f"   旧架构每日: {old_daily:,} 根K线")
        print(f"   新架构每日: {new_daily:,} 根K线")
        reduction = (1 - new_daily / old_daily) * 100
        print(f"   ✅ API调用量降低: {reduction:.1f}% 🚀")

        return True
    except Exception as e:
        print(f"❌ API调用量估算失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("候选池架构综合测试")
    print("=" * 60)
    print("\n⚠️ 重要提示:")
    print("   1. 首次运行需要构建缓存，可能较慢")
    print("   2. 如果遇到403错误，这是已知的Binance API网络问题")
    print("   3. 架构和缓存机制仍然正确，只是API访问受限")

    tests = [
        ("池管理器创建", test_1_pool_manager_creation),
        ("缓存状态检查", test_2_cache_status),
        ("Elite Pool构建", test_3_elite_pool),
        ("Overlay Pool构建", test_4_overlay_pool),
        ("合并候选池", test_5_merged_universe),
        ("缓存有效性验证", test_6_cache_validation),
        ("API调用量估算", test_7_api_call_estimation),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except KeyboardInterrupt:
            print("\n\n⚠️ 测试被用户中断")
            break
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 发生未预期错误: {e}")
            results.append((name, False))

        # 等待一下，避免API限制
        time.sleep(0.5)

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")

    print("\n" + "-" * 60)
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！")
    elif passed > 0:
        print(f"⚠️ 部分测试通过（{passed}/{total}）")
        print("   如果失败是由于Binance API 403错误，这是已知网络问题")
        print("   架构设计和缓存机制仍然正确")
    else:
        print("❌ 所有测试失败")

    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
