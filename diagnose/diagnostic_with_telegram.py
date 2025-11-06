#!/usr/bin/env python3
# coding: utf-8
"""
带Telegram通知的诊断脚本
运行后自动将诊断报告发送到Telegram群
"""

import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def send_telegram_message(message: str, bot_token: str, chat_id: str):
    """发送消息到Telegram"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Telegram单条消息限制4096字符，需要分割
    max_length = 4000
    messages = []

    if len(message) <= max_length:
        messages = [message]
    else:
        # 分割成多条消息
        lines = message.split('\n')
        current_msg = ""

        for line in lines:
            if len(current_msg) + len(line) + 1 <= max_length:
                current_msg += line + '\n'
            else:
                if current_msg:
                    messages.append(current_msg)
                current_msg = line + '\n'

        if current_msg:
            messages.append(current_msg)

    # 发送所有消息片段
    for i, msg in enumerate(messages):
        try:
            payload = {
                'chat_id': chat_id,
                'text': msg,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            if i < len(messages) - 1:
                import time
                time.sleep(1)  # 避免发送过快

        except Exception as e:
            print(f"发送消息失败 #{i+1}: {e}")

    return len(messages)

def send_telegram_document(file_path: str, bot_token: str, chat_id: str, caption: str = ""):
    """发送文件到Telegram"""
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {
                'chat_id': chat_id,
                'caption': caption
            }
            response = requests.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"发送文件失败: {e}")
        return False

def load_telegram_config():
    """加载Telegram配置"""
    config_path = project_root / "config" / "telegram.json"

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        if not config.get('enabled', False):
            return None

        return {
            'bot_token': config['bot_token'],
            'chat_id': config['chat_id']
        }
    except Exception as e:
        print(f"加载Telegram配置失败: {e}")
        return None

def main():
    print("=" * 80)
    print("🔍 CryptoSignal 诊断工具（带Telegram通知）")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 加载Telegram配置
    telegram_config = load_telegram_config()

    if telegram_config:
        print("✅ Telegram配置已加载")
        print(f"   Chat ID: {telegram_config['chat_id']}")
    else:
        print("⚠️  Telegram未配置或已禁用，将只保存本地报告")

    # 生成报告文件名
    report_filename = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = project_root / report_filename

    print(f"   报告文件: {report_filename}\n")

    # 运行诊断脚本并捕获输出
    print("开始运行诊断...")
    print("=" * 80 + "\n")

    import subprocess

    diagnostic_script = project_root / "diagnostic_scan.py"

    try:
        # 运行诊断脚本并实时显示输出
        with open(report_path, 'w') as f:
            process = subprocess.Popen(
                [sys.executable, str(diagnostic_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            output_lines = []
            for line in process.stdout:
                print(line, end='')  # 实时显示
                output_lines.append(line)
                f.write(line)  # 同时写入文件

            process.wait()
            full_output = ''.join(output_lines)

        print(f"\n\n{'=' * 80}")
        print(f"✅ 诊断完成！报告已保存到: {report_filename}")
        print("=" * 80 + "\n")

        # 如果配置了Telegram，发送报告
        if telegram_config:
            print("📤 正在发送诊断报告到Telegram...\n")

            # 提取关键信息作为摘要
            summary_parts = []

            # 提取配置检查结果
            if "第一部分" in full_output:
                config_section = full_output.split("第一部分")[1].split("=" * 80)[0]
                summary_parts.append("📋 <b>配置检查结果</b>\n" + config_section.strip())

            # 提取扫描结果统计
            if "第四部分" in full_output:
                stats_section = full_output.split("第四部分")[1].split("=" * 80)[0]
                summary_parts.append("\n📈 <b>统计汇总</b>\n" + stats_section.strip())

            # 如果没有第四部分（扫描失败），提取错误信息
            elif "扫描测试失败" in full_output:
                error_line = [line for line in full_output.split('\n') if '扫描测试失败' in line][0]
                summary_parts.append(f"\n❌ <b>扫描失败</b>\n{error_line}")

            # 组装摘要消息
            summary_message = f"""
🔍 <b>CryptoSignal 系统诊断报告</b>

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌿 分支: claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8

{''.join(summary_parts)}

📄 完整报告已上传（见附件）
"""

            # 发送摘要
            print("   发送摘要...")
            send_telegram_message(
                summary_message,
                telegram_config['bot_token'],
                telegram_config['chat_id']
            )

            # 发送完整报告文件
            print("   上传完整报告...")
            success = send_telegram_document(
                str(report_path),
                telegram_config['bot_token'],
                telegram_config['chat_id'],
                caption=f"📋 完整诊断报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            if success:
                print("\n✅ 诊断报告已成功发送到Telegram！")
            else:
                print("\n⚠️  报告发送失败，请手动查看本地文件")

        print(f"\n本地报告路径: {report_path}")
        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()

        # 尝试发送错误通知
        if telegram_config:
            error_message = f"""
❌ <b>诊断失败</b>

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌿 分支: claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8

错误信息:
<code>{str(e)}</code>

请检查服务器日志获取详细信息。
"""
            send_telegram_message(
                error_message,
                telegram_config['bot_token'],
                telegram_config['chat_id']
            )

if __name__ == "__main__":
    main()
