#!/usr/bin/env python3
# coding: utf-8
"""
完整流程回测工具

基于候选池进行完整的workflow回测：
1. 使用预定义的币种池（模拟候选池）
2. 每小时对所有币种运行analyze_symbol
3. 应用Prime/Watch发布标准
4. 使用实际的止盈止损策略
5. 模拟完整的交易流程

用法：
    python3 tools/run_full_backtest.py --days 7
    python3 tools/run_full_backtest.py --days 7 --symbols BTCUSDT ETHUSDT
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_backtest import BacktestEngine, BacktestDataLoader, calculate_metrics, generate_report, save_report
from ats_backtest.report import print_full_report


# 默认币种池（模拟Base + Overlay）
DEFAULT_SYMBOLS = [
    # 主流币（Base Pool核心）
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',

    # 大市值山寨币
    'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'MATICUSDT', 'LINKUSDT',
    'DOTUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'ETCUSDT',

    # 热门山寨币（可能出现在Overlay）
    'ARBUSDT', 'OPUSDT', 'APTUSDT', 'SUIUSDT', 'INJUSDT',
    'TIAUSDT', 'SEIUSDT', 'WLDUSDT', 'RNDRUSDT', 'FETUSDT',

    # MEME币
    '1000PEPEUSDT', 'SHIBUSDT', 'FLOKIUSDT', 'BONKUSDT',

    # AI概念
    'AGIXUSDT', 'OCEANUSDT',
]


class FullWorkflowBacktest:
    """
    完整工作流回测

    模拟真实的系统运行：
    - 每小时扫描候选池
    - 运行analyze_symbol分析
    - 应用发布标准
    - 模拟交易执行
    """

    def __init__(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        scan_interval_hours: int = 1,
        initial_capital: float = 10000,
        position_size_pct: float = 0.02,
        max_open_trades: int = 5,
        ttl_hours: int = 8,
    ):
        self.symbols = symbols
        self.start_time = start_time
        self.end_time = end_time
        self.scan_interval_hours = scan_interval_hours
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.max_open_trades = max_open_trades
        self.ttl_hours = ttl_hours

        # 统计
        self.total_scans = 0
        self.total_analyzed = 0
        self.total_signals_generated = 0
        self.total_prime_signals = 0
        self.total_watch_signals = 0

        # 数据加载器
        self.data_loader = BacktestDataLoader()

    def run(self):
        """运行完整回测"""
        print()
        print("=" * 70)
        print("  完整工作流回测")
        print("=" * 70)
        print(f"📅 时间范围: {self.start_time.date()} 到 {self.end_time.date()}")
        print(f"💰 初始资金: ${self.initial_capital:,.0f}")
        print(f"🔄 扫描间隔: {self.scan_interval_hours}小时")
        print(f"📊 币种池: {len(self.symbols)}个币种")
        print(f"⚙️  仓位: {self.position_size_pct*100:.1f}% | 最大持仓: {self.max_open_trades}")
        print()

        # 第1步：生成历史信号
        print("🔍 Step 1: 生成历史信号")
        print("-" * 70)
        signals = self._generate_historical_signals()

        if not signals:
            print("\n⚠️  未生成任何信号，回测终止")
            return None

        print(f"\n✅ 共生成 {len(signals)} 个信号")
        print(f"   ⭐ Prime: {self.total_prime_signals}")
        print(f"   👀 Watch: {self.total_watch_signals}")
        print()

        # 第2步：加载价格数据
        print("📈 Step 2: 加载价格数据")
        print("-" * 70)

        # 提取需要的币种
        symbols_needed = list(set(s['symbol'] for s in signals))
        price_data = self.data_loader.load_price_data(
            symbols=symbols_needed,
            start_time=self.start_time,
            end_time=self.end_time,
            interval='1h',
            use_cache=True
        )

        if not price_data:
            print("\n⚠️  未能加载价格数据，回测终止")
            return None

        print(f"\n✅ 已加载 {len(price_data)} 个币种的价格数据")
        print()

        # 第3步：运行回测引擎
        print("🚀 Step 3: 运行交易模拟")
        print("-" * 70)

        engine = BacktestEngine(
            start_time=self.start_time,
            end_time=self.end_time,
            initial_capital=self.initial_capital,
            position_size_pct=self.position_size_pct,
            max_open_trades=self.max_open_trades,
            ttl_hours=self.ttl_hours
        )

        result = engine.run_from_signals(signals, price_data)
        trades = result['trades']
        equity_curve = result['equity_curve']

        print(f"\n✅ 回测完成，共模拟 {len(trades)} 笔交易")
        print()

        # 第4步：计算指标
        print("📊 Step 4: 计算性能指标")
        print("-" * 70)
        metrics = calculate_metrics(trades, equity_curve, self.initial_capital)
        print("✅ 指标计算完成")
        print()

        # 第5步：生成报告
        print("📄 Step 5: 生成回测报告")
        print("-" * 70)

        config = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'symbols': self.symbols,
            'scan_interval_hours': self.scan_interval_hours,
            'initial_capital': self.initial_capital,
            'position_size_pct': self.position_size_pct,
            'max_open_trades': self.max_open_trades,
            'ttl_hours': self.ttl_hours,
            'total_scans': self.total_scans,
            'total_analyzed': self.total_analyzed,
            'total_signals_generated': self.total_signals_generated,
            'prime_signals': self.total_prime_signals,
            'watch_signals': self.total_watch_signals,
        }

        report = generate_report(trades, metrics, config, include_trades=True)

        # 保存报告
        report_path = save_report(report)
        print(f"✅ 报告已保存: {report_path}")
        print()

        # 显示完整报告
        print_full_report(trades, metrics, equity_curve)

        # 显示扫描统计
        self._print_scan_statistics()

        return {
            'trades': trades,
            'metrics': metrics,
            'signals': signals,
            'equity_curve': equity_curve,
            'report_path': report_path
        }

    def _generate_historical_signals(self) -> List[Dict]:
        """
        生成历史信号

        通过逐小时扫描候选池，运行analyze_symbol生成信号
        """
        signals = []

        current_time = self.start_time
        scan_count = 0

        while current_time <= self.end_time:
            scan_count += 1
            self.total_scans += 1

            if scan_count % 24 == 1:  # 每天显示一次进度
                print(f"⏰ 扫描时间点: {current_time.strftime('%Y-%m-%d %H:%M')}")

            # 对每个币种运行分析
            for symbol in self.symbols:
                try:
                    self.total_analyzed += 1

                    # 运行分析（这里会调用真实的analyze_symbol）
                    result = analyze_symbol(
                        symbol=symbol,
                        timestamp=current_time,
                        check_15m=False  # 简化，不检查15分钟确认
                    )

                    if not result:
                        continue

                    # 检查是否生成了信号
                    if result.get('should_publish'):
                        self.total_signals_generated += 1

                        # 判断Prime还是Watch
                        is_prime = result.get('is_prime', False)
                        if is_prime:
                            self.total_prime_signals += 1
                        else:
                            self.total_watch_signals += 1

                        # 提取信号信息
                        signal = {
                            'symbol': symbol,
                            'timestamp': current_time,
                            'entry_time': current_time,
                            'side': result['side'],
                            'probability': result['probability'],
                            'scores': result['scores'],
                            'is_prime': is_prime,

                            # 止盈止损（从pricing提取）
                            'entry_price': result['pricing']['entry_mid'],
                            'current_price': result['current_price'],
                            'stop_loss': result['pricing']['sl'],
                            'take_profit_1': result['pricing']['tp1'],
                            'tp1': result['pricing']['tp1'],
                            'take_profit_2': result['pricing']['tp2'],
                            'tp2': result['pricing']['tp2'],
                        }

                        signals.append(signal)

                        emoji = "⭐" if is_prime else "👀"
                        if self.total_signals_generated <= 10 or self.total_signals_generated % 10 == 0:
                            print(f"  {emoji} 信号#{self.total_signals_generated}: {symbol} {result['side'].upper()} "
                                  f"@ {result['current_price']:.4f} (Prob: {result['probability']:.1%})")

                except Exception as e:
                    # 分析失败，跳过（可能是数据不足等）
                    if 'DEBUG' in os.environ:
                        print(f"  ⚠️  {symbol} 分析失败: {str(e)[:50]}")
                    continue

            # 前进到下一个扫描时间点
            current_time += timedelta(hours=self.scan_interval_hours)

        return signals

    def _print_scan_statistics(self):
        """打印扫描统计"""
        print()
        print("=" * 70)
        print("  扫描统计")
        print("=" * 70)
        print(f"总扫描次数: {self.total_scans}")
        print(f"总分析次数: {self.total_analyzed}")
        print(f"生成信号数: {self.total_signals_generated}")
        print(f"  ⭐ Prime: {self.total_prime_signals} ({self.total_prime_signals/max(1,self.total_signals_generated)*100:.1f}%)")
        print(f"  👀 Watch: {self.total_watch_signals} ({self.total_watch_signals/max(1,self.total_signals_generated)*100:.1f}%)")
        print(f"信号生成率: {self.total_signals_generated/max(1,self.total_analyzed)*100:.2f}%")
        print("=" * 70)
        print()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='完整工作流回测',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 时间范围
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--days', type=int, help='回测最近N天（默认7天）')
    time_group.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')

    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--symbols', nargs='+', help='指定币种列表（默认使用预设池）')
    parser.add_argument('--interval', type=int, default=1, help='扫描间隔（小时，默认1）')

    # 交易参数
    parser.add_argument('--capital', type=float, default=10000, help='初始资金（默认10000）')
    parser.add_argument('--position-size', type=float, default=0.02, help='仓位比例（默认0.02=2%）')
    parser.add_argument('--max-trades', type=int, default=5, help='最大持仓数（默认5）')
    parser.add_argument('--ttl', type=int, default=8, help='信号TTL（小时，默认8）')

    args = parser.parse_args()

    # 处理时间范围
    if args.start:
        start_time = datetime.strptime(args.start, '%Y-%m-%d')
        if args.end:
            end_time = datetime.strptime(args.end, '%Y-%m-%d')
        else:
            end_time = datetime.utcnow()
    else:
        days = args.days or 7
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

    # 处理币种列表
    symbols = args.symbols if args.symbols else DEFAULT_SYMBOLS

    # 创建回测引擎
    backtest = FullWorkflowBacktest(
        symbols=symbols,
        start_time=start_time,
        end_time=end_time,
        scan_interval_hours=args.interval,
        initial_capital=args.capital,
        position_size_pct=args.position_size,
        max_open_trades=args.max_trades,
        ttl_hours=args.ttl
    )

    # 运行回测
    result = backtest.run()

    if result:
        print()
        print("=" * 70)
        print("  回测完成！")
        print("=" * 70)
        print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  回测中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
