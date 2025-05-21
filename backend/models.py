# models.py

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# ✅ 持仓量数据表
class OpenInterest(Base):
    __tablename__ = "open_interest"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    open_interest = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)

# ✅ 实时价格历史（可选：你也可以不定义这个，如果只用 open_interest）
class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)

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