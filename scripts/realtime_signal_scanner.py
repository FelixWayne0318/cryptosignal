#!/usr/bin/env python3
# coding: utf-8
"""
WebSocket实时信号扫描器（仅发送信号，不执行交易）

功能:
1. 使用WebSocket批量扫描优化（0次API调用）
2. 扫描200个高流动性币种
3. 发送Prime信号到Telegram
4. 支持定期扫描（每N分钟）

性能:
- 初始化：3-4分钟（首次）
- 扫描时间：12-15秒（200个币种）
- API调用：0次/扫描

使用方法:
    # 单次扫描（默认显示所有币种详细评分）
    python scripts/realtime_signal_scanner.py

    # 定期扫描（每5分钟）
    python scripts/realtime_signal_scanner.py --interval 300

    # 简化输出（只显示前10个币种详细评分）
    python scripts/realtime_signal_scanner.py --interval 300 --no-verbose

    # 测试（只扫描20个币种）
    python scripts/realtime_signal_scanner.py --max-symbols 20

配置方式:
    1. config/telegram.json (优先)
    2. 环境变量: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import os
import sys
import asyncio
import argparse
import signal
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.outputs.telegram_fmt import render_signal
from ats_core.logging import log, warn, error

# v6.6: 发布防抖动系统
from ats_core.publishing.anti_jitter import AntiJitter


def load_telegram_config():
    """
    加载Telegram配置

    优先级:
    1. config/telegram.json
    2. 环境变量

    Returns:
        (bot_token, chat_id) 或抛出异常
    """
    # 1. 尝试从config文件读取
    config_file = project_root / 'config' / 'telegram.json'
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            bot_token = config.get('bot_token', '').strip()
            chat_id = config.get('chat_id', '').strip()

            if bot_token and chat_id:
                log(f"✅ 从config/telegram.json加载配置")
                return bot_token, chat_id
        except Exception as e:
            warn(f"读取config/telegram.json失败: {e}")

    # 2. 从环境变量读取
    bot_token = (os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('ATS_TELEGRAM_BOT_TOKEN') or '').strip()
    chat_id = (os.getenv('TELEGRAM_CHAT_ID') or os.getenv('ATS_TELEGRAM_CHAT_ID') or '').strip()

    if bot_token and chat_id:
        log(f"✅ 从环境变量加载配置")
        return bot_token, chat_id

    # 3. 配置缺失
    raise RuntimeError(
        "Telegram配置未找到！\n"
        "请配置以下任一方式:\n"
        "1. config/telegram.json\n"
        "2. 环境变量: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
    )


def telegram_send_wrapper(text: str, bot_token: str, chat_id: str, parse_mode: str = "HTML") -> None:
    """
    发送Telegram消息（封装，支持config文件配置）

    Args:
        text: 消息文本
        bot_token: Bot Token
        chat_id: Chat ID
        parse_mode: 解析模式（默认HTML）
    """
    import urllib.request

    api = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }

    req = urllib.request.Request(api, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        _ = r.read()


class SignalScanner:
    """WebSocket实时信号扫描器"""

    def __init__(self, min_score: int = 35, send_telegram: bool = True, verbose: bool = True):
        """
        初始化扫描器

        Args:
            min_score: 最低信号分数（默认35，匹配batch_scan_optimized.py）
            send_telegram: 是否发送Telegram通知
            verbose: 是否显示所有币种的详细因子评分（默认True，可用--no-verbose关闭）
        """
        self.scanner = OptimizedBatchScanner()
        self.min_score = min_score
        self.send_telegram = send_telegram
        self.verbose = verbose
        self.initialized = False
        self.scan_count = 0

        # v6.6: 初始化防抖动系统（阈值匹配市场过滤后的实际概率分布）
        self.anti_jitter = AntiJitter(
            prime_entry_threshold=0.45,      # v6.6: 匹配市场过滤后的概率（P=0.45-0.60）
            prime_maintain_threshold=0.42,   # v6.6: 维持阈值相应降低
            watch_entry_threshold=0.40,      # v6.6: WATCH门槛
            watch_maintain_threshold=0.37,   # v6.6: 保持滞后性
            confirmation_bars=1,             # v6.6: 1/2确认即可，更快响应
            total_bars=2,
            cooldown_seconds=60              # v6.6: 更快恢复
        )

        log("✅ v6.6 防抖动系统初始化完成 (K/N=1/2, cooldown=60s, prime_entry=0.45, prime_maintain=0.42)")

        # 加载Telegram配置
        if send_telegram:
            try:
                self.bot_token, self.chat_id = load_telegram_config()
                log(f"✅ Telegram配置加载成功 (Chat ID: {self.chat_id})")
            except Exception as e:
                error(f"❌ Telegram配置加载失败: {e}")
                self.send_telegram = False
        else:
            self.bot_token = None
            self.chat_id = None

        log("✅ 信号扫描器创建成功")

    async def initialize(self):
        """初始化（约3-4分钟）"""
        if self.initialized:
            log("⚠️  已初始化，跳过")
            return

        log("\n" + "=" * 60)
        log("🚀 初始化WebSocket信号扫描器")
        log("=" * 60)

        # 发送启动通知
        if self.send_telegram:
            try:
                telegram_send_wrapper(
                    "🤖 <b>CryptoSignal v6.6 实时扫描器启动中...</b>\n\n"
                    "⏳ 正在初始化WebSocket缓存（约3-4分钟）\n"
                    "📊 目标: 200个高流动性币种\n"
                    "⚡ 后续扫描: 12-15秒/次\n\n"
                    "🎯 系统版本: v6.6\n"
                    "📦 6因子系统: T/M/C/V/O/B\n"
                    "🔧 L/S/F/I调制器: 连续调节\n"
                    "🎚️ 软约束: EV≤0和P<p_min标记但不拒绝\n"
                    "🎯 三层止损: 结构>订单簿>ATR\n"
                    "🆕 新币数据流架构: 1m/5m/15m粒度",
                    self.bot_token,
                    self.chat_id
                )
            except Exception as e:
                warn(f"发送启动通知失败: {e}")

        # 初始化批量扫描器
        await self.scanner.initialize()

        self.initialized = True

        # 发送就绪通知
        if self.send_telegram:
            try:
                telegram_send_wrapper(
                    "✅ <b>实时扫描器已就绪！</b>\n\n"
                    "🚀 WebSocket缓存已激活\n"
                    "📡 K线数据实时更新中\n"
                    "🔍 开始扫描交易信号...",
                    self.bot_token,
                    self.chat_id
                )
            except Exception as e:
                warn(f"发送就绪通知失败: {e}")

        log("\n" + "=" * 60)
        log("✅ 初始化完成！开始扫描...")
        log("=" * 60)

    async def scan_once(self, max_symbols: int = None):
        """
        执行一次扫描

        Args:
            max_symbols: 最大扫描币种数（测试用）

        Returns:
            扫描结果
        """
        if not self.initialized:
            raise RuntimeError("未初始化，请先调用 initialize()")

        self.scan_count += 1

        log("\n" + "=" * 60)
        log(f"🔍 第 {self.scan_count} 次扫描")
        log("=" * 60)

        # 执行扫描
        scan_result = await self.scanner.scan(
            min_score=self.min_score,
            max_symbols=max_symbols,
            verbose=self.verbose
        )

        # 提取Prime信号 - 使用四门系统验证
        signals = scan_result.get('results', [])
        prime_signals = []

        for s in signals:
            try:
                # 获取信号基础数据
                symbol = s.get('symbol', '')
                probability = s.get('probability', 0.5)

                # v6.6: 检查软约束（从analyze_symbol结果中获取）
                publish_info = s.get('publish', {})
                soft_filtered = publish_info.get('soft_filtered', False)
                ev = publish_info.get('EV', 0.0)  # 修复：使用大写'EV'匹配analyze_symbol输出

                # v6.6: 软约束真正"软化" - 仅记录警告，不阻止PRIME级别
                # 修复：soft_filtered应该只是警告标记，不应阻止信号发布
                # 原因：市场过滤会降低概率30%，导致P<p_min，但信号仍然有效
                constraints_passed = True  # 所有通过analyze_symbol的信号都视为约束通过

                # 获取软约束警告信息
                soft_warnings = []
                if ev <= 0:
                    soft_warnings.append(f"EV≤0 ({ev:.4f})")
                if probability < 0.52:  # p_min threshold
                    soft_warnings.append(f"P<p_min ({probability:.3f})")

                warning_str = " | ".join(soft_warnings) if soft_warnings else "无"

                # v6.6: 应用防抖动机制
                # 调用防抖动系统（v6.6中，软约束不影响gates_passed）
                new_level, should_publish = self.anti_jitter.update(
                    symbol=symbol,
                    probability=probability,
                    ev=ev,
                    gates_passed=constraints_passed  # v6.6: 使用软约束结果
                )

                # 只在满足以下条件时发布信号：
                # 1. 未被软约束过滤（v6.6中软约束仅标记）
                # 2. 防抖动系统确认（1/2棒确认 + 60秒冷却）
                # 3. 级别为PRIME
                if constraints_passed and should_publish and new_level == 'PRIME':
                    # 添加软约束信息到信号中
                    s['soft_constraints'] = {
                        'passed': True,
                        'warnings': soft_warnings,
                        'ev': ev,
                        'probability': probability
                    }
                    # 添加防抖动信息
                    s['anti_jitter'] = {
                        'level': new_level,
                        'confirmed': True,
                        'bars_in_state': self.anti_jitter.states[symbol].bars_in_state if symbol in self.anti_jitter.states else 0
                    }
                    prime_signals.append(s)
                    log(f"  ✅ {symbol}: 软约束通过 + 防抖动确认 (P={probability:.3f}, EV={ev:.4f}, 警告={warning_str})")
                elif constraints_passed and not should_publish:
                    # 通过软约束但防抖动未确认
                    log(f"  ⏸️  {symbol}: 软约束通过但等待防抖动确认 (P={probability:.3f}, level={new_level})")
                elif constraints_passed:
                    # 通过软约束但级别不是PRIME（可能是WATCH）
                    log(f"  🔍 {symbol}: 软约束通过但级别={new_level} (P={probability:.3f})")
                else:
                    # 被软约束过滤
                    log(f"  ❌ {symbol}: 被软约束过滤 (P={probability:.3f}, EV={ev:.4f})")

            except Exception as e:
                warn(f"  ⚠️  {symbol}: 软约束检查失败 - {e}")

        log("\n" + "=" * 60)
        log("📊 扫描结果")
        log("=" * 60)
        log(f"   总扫描: {scan_result.get('total_symbols', 0)} 个币种")  # 🔧 FIX: 修正键名 total -> total_symbols
        log(f"   耗时: {scan_result.get('elapsed_seconds', 0):.1f}秒")  # 🔧 FIX: 修正键名 elapsed -> elapsed_seconds
        log(f"   发现信号: {len(signals)} 个")
        log(f"   Prime信号: {len(prime_signals)} 个")
        log("=" * 60)

        # 发送Prime信号到Telegram
        if self.send_telegram and prime_signals:
            await self._send_signals_to_telegram(prime_signals)

        return scan_result

    async def _send_signals_to_telegram(self, signals: list):
        """发送信号到Telegram"""
        log(f"\n📤 发送 {len(signals)} 个Prime信号到Telegram...")

        for i, signal in enumerate(signals, 1):
            try:
                # 渲染信号（v6.7简洁版：适合非专业人士）
                message = render_signal(signal, is_watch=False)

                # 发送
                telegram_send_wrapper(message, self.bot_token, self.chat_id)

                log(f"   ✅ {i}/{len(signals)}: {signal.get('symbol')}")

            except Exception as e:
                error(f"   ❌ 发送失败 {signal.get('symbol')}: {e}")

        log(f"✅ 信号发送完成\n")

    def _calculate_next_scan_time(self) -> datetime:
        """
        智能计算下次扫描时间（对齐K线更新时机）

        策略：
        - 基础频率：5分钟
        - 智能对齐：在K线完成后的2-3分钟扫描（确保数据已更新）
        - 关键时刻：02, 07, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57分

        原理：
        - 15m K线在00, 15, 30, 45分完成，我们在02, 17, 32, 47分扫描
        - 1h K线在每小时00分完成，我们在05, 07分扫描
        - 这样确保扫描时数据已经更新完毕

        Returns:
            下次扫描的datetime对象
        """
        now = datetime.now()
        current_minute = now.minute

        # 关键时刻列表（K线完成后2-7分钟）
        key_minutes = [2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57]

        # 找到下一个关键时刻
        next_key_minute = None
        for km in key_minutes:
            if km > current_minute:
                next_key_minute = km
                break

        if next_key_minute is None:
            # 如果已经过了57分，下一个关键时刻是下一小时的02分
            next_scan = now.replace(minute=2, second=0, microsecond=0)
            next_scan = next_scan + timedelta(hours=1)
        else:
            # 使用下一个关键时刻
            next_scan = now.replace(minute=next_key_minute, second=0, microsecond=0)

        return next_scan

    async def run_periodic(self, interval_seconds: int = 300):
        """
        定期扫描

        Args:
            interval_seconds: 扫描间隔（秒），默认300秒=5分钟
        """
        if not self.initialized:
            await self.initialize()

        log("\n" + "=" * 60)
        log("🔄 启动定期扫描模式")
        log("=" * 60)
        log(f"   扫描间隔: {interval_seconds}秒 ({interval_seconds/60:.1f}分钟)")
        log(f"   最低分数: {self.min_score}")
        log("=" * 60)

        while True:
            try:
                # 执行扫描
                await self.scan_once()

                # 智能计算下次扫描时间（对齐K线更新时机）
                next_scan = self._calculate_next_scan_time()

                wait_seconds = (next_scan - datetime.now()).total_seconds()
                if wait_seconds > 0:
                    log(f"\n⏰ 下次扫描时间: {next_scan.strftime('%H:%M:%S')} （{wait_seconds:.0f}秒后）")
                    log(f"   原因: 对齐K线更新时机（确保数据最新）\n")
                    await asyncio.sleep(wait_seconds)

            except KeyboardInterrupt:
                log("\n⚠️  收到中断信号，停止扫描...")
                break
            except Exception as e:
                error(f"\n❌ 扫描出错: {e}")
                import traceback
                traceback.print_exc()
                log(f"等待60秒后重试...")
                await asyncio.sleep(60)

    async def close(self):
        """关闭扫描器"""
        if self.scanner:
            await self.scanner.close()
        log("✅ 扫描器已关闭")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='WebSocket实时信号扫描器（仅发信号，不交易）'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=0,
        help='扫描间隔（秒），0=单次扫描，300=每5分钟'
    )
    parser.add_argument(
        '--min-score',
        type=int,
        default=35,
        help='最低信号分数（默认35，匹配batch_scan_optimized.py）'
    )
    parser.add_argument(
        '--max-symbols',
        type=int,
        default=None,
        help='最大扫描币种数（测试用）'
    )
    parser.add_argument(
        '--no-telegram',
        action='store_true',
        help='不发送Telegram通知'
    )
    parser.add_argument(
        '--no-verbose',
        action='store_true',
        help='只显示前10个币种的详细评分（默认显示所有140个币种）'
    )

    args = parser.parse_args()

    # 创建扫描器
    scanner = SignalScanner(
        min_score=args.min_score,
        send_telegram=not args.no_telegram,
        verbose=not args.no_verbose  # 默认True，除非指定--no-verbose
    )

    # 设置信号处理（优雅退出）
    def signal_handler(sig, frame):
        log("\n⚠️  收到退出信号，正在关闭...")
        asyncio.create_task(scanner.close())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 初始化
        await scanner.initialize()

        # 单次扫描或定期扫描
        if args.interval > 0:
            await scanner.run_periodic(interval_seconds=args.interval)
        else:
            await scanner.scan_once(max_symbols=args.max_symbols)

    except KeyboardInterrupt:
        log("\n⚠️  用户中断")
    except Exception as e:
        error(f"\n❌ 运行错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scanner.close()


if __name__ == '__main__':
    asyncio.run(main())
