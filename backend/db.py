# db.py

from sqlalchemy import create_engine, Column, String, Float, DateTime, PrimaryKeyConstraint, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.dialects.postgresql import insert
from contextlib import contextmanager
import threading
import datetime

# PostgreSQL 连接字符串
#postgresql+psycopg2://postgres:123456@localhost:5432/crypto_monitor
#postgresql://yandavi_user:1UoakzxW06deiQhh03tVGpJvXMiin3g8@dpg-d0mrriu3jp1c738kgb60-a/yandavi
#postgresql://yandavi_ibqv_user:uOOPuNALuKxsmDuFz73bE0Vz1ZoL65IS@dpg-d0o8eb6mcj7s73e8fphg-a/yandavi_ibqv
DATABASE_URL = "postgresql://yandavi_ibqv_user:uOOPuNALuKxsmDuFz73bE0Vz1ZoL65IS@dpg-d0o8eb6mcj7s73e8fphg-a/yandavi_ibqv"



engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)
Base = declarative_base()

# 全局线程锁（用于防止并发写冲突）
db_lock = threading.Lock()


class OpenInterest(Base):
    __tablename__ = 'open_interest'
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open_interest = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=True)
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'timestamp', name='open_interest_pkey'),
    )


class Price(Base):
    __tablename__ = 'price'
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    price = Column(Float, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'timestamp', name='price_pkey'),
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



# 上下文管理器，用于自动提交或回滚事务
@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ✅ 批量保存持仓量，使用 PostgreSQL 的 ON CONFLICT DO UPDATE
def save_open_interest_bulk(data_list):
    with db_lock:
        with session_scope() as session:
            try:
                stmt = insert(OpenInterest).values(data_list)
                update_dict = {
                    'open_interest': stmt.excluded.open_interest
                }
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
        with session_scope() as session:
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
    with session_scope() as session:
        record = (
            session.query(OpenInterest)
            .filter(OpenInterest.symbol == symbol)
            .filter(OpenInterest.timestamp <= target_time)
            .order_by(OpenInterest.timestamp.desc())
            .first()
        )
        return record.open_interest if record else None

