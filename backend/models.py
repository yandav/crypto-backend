# models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, PrimaryKeyConstraint, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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

# 交易员信息
class Trader(Base):
    """交易员信息模型"""
    __tablename__ = 'traders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    source_url = Column(String, nullable=True)  # 数据来源URL
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    
    # 关联交易记录
    trades = relationship("Trade", back_populates="trader")

# 交易记录
class Trade(Base):
    """交易记录模型"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_id = Column(Integer, ForeignKey('traders.id'), nullable=False)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # LONG or SHORT
    entry_price = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    leverage = Column(Float, nullable=True)
    position_size = Column(Float, nullable=True)  # 仓位大小
    status = Column(String, nullable=False)  # OPEN, CLOSED, CANCELED
    pnl = Column(Float, nullable=True)  # 盈亏
    pnl_percentage = Column(Float, nullable=True)  # 盈亏百分比
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    source_data = Column(Text, nullable=True)  # 原始数据JSON
    
    # 关联交易员
    trader = relationship("Trader", back_populates="trades")

# 跟单配置
class TradeFollowConfig(Base):
    """跟单配置模型"""
    __tablename__ = 'trade_follow_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_id = Column(Integer, ForeignKey('traders.id'), nullable=False)
    is_enabled = Column(Boolean, default=True)
    leverage_multiplier = Column(Float, default=1.0)  # 杠杆倍数调整
    position_size_percentage = Column(Float, default=100.0)  # 仓位大小百分比
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

