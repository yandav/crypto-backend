from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime, timedelta

Base = declarative_base()

# ✅ 创建线程安全引擎 + 启用 WAL 模式
engine = create_engine("sqlite:///open_interest.db", connect_args={"check_same_thread": False})
with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL"))

# ✅ 使用 scoped_session 保证线程安全
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

# --- 模型定义 ---
class OpenInterest(Base):
    __tablename__ = 'open_interest'
    symbol = Column(String, primary_key=True)
    timestamp = Column(DateTime, primary_key=True)
    open_interest = Column(Float)

class PriceHistory(Base):
    __tablename__ = 'price_history'
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    timestamp = Column(DateTime)
    price = Column(Float)

# --- 创建表 ---
def create_tables():
    Base.metadata.create_all(engine)

# --- 持仓量保存 ---
def save_open_interest_data(data):
    session = Session()
    now = datetime.utcnow()
    try:
        for item in data:
            record = OpenInterest(
                symbol=item['symbol'],
                timestamp=now,
                open_interest=item['openInterest']
            )
            session.add(record)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"❌ 保存 open interest 失败: {e}")
    finally:
        session.close()

# --- 获取过去持仓量 ---
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

# --- 保存价格 ---
def save_price_history(data):
    session = Session()
    now = datetime.utcnow()
    try:
        for item in data:
            session.add(PriceHistory(
                symbol=item['symbol'],
                timestamp=now,
                price=item['price']
            ))
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"❌ 保存价格失败: {e}")
    finally:
        session.close()

# --- 获取历史价格 ---
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
