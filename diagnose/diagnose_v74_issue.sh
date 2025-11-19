#!/bin/bash

# v7.4问题全面诊断脚本
# 用于定位为什么服务器还是运行v7.3.2而非v7.4

echo "========================================="
echo "🔍 CryptoSignal v7.4 问题诊断脚本"
echo "========================================="
echo ""

# 1. 检查Git代码版本
echo "📦 1. Git代码状态检查"
echo "-----------------------------------"
echo "当前分支:"
git branch --show-current
echo ""
echo "最新commit:"
git log -1 --oneline
echo ""
echo "是否有未提交的变更:"
git status --short
echo ""

# 2. 检查config/params.json文件内容
echo "📝 2. 配置文件检查 (config/params.json)"
echo "-----------------------------------"
if [ -f "config/params.json" ]; then
    echo "✅ config/params.json 存在"
    echo ""
    echo "four_step_system配置:"
    grep -A 20 '"four_step_system"' config/params.json | head -25
    echo ""
else
    echo "❌ config/params.json 不存在!"
fi

# 3. 检查analyze_symbol.py是否有CFG.reload()
echo "🔧 3. analyze_symbol.py 代码检查"
echo "-----------------------------------"
if grep -n "CFG.reload()" ats_core/pipeline/analyze_symbol.py; then
    echo "✅ 找到 CFG.reload() 调用"
else
    echo "❌ 未找到 CFG.reload() 调用"
fi
echo ""

if grep -n '🔍 \[v7.4诊断\]' ats_core/pipeline/analyze_symbol.py; then
    echo "✅ 找到 v7.4诊断日志"
else
    echo "❌ 未找到 v7.4诊断日志"
fi
echo ""

# 4. 检查运行进程
echo "🏃 4. 运行进程检查"
echo "-----------------------------------"
if pgrep -f "realtime_signal_scanner" > /dev/null; then
    echo "✅ 找到运行中的进程:"
    ps aux | grep -v grep | grep realtime_signal_scanner
    echo ""
    echo "进程启动时间:"
    ps -p $(pgrep -f "realtime_signal_scanner" | head -1) -o lstart=
else
    echo "❌ 未找到运行中的进程"
fi
echo ""

# 5. 检查Python缓存
echo "🗑️  5. Python缓存检查"
echo "-----------------------------------"
echo "__pycache__ 目录数量:"
find . -type d -name "__pycache__" | wc -l
echo ""
echo "analyze_symbol相关缓存:"
find . -path "*/pipeline/__pycache__/analyze_symbol*.pyc" -o -path "*/pipeline/__pycache__/analyze_symbol*.pyo"
echo ""

# 6. 运行时Python诊断（关键）
echo "🐍 6. 运行时Python配置检查 (关键诊断)"
echo "-----------------------------------"
CURRENT_DIR=$(pwd)
python3 << PYTHON_EOF
import sys
import os
import json

# 添加项目路径（使用当前目录）
CURRENT_DIR = "$CURRENT_DIR"
sys.path.insert(0, CURRENT_DIR)
os.chdir(CURRENT_DIR)

print("Python路径:", sys.executable)
print("工作目录:", os.getcwd())
print("")

# 检查config/params.json文件内容
print("📄 读取 config/params.json 文件:")
try:
    with open('config/params.json', 'r') as f:
        file_config = json.load(f)
    four_step_config = file_config.get('four_step_system', {})
    print(f"  ✅ 文件中 four_step_system.enabled = {four_step_config.get('enabled')}")
    print(f"  ✅ 文件中 fusion_mode.enabled = {four_step_config.get('fusion_mode', {}).get('enabled')}")
except Exception as e:
    print(f"  ❌ 读取失败: {e}")
print("")

