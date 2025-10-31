#!/usr/bin/env python3
# coding: utf-8
"""
CryptoSignal v6.0 信号扫描器 (带四道闸检查)

✨ 新特性:
- ✅ 四道闸完整检查 (DataQual + EV>0 + Execution + Probability)
- ✅ F/I调节器集成 (温度/成本/门槛动态调节)
- ✅ 执行层指标 (spread/impact/OBI估算)
- ✅ 电报消息发送

使用方法:
    # 单次扫描并发送到电报
    python scripts/signal_scanner_v2.py

    # 测试模式（不发送电报）
    python scripts/signal_scanner_v2.py --dry-run

    # 指定币种测试
    python scripts/signal_scanner_v2.py --symbols BTCUSDT,ETHUSDT --dry-run

配置:
    config/telegram.json - 电报配置
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.gates.integrated_gates import FourGatesChecker
from ats_core.execution.metrics_estimator import ExecutionMetrics, get_execution_estimator
from ats_core.outputs.publisher import telegram_send
from ats_core.data.quality import DataQualMonitor


def load_telegram_config():
    """加载电报配置"""
    config_file = project_root / 'config' / 'telegram.json'

    if not config_file.exists():
        raise FileNotFoundError(
            f"电报配置文件不存在: {config_file}\n"
            "请创建 config/telegram.json 文件"
        )

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if not config.get('enabled', False):
        raise RuntimeError("电报发送未启用 (enabled=false)")

    bot_token = config.get('bot_token', '').strip()
    chat_id = config.get('chat_id', '').strip()

    if not bot_token or not chat_id:
        raise RuntimeError("电报配置不完整: bot_token 或 chat_id 缺失")

    return bot_token, chat_id


def simulate_signal_data(symbol: str):
    """
    模拟生成信号数据（用于测试）

    在生产环境中，这应该从实际的市场数据和因子计算中获取
    """
    import random

    # 模拟概率和因子值
    probability = 0.5 + random.random() * 0.35  # 0.5-0.85
    F_raw = random.random()  # 0-1
    I_raw = random.random()  # 0-1

    # 模拟K线数据（用于执行指标估算）
    close = 100.0 + random.random() * 10.0
    high = close * (1.0 + random.random() * 0.01)
    low = close * (1.0 - random.random() * 0.01)
    volume = 1000000 + random.random() * 5000000
    taker_buy_volume = volume * (0.4 + random.random() * 0.2)

    # 模拟执行指标
    estimator = get_execution_estimator()
    exec_metrics = estimator.calculate(
        high=high,
        low=low,
        close=close,
        volume=volume,
        taker_buy_volume=taker_buy_volume,
        avg_volume=volume * 0.8
    )

    return {
        'symbol': symbol,
        'probability': probability,
        'F_raw': F_raw,
        'I_raw': I_raw,
        'exec_metrics': exec_metrics,
        'close': close,
        'delta_p': random.uniform(0.02, 0.08)  # 概率变化
    }


def format_telegram_message(symbol: str, gate_results: dict, signal_data: dict) -> str:
    """
    格式化电报消息

    Args:
        symbol: 交易对
        gate_results: 四道闸结果
        signal_data: 信号数据

    Returns:
        格式化的HTML消息
    """
    # 判断通过状态
    all_passed = all(result.passed for result in gate_results.values())
    status_emoji = "✅" if all_passed else "⚠️"
    status_text = "通过全部闸门" if all_passed else "部分闸门未通过"

    # 提取关键指标
    gate1 = gate_results['gate1_dataqual']
    gate2 = gate_results['gate2_ev']
    gate3 = gate_results['gate3_execution']
    gate4 = gate_results['gate4_probability']

    # 构建消息
    message = f"""
🎯 <b>{status_emoji} CryptoSignal v6.0 信号</b>

📊 <b>交易对</b>: {symbol}
💰 <b>价格</b>: ${signal_data['close']:.4f}
📈 <b>概率</b>: {signal_data['probability']:.1%}

━━━━━━━━━━━━━━━━━━
<b>📋 四道闸检查</b>

{'✅' if gate1.passed else '❌'} <b>闸1 - 数据质量</b>
   DataQual: {gate1.value:.3f} {'≥' if gate1.passed else '<'} {gate1.threshold}

{'✅' if gate2.passed else '❌'} <b>闸2 - 期望收益</b>
   EV: {gate2.value:.4f} {'>' if gate2.passed else '≤'} {gate2.threshold}
   μ_win: {gate2.details['mu_win']:.3f}, μ_loss: {gate2.details['mu_loss']:.3f}

{'✅' if gate3.passed else '❌'} <b>闸3 - 执行层</b>
   Spread: {gate3.value['spread_bps']:.1f} bps
   Impact: {gate3.value['impact_bps']:.1f} bps
   OBI: {gate3.value['OBI']:.2f}

