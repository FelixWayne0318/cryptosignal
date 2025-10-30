#!/usr/bin/env python3
# coding: utf-8
"""
CryptoSignal v6.0 扫描器 + 电报通知

运行方式：
  python3 run_scanner.py

功能：
- 扫描所有高流动性币种
- 发现Prime信号立即发送到电报
- 显示完整的10+1维因子评分
"""
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def send_telegram(message: str, token: str, chat_id: str) -> bool:
    """发送电报消息"""
    try:
        import aiohttp

        url = f"https://api.telegram.org/bot{token}/sendMessage"

        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return True
                else:
                    error_text = await resp.text()
                    print(f"电报API错误 ({resp.status}): {error_text}")
                    return False

    except Exception as e:
        print(f"发送电报失败: {e}")
        return False


def format_signal_message(signal: Dict[str, Any]) -> str:
    """格式化信号消息"""
    symbol = signal.get('symbol', 'UNKNOWN')
    side = signal.get('side', 'unknown')
    price = signal.get('price', 0)

    # 评分数据
    scores = signal.get('scores', {})
    weighted_score = signal.get('weighted_score', 0)
    confidence = signal.get('confidence', 0)
    edge = signal.get('edge', 0)

    # 概率数据
    prob = signal.get('probability', {})
    side_long = signal.get('side_long', False)
    P_long = prob.get('P_long', 0)
    P_short = prob.get('P_short', 0)
    P_chosen = P_long if side_long else P_short

    # Prime判定
    publish = signal.get('publish', {})
    is_prime = publish.get('prime', False)
    prime_strength = publish.get('prime_strength', 0)

    # 方向表情
    side_emoji = "📈" if side == "long" else "📉"
    status_emoji = "✅" if is_prime else "⚠️"

    # 因子名称
    factor_names = {
        'T': 'T趋势', 'M': 'M动量', 'C': 'C资金流',
        'S': 'S结构', 'V': 'V量能', 'O': 'O持仓',
        'L': 'L流动性', 'B': 'B基差', 'Q': 'Q清算',
        'I': 'I独立性', 'F': 'F资金领先'
    }

    # 构造消息
    lines = [
        f"{status_emoji} <b>CryptoSignal Prime信号</b>",
        "",
        f"{side_emoji} <b>{symbol}</b> - {side.upper()}",
        "",
        "📊 <b>评分指标:</b>",
        f"  Prime强度: {prime_strength}/100",
        f"  置信度: {confidence}/100",
        f"  加权评分: {weighted_score:+d}/100",
        f"  优势度: {edge:+.2f}",
        f"  胜率: {P_chosen:.1%}",
        "",
        f"💰 价格: ${price:.6f}",
        "",
        "📈 <b>因子评分 (v6.0):</b>",
    ]

    # 添加因子评分
    for factor in ['T', 'M', 'C', 'S', 'V', 'O', 'L', 'B', 'Q', 'I', 'F']:
        score = scores.get(factor, 0)
        name = factor_names.get(factor, factor)
        lines.append(f"  {name}: {score:+d}")

    lines.extend([
        "",
        "🎯 系统版本: v6.0",
        "📦 权重模式: 100%百分比",
        "⚡ F因子: 已启用 (10.0%)",
        "",
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ])

    return "\n".join(lines)


