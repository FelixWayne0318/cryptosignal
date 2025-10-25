# CryptoSignal 系统改进实施计划

**服务器环境**: Vultr (16核/13GB内存/9.3GB磁盘)
**代码托管**: GitHub
**操作工具**: Termius (SSH)
**实施时间**: 预计4-6周
**当前分支**: `claude/analyze-system-improvements-011CUTZA4j28R7iSVXcgcAs9`

---

## 阶段0：环境准备（1-2天）⚙️

### 0.1 安装必要依赖

```bash
# 1. 更新系统包管理器
sudo apt update

# 2. 安装SQLite（轻量级数据库，推荐首选）
sudo apt install -y sqlite3 libsqlite3-dev

# 3. 安装Python依赖管理工具
pip3 install --upgrade pip setuptools wheel

# 4. 安装核心依赖包
pip3 install \
    numpy==1.24.3 \
    pandas==2.0.3 \
    pytest==7.4.0 \
    pytest-cov==4.1.0 \
    sqlalchemy==2.0.19 \
    aiohttp==3.8.5 \
    python-dotenv==1.0.0

# 5. 验证安装
python3 -c "import numpy, pandas, pytest, sqlalchemy, aiohttp; print('✅ All dependencies installed')"
```

**可选：如果需要PostgreSQL（生产环境推荐）**
```bash
# 安装PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库用户
sudo -u postgres createuser cryptosignal_user -P  # 会提示输入密码
sudo -u postgres createdb cryptosignal_db -O cryptosignal_user
```

### 0.2 创建数据目录

```bash
cd ~/cryptosignal

# 创建数据库目录
mkdir -p data/database

# 创建日志目录
mkdir -p data/logs

# 创建回测数据目录
mkdir -p data/backtest

# 创建测试fixtures目录
mkdir -p tests/fixtures
```

### 0.3 配置环境变量

```bash
# 编辑 .env 文件
cat >> ~/cryptosignal/.env <<'EOF'

# === 数据库配置 ===
# SQLite（推荐开始使用）
DATABASE_URL=sqlite:///data/database/cryptosignal.db

# PostgreSQL（如果安装了）
# DATABASE_URL=postgresql://cryptosignal_user:your_password@localhost/cryptosignal_db

# === 日志配置 ===
LOG_LEVEL=INFO
LOG_FILE=data/logs/cryptosignal.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5

# === 回测配置 ===
BACKTEST_DATA_DIR=data/backtest
BACKTEST_INITIAL_CAPITAL=10000

EOF

# 加载环境变量
source ~/cryptosignal/.env
```

---

## 阶段1：数据持久化（1周）💾

### 1.1 数据库设计

**创建文件：`ats_core/database/models.py`**

```python
# coding: utf-8
"""数据库模型定义"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Signal(Base):
    """交易信号表"""
    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)

    # 方向和概率
    side = Column(String(5), nullable=False)  # 'long' or 'short'
    probability = Column(Float, nullable=False)

    # 七维分数（JSON格式）
    scores = Column(JSON, nullable=False)
    # 示例：{"T": 85, "M": 70, "C": 65, "S": 60, "V": 75, "O": 80, "E": 70}

    # F调节器
    f_score = Column(Float)
    f_adjustment = Column(Float)

    # 加权分数
    weighted_score = Column(Float)

    # 给价计划
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)

    # 发布状态
    is_prime = Column(Boolean, default=False)
    is_watch = Column(Boolean, default=False)

    # 实际执行情况
    status = Column(String(10), default='open')  # open/closed/expired/cancelled
    exit_price = Column(Float)
    exit_time = Column(DateTime)
    pnl_percent = Column(Float)  # 实际盈亏百分比

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DailyMetrics(Base):
    """每日性能指标"""
    __tablename__ = 'daily_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True, unique=True)

    # 信号统计
    total_signals = Column(Integer, default=0)
    prime_signals = Column(Integer, default=0)
    watch_signals = Column(Integer, default=0)
    long_signals = Column(Integer, default=0)
    short_signals = Column(Integer, default=0)

    # 交易统计
    closed_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)

    # 绩效指标
    win_rate = Column(Float)
    avg_win = Column(Float)
    avg_loss = Column(Float)
    profit_factor = Column(Float)
    total_pnl = Column(Float, default=0.0)

    # 分维度统计（JSON）
    dimension_stats = Column(JSON)
    # 示例：{"T": {"avg": 75, "std": 15}, "M": {...}, ...}

    created_at = Column(DateTime, default=datetime.utcnow)

# 数据库连接管理
class Database:
    def __init__(self, db_url=None):
        if db_url is None:
            db_url = os.environ.get('DATABASE_URL', 'sqlite:///data/database/cryptosignal.db')

        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
        print("✅ Database tables created successfully")

    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()

# 全局数据库实例
db = Database()
```

