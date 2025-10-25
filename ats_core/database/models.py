# coding: utf-8
"""
数据库模型定义

使用SQLAlchemy ORM定义数据表结构
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class Signal(Base):
    """
    交易信号表

    记录每个生成的交易信号及其执行情况
    """
    __tablename__ = 'signals'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)

    # 方向和概率
    side = Column(String(5), nullable=False, index=True)  # 'long' or 'short'
    probability = Column(Float, nullable=False)

    # 七维分数（JSON格式）
    scores = Column(JSON, nullable=False)
    # 示例：{"T": 85, "M": 70, "C": 65, "S": 60, "V": 75, "O": 80, "E": 70}

    # 七维分数元数据（JSON格式，可选）
    scores_meta = Column(JSON)
    # 包含每个维度的详细信息

    # F调节器
    f_score = Column(Float)
    f_adjustment = Column(Float)

    # 加权分数
    weighted_score = Column(Float)

    # 基础概率（F调整前）
    base_probability = Column(Float)

    # 给价计划
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)

    # 当前价格
    current_price = Column(Float)

    # 发布状态
    is_prime = Column(Boolean, default=False, index=True)
    is_watch = Column(Boolean, default=False)
    dims_ok = Column(Integer)  # 达标维度数量

    # 15分钟微确认
    m15_ok = Column(Boolean)

    # 实际执行情况
    status = Column(String(10), default='open', index=True)  # open/closed/expired/cancelled
    exit_price = Column(Float)
    exit_time = Column(DateTime)
    exit_reason = Column(String(20))  # 'tp1', 'tp2', 'sl', 'expired', 'manual'

    # 盈亏
    pnl_percent = Column(Float)  # 百分比
    pnl_usdt = Column(Float)     # USDT金额

    # 实际持仓时间（小时）
    holding_hours = Column(Float)

    # 备注
    notes = Column(Text)

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Signal(id={self.id}, symbol={self.symbol}, side={self.side}, prob={self.probability:.2f}, status={self.status})>"


class DailyMetrics(Base):
    """
    每日性能指标表

    记录每天的交易统计和性能指标
    """
    __tablename__ = 'daily_metrics'

    # 主键
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
    expired_trades = Column(Integer, default=0)

    # 绩效指标
    win_rate = Column(Float)
    avg_win = Column(Float)
    avg_loss = Column(Float)
    avg_win_usdt = Column(Float)
    avg_loss_usdt = Column(Float)
    profit_factor = Column(Float)

    # 盈亏
    total_pnl = Column(Float, default=0.0)
    total_pnl_usdt = Column(Float, default=0.0)

    # 平均持仓时间
    avg_holding_hours = Column(Float)

    # 最佳/最差交易
    best_trade_pnl = Column(Float)
    best_trade_symbol = Column(String(20))
    worst_trade_pnl = Column(Float)
    worst_trade_symbol = Column(String(20))

    # 分维度统计（JSON）
    dimension_stats = Column(JSON)
    # 示例：{"T": {"avg": 75, "std": 15, "min": 40, "max": 100}, ...}

    # 分方向统计（JSON）
    direction_stats = Column(JSON)
    # 示例：{"long": {"count": 10, "win_rate": 0.6}, "short": {...}}

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DailyMetrics(date={self.date.date()}, signals={self.total_signals}, win_rate={self.win_rate})>"


class CandidatePool(Base):
    """
    候选池历史记录表

    记录每次运行时的候选池列表，用于：
    1. 追踪选币逻辑的变化
    2. 回测时重建历史候选池
    3. 分析哪些币种被频繁选中
    """
    __tablename__ = 'candidate_pools'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 时间戳
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)

    # 候选池类型（'base', 'overlay', 'merged'）
    pool_type = Column(String(20), nullable=False, index=True)

    # 候选币种列表（JSON数组）
    symbols = Column(JSON, nullable=False)
    # 示例：["BTCUSDT", "ETHUSDT", "SOLUSDT", ...]

    # 币种数量
    count = Column(Integer, nullable=False)

    # 选币参数（JSON，记录当时的筛选条件）
    filter_params = Column(JSON)
    # 示例：{"min_volume_24h": 1000000, "min_price_change_24h": 5, ...}

    # 运行方式（'manual', 'cron', 'api'）
    run_mode = Column(String(20))

    # 备注
    notes = Column(Text)

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CandidatePool(id={self.id}, timestamp={self.timestamp}, type={self.pool_type}, count={self.count})>"


# ========== 数据库连接管理 ==========

class Database:
    """数据库管理类"""

    def __init__(self, db_url=None):
        """
        初始化数据库连接

        Args:
            db_url: 数据库URL，默认从环境变量读取
        """
        if db_url is None:
            db_url = os.environ.get('DATABASE_URL', 'sqlite:///data/database/cryptosignal.db')

        # 如果是SQLite且使用相对路径，确保目录存在
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            if not db_path.startswith('/'):  # 相对路径
                # 获取项目根目录
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                db_path = os.path.join(project_root, db_path)
                db_url = f'sqlite:///{db_path}'

            # 确保目录存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
        print(f"✅ Database tables created successfully at: {self.db_url}")

    def drop_tables(self):
        """删除所有表（危险操作，仅用于测试）"""
        Base.metadata.drop_all(self.engine)
        print(f"⚠️  All tables dropped from: {self.db_url}")

    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()

    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# 全局数据库实例
db = Database()


# ========== 工具函数 ==========

def init_database(drop_existing=False):
    """
    初始化数据库

    Args:
        drop_existing: 是否删除现有表（危险！）
    """
    if drop_existing:
        print("⚠️  WARNING: Dropping all existing tables!")
        response = input("Are you sure? Type 'yes' to confirm: ")
        if response.lower() == 'yes':
            db.drop_tables()
        else:
            print("Cancelled.")
            return

    db.create_tables()
    print("✅ Database initialized successfully")


if __name__ == '__main__':
    # 测试：创建数据库
    init_database()
