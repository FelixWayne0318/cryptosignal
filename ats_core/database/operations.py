# coding: utf-8
"""
数据库操作封装

提供所有数据库CRUD操作的高级接口
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc
from .models import Signal, DailyMetrics, db


# ========== 信号操作 ==========

def save_signal(analysis_result: Dict) -> int:
    """
    保存分析信号到数据库

    Args:
        analysis_result: analyze_symbol() 返回的结果字典

    Returns:
        signal_id: 新创建的信号ID
    """
    session = db.get_session()
    try:
        pricing = analysis_result.get('pricing', {}) or {}
        publish = analysis_result.get('publish', {}) or {}

        # 计算入场价格（取entry_lo和entry_hi的中点）
        entry_price = None
        if pricing:
            entry_lo = pricing.get('entry_lo')
            entry_hi = pricing.get('entry_hi')
            if entry_lo is not None and entry_hi is not None:
                entry_price = (entry_lo + entry_hi) / 2

        signal = Signal(
            symbol=analysis_result['symbol'],
            timestamp=datetime.utcnow(),
            side=analysis_result['side'],
            probability=analysis_result.get('probability', 0.5),

            # 七维分数
            scores=analysis_result.get('scores', {}),
            scores_meta=analysis_result.get('scores_meta', {}),

            # F调节器
            f_score=analysis_result.get('F_score'),
            f_adjustment=analysis_result.get('F_adjustment'),

            # 加权分数（统一±100系统）
            weighted_score=analysis_result.get('weighted_score', 0),
            base_probability=analysis_result.get('P_base'),

            # 给价计划（从pricing中正确提取）
            entry_price=entry_price,
            stop_loss=pricing.get('sl'),
            take_profit_1=pricing.get('tp1'),
            take_profit_2=pricing.get('tp2'),

            # 当前价格（从analyze_symbol结果中获取最新价）
            current_price=analysis_result.get('price'),

            # 发布状态
            is_prime=publish.get('prime', False),
            is_watch=publish.get('watch', False),
            dims_ok=publish.get('dims_ok', 0),

            # 15分钟微确认
            m15_ok=analysis_result.get('m15_ok', False),
        )

        session.add(signal)
        session.commit()

        signal_id = signal.id
        print(f"✅ Signal saved: #{signal_id} {signal.symbol} {signal.side.upper()} {signal.probability:.1%}")
        return signal_id

    except Exception as e:
        session.rollback()
        print(f"❌ Failed to save signal: {e}")
        raise
    finally:
        session.close()


def update_signal_exit(
    signal_id: int,
    exit_price: float,
    exit_reason: str = 'manual',
    pnl_percent: Optional[float] = None,
    pnl_usdt: Optional[float] = None,
    notes: Optional[str] = None
) -> bool:
    """
    更新信号的退出信息

    Args:
        signal_id: 信号ID
        exit_price: 退出价格
        exit_reason: 退出原因 ('tp1', 'tp2', 'sl', 'expired', 'manual')
        pnl_percent: 盈亏百分比（可选，会自动计算）
        pnl_usdt: 盈亏金额（可选）
        notes: 备注

    Returns:
        是否更新成功
    """
    session = db.get_session()
    try:
        signal = session.query(Signal).filter_by(id=signal_id).first()

        if not signal:
            print(f"⚠️  Signal not found: ID {signal_id}")
            return False

        # 如果信号已关闭，警告
        if signal.status != 'open':
            print(f"⚠️  Signal #{signal_id} is already {signal.status}")
            return False

        # 计算盈亏（如果未提供）
        if pnl_percent is None and signal.entry_price:
            if signal.side == 'long':
                pnl_percent = (exit_price - signal.entry_price) / signal.entry_price * 100
            else:  # short
                pnl_percent = (signal.entry_price - exit_price) / signal.entry_price * 100

        # 计算持仓时间
        holding_hours = (datetime.utcnow() - signal.timestamp).total_seconds() / 3600

        # 更新字段
        signal.exit_price = exit_price
        signal.exit_time = datetime.utcnow()
        signal.exit_reason = exit_reason
        signal.pnl_percent = pnl_percent
        signal.pnl_usdt = pnl_usdt
        signal.holding_hours = holding_hours
        signal.status = 'closed'

        if notes:
            signal.notes = notes

        session.commit()

        emoji = "✅" if pnl_percent and pnl_percent > 0 else "❌"
        print(f"{emoji} Signal #{signal_id} closed: {signal.symbol} {signal.side.upper()}, "
              f"PnL: {pnl_percent:+.2f}%, Reason: {exit_reason}")

        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Failed to update signal: {e}")
        return False
    finally:
        session.close()


def get_open_signals(symbols: Optional[List[str]] = None) -> List[Signal]:
    """
    获取所有未平仓的信号

    Args:
        symbols: 可选的币种过滤列表

    Returns:
        未平仓信号列表
    """
    session = db.get_session()
    try:
        query = session.query(Signal).filter_by(status='open')

        if symbols:
            query = query.filter(Signal.symbol.in_(symbols))

        signals = query.order_by(desc(Signal.timestamp)).all()
        return signals
    finally:
        session.close()


def get_recent_signals(
    limit: int = 100,
    symbols: Optional[List[str]] = None,
    side: Optional[str] = None,
    is_prime: Optional[bool] = None,
    days: Optional[int] = None
) -> List[Signal]:
    """
    获取最近的信号

    Args:
        limit: 最多返回多少条
        symbols: 币种过滤
        side: 方向过滤 ('long' or 'short')
        is_prime: 是否只看正式信号
        days: 最近多少天

    Returns:
        信号列表
    """
    session = db.get_session()
    try:
        query = session.query(Signal)

        # 时间过滤
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Signal.timestamp >= cutoff)

        # 币种过滤
        if symbols:
            query = query.filter(Signal.symbol.in_(symbols))

        # 方向过滤
        if side:
            query = query.filter_by(side=side)

        # 正式信号过滤
        if is_prime is not None:
            query = query.filter_by(is_prime=is_prime)

        signals = query.order_by(desc(Signal.timestamp)).limit(limit).all()
        return signals
    finally:
        session.close()


# ========== 每日指标操作 ==========

def calculate_daily_metrics(date: Optional[datetime] = None) -> bool:
    """
    计算并保存某一天的性能指标

    Args:
        date: 计算哪一天的指标（默认今天）

    Returns:
        是否成功
    """
    if date is None:
        date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)

    session = db.get_session()
    try:
        # 查询当天的所有信号
        start = date
        end = date + timedelta(days=1)

        signals = session.query(Signal).filter(
            and_(
                Signal.timestamp >= start,
                Signal.timestamp < end
            )
        ).all()

        if not signals:
            print(f"⚠️  No signals found for {date.date()}")
            return False

        # ===== 统计信号 =====
        total_signals = len(signals)
        prime_signals = sum(1 for s in signals if s.is_prime)
        watch_signals = sum(1 for s in signals if s.is_watch)
        long_signals = sum(1 for s in signals if s.side == 'long')
        short_signals = sum(1 for s in signals if s.side == 'short')

        # ===== 统计已平仓交易 =====
        closed = [s for s in signals if s.status == 'closed' and s.pnl_percent is not None]
        closed_trades = len(closed)

        wins = [s for s in closed if s.pnl_percent > 0]
        losses = [s for s in closed if s.pnl_percent <= 0]
        expired = [s for s in signals if s.status == 'expired']

        winning_trades = len(wins)
        losing_trades = len(losses)
        expired_trades = len(expired)

        # ===== 绩效指标 =====
        win_rate = winning_trades / closed_trades if closed_trades > 0 else None

        avg_win = sum(s.pnl_percent for s in wins) / len(wins) if wins else None
        avg_loss = sum(s.pnl_percent for s in losses) / len(losses) if losses else None

        avg_win_usdt = sum(s.pnl_usdt for s in wins if s.pnl_usdt) / len([s for s in wins if s.pnl_usdt]) if wins else None
        avg_loss_usdt = sum(s.pnl_usdt for s in losses if s.pnl_usdt) / len([s for s in losses if s.pnl_usdt]) if losses else None

        total_pnl = sum(s.pnl_percent for s in closed) if closed else 0.0
        total_pnl_usdt = sum(s.pnl_usdt for s in closed if s.pnl_usdt) if closed else 0.0

        profit_factor = abs(sum(s.pnl_usdt for s in wins if s.pnl_usdt) / sum(s.pnl_usdt for s in losses if s.pnl_usdt)) \
                        if losses and sum(s.pnl_usdt for s in losses if s.pnl_usdt) != 0 else None

        # 平均持仓时间
        holding_times = [s.holding_hours for s in closed if s.holding_hours]
        avg_holding_hours = sum(holding_times) / len(holding_times) if holding_times else None

        # 最佳/最差交易
        best_trade = max(closed, key=lambda s: s.pnl_percent) if closed else None
        worst_trade = min(closed, key=lambda s: s.pnl_percent) if closed else None

        # ===== 分维度统计 =====
        dimension_stats = {}
        for dim in ['T', 'M', 'C', 'S', 'V', 'O', 'E']:
            scores = [s.scores.get(dim, 50) for s in signals if s.scores and dim in s.scores]
            if scores:
                dimension_stats[dim] = {
                    'avg': sum(scores) / len(scores),
                    'min': min(scores),
                    'max': max(scores),
                    'std': (sum((x - sum(scores)/len(scores))**2 for x in scores) / len(scores)) ** 0.5
                }

        # ===== 分方向统计 =====
        direction_stats = {}
        for side in ['long', 'short']:
            side_signals = [s for s in closed if s.side == side]
            if side_signals:
                side_wins = [s for s in side_signals if s.pnl_percent > 0]
                direction_stats[side] = {
                    'count': len(side_signals),
                    'win_count': len(side_wins),
                    'win_rate': len(side_wins) / len(side_signals),
                    'avg_pnl': sum(s.pnl_percent for s in side_signals) / len(side_signals)
                }

        # ===== 保存或更新指标 =====
        metrics = session.query(DailyMetrics).filter_by(date=start).first()
        if not metrics:
            metrics = DailyMetrics(date=start)

        metrics.total_signals = total_signals
        metrics.prime_signals = prime_signals
        metrics.watch_signals = watch_signals
        metrics.long_signals = long_signals
        metrics.short_signals = short_signals

        metrics.closed_trades = closed_trades
        metrics.winning_trades = winning_trades
        metrics.losing_trades = losing_trades
        metrics.expired_trades = expired_trades

        metrics.win_rate = win_rate
        metrics.avg_win = avg_win
        metrics.avg_loss = avg_loss
        metrics.avg_win_usdt = avg_win_usdt
        metrics.avg_loss_usdt = avg_loss_usdt
        metrics.profit_factor = profit_factor

        metrics.total_pnl = total_pnl
        metrics.total_pnl_usdt = total_pnl_usdt

        metrics.avg_holding_hours = avg_holding_hours

        if best_trade:
            metrics.best_trade_pnl = best_trade.pnl_percent
            metrics.best_trade_symbol = best_trade.symbol
        if worst_trade:
            metrics.worst_trade_pnl = worst_trade.pnl_percent
            metrics.worst_trade_symbol = worst_trade.symbol

        metrics.dimension_stats = dimension_stats
        metrics.direction_stats = direction_stats

        session.add(metrics)
        session.commit()

        print(f"✅ Daily metrics calculated for {date.date()}")
        print(f"   Signals: {total_signals} (Prime: {prime_signals}, Watch: {watch_signals})")
        if win_rate is not None:
            print(f"   Closed: {closed_trades}, Win Rate: {win_rate*100:.1f}%, Total PnL: {total_pnl:+.2f}%")
        else:
            print(f"   No closed trades yet")

        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Failed to calculate metrics: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def get_performance_summary(days: int = 30) -> Dict:
    """
    获取性能摘要（最近N天）

    Args:
        days: 统计最近多少天

    Returns:
        性能摘要字典
    """
    session = db.get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)

        # 查询所有已平仓的信号
        closed_signals = session.query(Signal).filter(
            and_(
                Signal.timestamp >= cutoff,
                Signal.status == 'closed',
                Signal.pnl_percent.isnot(None)
            )
        ).all()

        if not closed_signals:
            return {
                'error': f'No closed trades in the last {days} days',
                'total_trades': 0
            }

        # 计算基本统计
        wins = [s for s in closed_signals if s.pnl_percent > 0]
        losses = [s for s in closed_signals if s.pnl_percent <= 0]

        summary = {
            'period_days': days,
            'total_trades': len(closed_signals),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(closed_signals),

            'avg_win': sum(s.pnl_percent for s in wins) / len(wins) if wins else 0,
            'avg_loss': sum(s.pnl_percent for s in losses) / len(losses) if losses else 0,

            'total_pnl': sum(s.pnl_percent for s in closed_signals),
            'best_trade': max(s.pnl_percent for s in closed_signals),
            'worst_trade': min(s.pnl_percent for s in closed_signals),

            'avg_holding_hours': sum(s.holding_hours for s in closed_signals if s.holding_hours) / len([s for s in closed_signals if s.holding_hours]),

            # 分方向统计
            'long_trades': len([s for s in closed_signals if s.side == 'long']),
            'short_trades': len([s for s in closed_signals if s.side == 'short']),
            'long_win_rate': len([s for s in wins if s.side == 'long']) / len([s for s in closed_signals if s.side == 'long']) if [s for s in closed_signals if s.side == 'long'] else 0,
            'short_win_rate': len([s for s in wins if s.side == 'short']) / len([s for s in closed_signals if s.side == 'short']) if [s for s in closed_signals if s.side == 'short'] else 0,
        }

        # Profit Factor
        if losses and sum(abs(s.pnl_percent) for s in losses) > 0:
            summary['profit_factor'] = sum(s.pnl_percent for s in wins) / sum(abs(s.pnl_percent) for s in losses)
        else:
            summary['profit_factor'] = float('inf') if wins else 0

        return summary

    finally:
        session.close()


# ========== 批量操作 ==========

def expire_old_signals(hours: int = 24) -> int:
    """
    将超时未平仓的信号标记为过期

    Args:
        hours: 超过多少小时算过期

    Returns:
        过期的信号数量
    """
    session = db.get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        expired_signals = session.query(Signal).filter(
            and_(
                Signal.status == 'open',
                Signal.timestamp < cutoff
            )
        ).all()

        count = 0
        for signal in expired_signals:
            signal.status = 'expired'
            signal.exit_time = datetime.utcnow()
            signal.exit_reason = 'timeout'
            # 如果有当前价格，计算假设的盈亏
            if signal.current_price and signal.entry_price:
                if signal.side == 'long':
                    signal.pnl_percent = (signal.current_price - signal.entry_price) / signal.entry_price * 100
                else:
                    signal.pnl_percent = (signal.entry_price - signal.current_price) / signal.entry_price * 100
            count += 1

        session.commit()

        if count > 0:
            print(f"⏰ Expired {count} old signals (>{hours}h)")

        return count

    except Exception as e:
        session.rollback()
        print(f"❌ Failed to expire signals: {e}")
        return 0
    finally:
        session.close()


# ========== 候选池操作 ==========

def save_candidate_pool(
    symbols: List[str],
    pool_type: str = 'merged',
    filter_params: Optional[Dict] = None,
    run_mode: str = 'manual',
    notes: Optional[str] = None
) -> int:
    """
    保存候选池到数据库

    Args:
        symbols: 币种列表
        pool_type: 候选池类型 ('base', 'overlay', 'merged')
        filter_params: 筛选参数（可选）
        run_mode: 运行模式 ('manual', 'cron', 'api')
        notes: 备注（可选）

    Returns:
        pool_id: 新创建的候选池ID
    """
    from .models import CandidatePool

    session = db.get_session()
    try:
        pool = CandidatePool(
            timestamp=datetime.utcnow(),
            pool_type=pool_type,
            symbols=symbols,
            count=len(symbols),
            filter_params=filter_params or {},
            run_mode=run_mode,
            notes=notes
        )

        session.add(pool)
        session.commit()

        pool_id = pool.id
        print(f"✅ Candidate pool saved: #{pool_id} [{pool_type}] {len(symbols)} symbols")
        return pool_id

    except Exception as e:
        session.rollback()
        print(f"❌ Failed to save candidate pool: {e}")
        raise
    finally:
        session.close()


def get_recent_candidate_pools(
    days: int = 7,
    pool_type: Optional[str] = None,
    limit: int = 50
) -> List:
    """
    获取最近的候选池记录

    Args:
        days: 天数
        pool_type: 候选池类型过滤（可选）
        limit: 返回数量限制

    Returns:
        候选池记录列表
    """
    from .models import CandidatePool

    session = db.get_session()
    try:
        start_time = datetime.utcnow() - timedelta(days=days)

        query = session.query(CandidatePool).filter(
            CandidatePool.timestamp >= start_time
        )

        if pool_type:
            query = query.filter(CandidatePool.pool_type == pool_type)

        pools = query.order_by(desc(CandidatePool.timestamp)).limit(limit).all()

        return pools

    finally:
        session.close()
