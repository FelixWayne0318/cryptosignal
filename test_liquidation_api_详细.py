#!/usr/bin/env python3
"""测试不同的清算数据API端点"""
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

def test_public_liquidations():
    """测试公开清算数据API（不需要签名）"""
    print("【测试A】公开API: /fapi/v1/forceOrders (不需要签名)")
    print("-" * 80)
    
    try:
        url = "https://fapi.binance.com/fapi/v1/forceOrders?symbol=BTCUSDT&limit=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'test/1.0'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            print(f"✅ 成功获取 {len(data)} 条清算数据（公开API）")
            if data:
                print(f"   示例: {data[0]}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ 失败: HTTP {e.code}")
        try:
            error_data = json.loads(error_body)
            print(f"   Binance返回: {error_data}")
        except:
            print(f"   响应: {error_body}")
        return False
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_signed_liquidations():
    """测试签名清算数据API（需要签名）"""
    print("\n【测试B】签名API: /fapi/v1/allForceOrders (需要签名)")
    print("-" * 80)
    
    if not API_KEY or not API_SECRET:
        print("❌ 环境变量未设置")
        return False
    
    try:
        # 构建签名请求
        timestamp = int(time.time() * 1000)
        params = {
            'symbol': 'BTCUSDT',
            'limit': 10,
            'timestamp': timestamp
        }
        
        query_string = urllib.parse.urlencode(sorted(params.items()))
        signature = hmac.new(
            API_SECRET.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params['signature'] = signature
        
        url = f"https://fapi.binance.com/fapi/v1/allForceOrders?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                'X-MBX-APIKEY': API_KEY,
                'User-Agent': 'test/1.0'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            print(f"✅ 成功获取清算数据（签名API）")
            print(f"   数据: {data}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ 失败: HTTP {e.code}")
        try:
            error_data = json.loads(error_body)
            print(f"   Binance返回: {error_data}")
        except:
            print(f"   响应: {error_body}")
        return False
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("           清算数据API详细测试")
    print("=" * 80)
    print()
    
    # 测试公开API
    result_a = test_public_liquidations()
    
    # 测试签名API  
    result_b = test_signed_liquidations()
    
    # 总结
    print("\n" + "=" * 80)
    print("           测试总结")
    print("=" * 80)
    
    if result_a:
        print("\n✅ 好消息！公开API可以访问清算数据")
        print("   这意味着Q因子可以工作，无需特殊API权限")
        print("\n💡 解决方案：")
        print("   1. 我们的代码会优先使用公开API")
        print("   2. 不需要修改Binance API设置")
        print("   3. Q因子应该可以正常工作了")
    elif result_b:
        print("\n✅ 签名API可以访问清算数据")
        print("   但这只能看到您自己账户的清算订单")
        print("\n⚠️  问题：")
        print("   签名API返回的是个人清算历史，不是市场清算数据")
        print("   Q因子需要市场清算数据，需要公开API")
    else:
        print("\n❌ 两个API都无法访问")
        print("\n可能原因：")
        print("   1. Binance改变了API策略")
        print("   2. 地区限制")
        print("   3. 临时限流")

if __name__ == '__main__':
    main()
