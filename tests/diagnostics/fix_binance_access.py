#!/usr/bin/env python3
# coding: utf-8
"""
Binance API 访问修复脚本
尝试不同的方法来恢复对Binance API的访问
"""

import os
import sys
import urllib.request
import urllib.error
import json

def test_access(method_name, setup_func=None):
    """测试API访问"""
    print(f"\n{'='*60}")
    print(f"测试方法: {method_name}")
    print('='*60)

    if setup_func:
        setup_func()

    url = "https://fapi.binance.com/fapi/v1/ping"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
            print(f"✅ 成功! HTTP {r.status}")
            print(f"响应: {data.decode()}")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {e}")
        return False

def method1_original():
    """方法1: 使用原始代理设置"""
    # 不做任何修改，使用系统默认代理
    pass

def method2_no_proxy():
    """方法2: 完全禁用代理"""
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)

def method3_env_no_proxy():
    """方法3: 通过环境变量禁用代理"""
    os.environ['NO_PROXY'] = 'localhost,127.0.0.1,*.binance.com,binance.com,fapi.binance.com,api.binance.com'
    os.environ['no_proxy'] = 'localhost,127.0.0.1,*.binance.com,binance.com,fapi.binance.com,api.binance.com'

def method4_different_ua():
    """方法4: 更换User-Agent（继续使用代理）"""
    # User-Agent已经在test_access中更换了
    pass

def apply_fix_to_code():
    """应用修复到实际代码"""
    print(f"\n{'='*60}")
    print("应用修复到代码")
    print('='*60)

    target_file = "ats_core/sources/binance.py"

    if not os.path.exists(target_file):
        print(f"❌ 文件不存在: {target_file}")
        return False

    print(f"读取文件: {target_file}")

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经修复过
    if "# FIXED: Disable proxy for Binance" in content:
        print("⚠️  代码已经包含修复，跳过")
        return True

    # 找到_get函数并添加代理禁用代码
    import_section = content.find("def _get(")

    if import_section == -1:
        print("❌ 找不到_get函数")
        return False

    # 找到函数体开始位置
    func_start = content.find(":", import_section)
    next_line = content.find("\n", func_start) + 1

    # 准备插入的代码
    fix_code = '''    """
    统一 GET 请求，带重试与简单 UA；path_or_url 可以是完整 URL 或以 / 开头的路径
    """
    # FIXED: Disable proxy for Binance to avoid 403 errors
    if 'binance.com' in (path_or_url if path_or_url.startswith('http') else BASE + path_or_url):
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)

'''

    # 查找原始docstring的结束位置
    docstring_start = content.find('"""', func_start)
    if docstring_start != -1:
        docstring_end = content.find('"""', docstring_start + 3)
        if docstring_end != -1:
            # 在docstring之后插入
            insert_pos = docstring_end + 3
            # 跳过换行
            while insert_pos < len(content) and content[insert_pos] in '\n\r':
                insert_pos += 1

            new_content = content[:insert_pos] + '\n' + fix_code + content[insert_pos:]

            # 备份原文件
            backup_file = target_file + ".backup"
            print(f"备份原文件到: {backup_file}")
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # 写入修改后的内容
            print(f"写入修改后的文件: {target_file}")
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print("✅ 代码修复完成!")
            return True

    print("❌ 无法定位插入位置")
    return False

def main():
    print("=" * 60)
    print("Binance API 访问修复工具")
    print("=" * 60)

    methods = [
        ("方法1: 使用系统代理（当前状态）", method1_original),
        ("方法2: 完全禁用代理", method2_no_proxy),
        ("方法3: 通过NO_PROXY环境变量", method3_env_no_proxy),
        ("方法4: 更换User-Agent", method4_different_ua),
    ]

    successful_methods = []

    for name, setup in methods:
        if test_access(name, setup):
            successful_methods.append(name)

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    if successful_methods:
        print(f"\n✅ 成功的方法 ({len(successful_methods)}):")
        for method in successful_methods:
            print(f"  - {method}")

        print("\n" + "=" * 60)
        print("应用修复?")
        print("=" * 60)

        if "方法2" in successful_methods[0] or "方法3" in successful_methods[0]:
            response = input("\n是否要将修复应用到代码? (y/n): ")
            if response.lower() == 'y':
                if apply_fix_to_code():
                    print("\n✅ 修复完成! 现在可以运行主程序:")
                    print("   python3 -m ats_core.pipeline.main")
                else:
                    print("\n❌ 自动修复失败，请手动修改代码")
        else:
            print("\n⚠️  当前方法可用，但可能不稳定")
            print("建议: 检查代理服务器状态或联系网络管理员")

    else:
        print("\n❌ 所有方法都失败")
        print("\n建议:")
        print("  1. 检查网络连接")
        print("  2. 检查防火墙设置")
        print("  3. 更换代理服务器")
        print("  4. 使用Binance API Key")
        print("  5. 考虑使用备用数据源")

if __name__ == "__main__":
    main()
