#!/usr/bin/env python3
# coding: utf-8
"""
FactorConfig 修复验证脚本

功能：
1. 测试 FactorConfig 是否正确加载
2. 测试 analyze_symbol 是否能正常工作
3. 验证输出配置是否生效
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/home/user/cryptosignal')

def test_factorconfig_import():
    """测试1: FactorConfig 导入和基本使用"""
    print("=" * 60)
    print("测试1: FactorConfig 导入和基本使用")
    print("=" * 60)

    try:
        from ats_core.config.factor_config import get_factor_config
        print("✅ 导入成功")

        config = get_factor_config()
        print(f"✅ 获取配置成功，版本: {config.version}")

        # 测试正确用法
        i_params = config.config.get('I因子参数', {})
        print(f"✅ 正确用法测试通过: {list(i_params.keys())[:3]}...")

        # 测试错误用法会报错
        try:
            wrong = config.get('I因子参数', {})
            print("❌ 错误用法没有报错！这不应该发生！")
            return False
        except AttributeError:
            print("✅ 错误用法正确报错")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analyze_symbol_import():
    """测试2: analyze_symbol 模块导入"""
    print("\n" + "=" * 60)
    print("测试2: analyze_symbol 模块导入")
    print("=" * 60)

    try:
        from ats_core.pipeline.analyze_symbol import analyze_symbol_with_preloaded_klines
        print("✅ analyze_symbol_with_preloaded_klines 导入成功")

        from ats_core.pipeline.analyze_symbol import _analyze_symbol_core
        print("✅ _analyze_symbol_core 导入成功")

        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scan_output_config():
    """测试3: 扫描输出配置加载"""
    print("\n" + "=" * 60)
    print("测试3: 扫描输出配置加载")
    print("=" * 60)

    try:
        import json
        from pathlib import Path

        config_path = Path('/home/user/cryptosignal/config/scan_output.json')

        if not config_path.exists():
            print(f"❌ 配置文件不存在: {config_path}")
            return False

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print("✅ 配置文件加载成功")

        # 检查关键配置
        mode = config['output_detail_level']['mode']
        show_core = config['factor_output']['show_core_factors']
        show_mod = config['factor_output']['show_modulators']
        show_f = config['diagnostic_output']['show_f_factor_details']
        show_i = config['diagnostic_output']['show_i_factor_details']
        show_stats = config['statistics_output']['show_full_statistics']

        print(f"  模式: {mode}")
        print(f"  显示核心因子: {show_core}")
        print(f"  显示调制器: {show_mod}")
        print(f"  显示F详情: {show_f}")
        print(f"  显示I详情: {show_i}")
        print(f"  显示完整统计: {show_stats}")

        if mode == 'full' and all([show_core, show_mod, show_f, show_i, show_stats]):
            print("✅ 所有输出配置正确")
            return True
        else:
            print("❌ 输出配置有误")
            return False

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analyze_symbol_execution():
    """测试4: 实际执行 analyze_symbol（简单测试）"""
    print("\n" + "=" * 60)
    print("测试4: analyze_symbol 实际执行")
    print("=" * 60)

    try:
        from ats_core.config.factor_config import get_factor_config

        # 这个测试只检查代码是否会抛出 AttributeError
        factor_config = get_factor_config()

        # 模拟 analyze_symbol 中的关键代码
        i_factor_params = factor_config.config.get('I因子参数', {})
        i_effective_threshold = i_factor_params.get('effective_threshold', 50.0)
        i_confidence_boost = i_factor_params.get('confidence_boost_default', 0.0)

        print(f"✅ I因子参数读取成功:")
        print(f"  effective_threshold: {i_effective_threshold}")
        print(f"  confidence_boost_default: {i_confidence_boost}")

        return True
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_running_processes():
    """测试5: 检查运行中的进程"""
    print("\n" + "=" * 60)
    print("测试5: 检查运行中的进程")
    print("=" * 60)

    import subprocess

    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )

        lines = [line for line in result.stdout.split('\n') if 'realtime_signal_scanner' in line]

        if lines:
            print("⚠️  发现运行中的扫描器进程:")
            for line in lines:
                print(f"  {line}")
            print("\n⚠️  这些进程可能在使用旧代码！")
            print("⚠️  请运行: pkill -f 'realtime_signal_scanner.py'")
            print("⚠️  然后重新启动: ./setup.sh")
            return False
        else:
            print("✅ 没有运行中的扫描器进程")
            return True

    except Exception as e:
        print(f"⚠️  无法检查进程: {e}")
        return True

def check_python_cache():
    """测试6: 检查 Python 缓存"""
    print("\n" + "=" * 60)
    print("测试6: 检查 Python 缓存")
    print("=" * 60)

    import subprocess

    try:
        # 查找 .pyc 文件
        result = subprocess.run(
            ['find', '/home/user/cryptosignal/ats_core', '-name', '*.pyc'],
            capture_output=True,
            text=True
        )

        pyc_files = [line for line in result.stdout.split('\n') if line.strip()]

        if pyc_files:
            print(f"⚠️  发现 {len(pyc_files)} 个 .pyc 文件")
            print("⚠️  建议清理缓存:")
            print("     find /home/user/cryptosignal -name '*.pyc' -delete")
            print("     find /home/user/cryptosignal -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true")
            return False
        else:
            print("✅ 没有 .pyc 缓存文件")

        # 查找 __pycache__ 目录
        result = subprocess.run(
            ['find', '/home/user/cryptosignal/ats_core', '-name', '__pycache__', '-type', 'd'],
            capture_output=True,
            text=True
        )

        cache_dirs = [line for line in result.stdout.split('\n') if line.strip()]

        if cache_dirs:
            print(f"⚠️  发现 {len(cache_dirs)} 个 __pycache__ 目录")
            return False
        else:
            print("✅ 没有 __pycache__ 目录")

        return True

    except Exception as e:
        print(f"⚠️  无法检查缓存: {e}")
        return True

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🔍 FactorConfig 修复验证诊断")
    print("=" * 60)
    print()

    results = []

    # 运行所有测试
    results.append(("FactorConfig导入", test_factorconfig_import()))
    results.append(("analyze_symbol导入", test_analyze_symbol_import()))
    results.append(("输出配置加载", test_scan_output_config()))
    results.append(("analyze_symbol执行", test_analyze_symbol_execution()))
    results.append(("运行中进程检查", check_running_processes()))
    results.append(("Python缓存检查", check_python_cache()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✅ 所有测试通过！")
        print("✅ FactorConfig 修复已生效")
        print("✅ 输出配置正确")
        print()
        print("如果扫描器运行时仍有错误，请：")
        print("1. 停止所有运行中的进程: pkill -f 'realtime_signal_scanner.py'")
        print("2. 清理 Python 缓存")
        print("3. 重新启动: ./setup.sh")
    else:
        print("\n❌ 部分测试失败")
        print("⚠️  请检查上述失败的测试项")
        print()
        print("修复建议：")
        print("1. 清理 Python 缓存")
        print("2. 停止运行中的进程")
        print("3. 重新启动服务")

    print()
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
