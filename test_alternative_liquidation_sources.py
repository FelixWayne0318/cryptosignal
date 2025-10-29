#!/usr/bin/env python3
"""
测试清算数据的替代来源
由于 /fapi/v1/forceOrders 已停止维护，寻找其他数据源
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

def test_endpoint(name, url, need_sign=False):
    """测试一个API端点"""
    print(f"\n【测试】{name}")
    print("-" * 80)

    try:
        if need_sign and API_KEY and API_SECRET:
            # 添加签名
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}
            query_string = urllib.parse.urlencode(sorted(params.items()))
            signature = hmac.new(
                API_SECRET.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            if '?' in url:
                full_url = f"{url}&timestamp={timestamp}&signature={signature}"
            else:
                full_url = f"{url}?timestamp={timestamp}&signature={signature}"

            req = urllib.request.Request(
                full_url,
                headers={
                    'X-MBX-APIKEY': API_KEY,
                    'User-Agent': 'test/1.0'
                }
            )
        else:
            req = urllib.request.Request(url, headers={'User-Agent': 'test/1.0'})

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            print(f"✅ 成功！")
            print(f"   返回数据类型: {type(data)}")
            if isinstance(data, list):
                print(f"   数据数量: {len(data)}")
                if data:
                    print(f"   示例: {data[0]}")
            elif isinstance(data, dict):
                print(f"   数据字段: {list(data.keys())}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ 失败: HTTP {e.code}")
        try:
            error_data = json.loads(error_body)
            print(f"   Binance返回: {error_data}")
        except:
            print(f"   响应: {error_body[:200]}")
        return False
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def main():
    print("=" * 80)
    print("           寻找清算数据的替代来源")
    print("=" * 80)
    print()

    # 测试各种可能的API端点

    # 1. 尝试新版本的清算数据API
    test_endpoint(
        "清算数据 v2",
        "https://fapi.binance.com/fapi/v2/forceOrders?symbol=BTCUSDT&limit=10",
        need_sign=False
    )

    # 2. 尝试通过WebSocket历史数据
    test_endpoint(
        "Liquidation Snapshot",
        "https://fapi.binance.com/fapi/v1/allForceOrders?symbol=BTCUSDT",
        need_sign=True
    )

    # 3. 尝试通过aggTrades（成交数据）推断
    test_endpoint(
        "聚合成交数据 (可能包含清算)",
        "https://fapi.binance.com/fapi/v1/aggTrades?symbol=BTCUSDT&limit=10",
        need_sign=False
    )

    # 4. 尝试最近成交
    test_endpoint(
        "最近成交",
        "https://fapi.binance.com/fapi/v1/trades?symbol=BTCUSDT&limit=10",
        need_sign=False
    )

    # 5. 尝试24小时统计（可能包含清算统计）
    test_endpoint(
        "24小时统计",
        "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT",
        need_sign=False
    )

    # 6. 尝试持仓信息（包含清算价格）
    test_endpoint(
        "持仓信息 (包含清算价格)",
        "https://fapi.binance.com/fapi/v2/positionRisk?symbol=BTCUSDT",
        need_sign=True
    )

    # 7. 尝试全市场清算
    test_endpoint(
        "全市场清算流",
        "https://fapi.binance.com/fapi/v1/allForceOrders",
        need_sign=True
    )

    print("\n" + "=" * 80)
    print("           总结")
    print("=" * 80)
    print("\n可能的替代方案:")
    print("1. 使用聚合成交数据（aggTrades）分析异常交易")
    print("2. 使用持仓信息计算清算价格分布")
    print("3. 使用WebSocket实时监听清算事件")
    print("4. 使用第三方数据源（如Coinglass）")
    print("\n如果所有API都不可用，Q因子可能需要：")
    print("- 改用其他市场微观结构指标")
    print("- 或者暂时禁用Q因子（系统仍可用9个因子）")
    print("=" * 80)

if __name__ == '__main__':
    main()
