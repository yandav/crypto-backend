from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime, timedelta
from threading import Lock

# ✅ 全局线程锁，确保写入时串行
db_lock = Lock()

# ✅ ORM 基础定义
Base = declarative_base()

# ✅ 创建 SQLite 引擎，允许跨线程 + 启用 WAL 模式
engine = create_engine("sqlite:///open_interest.db", connect_args={"check_same_thread": False})
with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL"))

# ✅ 创建线程安全的 Session
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

# ✅ 定义持仓量表
class OpenInterest(Base):
    __tablename__ = 'open_interest'
    symbol = Column(String, primary_key=True)
    timestamp = Column(DateTime, primary_key=True)
    open_interest = Column(Float)

    __table_args__ = (
        Index('idx_oi_symbol_timestamp', 'symbol', 'timestamp'),
    )

# ✅ 定义价格历史表
class PriceHistory(Base):
    __tablename__ = 'price_history'
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    timestamp = Column(DateTime)
    price = Column(Float)

    __table_args__ = (
        Index('idx_price_symbol_timestamp', 'symbol', 'timestamp'),
    )

# ✅ 创建表（首次运行或升级结构时使用）
def create_tables():
    Base.metadata.create_all(engine)

# ✅ 保存单币种持仓量（逐条提交，避免锁冲突）
def save_open_interest_data(data):
    with db_lock:
        session = Session()
        now = datetime.utcnow().replace(second=0, microsecond=0)
        for item in data:
            try:
                record = OpenInterest(
                    symbol=item['symbol'],
                    timestamp=now,
                    open_interest=item['openInterest']
                )
                session.add(record)
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"❌ 保存 {item['symbol']} OI 失败: {e}")
        session.close()

# ✅ 保存单币种价格（逐条提交，避免锁冲突）
def save_price_history(data):
    with db_lock:
        session = Session()
        now = datetime.utcnow().replace(second=0, microsecond=0)
        for item in data:
            try:
                record = PriceHistory(
                    symbol=item['symbol'],
                    timestamp=now,
                    price=item['price']
                )
                session.add(record)
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"❌ 保存 {item['symbol']} 价格失败: {e}")
        session.close()

# ✅ 获取历史持仓量（用于涨幅计算）
def get_previous_oi(symbol, minutes_ago):
    session = Session()
    try:
        time_threshold = datetime.utcnow() - timedelta(minutes=minutes_ago)
        record = session.query(OpenInterest)\
                        .filter_by(symbol=symbol)\
                        .filter(OpenInterest.timestamp <= time_threshold)\
                        .order_by(OpenInterest.timestamp.desc())\
                        .first()
        return record.open_interest if record else None
    except Exception as e:
        print(f"❌ 查询 open interest 失败: {e}")
        return None
    finally:
        session.close()

# ✅ 获取历史价格（用于涨跌幅计算）
def get_price_change(symbol, minutes_ago):
    session = Session()
    try:
        time_threshold = datetime.utcnow() - timedelta(minutes=minutes_ago)
        record = session.query(PriceHistory)\
                        .filter_by(symbol=symbol)\
                        .filter(PriceHistory.timestamp <= time_threshold)\
                        .order_by(PriceHistory.timestamp.desc())\
                        .first()
        return record.price if record else None
    except Exception as e:
        print(f"❌ 查询价格失败: {e}")
        return None
    finally:
        session.close()
