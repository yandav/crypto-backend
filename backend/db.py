# backend/db.py
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

Base = declarative_base()
engine = create_engine("sqlite:///open_interest.db")
Session = sessionmaker(bind=engine)

class OpenInterest(Base):
    __tablename__ = 'open_interest'
    symbol = Column(String, primary_key=True)
    timestamp = Column(DateTime, primary_key=True)
    open_interest = Column(Float)

def create_tables():
    Base.metadata.create_all(engine)

def save_open_interest_data(data):
    session = Session()
    now = datetime.utcnow()
    for item in data:
        record = OpenInterest(
            symbol=item['symbol'],
            timestamp=now,
            open_interest=item['openInterest']
        )
        session.add(record)
    session.commit()
    session.close()

def get_previous_oi(symbol, minutes_ago):
    session = Session()
    time_threshold = datetime.utcnow() - timedelta(minutes=minutes_ago)
    record = session.query(OpenInterest).filter_by(symbol=symbol).filter(OpenInterest.timestamp <= time_threshold).order_by(OpenInterest.timestamp.desc()).first()
    session.close()
    return record.open_interest if record else None


class PriceHistory(Base):
    __tablename__ = 'price_history'
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    timestamp = Column(DateTime)
    price = Column(Float)

def get_price_change(symbol, minutes_ago):
    session = Session()
    time_threshold = datetime.utcnow() - timedelta(minutes=minutes_ago)
    record = session.query(PriceHistory).filter_by(symbol=symbol).filter(PriceHistory.timestamp <= time_threshold).order_by(PriceHistory.timestamp.desc()).first()
    session.close()
    if record:
        return record.price
    return None

def save_price_history(data):
    session = Session()
    now = datetime.utcnow()
    for item in data:
        session.add(PriceHistory(symbol=item['symbol'], timestamp=now, price=item['price']))
    session.commit()
    session.close()

