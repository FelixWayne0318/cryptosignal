#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binance API权限全面测试
测试API Key能访问哪些数据和权限
"""
import os
import sys
sys.path.insert(0, '/home/user/cryptosignal')

def test_api_permissions():
    """测试API所有权限"""

    # 检查环境变量
    api_key = os.environ.get('BINANCE_API_KEY', '')
    api_secret = os.environ.get('BINANCE_API_SECRET', '')

    if not api_key or not api_secret:
        print("❌ 环境变量未设置！")
        print("请先运行: source ~/.bashrc")
        return

    print("=" * 80)
    print("           Binance API 权限测试")
    print("=" * 80)
    print(f"\nAPI Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Secret:  {'*' * 10}...{api_secret[-4:]}")
    print()

    # ========================================
    # 测试1: 公开API（不需要认证）
    # ========================================
    print("【测试1】公开API - 合约K线数据（无需认证）")
    print("-" * 80)
    try:
        from ats_core.sources.binance import get_klines
        klines = get_klines('BTCUSDT', '1h', 5)
        print(f"✅ 成功获取 {len(klines)} 根K线数据")
        if klines:
            latest = klines[-1]
            print(f"   最新K线: 开盘={latest[1]}, 收盘={latest[4]}, 成交量={latest[5]}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()

    # ========================================
    # 测试2: 公开API - 订单簿
    # ========================================
    print("【测试2】公开API - 订单簿深度（无需认证）")
    print("-" * 80)
    try:
        from ats_core.sources.binance import get_orderbook_snapshot
        orderbook = get_orderbook_snapshot('BTCUSDT', limit=5)
        print(f"✅ 成功获取订单簿")
        print(f"   买单数量: {len(orderbook.get('bids', []))}")
        print(f"   卖单数量: {len(orderbook.get('asks', []))}")
        if orderbook.get('bids'):
            print(f"   最高买价: {orderbook['bids'][0][0]}")
        if orderbook.get('asks'):
            print(f"   最低卖价: {orderbook['asks'][0][0]}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()

    # ========================================
    # 测试3: 公开API - 标记价格
    # ========================================
    print("【测试3】公开API - 标记价格（无需认证）")
    print("-" * 80)
    try:
        from ats_core.sources.binance import get_mark_price
        mark = get_mark_price('BTCUSDT')
        print(f"✅ 成功获取标记价格")
        print(f"   标记价格: {mark}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()

    # ========================================
    # 测试4: 签名API - 账户信息（READ权限）
    # ========================================
    print("【测试4】签名API - 账户信息（需要READ权限）")
    print("-" * 80)
    try:
        import urllib.request
        import urllib.parse
        import json
        import time
        import hmac
        import hashlib

        # 构建请求
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        query_string = urllib.parse.urlencode(sorted(params.items()))
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params['signature'] = signature

        url = f"https://fapi.binance.com/fapi/v2/account?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                'X-MBX-APIKEY': api_key,
                'User-Agent': 'test/1.0'
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            print(f"✅ 成功访问账户信息")
            print(f"   总余额: {data.get('totalWalletBalance', 'N/A')} USDT")
            print(f"   可用余额: {data.get('availableBalance', 'N/A')} USDT")
            print(f"   持仓数量: {len(data.get('positions', []))}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if hasattr(e, 'read') else ''
        print(f"❌ 失败: HTTP {e.code}")
        if e.code == 401:
            print("   原因: API Key/Secret错误，或权限不足")
        elif e.code == 403:
            print("   原因: IP不在白名单，或API被禁用")
        if error_body:
            try:
                error_data = json.loads(error_body)
                print(f"   详情: {error_data.get('msg', error_body)}")
            except:
                print(f"   详情: {error_body[:200]}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()

    # ========================================
    # 测试5: 签名API - 清算数据（需要READ + FUTURES权限）
    # ========================================
    print("【测试5】签名API - 清算数据（需要READ + FUTURES权限）⭐")
    print("-" * 80)
    try:
        from ats_core.sources.binance import get_liquidations
        liquidations = get_liquidations('BTCUSDT', limit=10)
        print(f"✅ 成功获取 {len(liquidations)} 条清算数据")
        if liquidations:
            liq = liquidations[0]
            print(f"   示例清算:")
            print(f"     交易对: {liq.get('symbol')}")
            print(f"     方向: {liq.get('side')}")
            print(f"     价格: {liq.get('price')}")
            print(f"     数量: {liq.get('origQty')}")
            print(f"     时间: {liq.get('time')}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if hasattr(e, 'read') else ''
        print(f"❌ 失败: HTTP {e.code}")
        if e.code == 401:
            print("\n   【401错误分析】")
            print("   可能原因:")
            print("   1. ❌ 未启用 'Enable Reading' 权限")
            print("   2. ❌ 未启用 'Enable Futures' 权限（清算数据属于合约）")
            print("   3. ❌ API Key/Secret错误")
            print("   4. ❌ 服务器时间不同步")
        elif e.code == 403:
            print("\n   【403错误分析】")
            print("   可能原因:")
            print("   1. ❌ IP不在白名单中")
            print("   2. ❌ API被临时封禁")
        if error_body:
            try:
                error_data = json.loads(error_body)
                print(f"\n   Binance返回: {error_data.get('msg', error_body)}")
            except:
                print(f"\n   响应: {error_body[:200]}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        print("\n详细错误:")
        traceback.print_exc()
    print()

    # ========================================
    # 测试6: 现货API - 现货K线
    # ========================================
    print("【测试6】现货API - 现货K线（无需认证）")
    print("-" * 80)
    try:
        from ats_core.sources.binance import get_spot_klines
        spot_klines = get_spot_klines('BTCUSDT', '1h', 5)
        print(f"✅ 成功获取 {len(spot_klines)} 根现货K线")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()

    # ========================================
    # 总结
    # ========================================
    print("=" * 80)
    print("           测试总结")
    print("=" * 80)
    print("\n如果【测试5】失败且返回401错误，请检查:")
    print("  1. 登录 https://www.binance.com/en/my/settings/api-management")
    print("  2. 找到您的API Key")
    print("  3. 确认已勾选:")
    print("     ✅ Enable Reading")
    print("     ✅ Enable Futures")
    print("  4. 确认IP白名单包含: 139.180.157.152")
    print("\n如果【测试5】成功，说明Q因子可以正常工作！")
    print("=" * 80)

if __name__ == '__main__':
    test_api_permissions()