{'✅' if gate4.passed else '❌'} <b>闸4 - 概率门槛</b>
   p: {gate4.value['p']:.3f} {'≥' if gate4.details['check_p'] else '<'} {gate4.threshold['p_min']:.3f}
   ΔP: {abs(gate4.value['delta_p']):.3f} {'≥' if gate4.details['check_delta'] else '<'} {gate4.threshold['delta_p_min']:.3f}

━━━━━━━━━━━━━━━━━━
<b>🎛️ B层调节器</b>

F (拥挤度): {signal_data['F_raw']:.2f}
I (独立性): {signal_data['I_raw']:.2f}

━━━━━━━━━━━━━━━━━━
<b>📌 系统信息</b>

🔧 版本: v6.0 + 四道闸
⚡ 架构: A/B/C/D 四层
📦 状态: {status_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    return message.strip()


def scan_and_send(symbols: list, dry_run: bool = False):
    """
    扫描币种并发送信号

    Args:
        symbols: 币种列表
        dry_run: 是否为测试模式（不实际发送）
    """
    print("\n" + "=" * 60)
    print("🚀 CryptoSignal v6.0 信号扫描器 (带四道闸)")
    print("=" * 60)

    # 加载电报配置
    if not dry_run:
        try:
            bot_token, chat_id = load_telegram_config()
            print(f"✅ 电报配置已加载")
            print(f"   频道ID: {chat_id}")
        except Exception as e:
            print(f"❌ 电报配置加载失败: {e}")
            return
    else:
        print("⚠️  测试模式: 不发送电报消息")
        bot_token = chat_id = None

    # 初始化四道闸检查器
    dataqual_monitor = DataQualMonitor()
    four_gates = FourGatesChecker(dataqual_monitor)

    print(f"\n📊 开始扫描 {len(symbols)} 个币种...")
    print("=" * 60)

    signals_sent = 0
    signals_blocked = 0

    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] 🔍 分析 {symbol}...")

        try:
            # 模拟数据质量事件（用于DataQual计算）
            import random
            ts_exch = int(datetime.now().timestamp() * 1000)
            ts_srv = ts_exch + random.randint(-100, 100)
            dataqual_monitor.record_event(
                symbol=symbol,
                ts_exch=ts_exch,
                ts_srv=ts_srv,
                is_ordered=random.random() > 0.01
            )

            # 获取信号数据
            signal_data = simulate_signal_data(symbol)

            # 检查四道闸
            all_passed, gate_results = four_gates.check_all_gates(
                symbol=symbol,
                probability=signal_data['probability'],
                execution_metrics=signal_data['exec_metrics'],
                F_raw=signal_data['F_raw'],
                I_raw=signal_data['I_raw'],
                delta_p=signal_data['delta_p'],
                is_newcoin=False
            )

            # 显示结果
            if all_passed:
                print(f"   ✅ 通过全部四道闸")
                print(f"   📈 概率: {signal_data['probability']:.1%}")
                print(f"   💰 EV: {gate_results['gate2_ev'].value:.4f}")
                print(f"   📊 DataQual: {gate_results['gate1_dataqual'].value:.3f}")

                # 发送到电报
                if not dry_run:
                    message = format_telegram_message(symbol, gate_results, signal_data)

                    import os
                    os.environ['TELEGRAM_BOT_TOKEN'] = bot_token
                    os.environ['TELEGRAM_CHAT_ID'] = chat_id

                    telegram_send(message, chat_id=chat_id, parse_mode="HTML")
                    print(f"   📤 已发送到电报")
                    signals_sent += 1
                else:
                    print(f"   📝 测试模式: 跳过发送")
                    signals_sent += 1

            else:
                failed_gates = [
                    name.replace('gate', '闸').replace('_', ' ')
                    for name, result in gate_results.items()
                    if not result.passed
                ]
                print(f"   ❌ 未通过: {', '.join(failed_gates)}")
                signals_blocked += 1

        except Exception as e:
            print(f"   ⚠️  处理失败: {e}")
            import traceback
            traceback.print_exc()

    # 总结
    print("\n" + "=" * 60)
    print("📊 扫描完成")
    print("=" * 60)
    print(f"   总扫描: {len(symbols)} 个币种")
    print(f"   通过闸门: {signals_sent} 个")
    print(f"   被拦截: {signals_blocked} 个")
    print(f"   通过率: {signals_sent/len(symbols):.1%}")
    print("=" * 60)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="CryptoSignal v6.0 信号扫描器 (带四道闸)"
    )
    parser.add_argument(
        '--symbols',
        type=str,
        default='BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT',
        help='逗号分隔的币种列表（默认: BTC/ETH/BNB/SOL/ADA）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='测试模式：不实际发送电报消息'
    )

    args = parser.parse_args()

    # 解析币种列表
    symbols = [s.strip() for s in args.symbols.split(',')]

    # 执行扫描
    scan_and_send(symbols, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
