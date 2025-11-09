#!/bin/bash
# 验证问题3修复是否正确应用

echo "============================================================"
echo "验证问题3修复（p_min统一到FIModulator）"
echo "============================================================"

echo ""
echo "1️⃣ 检查 analyze_symbol.py 是否使用 FIModulator:"
echo "------------------------------------------------------------"
if grep -q "fi_modulator = get_fi_modulator()" ats_core/pipeline/analyze_symbol.py; then
    echo "✅ 找到 FIModulator 调用"
    grep -A 3 "fi_modulator = get_fi_modulator()" ats_core/pipeline/analyze_symbol.py | head -4
else
    echo "❌ 没有找到 FIModulator 调用"
fi

echo ""
echo "2️⃣ 检查 fi_thresholds 是否添加到结果字典:"
echo "------------------------------------------------------------"
if grep -q '"fi_thresholds":' ats_core/pipeline/analyze_symbol.py; then
    echo "✅ 找到 fi_thresholds 定义"
    grep -A 5 '"fi_thresholds":' ats_core/pipeline/analyze_symbol.py | head -6
else
    echo "❌ 没有找到 fi_thresholds"
fi

echo ""
echo "3️⃣ 检查 telegram_fmt.py 是否读取 fi_thresholds:"
echo "------------------------------------------------------------"
if grep -q "fi_thresholds = _get(r, \"fi_thresholds\")" ats_core/outputs/telegram_fmt.py; then
    echo "✅ 找到 fi_thresholds 读取"
    grep "fi_thresholds = _get" ats_core/outputs/telegram_fmt.py
else
    echo "❌ 没有找到 fi_thresholds 读取"
fi

echo ""
echo "4️⃣ 检查是否显示 F 和 I 的 p_min 调整:"
echo "------------------------------------------------------------"
if grep -q 'p_min调整(F)' ats_core/outputs/telegram_fmt.py; then
    echo "✅ 找到 F 的 p_min 调整显示"
    grep 'p_min调整(F)' ats_core/outputs/telegram_fmt.py
else
    echo "❌ 没有找到 F 的 p_min 调整"
fi

if grep -q 'p_min调整(I)' ats_core/outputs/telegram_fmt.py; then
    echo "✅ 找到 I 的 p_min 调整显示"
    grep 'p_min调整(I)' ats_core/outputs/telegram_fmt.py
else
    echo "❌ 没有找到 I 的 p_min 调整"
fi

echo ""
echo "5️⃣ 检查是否显示完整的概率阈值公式:"
echo "------------------------------------------------------------"
if grep -q '概率阈值:' ats_core/outputs/telegram_fmt.py; then
    echo "✅ 找到概率阈值公式显示"
    grep '概率阈值:' ats_core/outputs/telegram_fmt.py
else
    echo "❌ 没有找到概率阈值公式"
fi

echo ""
echo "6️⃣ 检查 ModulatorChain 是否标记为已弃用:"
echo "------------------------------------------------------------"
if grep -q "DEPRECATED" ats_core/modulators/modulator_chain.py; then
    echo "✅ 找到 DEPRECATED 标记"
    grep -B 1 -A 1 "DEPRECATED" ats_core/modulators/modulator_chain.py | head -5
else
    echo "⚠️ 没有找到 DEPRECATED 标记"
fi

echo ""
echo "============================================================"
echo "✅ 验证完成！"
echo "============================================================"
echo ""
echo "📝 结论:"
echo "   如果以上所有检查都显示 ✅，说明代码已正确修复。"
echo "   批量扫描日志使用简化格式（性能优化），不会显示详细信息。"
echo "   当系统发现真实信号并发送到 Telegram 时，会使用详细格式。"
echo ""
echo "🔍 如何查看详细输出:"
echo "   1. 等待真实信号（会自动使用详细格式）"
echo "   2. 查看 Telegram 机器人发送的消息"
echo "   3. 或运行: python3 tests/test_problem3_fix.py"
echo ""