**创建文件：`ats_core/database/operations.py`**

```python
# coding: utf-8
"""数据库操作封装"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from .models import Signal, DailyMetrics, db

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
        publish = analysis_result.get('publish', {})

        signal = Signal(
            symbol=analysis_result['symbol'],
            timestamp=datetime.utcnow(),
            side=analysis_result['side'],
            probability=analysis_result['probability'],
            scores=analysis_result['scores'],
            f_score=analysis_result.get('F_score'),
            f_adjustment=analysis_result.get('F_adjustment'),
            weighted_score=analysis_result.get('UpScore') if analysis_result['side'] == 'long' else analysis_result.get('DownScore'),
            entry_price=pricing.get('entry'),
            stop_loss=pricing.get('sl'),
            take_profit_1=pricing.get('tp1'),
            take_profit_2=pricing.get('tp2'),
            is_prime=publish.get('prime', False),
            is_watch=publish.get('watch', False),
        )

        session.add(signal)
        session.commit()

        signal_id = signal.id
        print(f"✅ Signal saved: {signal.symbol} {signal.side} (ID: {signal_id})")
        return signal_id

    except Exception as e:
        session.rollback()
        print(f"❌ Failed to save signal: {e}")
        raise
    finally:
        session.close()

def update_signal_exit(signal_id: int, exit_price: float, pnl_percent: float, status: str = 'closed'):
    """
    更新信号的退出信息

    Args:
        signal_id: 信号ID
        exit_price: 退出价格
        pnl_percent: 盈亏百分比
        status: 状态（closed/expired）
    """
    session = db.get_session()
    try:
        signal = session.query(Signal).filter_by(id=signal_id).first()
        if signal:
            signal.exit_price = exit_price
            signal.exit_time = datetime.utcnow()
            signal.pnl_percent = pnl_percent
            signal.status = status
            session.commit()
            print(f"✅ Signal updated: ID {signal_id}, PnL: {pnl_percent:.2f}%")
        else:
            print(f"⚠️  Signal not found: ID {signal_id}")
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to update signal: {e}")
        raise
    finally:
        session.close()

def get_open_signals() -> List[Signal]:
    """获取所有未平仓的信号"""
    session = db.get_session()
    try:
        signals = session.query(Signal).filter_by(status='open').all()
        return signals
    finally:
        session.close()

def calculate_daily_metrics(date: datetime = None):
    """
    计算并保存每日性能指标

    Args:
        date: 计算哪一天的指标（默认今天）
    """
    if date is None:
        date = datetime.utcnow().date()

    session = db.get_session()
    try:
        # 查询当天的所有信号
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())

        signals = session.query(Signal).filter(
            Signal.timestamp >= start,
            Signal.timestamp <= end
        ).all()

        if not signals:
            print(f"⚠️  No signals found for {date}")
            return

        # 统计信号
        total_signals = len(signals)
        prime_signals = sum(1 for s in signals if s.is_prime)
        watch_signals = sum(1 for s in signals if s.is_watch)
        long_signals = sum(1 for s in signals if s.side == 'long')
        short_signals = sum(1 for s in signals if s.side == 'short')

        # 统计已平仓交易
        closed = [s for s in signals if s.status == 'closed' and s.pnl_percent is not None]
        closed_trades = len(closed)
        winning_trades = sum(1 for s in closed if s.pnl_percent > 0)
        losing_trades = sum(1 for s in closed if s.pnl_percent <= 0)

        # 计算绩效指标
        win_rate = winning_trades / closed_trades if closed_trades > 0 else None

        wins = [s.pnl_percent for s in closed if s.pnl_percent > 0]
        losses = [s.pnl_percent for s in closed if s.pnl_percent <= 0]

        avg_win = sum(wins) / len(wins) if wins else None
        avg_loss = sum(losses) / len(losses) if losses else None

        total_pnl = sum(s.pnl_percent for s in closed)

        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else None

        # 分维度统计
        dimension_stats = {}
        for dim in ['T', 'M', 'C', 'S', 'V', 'O', 'E']:
            scores = [s.scores.get(dim, 50) for s in signals if s.scores]
            if scores:
                dimension_stats[dim] = {
                    'avg': sum(scores) / len(scores),
                    'min': min(scores),
                    'max': max(scores)
                }

        # 保存或更新指标
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
        metrics.win_rate = win_rate
        metrics.avg_win = avg_win
        metrics.avg_loss = avg_loss
        metrics.profit_factor = profit_factor
        metrics.total_pnl = total_pnl
        metrics.dimension_stats = dimension_stats

        session.add(metrics)
        session.commit()

        print(f"✅ Daily metrics calculated for {date}")
        print(f"   Signals: {total_signals} (Prime: {prime_signals}, Watch: {watch_signals})")
        print(f"   Closed: {closed_trades}, Win Rate: {win_rate*100:.1f}%" if win_rate else "   No closed trades yet")

    except Exception as e:
        session.rollback()
        print(f"❌ Failed to calculate metrics: {e}")
        raise
    finally:
        session.close()
```

