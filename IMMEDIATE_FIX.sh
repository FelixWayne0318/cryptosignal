#!/bin/bash
# ============================================== #
# 立即修复脚本 - 停止旧服务并重启
# ============================================== #

echo "=============================================="
echo "🔧 立即修复 - FactorConfig 错误"
echo "=============================================="
echo ""

# 显示当前状态
echo "1️⃣ 检查运行中的进程..."
ps aux | grep -E "realtime_signal_scanner|python.*scanner" | grep -v grep

echo ""
echo "2️⃣ 强制停止所有 Python 扫描器进程..."
pkill -9 -f "realtime_signal_scanner"
pkill -9 -f "python.*scanner"
sleep 3

echo ""
echo "3️⃣ 验证进程已停止..."
REMAINING=$(ps aux | grep -E "realtime_signal_scanner|python.*scanner" | grep -v grep | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ 所有进程已停止"
else
    echo "❌ 仍有进程运行！"
    ps aux | grep -E "realtime_signal_scanner|python.*scanner" | grep -v grep
    exit 1
fi

echo ""
echo "4️⃣ 清理 Python 缓存..."
cd /home/user/cryptosignal
find . -name "*.pyc" -delete 2>/dev/null
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
echo "✅ 缓存已清理"

echo ""
echo "5️⃣ 验证代码修复..."
if grep -q "factor_config\.config\.get('I因子参数'" ats_core/pipeline/analyze_symbol.py; then
    echo "✅ 代码修复已存在"
else
    echo "❌ 代码修复未找到！"
    echo "正在应用修复..."
    
    # 检查是否需要修复
    if grep -q "factor_config\.get('I因子参数'" ats_core/pipeline/analyze_symbol.py; then
        echo "发现错误用法，正在修复..."
        sed -i "s/factor_config\.get('I因子参数'/factor_config.config.get('I因子参数'/g" ats_core/pipeline/analyze_symbol.py
        echo "✅ 修复已应用"
    fi
fi

echo ""
echo "6️⃣ 重新启动服务..."
./setup.sh

