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
from ats_core.outputs.telegram_fmt import render_trade_v72
from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements
from ats_core.publishing.anti_jitter import AntiJitter
from ats_core.config.anti_jitter_config import get_config

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


def telegram_send_wrapper(message: str, bot_token: str, chat_id: str):
    """Telegram发送包装器（发送单独的交易信号）"""
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()


class RealtimeSignalScanner:
    """实时信号扫描器（v7.2增强版）"""

    def __init__(
        self,
        min_score: int = 35,
        watch_score: int = 30,
        send_telegram: bool = True,
        enable_watch: bool = True,
        record_data: bool = True,
        verbose: bool = True
    ):
        """
        初始化扫描器

        Args:
            min_score: 最低confidence阈值（v7.2 PRIME信号）
            watch_score: WATCH信号阈值（蓄势待发）
            send_telegram: 是否发送Telegram通知
            enable_watch: 是否启用WATCH信号（蓄势待发）
            record_data: 是否记录数据到数据库（v7.2特性）
            verbose: 是否显示详细输出
        """
        self.min_score = min_score
        self.watch_score = watch_score
        self.send_telegram = send_telegram
        self.enable_watch = enable_watch
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

        # 防抖动系统（AntiJitter）
        if send_telegram:
            anti_jitter_config = get_config("1h")  # 1小时K线，1小时冷却期
            self.anti_jitter = AntiJitter(config=anti_jitter_config)
            log(f"✅ 防抖动系统已启用: {anti_jitter_config.cooldown_seconds}秒冷却期")

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
        """
        if not self.initialized:
            await self.initialize()

        log("\n" + "=" * 60)
        log(f"📡 开始v7.2扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("=" * 60)

        # 执行批量扫描
        scan_result = await self.scanner.scan(max_symbols=max_symbols)

        # 提取信号列表
        results = scan_result.get('results', [])

        if not results:
            warn("扫描无结果")
            return

        # v7.2增强：对每个信号应用v7.2分析
        v72_results = []
        for result in results:
            try:
                # 应用v7.2增强
                v72_result = self._apply_v72_enhancements(result)
                v72_results.append(v72_result)

                # 记录到数据库
                if self.record_data:
                    self.recorder.record_signal_snapshot(v72_result)
                    self.analysis_db.write_complete_signal(v72_result)

            except Exception as e:
                error(f"v7.2增强失败 {result.get('symbol')}: {e}")
                continue

        # 过滤Prime信号（四道闸门 + AntiJitter）
        prime_signals = self._filter_prime_signals_v72(v72_results)

        # 过滤WATCH信号（蓄势待发）
        watch_signals = []
        if self.enable_watch:
            watch_signals = self._filter_watch_signals_v72(v72_results, prime_signals)

        # 统计
        log(f"\n📊 扫描统计:")
        log(f"   总币种数: {len(results)}")
        log(f"   v7.2增强: {len(v72_results)}")
        log(f"   Prime信号: {len(prime_signals)}")
        if prime_signals:
            log(f"   Prime列表: {', '.join([s['symbol'] for s in prime_signals])}")
        if watch_signals:
            log(f"   WATCH信号: {len(watch_signals)}")
            log(f"   WATCH列表: {', '.join([s['symbol'] for s in watch_signals])}")

        # 发送Telegram
        if self.send_telegram and prime_signals:
            await self._send_signals_to_telegram_v72(prime_signals, is_watch=False)

        if self.send_telegram and self.enable_watch and watch_signals:
            await self._send_signals_to_telegram_v72(watch_signals, is_watch=True)

        log("=" * 60 + "\n")

    def _apply_v72_enhancements(self, result: dict) -> dict:
        """应用v7.2增强分析"""
        symbol = result.get('symbol')
        klines = result.get('klines', [])
        oi_data = result.get('oi_data', [])
        cvd_series = result.get('cvd_series', [])
        atr = result.get('atr', 0)

        if len(klines) >= 100 and len(cvd_series) >= 10:
            try:
                v72_enhanced = analyze_with_v72_enhancements(
                    original_result=result,
                    symbol=symbol,
                    klines=klines,
                    oi_data=oi_data,
                    cvd_series=cvd_series,
                    atr_now=atr
                )
                return v72_enhanced
            except Exception as e:
                warn(f"v7.2增强失败 {symbol}: {e}")
                return result
        else:
            return result

    def _filter_prime_signals_v72(self, results: list) -> list:
        """
        v7.2版本的Prime信号过滤

        过滤条件：
        1. v72_enhancements存在
        2. all_gates_passed = True（四道闸门全部通过）
        3. confidence_v72 >= min_score
        4. 通过AntiJitter防抖动检查
        """
        prime_signals = []

        for result in results:
            symbol = result.get('symbol')
            v72 = result.get('v72_enhancements', {})

            # 检查v7.2增强数据
            if not v72:
                continue

            # 检查四道闸门（关键！）
            all_gates_passed = v72.get('gates', {}).get('pass_all', False)
            if not all_gates_passed:
                continue

            # 检查confidence
            confidence = v72.get('confidence_v72', 0)
            if confidence < self.min_score:
                continue

            # AntiJitter防抖动检查
            if self.send_telegram:
                probability = v72.get('P_calibrated', 0.5)
                ev_net = v72.get('EV_net', 0)
                level, should_publish = self.anti_jitter.update(
                    symbol=symbol,
                    probability=probability,
                    ev=ev_net,
                    gates_passed=all_gates_passed
                )

                if not should_publish:
                    log(f"   ⏭️  跳过 {symbol} (防抖动)")
                    continue

            # 通过所有检查
            prime_signals.append(result)

        return prime_signals

    def _filter_watch_signals_v72(self, results: list, prime_signals: list) -> list:
        """
        v7.2版本的WATCH信号过滤（蓄势待发）

        过滤条件：
        1. v72_enhancements存在
        2. 不是Prime信号（已被Prime过滤）
        3. confidence_v72 >= watch_score (30-34之间)
        4. 四道闸门至少通过3个
        5. 通过AntiJitter WATCH级别检查

        Args:
            results: 所有v7.2增强后的信号
            prime_signals: 已过滤的Prime信号列表

        Returns:
            WATCH信号列表
        """
        watch_signals = []
        prime_symbols = {s['symbol'] for s in prime_signals}

        for result in results:
            symbol = result.get('symbol')

            # 跳过已经是Prime的信号
            if symbol in prime_symbols:
                continue

            v72 = result.get('v72_enhancements', {})
            if not v72:
                continue

            # 检查confidence（在watch_score和min_score之间）
            confidence = v72.get('confidence_v72', 0)
            if confidence < self.watch_score or confidence >= self.min_score:
                continue

            # 检查四道闸门（至少通过3个）
            gate_results = v72.get('gate_results', {})
            gates_passed_count = sum(1 for g in gate_results.values() if g.get('passed', False))
            if gates_passed_count < 3:
                continue

            # AntiJitter WATCH级别检查
            if self.send_telegram:
                probability = v72.get('P_calibrated', 0.5)
                ev_net = v72.get('EV_net', 0)
                level, should_publish = self.anti_jitter.update(
                    symbol=symbol,
                    probability=probability,
                    ev=ev_net,
                    gates_passed=False  # WATCH级别不要求全部通过
                )

                # WATCH级别应该在0.43-0.50之间
                if level != 'WATCH':
                    continue

            # 通过所有检查
            watch_signals.append(result)

        return watch_signals

    async def _send_signals_to_telegram_v72(self, signals: list, is_watch: bool = False):
        """
        发送v7.2格式的信号到Telegram

        Args:
            signals: 信号列表
            is_watch: 是否为WATCH信号（观察信号）
        """
        signal_type = "WATCH观察" if is_watch else "Prime交易"
        log(f"\n📤 发送 {len(signals)} 个v7.2 {signal_type}信号到Telegram...")

        for i, signal in enumerate(signals, 1):
            try:
                # 使用v7.2消息格式（is_watch参数会改变消息头部）
                if is_watch:
                    from ats_core.outputs.telegram_fmt import render_signal_v72
                    message = render_signal_v72(signal, is_watch=True)
                else:
                    message = render_trade_v72(signal)

                # 发送
                telegram_send_wrapper(message, self.bot_token, self.chat_id)

                symbol = signal.get('symbol')
                confidence = signal.get('v72_enhancements', {}).get('confidence_v72', 0)
                F_v2 = signal.get('v72_enhancements', {}).get('F_v2', 0)

                log(f"   ✅ {i}/{len(signals)}: {symbol} (confidence={confidence:.1f}, F={F_v2:.0f})")

            except Exception as e:
                error(f"   ❌ 发送失败 {signal.get('symbol')}: {e}")

        log(f"✅ v7.2信号发送完成\n")

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