### 1.2 集成到现有代码

**修改 `tools/manual_run.py`，添加数据库记录：**

```python
# 在文件开头添加
from ats_core.database.models import db
from ats_core.database.operations import save_signal

# 在 main() 函数中，分析完成后添加
for result in results:
    if result.get('publish', {}).get('prime'):
        # 保存到数据库
        try:
            signal_id = save_signal(result)
            result['signal_id'] = signal_id  # 添加到结果中
        except Exception as e:
            print(f"⚠️  Failed to save signal to database: {e}")
```

### 1.3 初始化数据库

**创建脚本：`scripts/init_database.py`**

```python
#!/usr/bin/env python3
# coding: utf-8
"""初始化数据库"""
import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.database.models import db

if __name__ == '__main__':
    print("Creating database tables...")
    db.create_tables()
    print("✅ Database initialization completed!")
```

**执行初始化：**
```bash
cd ~/cryptosignal
python3 scripts/init_database.py
```

---

## 阶段2：回测系统（2-3周）📈

### 2.1 回测引擎核心

**创建文件：`ats_backtest/engine.py`**

```python
# coding: utf-8
"""回测引擎"""
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

@dataclass
class BacktestTrade:
    """回测交易记录"""
    symbol: str
    entry_time: datetime
    entry_price: float
    side: str  # 'long' or 'short'
    stop_loss: float
    take_profit: float
    probability: float
    scores: Dict[str, int]

    # 退出信息
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # 'tp', 'sl', 'expired'
    pnl_percent: Optional[float] = None
    pnl_usdt: Optional[float] = None

    @property
    def is_open(self):
        return self.exit_time is None

    @property
    def is_win(self):
        return self.pnl_percent and self.pnl_percent > 0

class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000,
        position_size_pct: float = 0.02,  # 每次开仓2%资金
        max_open_trades: int = 5,
        ttl_hours: int = 8
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.max_open_trades = max_open_trades
        self.ttl_hours = ttl_hours

        self.trades: List[BacktestTrade] = []
        self.current_capital = initial_capital
        self.equity_curve = []

    def run(self, symbols: List[str]):
        """
        运行回测

        Args:
            symbols: 要回测的币种列表

        Returns:
            回测结果字典
        """
        print(f"🚀 Starting backtest: {self.start_date} to {self.end_date}")
        print(f"   Capital: ${self.initial_capital:,.0f}, Position Size: {self.position_size_pct*100}%")

        current_time = self.start_date
        hour_count = 0

        while current_time <= self.end_date:
            # 每小时检查一次
            hour_count += 1

            # 1. 检查持仓，更新已开仓交易
            self._check_open_trades(current_time)

            # 2. 生成新信号（如果有空余仓位）
            open_count = sum(1 for t in self.trades if t.is_open)
            if open_count < self.max_open_trades:
                for symbol in symbols:
                    signal = self._generate_signal(symbol, current_time)
                    if signal and signal.get('publish', {}).get('prime'):
                        self._open_trade(signal, current_time)

                        # 检查是否达到最大持仓
                        if sum(1 for t in self.trades if t.is_open) >= self.max_open_trades:
                            break

            # 3. 记录权益曲线
            if hour_count % 24 == 0:  # 每天记录一次
                self.equity_curve.append({
                    'time': current_time,
                    'equity': self.current_capital,
                    'open_trades': open_count
                })

            # 进入下一小时
            current_time += timedelta(hours=1)

        # 强制平仓所有未平仓交易
        self._close_all_trades(self.end_date, reason='backtest_end')

        # 计算绩效指标
        return self._calculate_metrics()

    def _generate_signal(self, symbol: str, current_time: datetime) -> Optional[Dict]:
        """
        生成历史信号（需要从历史数据重新计算）

        注意：这里需要调用 analyze_symbol，但使用历史数据
        """
        # TODO: 实现历史数据获取和分析
        # 这是回测的核心难点，需要：
        # 1. 获取 current_time 之前的历史K线
        # 2. 调用 analyze_symbol 进行分析
        # 3. 返回分析结果
        pass

    def _open_trade(self, signal: Dict, entry_time: datetime):
        """开仓"""
        pricing = signal.get('pricing', {})
        if not pricing:
            return

        # 计算仓位大小
        position_value = self.current_capital * self.position_size_pct

        trade = BacktestTrade(
            symbol=signal['symbol'],
            entry_time=entry_time,
            entry_price=pricing['entry'],
            side=signal['side'],
            stop_loss=pricing['sl'],
            take_profit=pricing.get('tp2', pricing.get('tp1')),  # 优先使用TP2
            probability=signal['probability'],
            scores=signal['scores']
        )

        self.trades.append(trade)
        print(f"📊 Open: {trade.symbol} {trade.side} @ {trade.entry_price:.2f}")

    def _check_open_trades(self, current_time: datetime):
        """检查并更新持仓"""
        for trade in self.trades:
            if not trade.is_open:
                continue

            # 获取当前价格
            current_price = self._get_price(trade.symbol, current_time)
            if current_price is None:
                continue

            # 检查止盈止损
            exit_reason = None
            exit_price = None

            if trade.side == 'long':
                if current_price >= trade.take_profit:
                    exit_reason = 'tp'
                    exit_price = trade.take_profit
                elif current_price <= trade.stop_loss:
                    exit_reason = 'sl'
                    exit_price = trade.stop_loss
            else:  # short
                if current_price <= trade.take_profit:
                    exit_reason = 'tp'
                    exit_price = trade.take_profit
                elif current_price >= trade.stop_loss:
                    exit_reason = 'sl'
                    exit_price = trade.stop_loss

            # 检查过期
            if (current_time - trade.entry_time).total_seconds() / 3600 >= self.ttl_hours:
                exit_reason = 'expired'
                exit_price = current_price

            if exit_reason:
                self._close_trade(trade, exit_price, current_time, exit_reason)

    def _close_trade(self, trade: BacktestTrade, exit_price: float, exit_time: datetime, reason: str):
        """平仓"""
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.exit_reason = reason

        # 计算盈亏
        if trade.side == 'long':
            trade.pnl_percent = (exit_price - trade.entry_price) / trade.entry_price * 100
        else:  # short
            trade.pnl_percent = (trade.entry_price - exit_price) / trade.entry_price * 100

        # 计算USDT盈亏
        position_value = self.current_capital * self.position_size_pct
        trade.pnl_usdt = position_value * trade.pnl_percent / 100

        # 更新资金
        self.current_capital += trade.pnl_usdt

        emoji = "✅" if trade.is_win else "❌"
        print(f"{emoji} Close: {trade.symbol} {trade.exit_reason.upper()} @ {exit_price:.2f}, "
              f"PnL: {trade.pnl_percent:+.2f}% (${trade.pnl_usdt:+.2f})")

    def _close_all_trades(self, exit_time: datetime, reason: str):
        """强制平仓所有交易"""
        for trade in self.trades:
            if trade.is_open:
                current_price = self._get_price(trade.symbol, exit_time)
                if current_price:
                    self._close_trade(trade, current_price, exit_time, reason)

    def _get_price(self, symbol: str, time: datetime) -> Optional[float]:
        """获取历史价格"""
        # TODO: 实现历史价格获取
        # 需要从缓存的历史数据中获取
        pass

    def _calculate_metrics(self) -> Dict:
        """计算回测绩效指标"""
        closed_trades = [t for t in self.trades if not t.is_open]

        if not closed_trades:
            return {"error": "No trades executed"}

        wins = [t for t in closed_trades if t.is_win]
        losses = [t for t in closed_trades if not t.is_win]

        total_pnl = sum(t.pnl_usdt for t in closed_trades)
        total_pnl_pct = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        win_rate = len(wins) / len(closed_trades) if closed_trades else 0
        avg_win = sum(t.pnl_percent for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl_percent for t in losses) / len(losses) if losses else 0

        profit_factor = abs(sum(t.pnl_usdt for t in wins) / sum(t.pnl_usdt for t in losses)) if losses and sum(t.pnl_usdt for t in losses) != 0 else float('inf')

        # 计算最大回撤
        max_drawdown = self._calculate_max_drawdown()

        return {
            "summary": {
                "initial_capital": self.initial_capital,
                "final_capital": self.current_capital,
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
                "total_trades": len(closed_trades),
                "winning_trades": len(wins),
                "losing_trades": len(losses),
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "max_drawdown": max_drawdown,
            },
            "trades": [
                {
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_time": t.entry_time.isoformat(),
                    "entry_price": t.entry_price,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "exit_price": t.exit_price,
                    "exit_reason": t.exit_reason,
                    "pnl_percent": t.pnl_percent,
                    "pnl_usdt": t.pnl_usdt,
                }
                for t in closed_trades
            ],
            "equity_curve": self.equity_curve
        }

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.equity_curve:
            return 0.0

        peak = self.initial_capital
        max_dd = 0.0

        for point in self.equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return max_dd
```

