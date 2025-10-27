#!/usr/bin/env python3
# coding: utf-8
"""
服务器诊断和修复脚本
"""

import os
import sys
import urllib.request
import urllib.error
import json
from datetime import datetime

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_api_access():
    """测试Binance API访问"""
    print_section("1. 测试Binance API访问")

    endpoints = [
        ("Futures Ping", "https://fapi.binance.com/fapi/v1/ping"),
        ("Spot Ping", "https://api.binance.com/api/v3/ping"),
        ("Futures 24h Ticker (BTCUSDT)", "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT"),
    ]

    results = []

    for name, url in endpoints:
        print(f"\n测试: {name}")
        print(f"URL: {url}")

        # 测试1: 使用代理
        print("  [1] 使用系统代理...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ats-analyzer/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = r.read()
                print(f"      ✅ 成功 (HTTP {r.status})")
                results.append((name, "代理", True, r.status))
        except urllib.error.HTTPError as e:
            print(f"      ❌ 失败 (HTTP {e.code}: {e.reason})")
            results.append((name, "代理", False, e.code))
        except Exception as e:
            print(f"      ❌ 异常: {type(e).__name__}: {e}")
            results.append((name, "代理", False, str(e)))

        # 测试2: 不使用代理
        print("  [2] 不使用代理...")
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = r.read()
                print(f"      ✅ 成功 (HTTP {r.status})")
                results.append((name, "无代理", True, r.status))
        except urllib.error.HTTPError as e:
            print(f"      ❌ 失败 (HTTP {e.code}: {e.reason})")
            results.append((name, "无代理", False, e.code))
        except Exception as e:
            print(f"      ❌ 异常: {type(e).__name__}: {e}")
            results.append((name, "无代理", False, str(e)))

    return results

def check_database():
    """检查数据库状态"""
    print_section("2. 检查数据库状态")

    import sqlite3

    db_path = "data/database/cryptosignal.db"
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查信号总数
    cursor.execute("SELECT COUNT(*) FROM signals")
    total = cursor.fetchone()[0]
    print(f"信号总数: {total}")

    # 检查最近的信号
    cursor.execute("""
        SELECT symbol, side, created_at, updated_at
        FROM signals
        ORDER BY updated_at DESC
        LIMIT 5
    """)

    print("\n最近5条信号:")
    for row in cursor.fetchall():
        symbol, side, created, updated = row
        print(f"  - {symbol} ({side}) - 创建:{created}, 更新:{updated}")

    # 检查最后更新时间
    cursor.execute("SELECT MAX(updated_at) FROM signals")
    last_update = cursor.fetchone()[0]
    print(f"\n数据库最后更新时间: {last_update}")
    print(f"当前时间: {datetime.now()}")

    conn.close()

def check_environment():
    """检查环境配置"""
    print_section("3. 检查环境配置")

    # 代理设置
    print("\n代理设置:")
    for key in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"]:
        val = os.environ.get(key)
        if val:
            print(f"  {key} = {val}")

    # Binance设置
    print("\nBinance配置:")
    for key in ["BINANCE_FAPI_BASE", "BINANCE_SPOT_BASE"]:
        val = os.environ.get(key, "未设置")
        print(f"  {key} = {val}")

def generate_fix_recommendations(test_results):
    """生成修复建议"""
    print_section("4. 修复建议")

    # 分析测试结果
    proxy_success = any(r[1] == "代理" and r[2] for r in test_results)
    no_proxy_success = any(r[1] == "无代理" and r[2] for r in test_results)

    all_403 = all(r[3] == 403 for r in test_results if not r[2])

    if all_403:
        print("\n❌ 所有请求都返回403 Forbidden")
        print("\n可能原因：")
        print("  1. 服务器IP被Binance封禁")
        print("  2. 地理位置限制")
        print("  3. 代理IP被封禁")

        print("\n建议解决方案：")
        print("  方案1: 更换服务器或使用VPN")
        print("  方案2: 使用Binance API Key（提高访问限制）")
        print("  方案3: 更换代理服务器")
        print("  方案4: 联系Binance支持")

    elif proxy_success and not no_proxy_success:
        print("\n✅ 使用代理可以访问")
        print("\n建议：确保代码中正确使用了系统代理")

    elif no_proxy_success and not proxy_success:
        print("\n✅ 不使用代理可以访问")
        print("\n建议解决方案：")
        print("  1. 在代码中禁用代理")
        print("  2. 将binance.com添加到NO_PROXY环境变量")

        print("\n修复代码示例：")
        print("""
# 在 ats_core/sources/binance.py 的 _get 函数中添加：

def _get(path_or_url, params, *, timeout=8.0, retries=2):
    # ... 现有代码 ...

    # 禁用代理（如果需要）
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)

    # ... 后续代码 ...
""")

    else:
        print("\n❌ 两种方式都无法访问")
        print("\n可能原因：")
        print("  1. 网络连接问题")
        print("  2. Binance API暂时不可用")
        print("  3. 防火墙阻止")

def main():
    print("=" * 70)
    print("  Cryptosignal 服务器诊断工具")
    print("=" * 70)
    print(f"时间: {datetime.now()}")

    try:
        # 1. 测试API访问
        test_results = test_api_access()

        # 2. 检查数据库
        check_database()

        # 3. 检查环境
        check_environment()

        # 4. 生成建议
        generate_fix_recommendations(test_results)

        print("\n" + "=" * 70)
        print("  诊断完成")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
