# models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Price(Base):
    """价格数据模型"""
    __tablename__ = 'prices'
    
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    price = Column(Float, nullable=False)
    
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'timestamp', name='prices_pkey'),
    )

class OpenInterest(Base):
    """持仓量数据模型"""
    __tablename__ = 'open_interest'
    
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open_interest = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=True)
    funding_rate = Column(Float, nullable=True)
    
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'timestamp', name='open_interest_pkey'),
    )

class PriceChange(Base):
    """价格变化数据模型"""
    __tablename__ = 'price_changes'
    
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    price = Column(Float, nullable=False)
    change_1m = Column(Float, nullable=True)
    change_5m = Column(Float, nullable=True)
    change_15m = Column(Float, nullable=True)
    change_1h = Column(Float, nullable=True)
    
    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'timestamp', name='price_changes_pkey'),
    )

# ✅ 实时价格历史（可选：你也可以不定义这个，如果只用 open_interest）
class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)

