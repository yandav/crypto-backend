# database.py

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import insert
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging
from typing import List, Optional, Dict, Any

from models import Base, Price, OpenInterest, PriceChange
from config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_engine(**config.get_db_config())

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionLocal)

@contextmanager
def get_db_session():
    """数据库会话上下文管理器"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()

def init_db():
    """初始化数据库表"""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("数据库表初始化成功")
    except Exception as e:
        logger.error(f"数据库表初始化失败: {str(e)}", exc_info=True)
        raise

def save_prices(data_list: List[Dict[str, Any]], batch_size: int = 1000) -> None:
    """批量保存价格数据"""
    try:
        with get_db_session() as session:
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                stmt = insert(Price).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'timestamp'],
                    set_=dict(price=stmt.excluded.price)
                )
                session.execute(stmt)
                session.flush()
            logger.info(f"Successfully saved {len(data_list)} price records")
    except Exception as e:
        logger.error(f"Error saving prices: {str(e)}", exc_info=True)
        raise

def save_open_interest(data_list: List[Dict[str, Any]], batch_size: int = 1000) -> None:
    """批量保存持仓量数据"""
    try:
        with get_db_session() as session:
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                stmt = insert(OpenInterest).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'timestamp'],
                    set_=dict(
                        open_interest=stmt.excluded.open_interest,
                        change_pct=stmt.excluded.change_pct,
                        funding_rate=stmt.excluded.funding_rate
                    )
                )
                session.execute(stmt)
                session.flush()
            logger.info(f"Successfully saved {len(data_list)} open interest records")
    except Exception as e:
        logger.error(f"Error saving open interest: {str(e)}", exc_info=True)
        raise

def get_price_history(symbol: str, minutes_ago: int) -> Optional[float]:
    """获取指定时间前的价格数据"""
    try:
        with get_db_session() as session:
            target_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
            result = session.query(Price).filter(
                Price.symbol == symbol,
                Price.timestamp <= target_time
            ).order_by(desc(Price.timestamp)).first()
            return result.price if result else None
    except Exception as e:
        logger.error(f"Error getting price history for {symbol}: {str(e)}", exc_info=True)
        return None

def get_open_interest_history(symbol: str, minutes_ago: int) -> Optional[float]:
    """获取指定时间前的持仓量数据"""
    try:
        with get_db_session() as session:
            target_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
            result = session.query(OpenInterest).filter(
                OpenInterest.symbol == symbol,
                OpenInterest.timestamp <= target_time
            ).order_by(desc(OpenInterest.timestamp)).first()
            return result.open_interest if result else None
    except Exception as e:
        logger.error(f"Error getting open interest history for {symbol}: {str(e)}", exc_info=True)
        return None

def get_latest_data(symbol: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """获取最新数据"""
    try:
        with get_db_session() as session:
            query = session.query(Price)
            if symbol:
                query = query.filter(Price.symbol == symbol)
            results = query.order_by(desc(Price.timestamp)).limit(limit).all()
            return [
                {
                    "symbol": r.symbol,
                    "price": r.price,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"Error getting latest data: {str(e)}", exc_info=True)
        return []

def cleanup_old_data(days: int = None) -> None:
    """清理旧数据"""
    if days is None:
        days = config.DATA_RETENTION_DAYS
        
    try:
        with get_db_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 清理价格数据
            price_deleted = session.query(Price).filter(
                Price.timestamp < cutoff_date
            ).delete(synchronize_session=False)
            
            # 清理持仓量数据
            oi_deleted = session.query(OpenInterest).filter(
                OpenInterest.timestamp < cutoff_date
            ).delete(synchronize_session=False)
            
            # 清理价格变化数据
            pc_deleted = session.query(PriceChange).filter(
                PriceChange.timestamp < cutoff_date
            ).delete(synchronize_session=False)
            
            logger.info(
                f"Cleaned up data older than {days} days: "
                f"Prices: {price_deleted}, "
                f"Open Interest: {oi_deleted}, "
                f"Price Changes: {pc_deleted}"
            )
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}", exc_info=True)
        raise
