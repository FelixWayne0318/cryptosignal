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
    # 单次扫描
    python scripts/realtime_signal_scanner.py

    # 定期扫描（每5分钟）
    python scripts/realtime_signal_scanner.py --interval 300

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
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.outputs.telegram_fmt import render_trade
from ats_core.logging import log, warn, error


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

    def __init__(self, min_score: int = 50, send_telegram: bool = True):
        """
        初始化扫描器

        Args:
            min_score: 最低信号分数（默认50，可调整：40-70）
            send_telegram: 是否发送Telegram通知
        """
        self.scanner = OptimizedBatchScanner()
        self.min_score = min_score
        self.send_telegram = send_telegram
        self.initialized = False
        self.scan_count = 0

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
                    "🤖 <b>CryptoSignal v6.0 实时扫描器启动中...</b>\n\n"
                    "⏳ 正在初始化WebSocket缓存（约3-4分钟）\n"
                    "📊 目标: 200个高流动性币种\n"
                    "⚡ 后续扫描: 12-15秒/次\n\n"
                    "🎯 系统版本: v6.0\n"
                    "📦 权重模式: 100%百分比\n"
                    "⚡ F因子: 已启用 (10.0%)",
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
            max_symbols=max_symbols
        )

        # 提取Prime信号
        signals = scan_result.get('results', [])
        prime_signals = [
            s for s in signals
            if s.get('tier') == 'prime'
        ]

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
                # 渲染信号
                message = render_trade(signal)

                # 添加v6.0系统标识
                footer = f"""

━━━━━━━━━━━━━━━━━━
🎯 <b>系统版本: v6.0</b>
📦 权重模式: 100%百分比
⚡ F因子: 已启用 (10.0%)

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                message = message + footer

                # 发送
                telegram_send_wrapper(message, self.bot_token, self.chat_id)

                log(f"   ✅ {i}/{len(signals)}: {signal.get('symbol')}")

            except Exception as e:
                error(f"   ❌ 发送失败 {signal.get('symbol')}: {e}")

        log(f"✅ 信号发送完成\n")

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

                # 等待下次扫描
                next_scan = datetime.now()
                next_scan = next_scan.replace(
                    second=0, microsecond=0
                )
                next_scan = next_scan.replace(
                    minute=(next_scan.minute // (interval_seconds // 60) + 1) * (interval_seconds // 60)
                )

                wait_seconds = (next_scan - datetime.now()).total_seconds()
                if wait_seconds > 0:
                    log(f"\n⏰ 等待 {wait_seconds:.0f}秒后进行下次扫描（{next_scan.strftime('%H:%M')}）...\n")
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
        default=70,
        help='最低信号分数（默认70）'
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

    args = parser.parse_args()

    # 创建扫描器
    scanner = SignalScanner(
        min_score=args.min_score,
        send_telegram=not args.no_telegram
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
