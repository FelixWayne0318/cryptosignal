#!/bin/bash
# 一键诊断脚本（自动发送到Telegram）

cd ~/cryptosignal

echo "🔍 开始系统诊断（带Telegram通知）..."
echo ""
echo "诊断内容："
echo "  1. 检查代码版本和配置"
echo "  2. 验证关键修复是否生效"
echo "  3. 运行测试扫描（10个币种）"
echo "  4. 详细分析信号产生过程"
echo "  5. 生成诊断报告并发送到Telegram"
echo ""
echo "预计耗时: 1-3分钟"
echo ""
echo "按 Enter 开始，或 Ctrl+C 取消..."
read

# 使用带Telegram通知的诊断脚本
python3 diagnostic_with_telegram.py
