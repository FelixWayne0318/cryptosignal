#!/usr/bin/env python3
"""
运行时代码诊断脚本 - 检查实际执行的代码路径

Purpose:
    在服务器上运行，检查为什么四步系统没有真正执行
"""

import sys
import os
import json

print("=" * 70)
print("🔍 运行时代码诊断")
print("=" * 70)
print()

# 1. 检查当前工作目录
print("📍 1. 工作目录检查")
print("-" * 70)
cwd = os.getcwd()
print(f"  当前目录: {cwd}")
print()

# 2. 检查Python路径
print("📍 2. Python模块搜索路径")
print("-" * 70)
for i, path in enumerate(sys.path[:5], 1):
    print(f"  {i}. {path}")
print(f"  ... (共{len(sys.path)}个路径)")
print()

# 3. 检查analyze_symbol模块的实际位置
print("📍 3. analyze_symbol模块位置")
print("-" * 70)
try:
    import ats_core.pipeline.analyze_symbol as analyze_module
    module_file = analyze_module.__file__
    print(f"  ✅ 模块文件: {module_file}")

    # 检查文件修改时间
    import datetime
    mtime = os.path.getmtime(module_file)
    mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    print(f"  📅 修改时间: {mtime_str}")

    # 检查文件中是否包含四步系统代码
    with open(module_file, 'r') as f:
        content = f.read()
        has_four_step = 'run_four_step_decision' in content
        has_fusion = 'fusion_mode' in content
        has_v74_comment = 'v7.4' in content

    print(f"  ✅ 包含run_four_step_decision: {has_four_step}")
    print(f"  ✅ 包含fusion_mode: {has_fusion}")
    print(f"  ✅ 包含v7.4注释: {has_v74_comment}")

except Exception as e:
    print(f"  ❌ 无法导入: {e}")
print()

# 4. 检查four_step_system模块
print("📍 4. four_step_system模块检查")
print("-" * 70)
try:
    import ats_core.decision.four_step_system as fss_module
    fss_file = fss_module.__file__
    print(f"  ✅ 模块文件: {fss_file}")

    # 检查run_four_step_decision函数
    has_func = hasattr(fss_module, 'run_four_step_decision')
    print(f"  ✅ run_four_step_decision函数存在: {has_func}")

except Exception as e:
    print(f"  ❌ 无法导入four_step_system: {e}")
print()

# 5. 检查配置文件
print("📍 5. 配置文件检查")
print("-" * 70)
try:
    # 尝试从当前目录加载
    config_path = os.path.join(cwd, 'config', 'params.json')
    if not os.path.exists(config_path):
        config_path = os.path.expanduser('~/cryptosignal/config/params.json')

    print(f"  配置文件路径: {config_path}")

    with open(config_path, 'r') as f:
        params = json.load(f)

    fss_config = params.get('four_step_system', {})
    enabled = fss_config.get('enabled', False)
    fusion_enabled = fss_config.get('fusion_mode', {}).get('enabled', False)

    print(f"  ✅ four_step_system.enabled: {enabled}")
    print(f"  ✅ fusion_mode.enabled: {fusion_enabled}")

    if not enabled:
        print(f"  ❌ 四步系统未启用！")
    if not fusion_enabled:
        print(f"  ⚠️  融合模式未启用")

except Exception as e:
    print(f"  ❌ 配置加载失败: {e}")
print()

# 6. 检查CFG对象（运行时配置）
print("📍 6. CFG运行时配置检查")
print("-" * 70)
try:
    from ats_core.cfg import CFG
    runtime_params = CFG.params

    fss_runtime = runtime_params.get('four_step_system', {})
    enabled_runtime = fss_runtime.get('enabled', False)
    fusion_runtime = fss_runtime.get('fusion_mode', {}).get('enabled', False)

    print(f"  ✅ CFG.params中four_step_system.enabled: {enabled_runtime}")
    print(f"  ✅ CFG.params中fusion_mode.enabled: {fusion_runtime}")

    if not enabled_runtime:
        print(f"  ❌ 运行时配置显示四步系统未启用！")
        print(f"  🔍 这可能是问题根源：CFG加载了错误的配置")

except Exception as e:
    print(f"  ❌ CFG检查失败: {e}")
print()

# 7. 模拟执行analyze_symbol检查调用流程
print("📍 7. 模拟analyze_symbol调用流程")
print("-" * 70)
try:
    from ats_core.cfg import CFG
    params = CFG.params

    # 检查四步系统是否会被调用
    will_call_four_step = params.get("four_step_system", {}).get("enabled", False)
    print(f"  四步系统会被调用: {will_call_four_step}")

    if will_call_four_step:
        print(f"  ✅ 代码逻辑会调用四步系统")

        # 检查融合模式
        fusion_config = params.get("four_step_system", {}).get("fusion_mode", {})
        fusion_enabled = fusion_config.get("enabled", False)

        if fusion_enabled:
            print(f"  ✅ 融合模式已启用，四步系统会替代旧决策")
        else:
            print(f"  ⚠️  融合模式未启用，只是Dual Run模式")
    else:
        print(f"  ❌ 代码逻辑不会调用四步系统")
        print(f"  ❌ 这就是为什么日志显示v7.3！")

except Exception as e:
    print(f"  ❌ 模拟失败: {e}")
print()

# 8. 检查batch_scan_optimized
print("📍 8. batch_scan_optimized模块检查")
print("-" * 70)
try:
    import ats_core.pipeline.batch_scan_optimized as batch_module
    batch_file = batch_module.__file__
    print(f"  ✅ 模块文件: {batch_file}")

    # 检查是否调用analyze_symbol_with_preloaded_klines
    with open(batch_file, 'r') as f:
        content = f.read()
        has_preloaded = 'analyze_symbol_with_preloaded_klines' in content

    print(f"  ✅ 使用analyze_symbol_with_preloaded_klines: {has_preloaded}")

except Exception as e:
    print(f"  ❌ 检查失败: {e}")
print()

print("=" * 70)
print("📊 诊断总结")
print("=" * 70)
print()
print("如果CFG.params显示四步系统未启用，问题可能是：")
print("  1. CFG在初始化时加载了旧的/错误的配置文件")
print("  2. 配置文件没有被正确重载")
print("  3. 存在多个config/params.json文件")
print()
print("建议下一步：")
print("  1. 检查CFG模块的配置加载逻辑")
print("  2. 确认config/params.json文件路径")
print("  3. 添加显式日志到analyze_symbol.py开头")
print()
