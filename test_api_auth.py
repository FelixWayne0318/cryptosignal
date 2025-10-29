#!/usr/bin/env python3
# coding: utf-8
"""
测试Binance API认证配置

用于验证BINANCE_API_KEY和BINANCE_API_SECRET是否正确配置
"""
import os
import sys

# 确保可以导入ats_core模块
sys.path.insert(0, '/home/user/cryptosignal')

def test_api_config():
    """测试API配置"""
    print("\n" + "=" * 80)
    print("Binance API认证配置测试")
    print("=" * 80)

    # 检查环境变量
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")

    print("\n1️⃣  检查环境变量...")
    if api_key:
        print(f"   ✅ BINANCE_API_KEY: {api_key[:8]}...{api_key[-4:]} (长度: {len(api_key)})")
    else:
        print("   ❌ BINANCE_API_KEY: 未设置")

    if api_secret:
        print(f"   ✅ BINANCE_API_SECRET: ****...{api_secret[-4:]} (长度: {len(api_secret)})")
    else:
        print("   ❌ BINANCE_API_SECRET: 未设置")

    if not api_key or not api_secret:
        print("\n" + "=" * 80)
        print("❌ API认证未配置")
        print("=" * 80)
        print("\n请按照以下步骤配置：")
        print("\n1. 获取Binance API Key（只需读取权限）")
        print("   访问：https://www.binance.com/en/my/settings/api-management")
        print("\n2. 设置环境变量：")
        print("   export BINANCE_API_KEY=\"your_api_key_here\"")
        print("   export BINANCE_API_SECRET=\"your_api_secret_here\"")
        print("\n3. 重新运行此脚本验证")
        print("\n详细配置指南请查看：ENABLE_Q_FACTOR.md")
        print("=" * 80)
        return False

    # 测试API访问
    print("\n2️⃣  测试API访问...")
    try:
        from ats_core.sources.binance import get_liquidations

        print("   获取BTCUSDT清算数据...")
        liquidations = get_liquidations('BTCUSDT', limit=10)

        print(f"   ✅ 成功获取 {len(liquidations)} 条清算数据")

        if liquidations:
            sample = liquidations[0]
            print(f"\n   示例数据：")
            print(f"   - Symbol: {sample.get('symbol')}")
            print(f"   - Side: {sample.get('side')}")
            print(f"   - Price: {sample.get('price')}")
            print(f"   - Quantity: {sample.get('origQty')}")

        print("\n" + "=" * 80)
        print("✅ API认证配置成功！Q因子已启用")
        print("=" * 80)
        print("\n现在可以运行完整测试：")
        print("PYTHONPATH=/home/user/cryptosignal python3 test_10d_analysis.py")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"   ❌ 失败: {e}")
        print("\n" + "=" * 80)
        print("❌ API访问失败")
        print("=" * 80)
        print("\n可能的原因：")
        print("1. API Key或Secret错误")
        print("2. API权限不足（需要启用读取权限）")
        print("3. IP不在白名单中（如果启用了IP限制）")
        print("4. 服务器时间不同步")
        print("\n故障排查：")
        print("- 检查API Key是否正确复制（无多余空格）")
        print("- 确认在Binance设置中启用了读取权限")
        print("- 如果启用了IP白名单，添加当前服务器IP")
        print("- 同步服务器时间：sudo ntpdate pool.ntp.org")
        print("\n详细配置指南请查看：ENABLE_Q_FACTOR.md")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = test_api_config()
    sys.exit(0 if success else 1)
