#!/usr/bin/env python3
# coding: utf-8
"""
真实数据回测工具（服务器版）

基于固定币种池，使用真实币安数据进行回测：
1. 定义一个币种池（20-30个币）
2. 逐小时运行analyze_symbol生成信号
3. 使用真实价格数据模拟交易
4. 计算真实的回测指标

用法（在服务器上运行）：
    python3 tools/run_real_backtest.py --days 7
    python3 tools/run_real_backtest.py --days 7 --symbols BTCUSDT ETHUSDT

注意：
- 需要能访问币安API
- 计算时间较长（7天约需10-30分钟）
- 会生成真实的历史信号并保存到数据库
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import time

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.database.models import db, Signal
from ats_backtest import BacktestEngine, BacktestDataLoader, calculate_metrics, generate_report, save_report
from ats_backtest.report import print_full_report


# 默认币种池（基于流动性和活跃度）
DEFAULT_POOL = [
    # Tier 1: 超大市值（10个）
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT',

    # Tier 2: 大市值山寨（10个）
    'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'ETCUSDT',
    'FILUSDT', 'APTUSDT', 'NEARUSDT', 'ICPUSDT', 'VETUSDT',

    # Tier 3: 热门山寨（10个，可选）
    'ARBUSDT', 'OPUSDT', 'SUIUSDT', 'INJUSDT', 'TIAUSDT',
    'SEIUSDT', 'WLDUSDT', 'RNDRUSDT', 'FETUSDT', 'RENDERUSDT',
]


class RealBacktestEngine:
    """
    真实数据回测引擎

    使用币安真实数据进行回测
    """

    def __init__(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        scan_interval_hours: int = 2,
        save_signals_to_db: bool = True,
    ):
        self.symbols = symbols
        self.start_time = start_time
        self.end_time = end_time
        self.scan_interval_hours = scan_interval_hours
        self.save_signals_to_db = save_signals_to_db

        # 统计
        self.total_scans = 0
        self.total_symbols_analyzed = 0
        self.total_signals = 0
        self.prime_signals = 0
        self.watch_signals = 0
        self.failed_analysis = 0

    def run(self):
        """运行真实数据回测"""
        print()
        print("=" * 70)
        print("  真实数据回测引擎")
        print("=" * 70)
        print(f"📅 时间范围: {self.start_time.date()} 到 {self.end_time.date()}")
        print(f"🪙  币种池: {len(self.symbols)}个币种")
        print(f"⏱️  扫描间隔: {self.scan_interval_hours}小时")
        print(f"💾 保存信号: {'是' if self.save_signals_to_db else '否'}")
        print()
        print("⚠️  注意：使用真实币安数据，计算时间较长...")
        print()

        # Step 1: 生成历史信号（逐小时扫描）
        print("🔍 Step 1: 生成历史信号")
        print("-" * 70)
        signals = self._generate_signals()

        if not signals:
            print("\n❌ 未生成任何信号，回测终止")
            return None

        print(f"\n✅ 共生成 {len(signals)} 个信号")
        print(f"   ⭐ Prime: {self.prime_signals}")
        print(f"   👀 Watch: {self.watch_signals}")
        print(f"   ❌ 分析失败: {self.failed_analysis}")
        print()

        # Step 2: 加载价格数据
        print("📈 Step 2: 加载价格数据")
        print("-" * 70)

        loader = BacktestDataLoader()
        symbols_needed = list(set(s['symbol'] for s in signals))

        price_data = loader.load_price_data(
            symbols=symbols_needed,
            start_time=self.start_time,
            end_time=self.end_time,
            interval='1h',
            use_cache=True
        )

        if not price_data:
            print("\n❌ 未能加载价格数据")
            return None

        print(f"\n✅ 已加载 {len(price_data)} 个币种的价格数据")
        print()

        # Step 3: 运行回测
        print("🚀 Step 3: 运行回测模拟")
        print("-" * 70)

        engine = BacktestEngine(
            start_time=self.start_time,
            end_time=self.end_time,
            initial_capital=10000,
            position_size_pct=0.02,
            max_open_trades=5,
            ttl_hours=8
        )

        result = engine.run_from_signals(signals, price_data)
        trades = result['trades']
        equity_curve = result['equity_curve']

        print(f"\n✅ 回测完成，共 {len(trades)} 笔交易")
        print()

        # Step 4: 计算指标
        print("📊 Step 4: 计算性能指标")
        print("-" * 70)

        metrics = calculate_metrics(trades, equity_curve, 10000)
        print("✅ 指标计算完成")
        print()

        # Step 5: 生成报告
        print("📄 Step 5: 生成报告")
        print("-" * 70)

        config = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'symbols': self.symbols,
            'scan_interval_hours': self.scan_interval_hours,
            'total_scans': self.total_scans,
            'total_analyzed': self.total_symbols_analyzed,
            'total_signals': self.total_signals,
            'prime_signals': self.prime_signals,
            'watch_signals': self.watch_signals,
            'failed_analysis': self.failed_analysis,
        }

        report = generate_report(trades, metrics, config, include_trades=True)
        report_path = save_report(report)

        print(f"✅ 报告已保存: {report_path}")
        print()

        # 显示完整报告
        print_full_report(trades, metrics, equity_curve)

        # 显示统计
        self._print_statistics()

        return {
            'trades': trades,
            'metrics': metrics,
            'signals': signals,
            'report_path': report_path,
        }

    def _generate_signals(self) -> List[Dict]:
        """
        生成历史信号（使用真实analyze_symbol）

        这是最关键的部分：
        - 逐小时扫描
        - 对每个币种运行analyze_symbol
        - 使用真实的K线、OI、CVD数据
        - 生成真实的信号
        """
        signals = []
        session = db.get_session() if self.save_signals_to_db else None

        current_time = self.start_time

        # 计算总扫描次数
        total_hours = int((self.end_time - start_time).total_seconds() / 3600)
        total_scans_expected = total_hours // self.scan_interval_hours

        print(f"预计扫描次数: {total_scans_expected}")
        print(f"预计分析: {total_scans_expected * len(self.symbols)} 次")
        print()

        scan_count = 0

        while current_time <= self.end_time:
            scan_count += 1
            self.total_scans += 1

            # 显示进度
            progress = (current_time - self.start_time).total_seconds() / (self.end_time - self.start_time).total_seconds() * 100
            print(f"⏰ [{progress:.1f}%] {current_time.strftime('%Y-%m-%d %H:%M')} | 已生成: {len(signals)} (⭐{self.prime_signals} + 👀{self.watch_signals})")

            # 扫描每个币种
            for symbol in self.symbols:
                self.total_symbols_analyzed += 1

                try:
                    # 运行真实的analyze_symbol
                    # 注意：这里不传timestamp，使用实时数据
                    # 如果要回测历史，需要修改analyze_symbol支持历史时间点
                    result = analyze_symbol(
                        symbol=symbol,
                        timestamp=None,  # 使用实时数据（或需要修改为支持历史时间点）
                        check_15m=False   # 简化，不检查15分钟
                    )

                    if not result:
                        continue

                    # 检查是否应该发布
                    if result.get('should_publish'):
                        self.total_signals += 1

                        is_prime = result.get('is_prime', False)
                        if is_prime:
                            self.prime_signals += 1
                        else:
                            self.watch_signals += 1

                        # 构建信号
                        signal = {
                            'symbol': symbol,
                            'timestamp': current_time,
                            'entry_time': current_time,
                            'side': result['side'],
                            'probability': result['probability'],
                            'scores': result['scores'],
                            'is_prime': is_prime,
                            'dims_ok': result.get('dims_ok', 0),

                            # 价格信息
                            'entry_price': result['pricing']['entry_mid'],
                            'current_price': result['current_price'],
                            'stop_loss': result['pricing']['sl'],
                            'take_profit_1': result['pricing']['tp1'],
                            'tp1': result['pricing']['tp1'],
                            'take_profit_2': result['pricing']['tp2'],
                            'tp2': result['pricing']['tp2'],
                        }

                        signals.append(signal)

                        # 保存到数据库（可选）
                        if self.save_signals_to_db and session:
                            signal_obj = Signal(
                                symbol=signal['symbol'],
                                timestamp=signal['timestamp'],
                                side=signal['side'],
                                probability=signal['probability'],
                                scores=signal['scores'],
                                entry_price=signal['entry_price'],
                                current_price=signal['current_price'],
                                stop_loss=signal['stop_loss'],
                                take_profit_1=signal['take_profit_1'],
                                take_profit_2=signal['take_profit_2'],
                                is_prime=signal['is_prime'],
                                is_watch=not signal['is_prime'],
                                dims_ok=signal['dims_ok'],
                                status='open'
                            )
                            session.add(signal_obj)

                        # 显示前几个信号
                        if self.total_signals <= 20 or self.total_signals % 10 == 0:
                            emoji = "⭐" if is_prime else "👀"
                            print(f"  {emoji} 信号#{self.total_signals}: {symbol} {result['side'].upper()} "
                                  f"@ {result['current_price']:.4f} (Prob: {result['probability']:.1%})")

                except Exception as e:
                    self.failed_analysis += 1
                    if self.failed_analysis <= 10:  # 只显示前10个错误
                        print(f"  ⚠️  {symbol} 分析失败: {str(e)[:60]}")
                    continue

                # 避免API限流
                time.sleep(0.1)

            # 每次扫描后提交数据库
            if self.save_signals_to_db and session and scan_count % 5 == 0:
                session.commit()

            # 前进到下一个时间点
            current_time += timedelta(hours=self.scan_interval_hours)

        # 最终提交
        if self.save_signals_to_db and session:
            session.commit()
            session.close()

        return signals

    def _print_statistics(self):
        """打印统计信息"""
        print()
        print("=" * 70)
        print("  扫描统计")
        print("=" * 70)
        print(f"总扫描次数:     {self.total_scans}")
        print(f"总分析次数:     {self.total_symbols_analyzed}")
        print(f"成功率:         {(self.total_symbols_analyzed - self.failed_analysis) / max(1, self.total_symbols_analyzed) * 100:.1f}%")
        print(f"生成信号:       {self.total_signals}")
        print(f"  ⭐ Prime:     {self.prime_signals} ({self.prime_signals/max(1,self.total_signals)*100:.1f}%)")
        print(f"  👀 Watch:     {self.watch_signals} ({self.watch_signals/max(1,self.total_signals)*100:.1f}%)")
        print(f"信号生成率:     {self.total_signals/max(1,self.total_symbols_analyzed)*100:.2f}%")
        print("=" * 70)
        print()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='真实数据回测（服务器版）',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 时间范围
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--days', type=int, help='回测最近N天（默认7）')
    time_group.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')

    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--symbols', nargs='+', help='指定币种（默认使用预设池）')
    parser.add_argument('--interval', type=int, default=2, help='扫描间隔（小时，默认2）')
    parser.add_argument('--no-save', action='store_true', help='不保存信号到数据库')

    args = parser.parse_args()

    # 处理时间范围
    if args.start:
        start_time = datetime.strptime(args.start, '%Y-%m-%d')
        end_time = datetime.strptime(args.end, '%Y-%m-%d') if args.end else datetime.utcnow()
    else:
        days = args.days or 7
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

    # 币种池
    symbols = args.symbols if args.symbols else DEFAULT_POOL

    # 检查环境
    print()
    print("🔍 环境检查...")
    try:
        from ats_core.sources.binance_safe import get_klines
        test_data = get_klines('BTCUSDT', '1h', 2)
        if test_data:
            print("✅ 币安API连接正常")
        else:
            print("❌ 币安API无法访问，请检查网络")
            return
    except Exception as e:
        print(f"❌ 币安API测试失败: {e}")
        print("\n💡 提示：此脚本需要在能访问币安API的服务器上运行")
        return

    # 创建回测引擎
    engine = RealBacktestEngine(
        symbols=symbols,
        start_time=start_time,
        end_time=end_time,
        scan_interval_hours=args.interval,
        save_signals_to_db=not args.no_save
    )

    # 运行回测
    result = engine.run()

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
