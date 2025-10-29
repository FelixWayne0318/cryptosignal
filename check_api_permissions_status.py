#!/usr/bin/env python3
"""
检查Binance API的实际权限状态
通过测试不同的API端点来确定权限
"""
import os
import sys
import urllib.request
import urllib.parse
import json
import time
import hmac
import hashlib

sys.path.insert(0, '/home/user/cryptosignal')

API_KEY = os.environ.get('BINANCE_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_API_SECRET', '')

def make_signed_request(endpoint, params=None):
    """发送签名请求"""
    if params is None:
        params = {}

    timestamp = int(time.time() * 1000)
    params['timestamp'] = timestamp

    query_string = urllib.parse.urlencode(sorted(params.items()))
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    params['signature'] = signature

    url = f"https://fapi.binance.com{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            'X-MBX-APIKEY': API_KEY,
            'User-Agent': 'test/1.0'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return True, json.loads(response.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_data = json.loads(error_body)
            return False, {'code': e.code, 'error': error_data}
        except:
            return False, {'code': e.code, 'error': error_body}
    except Exception as e:
        return False, {'error': str(e)}

def main():
    print("=" * 80)
    print("           Binance API 权限状态检查")
    print("=" * 80)
    print()

    if not API_KEY or not API_SECRET:
        print("❌ 环境变量未设置")
        return

    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print()

    # 测试1: 获取服务器时间（公开，无需认证）
    print("【1/5】测试: 服务器时间 (公开API)")
    print("-" * 80)
    try:
        url = "https://fapi.binance.com/fapi/v1/time"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            print(f"✅ 成功 - 服务器时间: {data.get('serverTime')}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()

    # 测试2: 账户信息 (需要READ权限)
    print("【2/5】测试: 账户信息 (需要READ权限)")
    print("-" * 80)
    success, result = make_signed_request('/fapi/v2/account')
    if success:
        print(f"✅ 成功 - READ权限正常")
        print(f"   余额: {result.get('totalWalletBalance')} USDT")
    else:
        print(f"❌ 失败 - {result}")
        if result.get('code') == 401:
            print("   ⚠️  READ权限可能未启用")
    print()

    # 测试3: 持仓信息 (需要READ + FUTURES权限)
    print("【3/5】测试: 持仓信息 (需要READ + FUTURES权限)")
    print("-" * 80)
    success, result = make_signed_request('/fapi/v2/positionRisk')
    if success:
        print(f"✅ 成功 - FUTURES权限正常")
        print(f"   持仓数量: {len(result)}")
    else:
        print(f"❌ 失败 - {result}")
        if result.get('code') == 401:
            print("   ⚠️  FUTURES权限可能未启用或未生效")
    print()

    # 测试4: 账户交易列表 (需要READ + FUTURES权限)
    print("【4/5】测试: 账户交易列表 (需要READ + FUTURES)")
    print("-" * 80)
    success, result = make_signed_request('/fapi/v1/userTrades', {'symbol': 'BTCUSDT', 'limit': 1})
    if success:
        print(f"✅ 成功 - FUTURES权限正常")
    else:
        print(f"❌ 失败 - {result}")
    print()

    # 测试5: 我的强平订单 (需要READ + FUTURES权限)
    print("【5/5】测试: 我的强平订单 (需要READ + FUTURES)")
    print("-" * 80)
    success, result = make_signed_request('/fapi/v1/allForceOrders', {'symbol': 'BTCUSDT', 'limit': 10})
    if success:
        print(f"✅ 成功 - 清算数据API权限正常")
        print(f"   返回数据: {result}")
    else:
        print(f"❌ 失败 - {result}")
        error = result.get('error', {})
        if isinstance(error, dict):
            msg = error.get('msg', '')
            if 'Invalid' in msg or 'format' in msg:
                print("\n   【分析】")
                print("   错误提示API Key格式无效，可能原因：")
                print("   1. 权限修改后未生效（需等待5-30分钟）")
                print("   2. 需要重新生成API Key")
                print("   3. 清算数据API需要特殊权限")
    print()

    # 总结
    print("=" * 80)
    print("           权限状态总结")
    print("=" * 80)
    print("\n建议：")
    print("1. 如果测试2成功但测试5失败，说明FUTURES权限可能未完全生效")
    print("2. 建议重新生成API Key，同时勾选 READ + FUTURES 权限")
    print("3. 新生成的Key会立即生效，无需等待")
    print("\n如何重新生成：")
    print("  https://www.binance.com/en/my/settings/api-management")
    print("=" * 80)

if __name__ == '__main__':
    main()