### 2.2 使用示例

**创建脚本：`tools/run_backtest.py`**

```python
#!/usr/bin/env python3
# coding: utf-8
"""运行回测"""
import sys
sys.path.insert(0, '/home/user/cryptosignal')

from datetime import datetime, timedelta
from ats_backtest.engine import BacktestEngine
import json

def main():
    # 回测配置
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)  # 回测最近30天

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

    # 创建回测引擎
    engine = BacktestEngine(
        start_date=start_date,
        end_date=end_date,
        initial_capital=10000,
        position_size_pct=0.02,
        max_open_trades=5,
        ttl_hours=8
    )

    # 运行回测
    results = engine.run(symbols)

    # 打印结果
    print("\n" + "="*50)
    print("📊 BACKTEST RESULTS")
    print("="*50)

    summary = results['summary']
    print(f"\nInitial Capital: ${summary['initial_capital']:,.2f}")
    print(f"Final Capital:   ${summary['final_capital']:,.2f}")
    print(f"Total PnL:       ${summary['total_pnl']:+,.2f} ({summary['total_pnl_pct']:+.2f}%)")
    print(f"\nTotal Trades:    {summary['total_trades']}")
    print(f"Winning Trades:  {summary['winning_trades']}")
    print(f"Losing Trades:   {summary['losing_trades']}")
    print(f"Win Rate:        {summary['win_rate']*100:.1f}%")
    print(f"\nAvg Win:         {summary['avg_win']:+.2f}%")
    print(f"Avg Loss:        {summary['avg_loss']:+.2f}%")
    print(f"Profit Factor:   {summary['profit_factor']:.2f}")
    print(f"Max Drawdown:    {summary['max_drawdown']:.2f}%")

    # 保存详细结果
    with open('data/backtest/last_backtest_result.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Detailed results saved to: data/backtest/last_backtest_result.json")

if __name__ == '__main__':
    main()
```