async def run_scanner():
    """运行扫描器"""
    try:
        print("=" * 70)
        print("CryptoSignal v6.0 扫描器 + 电报通知")
        print("=" * 70)
        print()

        # 1. 加载配置
        print("【1】加载配置...")

        with open('config/telegram.json', 'r') as f:
            tg_config = json.load(f)

        bot_token = tg_config.get('bot_token')
        chat_id = tg_config.get('chat_id')

        if not bot_token or not chat_id:
            print("❌ 电报配置不完整")
            return 1

        print(f"  ✅ 电报 Chat ID: {chat_id}")

        with open('config/params.json', 'r') as f:
            params = json.load(f)

        version = params['weights_comment']['_version']
        f_weight = params['weights'].get('F', 0)

        print(f"  ✅ 权重系统: {version}")
        print(f"  ✅ F因子权重: {f_weight}%")
        print()

        # 2. 发送启动消息
        start_msg = f"""
🚀 <b>CryptoSignal v6.0 启动</b>

✅ 系统版本: {version}
✅ F因子: 已启用 ({f_weight}%)
✅ 权重模式: 100%百分比

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

开始扫描市场...
        """

        print("发送启动消息到电报...")
        await send_telegram(start_msg, bot_token, chat_id)
        print("✅ 启动消息已发送")
        print()

        # 3. 运行扫描
        print("【2】初始化扫描器...")

        from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner

        scanner = OptimizedBatchScanner()

        # 定义信号回调
        signals_sent = []

        async def on_signal(signal: Dict[str, Any]):
            """发现信号时的回调"""
            symbol = signal.get('symbol', 'UNKNOWN')
            prime_strength = signal.get('publish', {}).get('prime_strength', 0)

            print(f"\n🔔 发现信号: {symbol} (Prime={prime_strength})")
            print("发送到电报...")

            # 格式化并发送
            message = format_signal_message(signal)
            success = await send_telegram(message, bot_token, chat_id)

            if success:
                print(f"✅ {symbol} 信号已发送")
                signals_sent.append(symbol)
            else:
                print(f"❌ {symbol} 发送失败")

        # 初始化
        print("预加载市场数据...")
        await scanner.initialize()
        print("✅ 初始化完成")
        print()

        # 4. 扫描
        print("【3】开始扫描...")
        print("-" * 70)

        results = await scanner.scan(
            min_score=70,
            on_signal_found=on_signal
        )

        # 5. 检查结果
        print()
        print("【4】检查扫描结果...")

        # 修复：正确获取信号列表
        all_signals = results.get('results', [])
        signals_found = results.get('signals_found', 0)
        elapsed = results.get('elapsed_seconds', 0)

        print(f"扫描统计:")
        print(f"  总计发现: {signals_found} 个信号")
        print(f"  通过回调发送: {len(signals_sent)} 个")
        print()

        # 6. 检查是否有未发送的信号（回调失败）
        if signals_found > len(signals_sent):
            print(f"⚠️  发现 {signals_found - len(signals_sent)} 个信号未通过回调发送")
            print("尝试手动发送...")

            for signal in all_signals:
                symbol = signal.get('symbol', 'UNKNOWN')
                if symbol not in signals_sent:
                    print(f"\n补发信号: {symbol}")
                    message = format_signal_message(signal)
                    success = await send_telegram(message, bot_token, chat_id)
                    if success:
                        print(f"✅ {symbol} 补发成功")
                        signals_sent.append(symbol)
                    else:
                        print(f"❌ {symbol} 补发失败")

        # 7. 发送总结
        print()
        print("【5】发送扫描总结...")

        cache_stats = results.get('cache_stats', {})
        cache_hit_rate = cache_stats.get('hit_rate', '100.0%')

        # 如果是字符串格式（如"100.0%"），直接使用；如果是float，格式化
        if isinstance(cache_hit_rate, (int, float)):
            cache_hit_rate_str = f"{cache_hit_rate * 100:.1f}%"
        else:
            cache_hit_rate_str = str(cache_hit_rate)

        summary_msg = f"""
📊 <b>扫描完成</b>

🎯 发现信号: {signals_found} 个
📤 已发送: {len(signals_sent)} 个

⏱️ 扫描时间: {elapsed:.1f}秒
🚀 API调用: {results.get('api_calls', 0)}次
💾 缓存命中率: {cache_hit_rate_str}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        await send_telegram(summary_msg, bot_token, chat_id)
        print("✅ 总结已发送")

        # 8. 清理
        await scanner.close()

        print()
        print("=" * 70)
        print(f"✅ 扫描完成！共发现 {signals_found} 个信号，已发送 {len(signals_sent)} 个")
        print("=" * 70)

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_scanner()))
