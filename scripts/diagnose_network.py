#!/usr/bin/env python3
"""
网络连接诊断工具
用于排查Binance API连接问题
"""

import socket
import subprocess
import sys
import asyncio
import aiohttp
from typing import Tuple


def check_dns_resolution(hostname: str) -> Tuple[bool, str]:
    """检查DNS解析"""
    try:
        ip = socket.gethostbyname(hostname)
        return True, f"✅ DNS解析成功: {hostname} -> {ip}"
    except socket.gaierror as e:
        return False, f"❌ DNS解析失败: {hostname}\n   错误: {e}"


def check_ping(hostname: str) -> Tuple[bool, str]:
    """检查网络连通性（ping）"""
    try:
        result = subprocess.run(
            ['ping', '-c', '3', hostname],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # 提取平均延迟
            output = result.stdout
            if 'avg' in output:
                latency = output.split('avg')[0].split('/')[-1].strip()
                return True, f"✅ 网络连通正常: {hostname}\n   平均延迟: {latency}ms"
            return True, f"✅ 网络连通正常: {hostname}"
        else:
            return False, f"❌ 网络不通: {hostname}\n   {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, f"❌ Ping超时: {hostname}"
    except Exception as e:
        return False, f"⚠️  无法执行ping: {e}"


async def check_https_connection(url: str) -> Tuple[bool, str]:
    """检查HTTPS连接"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                status = response.status
                if status == 200:
                    return True, f"✅ HTTPS连接成功: {url}\n   状态码: {status}"
                else:
                    return False, f"⚠️  HTTPS连接异常: {url}\n   状态码: {status}"
    except aiohttp.ClientConnectorError as e:
        return False, f"❌ HTTPS连接失败: {url}\n   错误: {e}"
    except asyncio.TimeoutError:
        return False, f"❌ HTTPS连接超时: {url}"
    except Exception as e:
        return False, f"❌ HTTPS连接错误: {url}\n   错误: {e}"


def check_dns_server():
    """检查DNS服务器配置"""
    try:
        with open('/etc/resolv.conf', 'r') as f:
            content = f.read()
            nameservers = [line.split()[1] for line in content.split('\n')
                          if line.strip().startswith('nameserver')]
            if nameservers:
                return True, f"✅ DNS服务器配置:\n   " + "\n   ".join(nameservers)
            else:
                return False, "❌ 未找到DNS服务器配置"
    except Exception as e:
        return False, f"⚠️  无法读取DNS配置: {e}"


async def main():
    print("\n" + "="*60)
    print("🔍 Binance API 网络连接诊断")
    print("="*60 + "\n")

    # 目标主机
    binance_hosts = [
        'fapi.binance.com',
        'api.binance.com',
        'www.binance.com'
    ]

    # 1. 检查DNS服务器配置
    print("1️⃣  检查DNS服务器配置")
    print("-" * 60)
    success, msg = check_dns_server()
    print(msg)
    print()

    # 2. DNS解析测试
    print("2️⃣  DNS解析测试")
    print("-" * 60)
    all_dns_ok = True
    for host in binance_hosts:
        success, msg = check_dns_resolution(host)
        print(msg)
        if not success:
            all_dns_ok = False
    print()

    if not all_dns_ok:
        print("⚠️  发现DNS解析问题！建议：")
        print("   1. 检查网络连接: ping 8.8.8.8")
        print("   2. 尝试使用Google DNS:")
        print("      sudo nano /etc/resolv.conf")
        print("      添加: nameserver 8.8.8.8")
        print("      添加: nameserver 8.8.4.4")
        print("   3. 或尝试Cloudflare DNS:")
        print("      nameserver 1.1.1.1")
        print("      nameserver 1.0.0.1")
        print()

    # 3. Ping测试
    print("3️⃣  网络连通性测试（Ping）")
    print("-" * 60)
    for host in binance_hosts:
        success, msg = check_ping(host)
        print(msg)
    print()

    # 4. HTTPS连接测试
    print("4️⃣  HTTPS连接测试")
    print("-" * 60)
    test_urls = [
        'https://fapi.binance.com/fapi/v1/ping',
        'https://api.binance.com/api/v3/ping'
    ]
    all_https_ok = True
    for url in test_urls:
        success, msg = await check_https_connection(url)
        print(msg)
        if not success:
            all_https_ok = False
    print()

    # 5. 诊断总结
    print("="*60)
    print("📊 诊断总结")
    print("="*60)
    if all_dns_ok and all_https_ok:
        print("✅ 网络连接正常，可以访问Binance API")
        print("   如果系统仍然报错，请检查：")
        print("   - 防火墙设置")
        print("   - 代理配置")
        print("   - Python aiohttp库版本")
    else:
        print("❌ 发现网络问题，请按照上述建议修复")
        print("\n常见解决方案：")
        print("1. DNS问题: 更换DNS服务器（8.8.8.8或1.1.1.1）")
        print("2. 防火墙: 检查是否阻止了HTTPS连接")
        print("3. 网络: 联系VPS提供商检查网络配置")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  诊断已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