---

## 阶段3：测试框架（1-2周）🧪

### 3.1 安装pytest并配置

```bash
cd ~/cryptosignal

# 创建pytest配置
cat > pytest.ini <<'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov=ats_core
    --cov-report=html
    --cov-report=term-missing
EOF
```

### 3.2 核心单元测试示例

**创建文件：`tests/unit/test_scoring_utils.py`**

```python
# coding: utf-8
"""测试评分工具函数"""
import pytest
import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.features.scoring_utils import directional_score, sigmoid_score, linear_clamped_score

class TestDirectionalScore:
    """测试 directional_score 函数"""

    def test_neutral_value(self):
        """测试中性值返回50分"""
        assert directional_score(0.0, neutral=0.0) == 50
        assert directional_score(1.0, neutral=1.0) == 50

    def test_positive_deviation(self):
        """测试正向偏移返回>50分"""
        score = directional_score(3.0, neutral=0.0, scale=3.0)
        assert 50 < score <= 100

    def test_negative_deviation(self):
        """测试负向偏移返回<50分但>=min_score"""
        score = directional_score(-3.0, neutral=0.0, scale=3.0, min_score=10)
        assert 10 <= score < 50

    def test_extreme_negative_reaches_min_score(self):
        """测试极端负值不会低于min_score"""
        score = directional_score(-1000, neutral=0.0, scale=3.0, min_score=10)
        assert score == 10

    def test_extreme_positive_reaches_100(self):
        """测试极端正值达到100分"""
        score = directional_score(1000, neutral=0.0, scale=3.0)
        assert score == 100

    def test_symmetry(self):
        """测试对称性：正负偏移应该对称"""
        pos = directional_score(5.0, neutral=0.0, scale=3.0)
        neg = directional_score(-5.0, neutral=0.0, scale=3.0, min_score=0)
        assert abs((pos - 50) + (neg - 50)) < 2  # 允许1分误差

    def test_volume_ratio_example(self):
        """测试量能比值评分示例"""
        # v5 = v20 → 中性
        assert directional_score(1.0, neutral=1.0, scale=0.3) == 50

        # v5 = 1.3*v20 → 放量
        score_vol = directional_score(1.3, neutral=1.0, scale=0.3)
        assert score_vol > 65

        # v5 = 0.7*v20 → 缩量
        score_shrink = directional_score(0.7, neutral=1.0, scale=0.3)
        assert score_shrink < 35

class TestSigmoidScore:
    """测试 sigmoid_score 函数"""

    def test_center_value(self):
        """测试中心值返回50分"""
        assert sigmoid_score(0.0, center=0.0) == 50

    def test_boundary_values(self):
        """测试边界值"""
        assert sigmoid_score(1000, center=0.0) == 100
        assert sigmoid_score(-1000, center=0.0) == 0

class TestLinearClampedScore:
    """测试 linear_clamped_score 函数"""

    def test_min_value(self):
        """测试最小值"""
        assert linear_clamped_score(0, 0, 100) == 0

    def test_max_value(self):
        """测试最大值"""
        assert linear_clamped_score(100, 0, 100) == 100

    def test_middle_value(self):
        """测试中间值"""
        assert linear_clamped_score(50, 0, 100) == 50

    def test_clamping(self):
        """测试截断"""
        assert linear_clamped_score(-10, 0, 100) == 0
        assert linear_clamped_score(110, 0, 100) == 100

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### 3.3 运行测试

```bash
cd ~/cryptosignal

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_scoring_utils.py -v