# 检查CFG加载的配置
print("🔍 检查 CFG 加载的配置:")
try:
    from ats_core.cfg import CFG

    # 强制重载
    print("  执行 CFG.reload()...")
    CFG.reload()

    runtime_config = CFG.params
    four_step_runtime = runtime_config.get('four_step_system', {})

    print(f"  CFG.params中 four_step_system.enabled = {four_step_runtime.get('enabled')}")
    print(f"  CFG.params中 fusion_mode.enabled = {four_step_runtime.get('fusion_mode', {}).get('enabled')}")

    # 比较文件和CFG
    file_enabled = four_step_config.get('enabled')
    cfg_enabled = four_step_runtime.get('enabled')

    if file_enabled == cfg_enabled:
        print(f"  ✅ 配置一致: 文件={file_enabled}, CFG={cfg_enabled}")
    else:
        print(f"  ❌ 配置不一致! 文件={file_enabled}, CFG={cfg_enabled}")
        print("  ⚠️  这是问题根源!")

    # 检查CFG加载的配置文件路径
    print("")
    print(f"  CFG配置文件路径: {CFG._params_file}")

except Exception as e:
    print(f"  ❌ CFG检查失败: {e}")
    import traceback
    traceback.print_exc()

print("")

# 检查analyze_symbol.py模块
print("📦 检查 analyze_symbol.py 模块:")
try:
    import ats_core.pipeline.analyze_symbol as analyze_module
    print(f"  模块路径: {analyze_module.__file__}")

    # 读取源代码检查
    with open(analyze_module.__file__, 'r') as f:
        source_code = f.read()

    has_reload = 'CFG.reload()' in source_code
    has_diagnostic = '🔍 [v7.4诊断]' in source_code
    has_four_step = 'run_four_step_decision' in source_code

    print(f"  ✅ 包含 CFG.reload(): {has_reload}")
    print(f"  ✅ 包含 v7.4诊断日志: {has_diagnostic}")
    print(f"  ✅ 包含 run_four_step_decision: {has_four_step}")

    if not has_reload:
        print("  ❌ 警告: 代码中没有 CFG.reload()!")
    if not has_diagnostic:
        print("  ❌ 警告: 代码中没有 v7.4诊断日志!")

except Exception as e:
    print(f"  ❌ 模块检查失败: {e}")
    import traceback
    traceback.print_exc()

print("")

# 检查path_resolver
print("🗂️  检查 config path_resolver:")
try:
    from ats_core.config.path_resolver import get_config_root, get_params_file

    config_root = get_config_root()
    params_file = get_params_file()

    print(f"  配置根目录: {config_root}")
    print(f"  参数文件路径: {params_file}")
    print(f"  参数文件存在: {params_file.exists()}")

    # 检查环境变量
    import os
    env_config = os.environ.get('CRYPTOSIGNAL_CONFIG_ROOT')
    env_params = os.environ.get('ATS_PARAMS_FILE')
    print(f"  环境变量 CRYPTOSIGNAL_CONFIG_ROOT: {env_config}")
    print(f"  环境变量 ATS_PARAMS_FILE: {env_params}")

except Exception as e:
    print(f"  ❌ path_resolver检查失败: {e}")

PYTHON_EOF

echo ""

# 7. 检查最近的日志
echo "📋 7. 最近的服务器日志检查"
echo "-----------------------------------"
LOG_FILE=$(ls -t /tmp/cryptosignal_*.log 2>/dev/null | head -1)
if [ -n "$LOG_FILE" ]; then
    echo "日志文件: $LOG_FILE"
    echo ""
    echo "查找v7.4相关日志:"
    grep -E "(v7\.(3|4)|四步系统|four_step|Step[1-4]|🔍.*v7.4诊断)" "$LOG_FILE" | tail -20
    echo ""
    echo "查找闸门相关日志:"
    grep -E "(闸门|Gate)" "$LOG_FILE" | tail -10
else
    echo "❌ 未找到日志文件 (/tmp/cryptosignal_*.log)"
fi
echo ""

# 8. 总结
echo "========================================="
echo "📊 诊断总结"
echo "========================================="
echo ""
echo "请将以上完整输出发送给我分析。"
echo ""
echo "关键检查点:"
echo "1. config/params.json 文件中 four_step_system.enabled 值"
echo "2. CFG.params 运行时加载的 four_step_system.enabled 值"
echo "3. 两者是否一致"
echo "4. analyze_symbol.py 是否包含 CFG.reload()"
echo "5. 日志中是否出现 '🔍 [v7.4诊断]' 输出"
echo ""
