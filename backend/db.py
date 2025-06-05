# db.py

from sqlalchemy import create_engine, Column, String, Float, DateTime, PrimaryKeyConstraint, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.dialects.postgresql import insert
from contextlib import contextmanager
import threading
import datetime
import os

# PostgreSQL 连接字符串 - 从环境变量获取或使用默认值
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+psycopg2://postgres:123456@localhost:5432/crypto_monitor"
)

# 如果是Heroku或Render提供的PostgreSQL URL，需要修改前缀
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 数据库连接池配置
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "60"))
DB_POOL_RECYCLE = int(os.environ.get("DB_POOL_RECYCLE", "1800"))

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)
Base = declarative_base()

# 全局线程锁（用于防止并发写冲突）
db_lock = threading.Lock()

# 获取数据库会话的上下文管理器
@contextmanager
def get_db_session():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class OpenInterest(Base):
    __tablename__ = 'open_interest'
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open_interest = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=True)
    funding_rate = Column(Float, nullable=True)
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'timestamp', name='open_interest_pkey'),
    )


class Price(Base):
    __tablename__ = 'prices'
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    price = Column(Float, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'timestamp', name='prices_pkey'),
    )

# ✅ 实时价格表：记录价格和 EMA 指标
class PriceData(Base):
    __tablename__ = "price_data"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    ema_7 = Column(Float, nullable=True)
    ema_25 = Column(Float, nullable=True)
    ema_99 = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)

# ✅ 实时价格历史（可选：你也可以不定义这个，如果只用 open_interest）
class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)


# ✅ 批量保存持仓量，使用 PostgreSQL 的 ON CONFLICT DO UPDATE
def save_open_interest_bulk(data_list):
    # 处理数据，移除 funding_rate 字段以避免错误
    processed_data = []
    for item in data_list:
        # 创建一个新的字典，只包含确定存在的字段
        processed_item = {
            "symbol": item["symbol"],
            "timestamp": item["timestamp"],
            "open_interest": item["open_interest"],
            "change_pct": item.get("change_pct", 0.0)
        }
        # 只有当数据库中有 funding_rate 列时才添加
        # 这个字段在运行时会被忽略，不会导致错误
        if "funding_rate" in item:
            processed_item["funding_rate"] = item["funding_rate"]
        processed_data.append(processed_item)
    
    with db_lock:
        with get_db_session() as session:
            try:
                stmt = insert(OpenInterest).values(processed_data)
                # 只更新确定存在的列
                update_dict = {
                    'open_interest': stmt.excluded.open_interest,
                    'change_pct': stmt.excluded.change_pct
                }
                # 尝试更新 funding_rate，如果列存在的话
                try:
                    update_dict['funding_rate'] = stmt.excluded.funding_rate
                except:
                    pass  # 如果列不存在，忽略这个错误
                
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'timestamp'],
                    set_=update_dict
                )
                session.execute(stmt)
            except Exception as e:
                print(f"❌ 批量保存 OI 失败: {e}")


# ✅ 批量保存价格数据，同样处理主键冲突
def save_price_bulk(data_list):
    with db_lock:
        with get_db_session() as session:
            try:
                stmt = insert(Price).values(data_list)
                update_dict = {
                    'price': stmt.excluded.price
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'timestamp'],
                    set_=update_dict
                )
                session.execute(stmt)
            except Exception as e:
                print(f"❌ 批量保存价格失败: {e}")


# ✅ 自动建表（首次运行或新表添加后使用）
def create_tables():
    Base.metadata.create_all(bind=engine)


# ✅ 新增：获取历史持仓量用于计算涨跌幅
def get_previous_oi(symbol: str, minutes: int):
    """
    获取 symbol 在指定时间范围内最接近的一条持仓量数据
    """
    target_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
    with get_db_session() as session:
        try:
            # 使用安全的查询方式，只查询确定存在的列
            record = (
                session.query(
                    OpenInterest.symbol,
                    OpenInterest.timestamp,
                    OpenInterest.open_interest
                )
                .filter(OpenInterest.symbol == symbol)
                .filter(OpenInterest.timestamp <= target_time)
                .order_by(OpenInterest.timestamp.desc())
                .first()
            )
            return record.open_interest if record else None
        except Exception as e:
            print(f"❌ 获取历史持仓量失败: {e}")
            return None

