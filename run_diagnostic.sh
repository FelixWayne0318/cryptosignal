#!/bin/bash
# 一键诊断脚本

cd ~/cryptosignal

echo "🔍 开始系统诊断..."
echo ""
echo "诊断内容："
echo "  1. 检查代码版本和配置"
echo "  2. 验证关键修复是否生效"
echo "  3. 运行测试扫描（10个币种）"
echo "  4. 详细分析信号产生过程"
echo "  5. 生成诊断报告"
echo ""
echo "预计耗时: 1-3分钟"
echo ""
echo "按 Enter 开始，或 Ctrl+C 取消..."
read

# 运行诊断并保存到文件
REPORT_FILE="diagnostic_report_$(date +%Y%m%d_%H%M%S).txt"

python3 diagnostic_scan.py 2>&1 | tee "$REPORT_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 诊断完成！报告已保存到: $REPORT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 快速查看报告关键部分:"
echo ""
echo "1. 查看配置检查结果:"
echo "   grep -A 10 '第一部分' $REPORT_FILE"
echo ""
echo "2. 查看统计汇总:"
echo "   grep -A 20 '第四部分' $REPORT_FILE"
echo ""
echo "3. 查看完整报告:"
echo "   cat $REPORT_FILE"
echo ""
