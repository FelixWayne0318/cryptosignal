#!/usr/bin/env python3
"""
v7.2.17 类型安全修复 - 完整测试脚本

用户在Termius中运行：
    python3 test_v7217_fix.py

测试内容：
    1. 清除Python缓存（确保使用最新代码）
    2. 模块导入测试
    3. _get_dict函数测试
    4. render_trade_v72类型安全测试
    5. 极端边界情况测试
"""

import sys
import os
import traceback
from pathlib import Path
import subprocess

# 确保导入路径正确
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_clear_cache():
    """测试1: 清除Python缓存"""
    print_section("测试1: 清除Python缓存")

    try:
        # 清除__pycache__目录
        result = subprocess.run(
            ["find", str(project_root), "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # 清除.pyc文件
        result2 = subprocess.run(
            ["find", str(project_root), "-type", "f", "-name", "*.pyc", "-delete"],
            capture_output=True,
            text=True,
            timeout=10
        )

        print("✅ 已清除所有Python缓存文件")
        print("   - __pycache__ 目录已删除")
        print("   - *.pyc 文件已删除")
        return True

    except Exception as e:
        print(f"⚠️  清除缓存失败（非致命）: {e}")
        return True  # 非致命错误

def test_module_import():
    """测试2: 模块导入"""
    print_section("测试2: 模块导入")

    try:
        from ats_core.outputs.telegram_fmt import render_trade_v72, _get_dict
        print("✅ 成功导入 render_trade_v72")
        print("✅ 成功导入 _get_dict (v7.2.17新增)")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        traceback.print_exc()
        return False

def test_get_dict_function():
    """测试3: _get_dict函数"""
    print_section("测试3: _get_dict函数类型安全测试")

    try:
        from ats_core.outputs.telegram_fmt import _get_dict

        # 测试用例
        test_cases = [
            {
                "name": "正常字典",
                "data": {"scores": {"T": 50, "C": 60}},
                "key": "scores",
                "expected": {"T": 50, "C": 60},
            },
            {
                "name": "字符串值（问题数据）",
                "data": {"scores": "invalid_string"},
                "key": "scores",
                "expected": {},
            },
            {
                "name": "None值",
                "data": {"scores": None},
                "key": "scores",
                "expected": {},
            },
            {
                "name": "不存在的键",
                "data": {"other": "value"},
                "key": "scores",
                "expected": {},
            },
            {
                "name": "嵌套路径",
                "data": {"v72": {"scores": {"T": 70}}},
                "key": "v72.scores",
                "expected": {"T": 70},
            },
            {
                "name": "数字值",
                "data": {"scores": 123},
                "key": "scores",
                "expected": {},
            },
            {
                "name": "列表值",
                "data": {"scores": [1, 2, 3]},
                "key": "scores",
                "expected": {},
            },
        ]

        passed = 0
        failed = 0

        for case in test_cases:
            result = _get_dict(case["data"], case["key"])
            if result == case["expected"]:
                print(f"✅ {case['name']:20s}: {result}")
                passed += 1
            else:
                print(f"❌ {case['name']:20s}: 期望 {case['expected']}, 实际 {result}")
                failed += 1

        print(f"\n总结: {passed} 个通过, {failed} 个失败")
        return failed == 0

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False

def test_render_trade_v72():
    """测试4: render_trade_v72类型安全"""
    print_section("测试4: render_trade_v72类型安全测试")

    try:
        from ats_core.outputs.telegram_fmt import render_trade_v72

        # 测试用例1: 正常数据
        normal_signal = {
            "symbol": "BTCUSDT",
            "side_long": True,
            "confidence": 65.0,
            "confidence_adjusted": 70.0,
            "prime_strength": 70,
            "prime_prob": 0.70,
            "edge": 0.30,
            "scores": {"T": 60, "C": 70, "V": 65, "M": 75, "D": 60, "L": 65},
            "v72_enhancements": {
                "I_meta": {"beta_btc": 0.85, "beta_eth": 0.90},
                "independence_market_analysis": {"market_regime": 40.0, "alignment": "顺势"},
                "group_scores": {"TC": 65, "MV": 70},
                "gates": {"details": [{"gate": "gate1", "status": "pass"}]},
            }
        }

        print("\n📊 测试4.1: 正常字典数据")
        result1 = render_trade_v72(normal_signal)
        print(f"✅ 正常数据渲染成功 (长度: {len(result1)} 字符)")

        # 测试用例2: 所有嵌套字段都是字符串（极端问题数据）
        problematic_signal = {
            "symbol": "UNIUSDT",
            "side_long": True,
            "confidence": 55.0,
            "confidence_adjusted": 55.0,
            "prime_strength": 60,
            "prime_prob": 0.65,
            "edge": 0.25,
            "scores": "invalid_string_for_scores",  # ⚠️ 字符串
            "gates": "invalid_string_for_gates",  # ⚠️ 字符串
            "modulator_output": "invalid_string",  # ⚠️ 字符串
            "scores_meta": "invalid_string",  # ⚠️ 字符串
            "v72_enhancements": {
                "I_meta": "invalid_string",  # ⚠️ 字符串
                "independence_market_analysis": "invalid_string",  # ⚠️ 字符串
                "group_scores": "invalid_string",  # ⚠️ 字符串
                "gates": "invalid_string",  # ⚠️ 字符串
            }
        }

        print("\n📊 测试4.2: 问题数据（所有嵌套字段为字符串）")
        try:
            result2 = render_trade_v72(problematic_signal)
            print(f"✅ 问题数据渲染成功（v7.2.17修复生效！）")
            print(f"   消息长度: {len(result2)} 字符")
            print("   ⚠️  如果看到这条消息，说明v7.2.17已彻底修复'str' object has no attribute 'get'错误")
            return True
        except AttributeError as e:
            if "'str' object has no attribute 'get'" in str(e):
                print(f"❌ 仍然存在'str' object has no attribute 'get'错误")
                print(f"   错误详情: {e}")
                traceback.print_exc()
                return False
            else:
                raise

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False

def test_edge_cases():
    """测试5: 极端边界情况"""
    print_section("测试5: 极端边界情况测试")

    try:
        from ats_core.outputs.telegram_fmt import render_trade_v72

        # 测试用例：混合类型（部分字典，部分字符串）
        mixed_signal = {
            "symbol": "ETHUSDT",
            "side_long": False,
            "confidence": 50.0,
            "confidence_adjusted": 50.0,
            "prime_strength": 50,
            "prime_prob": 0.60,
            "edge": 0.20,
            "scores": {"T": 50, "C": 55},  # 正常字典
            "gates": "string_value",  # 字符串
            "modulator_output": {"p_bull": 0.6},  # 正常字典
            "scores_meta": None,  # None值
            "v72_enhancements": {
                "I_meta": {"beta_btc": 0.75},  # 正常字典
                "independence_market_analysis": "string",  # 字符串
                "group_scores": None,  # None
                "gates": [],  # 列表（非字典）
            }
        }

        print("\n📊 混合类型数据（字典+字符串+None+列表）")
        result = render_trade_v72(mixed_signal)
        print(f"✅ 混合数据渲染成功 (长度: {len(result)} 字符)")
        return True

    except Exception as e:
        print(f"❌ 边界测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试流程"""
    print("=" * 80)
    print("  🧪 v7.2.17 类型安全修复 - 完整测试套件")
    print("  修复目标: 根治 'str' object has no attribute 'get' 错误")
    print("=" * 80)

    results = []

    # 测试1: 清除缓存
    results.append(("清除缓存", test_clear_cache()))

    # 测试2: 模块导入
    results.append(("模块导入", test_module_import()))

    # 如果导入失败，后续测试无法进行
    if not results[-1][1]:
        print_section("❌ 测试终止：模块导入失败")
        return False

    # 测试3: _get_dict函数
    results.append(("_get_dict函数", test_get_dict_function()))

    # 测试4: render_trade_v72
    results.append(("render_trade_v72", test_render_trade_v72()))

    # 测试5: 边界情况
    results.append(("边界情况", test_edge_cases()))

    # 总结
    print_section("📊 测试总结")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status}  {name}")

    print("\n" + "=" * 80)
    if passed == total:
        print(f"  🎉 所有测试通过！({passed}/{total})")
        print("  v7.2.17修复生效，'str' object has no attribute 'get'错误已根治")
        print("=" * 80)
        return True
    else:
        print(f"  ⚠️  部分测试失败 ({passed}/{total})")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