# 运行测试并生成覆盖率报告
pytest --cov=ats_core --cov-report=html

# 查看覆盖率报告
# 在浏览器中打开 htmlcov/index.html
```

---

## 阶段4：性能优化（1-2周）⚡

### 4.1 使用numpy加速

**创建文件：`ats_core/features/ta_core_fast.py`**

```python
# coding: utf-8
"""快速技术分析函数（numpy版本）"""
import numpy as np

def ema_fast(arr: np.ndarray, period: int) -> np.ndarray:
    """
    快速EMA计算（比纯Python快3-5倍）

    Args:
        arr: 价格数组
        period: EMA周期

    Returns:
        EMA数组
    """
    k = 2.0 / (period + 1)
    ema = np.zeros_like(arr, dtype=np.float64)
    ema[0] = arr[0]

    for i in range(1, len(arr)):
        ema[i] = ema[i-1] + k * (arr[i] - ema[i-1])

    return ema

def atr_fast(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """
    快速ATR计算

    Args:
        high, low, close: 价格数组
        period: ATR周期

    Returns:
        ATR数组
    """
    # 计算True Range
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        )
    )
    tr[0] = high[0] - low[0]  # 第一个值特殊处理

    # ATR = EMA(TR, period)
    return ema_fast(tr, period)

