#!/usr/bin/env python3
# coding: utf-8
"""
实时信号扫描器（v7.2增强版 - 统一版本）

功能特性:
1. ✅ v7.2增强分析（F因子v2、因子分组、统计校准、四道闸门）
2. ✅ WebSocket批量扫描优化（0次API调用）
3. ✅ 自动数据采集（信号快照、分析数据库）
4. ✅ Telegram通知（v7.2格式 + 扫描摘要）
5. ✅ 防抖动系统（避免重复通知）
6. ✅ 自动提交报告到Git仓库

性能指标:
- 初始化：3-4分钟（首次）
- 扫描速度：12-15秒（200个币种）
- API调用：0次/扫描
- 数据新鲜度：实时更新

使用方法:
    # 单次扫描
    python scripts/realtime_signal_scanner.py

    # 定期扫描（每5分钟）
    python scripts/realtime_signal_scanner.py --interval 300

    # 测试模式（只扫描20个币种）
    python scripts/realtime_signal_scanner.py --max-symbols 20

    # 查看数据统计
    python scripts/realtime_signal_scanner.py --show-stats

配置方式:
    1. config/telegram.json (推荐)
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
from ats_core.logging import log, warn, error

# v7.2增强: 数据采集模块
try:
    from ats_core.data.trade_recorder import get_recorder
    from ats_core.data.analysis_db import get_analysis_db
    DATA_RECORDING_AVAILABLE = True
except ImportError as e:
    warn(f"数据采集模块不可用: {e}")
    DATA_RECORDING_AVAILABLE = False


def load_telegram_config():
    """
    加载Telegram配置

    优先级:
    1. config/telegram.json
    2. 环境变量

    Returns:
        (bot_token, chat_id, enabled) 或抛出异常
    """
    # 1. 尝试从config文件读取
    config_file = project_root / 'config' / 'telegram.json'
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            enabled = config.get('enabled', False)
            bot_token = config.get('bot_token', '').strip()
            chat_id = config.get('chat_id', '').strip()

            if bot_token and chat_id:
                log(f"✅ 从config/telegram.json加载配置 (enabled={enabled})")
                return bot_token, chat_id, enabled
        except Exception as e:
            warn(f"读取config/telegram.json失败: {e}")

    # 2. 从环境变量读取
    bot_token = (os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('ATS_TELEGRAM_BOT_TOKEN') or '').strip()
    chat_id = (os.getenv('TELEGRAM_CHAT_ID') or os.getenv('ATS_TELEGRAM_CHAT_ID') or '').strip()

    if bot_token and chat_id:
        log(f"✅ 从环境变量加载配置")
        return bot_token, chat_id, True

    # 3. 配置缺失
    raise RuntimeError(
        "Telegram配置未找到！\n"
        "请配置以下任一方式:\n"
        "1. config/telegram.json\n"
        "2. 环境变量: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
    )


class RealtimeSignalScanner:
    """实时信号扫描器（v7.2增强版）"""

    def __init__(
        self,
        send_telegram: bool = True,
        record_data: bool = True,
        verbose: bool = True
    ):
        """
        初始化扫描器

        Args:
            send_telegram: 是否发送Telegram通知
            record_data: 是否记录数据到数据库（v7.2特性）
            verbose: 是否显示详细输出
        """
        self.send_telegram = send_telegram
        self.record_data = record_data and DATA_RECORDING_AVAILABLE
        self.verbose = verbose
        self.initialized = False

        # Telegram配置
        self.telegram_enabled = False
        if send_telegram:
            try:
                self.bot_token, self.chat_id, self.telegram_enabled = load_telegram_config()
                if not self.telegram_enabled:
                    log("ℹ️  Telegram通知已在配置中禁用")
                    self.send_telegram = False
            except Exception as e:
                error(f"Telegram配置失败: {e}")
                warn("将禁用Telegram通知")
                self.send_telegram = False

        # v7.2: 数据记录器
        if self.record_data:
            try:
                self.recorder = get_recorder()
                self.analysis_db = get_analysis_db()
                log(f"✅ 数据采集已启用（TradeRecorder + AnalysisDB）")

                # 显示当前统计
                stats = self.recorder.get_statistics()
                log(f"   已记录信号: {stats['total_signals']}个")
                log(f"   通过闸门: {stats['gates_passed']}个 ({stats['gates_pass_rate']*100:.1f}%)")
            except Exception as e:
                error(f"数据采集初始化失败: {e}")
                warn("将禁用数据记录")
                self.record_data = False

        # 批量扫描器（使用优化版本）
        self.scanner = None

    async def initialize(self):
        """初始化扫描器"""
        if self.initialized:
            return

        log("\n" + "=" * 60)
        log("🚀 初始化实时信号扫描器（v7.2增强版）")
        log("=" * 60)

        # 初始化批量扫描器
        self.scanner = OptimizedBatchScanner()
        await self.scanner.initialize()

        self.initialized = True
        log("=" * 60)
        log("✅ 扫描器初始化完成")
        log("=" * 60 + "\n")

    async def scan_once(self, max_symbols: int = None):
        """
        执行一次扫描

        Args:
            max_symbols: 最大扫描币种数（None=全部）

        Note:
            - batch_scan_optimized已经包含了统计报告生成和Telegram发送
            - 如果有信号，会自动发送扫描摘要到Telegram
            - 数据会自动写入数据库和Git仓库
        """
        if not self.initialized:
            await self.initialize()

        log("\n" + "=" * 60)
        log(f"📡 开始扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("=" * 60)

        # 执行批量扫描（包含所有v7.2功能）
        # batch_scan_optimized会自动：
        # 1. 生成统计报告
        # 2. 写入数据库
        # 3. 发送Telegram摘要（如果有信号）
        # 4. 提交到Git仓库
        scan_result = await self.scanner.scan(max_symbols=max_symbols)

        log("=" * 60)
        log(f"✅ 扫描完成")
        log("=" * 60 + "\n")

        return scan_result

    async def run_periodic(self, interval_seconds: int = 300):
        """
        定期扫描

        Args:
            interval_seconds: 扫描间隔（秒）
        """
        if not self.initialized:
            await self.initialize()

        log("\n" + "=" * 60)
        log("🔄 启动定期扫描模式")
        log("=" * 60)
        log(f"   扫描间隔: {interval_seconds}秒 ({interval_seconds/60:.1f}分钟)")
        log(f"   Telegram: {'启用' if self.send_telegram else '禁用'}")
        log(f"   数据记录: {'启用' if self.record_data else '禁用'}")
        log("=" * 60)

        while True:
            try:
                # 执行扫描
                await self.scan_once()

                # 等待下次扫描
                next_scan = datetime.now() + timedelta(seconds=interval_seconds)
                log(f"\n⏰ 下次扫描时间: {next_scan.strftime('%Y-%m-%d %H:%M:%S')}")
                log(f"   （{interval_seconds}秒后）\n")

                await asyncio.sleep(interval_seconds)

            except KeyboardInterrupt:
                log("\n⚠️ 收到中断信号，正在停止...")
                break
            except Exception as e:
                error(f"扫描出错: {e}")
                import traceback
                traceback.print_exc()
                log("⏳ 等待60秒后重试...\n")
                await asyncio.sleep(60)

        log("✅ 扫描器已停止")

    def show_statistics(self):
        """显示数据采集统计（v7.2特性）"""
        if not self.record_data:
            log("❌ 数据记录未启用")
            log("提示: 使用 --record-data 启用数据采集")
            return

        stats = self.recorder.get_statistics()

        log("\n" + "=" * 60)
        log("📊 数据采集统计")
        log("=" * 60)
        log(f"总信号数: {stats['total_signals']}")
        log(f"通过闸门: {stats['gates_passed']} ({stats['gates_pass_rate']*100:.1f}%)")
        log(f"平均confidence: {stats['avg_confidence']:.2f}")
        log(f"平均预测概率: {stats['avg_predicted_p']:.3f}")
        log(f"平均预测EV: {stats['avg_predicted_ev']:+.4f}")

        if stats['side_distribution']:
            log(f"\n多空分布:")
            for side, count in stats['side_distribution'].items():
                log(f"  {side}: {count}个")

        if stats['total_trades'] > 0:
            log(f"\n交易结果:")
            log(f"  总交易: {stats['total_trades']}")
            log(f"  胜场: {stats['wins']}")
            log(f"  胜率: {stats['winrate']*100:.1f}%")

        # 最近10个信号
        recent = self.recorder.get_recent_signals(limit=10)
        if recent:
            log(f"\n最近10个信号:")
            for sig in recent:
                timestamp = datetime.fromtimestamp(sig['timestamp'] / 1000).strftime('%m-%d %H:%M')
                gates = "✅" if sig['all_gates_passed'] else "❌"
                log(f"  {timestamp} {sig['symbol']:10s} {sig['side']:5s} conf={sig['confidence']:5.1f} P={sig['predicted_p']:.3f} {gates}")

        log("=" * 60 + "\n")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='实时信号扫描器（v7.2增强版 - 统一版本）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  单次扫描:
    python scripts/realtime_signal_scanner.py

  定期扫描（每5分钟）:
    python scripts/realtime_signal_scanner.py --interval 300

  测试模式（20个币种）:
    python scripts/realtime_signal_scanner.py --max-symbols 20

  查看数据统计:
    python scripts/realtime_signal_scanner.py --show-stats

  禁用Telegram:
    python scripts/realtime_signal_scanner.py --no-telegram

  禁用数据记录:
    python scripts/realtime_signal_scanner.py --no-record
        """
    )

    parser.add_argument('--interval', type=int, default=None,
                        help='定期扫描间隔(秒), 不指定则单次扫描')
    parser.add_argument('--max-symbols', type=int, default=None,
                        help='最大扫描币种数（测试用）')
    parser.add_argument('--no-telegram', action='store_true',
                        help='禁用Telegram通知')
    parser.add_argument('--no-record', action='store_true',
                        help='禁用数据记录（v7.2特性）')
    parser.add_argument('--show-stats', action='store_true',
                        help='显示数据统计并退出')
    parser.add_argument('--verbose', action='store_true', default=True,
                        help='显示详细输出（默认启用）')

    args = parser.parse_args()

    # 如果只是查看统计
    if args.show_stats:
        scanner = RealtimeSignalScanner(record_data=True)
        scanner.show_statistics()
        return

    # 创建扫描器
    scanner = RealtimeSignalScanner(
        send_telegram=not args.no_telegram,
        record_data=not args.no_record,
        verbose=args.verbose
    )

    # 设置信号处理
    def signal_handler(sig, frame):
        log("\n⚠️ 收到中断信号，正在停止...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 执行扫描
    if args.interval:
        # 定期扫描
        await scanner.run_periodic(interval_seconds=args.interval)
    else:
        # 单次扫描
        await scanner.scan_once(max_symbols=args.max_symbols)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n✅ 程序已停止")
    except Exception as e:
        error(f"程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
