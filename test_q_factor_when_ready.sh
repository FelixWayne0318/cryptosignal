#!/bin/bash
#
# Q因子测试脚本 - 在Binance API可访问时运行
#
# 当前状态：API密钥已配置，等待网络访问恢复
#

echo "════════════════════════════════════════════════════════════════"
echo "           Q因子测试 - Binance API配置验证"
echo "════════════════════════════════════════════════════════════════"
echo ""

# 加载环境变量
source ~/.bashrc

# 检查环境变量
echo "1️⃣  检查API配置..."
if [ -n "$BINANCE_API_KEY" ] && [ -n "$BINANCE_API_SECRET" ]; then
    echo "   ✅ API Key: ${BINANCE_API_KEY:0:8}...${BINANCE_API_KEY: -4}"
    echo "   ✅ Secret: ****...${BINANCE_API_SECRET: -4}"
else
    echo "   ❌ 环境变量未加载"
    echo "   请运行: source ~/.bashrc"
    exit 1
fi

echo ""
echo "2️⃣  测试Binance API连接..."
python3 -c "
import sys
sys.path.insert(0, '/home/user/cryptosignal')
from ats_core.sources.binance import get_klines

try:
    klines = get_klines('BTCUSDT', '1h', 2)
    print('   ✅ Binance API可访问')
except Exception as e:
    if '403' in str(e):
        print('   ❌ HTTP 403: API访问被阻止（可能是临时限流）')
        print('   💡 建议：稍后重试或联系服务器管理员检查网络设置')
    else:
        print(f'   ❌ API错误: {e}')
    import sys
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "⚠️  Binance API当前不可访问"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "可能原因："
    echo "  • 临时限流（等待一段时间后重试）"
    echo "  • 网络防火墙限制"
    echo "  • Binance维护中"
    echo ""
    echo "解决方法："
    echo "  1. 等待10-30分钟后重新运行此脚本"
    echo "  2. 检查服务器网络设置"
    echo "  3. 确认IP白名单配置：139.180.157.152"
    echo ""
    exit 1
fi

echo ""
echo "3️⃣  测试API认证..."
python3 test_api_auth.py

if [ $? -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "✅ API配置成功！Q因子已启用"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "下一步："
    echo "  • 运行完整测试: python3 test_10d_analysis.py"
    echo "  • 验证系统: python3 verify_10d_system.py"
    echo "  • 启动生产系统: python3 run_scanner.py"
    echo ""
else
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "⚠️  API认证失败"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "请检查："
    echo "  • API Key是否正确"
    echo "  • 是否启用了读取权限"
    echo "  • IP白名单是否包含：139.180.157.152"
    echo "  • 服务器时间是否同步"
    echo ""
fi