# 性能基准测试
if __name__ == '__main__':
    import time

    # 生成测试数据
    data = np.random.randn(1000).cumsum() + 100

    # 测试EMA性能
    start = time.time()
    for _ in range(1000):
        result = ema_fast(data, 30)
    numpy_time = time.time() - start

    print(f"numpy EMA: {numpy_time:.3f}s for 1000 iterations")
    print(f"Expected speedup: 3-5x compared to pure Python")
```

### 4.2 异步并行处理

**创建文件：`ats_core/pipeline/batch_scan_async.py`**

```python
# coding: utf-8
"""异步批量扫描"""
import asyncio
import aiohttp
from typing import List, Dict
import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.pipeline.analyze_symbol import analyze_symbol

async def fetch_klines_async(session: aiohttp.ClientSession, symbol: str, interval: str, limit: int):
    """异步获取K线数据"""
    url = f"https://fapi.binance.com/fapi/v1/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}

    async with session.get(url, params=params) as response:
        return await response.json()

async def analyze_symbol_async(symbol: str) -> Dict:
    """异步分析单个币种"""
    # 注意：analyze_symbol本身是同步的，但可以放在executor中运行
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, analyze_symbol, symbol)
    return result

async def scan_symbols_parallel(symbols: List[str], max_concurrent: int = 10) -> List[Dict]:
    """
    并行扫描多个币种

    Args:
        symbols: 币种列表
        max_concurrent: 最大并发数

    Returns:
        分析结果列表
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_analyze(symbol):
        async with semaphore:
            try:
                return await analyze_symbol_async(symbol)
            except Exception as e:
                print(f"❌ Error analyzing {symbol}: {e}")
                return None

    tasks = [limited_analyze(s) for s in symbols]
    results = await asyncio.gather(*tasks)

    # 过滤掉失败的结果
    return [r for r in results if r is not None]

# 使用示例
if __name__ == '__main__':
    import time

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"] * 10  # 50个币种

    # 串行版本
    print("Testing serial processing...")
    start = time.time()
    results_serial = [analyze_symbol(s) for s in symbols]
    serial_time = time.time() - start
    print(f"Serial: {serial_time:.2f}s for {len(symbols)} symbols")

    # 并行版本
    print("\nTesting parallel processing...")
    start = time.time()
    results_parallel = asyncio.run(scan_symbols_parallel(symbols, max_concurrent=10))
    parallel_time = time.time() - start
    print(f"Parallel: {parallel_time:.2f}s for {len(symbols)} symbols")
    print(f"Speedup: {serial_time/parallel_time:.2f}x")
```

---

## 阶段5：日志监控（3-5天）📝

### 5.1 结构化日志系统

**创建文件：`ats_core/logging_system.py`**

```python
# coding: utf-8
"""改进的日志系统"""
import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    """结构化JSON日志格式"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # 添加额外字段
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        return json.dumps(log_data, ensure_ascii=False)

