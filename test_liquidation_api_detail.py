#!/usr/bin/env python3
"""Test different liquidation API endpoints in detail"""
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
    """Test public liquidation API (no signature required)"""
    print("【Test A】Public API: /fapi/v1/forceOrders (no signature)")
    print("-" * 80)

    try:
        url = "https://fapi.binance.com/fapi/v1/forceOrders?symbol=BTCUSDT&limit=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'test/1.0'})

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            print(f"✅ Success: Got {len(data)} liquidation orders (public API)")
            if data:
                print(f"   Example: {data[0]}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Failed: HTTP {e.code}")
        try:
            error_data = json.loads(error_body)
            print(f"   Binance response: {error_data}")
        except:
            print(f"   Response: {error_body}")
        return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_signed_liquidations():
    """Test signed liquidation API (signature required)"""
    print("\n【Test B】Signed API: /fapi/v1/allForceOrders (signature required)")
    print("-" * 80)

    if not API_KEY or not API_SECRET:
        print("❌ Environment variables not set")
        return False

    try:
        # Build signed request
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
            print(f"✅ Success: Got liquidation data (signed API)")
            print(f"   Data: {data}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Failed: HTTP {e.code}")
        try:
            error_data = json.loads(error_body)
            print(f"   Binance response: {error_data}")
        except:
            print(f"   Response: {error_body}")
        return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("           Liquidation API Detailed Test")
    print("=" * 80)
    print()

    # Test public API
    result_a = test_public_liquidations()

    # Test signed API
    result_b = test_signed_liquidations()

    # Summary
    print("\n" + "=" * 80)
    print("           Test Summary")
    print("=" * 80)

    if result_a:
        print("\n✅ Good news! Public API can access liquidation data")
        print("   This means Q factor can work without special API permissions")
        print("\n💡 Solution:")
        print("   1. Our code will use public API first")
        print("   2. No need to modify Binance API settings")
        print("   3. Q factor should work now")
    elif result_b:
        print("\n✅ Signed API can access liquidation data")
        print("   But this only shows your own account liquidations")
        print("\n⚠️  Issue:")
        print("   Signed API returns personal liquidation history, not market data")
        print("   Q factor needs market liquidation data from public API")
    else:
        print("\n❌ Both APIs failed")
        print("\nPossible reasons:")
        print("   1. Binance changed API policy")
        print("   2. Regional restrictions")
        print("   3. Temporary rate limiting")

if __name__ == '__main__':
    main()
