#!/usr/bin/env python3
"""
强制重新加载配置并验证

Purpose:
    测试CFG配置重载，确认four_step_system配置正确
"""

import sys
import os

# 确保在正确的目录
os.chdir(os.path.expanduser('~/cryptosignal'))
sys.path.insert(0, os.getcwd())

print("=" * 70)
print("🔄 强制重新加载配置")
print("=" * 70)
print()

# 1. 检查配置文件
print("📍 1. 检查配置文件内容")
print("-" * 70)

import json
config_path = os.path.expanduser('~/cryptosignal/config/params.json')
with open(config_path, 'r') as f:
    file_params = json.load(f)

fss_file = file_params.get('four_step_system', {})
print(f"  配置文件路径: {config_path}")
print(f"  ✅ four_step_system.enabled: {fss_file.get('enabled')}")
print(f"  ✅ fusion_mode.enabled: {fss_file.get('fusion_mode', {}).get('enabled')}")
print()

# 2. 导入并检查CFG（首次加载）
print("📍 2. CFG初始状态")
print("-" * 70)

from ats_core.cfg import CFG

# 首次加载
initial_params = CFG.params
fss_initial = initial_params.get('four_step_system', {})
print(f"  CFG首次加载four_step_system.enabled: {fss_initial.get('enabled')}")
print(f"  CFG首次加载fusion_mode.enabled: {fss_initial.get('fusion_mode', {}).get('enabled')}")
print()

# 3. 强制重新加载
print("📍 3. 强制重新加载配置")
print("-" * 70)

CFG.reload()
print("  ✅ 已调用CFG.reload()")

reloaded_params = CFG.params
fss_reloaded = reloaded_params.get('four_step_system', {})
print(f"  CFG重载后four_step_system.enabled: {fss_reloaded.get('enabled')}")
print(f"  CFG重载后fusion_mode.enabled: {fss_reloaded.get('fusion_mode', {}).get('enabled')}")
print()

# 4. 对比
print("📍 4. 配置对比")
print("-" * 70)

file_enabled = fss_file.get('enabled')
cfg_enabled = fss_reloaded.get('enabled')

if file_enabled == cfg_enabled == True:
    print("  ✅ 配置文件和CFG一致，四步系统已启用")
elif file_enabled != cfg_enabled:
    print(f"  ❌ 配置不一致！")
    print(f"     文件: {file_enabled}")
    print(f"     CFG:  {cfg_enabled}")
else:
    print(f"  ❌ 四步系统未启用（文件={file_enabled}, CFG={cfg_enabled}）")
print()

# 5. 检查配置文件路径
print("📍 5. CFG使用的配置文件路径")
print("-" * 70)

from ats_core.config.path_resolver import get_params_file
params_file = get_params_file()
print(f"  路径解析器返回: {params_file}")
print(f"  实际读取: {config_path}")
print(f"  路径一致: {str(params_file) == config_path}")
print()

# 6. 测试四步系统导入
print("📍 6. 测试四步系统模块导入")
print("-" * 70)

try:
    from ats_core.decision.four_step_system import run_four_step_decision
    print("  ✅ run_four_step_decision 导入成功")

    # 检查函数签名
    import inspect
    sig = inspect.signature(run_four_step_decision)
    print(f"  ✅ 函数参数: {list(sig.parameters.keys())}")
except Exception as e:
    print(f"  ❌ 导入失败: {e}")
print()

# 7. 模拟analyze_symbol的配置读取
print("📍 7. 模拟analyze_symbol配置读取")
print("-" * 70)

# 这是analyze_symbol.py中实际使用的代码
from ats_core.cfg import CFG as analyze_cfg
params_in_analyze = analyze_cfg.params

will_call = params_in_analyze.get("four_step_system", {}).get("enabled", False)
fusion_enabled = params_in_analyze.get("four_step_system", {}).get("fusion_mode", {}).get("enabled", False)

print(f"  analyze_symbol会调用四步系统: {will_call}")
print(f"  analyze_symbol会使用融合模式: {fusion_enabled}")

if will_call and fusion_enabled:
    print("  ✅ 配置正确，四步系统应该会运行")
else:
    print("  ❌ 配置有问题，四步系统不会运行")
    print()
    print("  🔍 问题定位：")
    if not will_call:
        print("     • four_step_system.enabled = False")
        print("     • 需要确认config/params.json是否正确")
    if not fusion_enabled:
        print("     • fusion_mode.enabled = False")
print()

print("=" * 70)
print("📊 诊断完成")
print("=" * 70)
print()

if will_call and fusion_enabled:
    print("✅ 配置正确！如果服务器仍显示v7.3，问题可能是：")
    print("   1. 服务器进程需要重启以重新加载配置")
    print("   2. 进程启动时CFG._params已被缓存")
    print()
    print("🔧 解决方案：")
    print("   在analyze_symbol.py开头添加强制重载：")
    print("   from ats_core.cfg import CFG")
    print("   CFG.reload()  # 强制重新加载配置")
else:
    print("❌ 配置有问题！")
    print()
    print("🔧 请检查：")
    print(f"   1. 配置文件: {config_path}")
    print("   2. 确认four_step_system.enabled: true")
    print("   3. 确认fusion_mode.enabled: true")