def setup_logging(
    log_level: str = 'INFO',
    log_file: str = 'data/logs/cryptosignal.log',
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    配置日志系统

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的备份文件数量
    """
    # 创建日志目录
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # 获取根logger
    logger = logging.getLogger('cryptosignal')
    logger.setLevel(getattr(logging, log_level.upper()))

    # 文件处理器（结构化JSON）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(StructuredFormatter())
    logger.addHandler(file_handler)

    # 控制台处理器（人类可读）
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

# 全局logger实例
logger = setup_logging(
    log_level=os.environ.get('LOG_LEVEL', 'INFO'),
    log_file=os.environ.get('LOG_FILE', 'data/logs/cryptosignal.log')
)

# 便捷函数
def log_signal(symbol: str, side: str, probability: float, scores: Dict[str, int]):
    """记录交易信号"""
    logger.info(
        f"Signal generated: {symbol} {side.upper()}",
        extra={
            'event': 'signal_generated',
            'symbol': symbol,
            'side': side,
            'probability': probability,
            'scores': scores
        }
    )

def log_performance(metric: str, value: float, **kwargs):
    """记录性能指标"""
    logger.info(
        f"Performance: {metric}={value}",
        extra={
            'event': 'performance_metric',
            'metric': metric,
            'value': value,
            **kwargs
        }
    )

def log_error(message: str, **kwargs):
    """记录错误"""
    logger.error(
        message,
        extra={
            'event': 'error',
            **kwargs
        }
    )
```

### 5.2 性能监控装饰器

**创建文件：`ats_core/monitoring.py`**

```python
# coding: utf-8
"""性能监控工具"""
import time
import functools
from typing import Callable
from .logging_system import logger, log_performance

def monitor_performance(func: Callable) -> Callable:
    """
    性能监控装饰器

    自动记录函数执行时间和成功率
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        error = None

        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            error = str(e)
            raise
        finally:
            elapsed_time = time.time() - start_time

            log_performance(
                metric='execution_time',
                value=elapsed_time,
                function=func.__name__,
                success=success,
                error=error
            )

    return wrapper

# 使用示例
@monitor_performance
def analyze_symbol_monitored(symbol: str):
    from ats_core.pipeline.analyze_symbol import analyze_symbol
    return analyze_symbol(symbol)
```

---

## 总结：实施路线图时间表

| 阶段 | 任务 | 预计时间 | 依赖 |
|-----|------|---------|------|
| **阶段0** | 环境准备 | 1-2天 | 无 |
| **阶段1** | 数据持久化 | 1周 | 阶段0 |
| **阶段2** | 回测系统 | 2-3周 | 阶段1 |
| **阶段3** | 测试框架 | 1-2周 | 阶段0 |
| **阶段4** | 性能优化 | 1-2周 | 阶段1 |
| **阶段5** | 日志监控 | 3-5天 | 阶段0 |

**总计**: 4-6周

---

## 验证清单 ✅

每个阶段完成后的验证步骤：

### 阶段0验证
```bash
# 检查依赖安装
python3 -c "import numpy, pandas, pytest, sqlalchemy, aiohttp; print('✅ OK')"

# 检查数据库
sqlite3 data/database/cryptosignal.db ".tables"

# 检查环境变量
source .env && echo $DATABASE_URL
```

### 阶段1验证
```bash
# 运行数据库初始化
python3 scripts/init_database.py

# 手动运行一次并检查数据库
python3 tools/manual_run.py --top 5
sqlite3 data/database/cryptosignal.db "SELECT * FROM signals LIMIT 5;"
```

### 阶段2验证
```bash
# 运行回测
python3 tools/run_backtest.py

# 检查回测结果
cat data/backtest/last_backtest_result.json
```

### 阶段3验证
```bash
# 运行测试
pytest tests/ -v

# 检查覆盖率
pytest --cov=ats_core --cov-report=term-missing
```

### 阶段4验证
```bash
# 性能基准测试
python3 ats_core/features/ta_core_fast.py
python3 ats_core/pipeline/batch_scan_async.py
```

### 阶段5验证
```bash
# 检查日志文件
tail -f data/logs/cryptosignal.log

# 检查日志格式
python3 -c "from ats_core.logging_system import logger; logger.info('Test log')"
```

---

## 下一步行动建议 🎯

**建议优先级**:
1. **立即开始阶段0**（环境准备）- 2小时内可完成
2. **本周完成阶段1**（数据持久化）- 最关键的基础设施
3. **下周开始阶段2**（回测系统）- 最高价值

**需要你确认的问题**：
1. 是否使用SQLite（推荐）还是PostgreSQL？
2. 是否立即开始实施？
3. 是否需要我生成完整的代码文件？

告诉我你的决定，我可以立即开始实施！
