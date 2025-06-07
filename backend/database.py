# database.py

from sqlalchemy import create_engine, desc, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging
from typing import List, Optional, Dict, Any
import time
import threading
import os

from models import Base, Price, OpenInterest, PriceChange, Trade
from config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建数据库引擎，使用配置文件中的连接池设置
db_config = config.get_db_config()
engine = create_engine(**db_config)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionLocal)

# 简单的内存缓存实现
class SimpleCache:
    def __init__(self, ttl_seconds=60, max_size=500):
        self.cache = {}
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def get(self, key):
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    # 过期了，删除
                    del self.cache[key]
            return None
    
    def set(self, key, value):
        with self.lock:
            # 如果缓存满了，删除最旧的条目
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
                del self.cache[oldest_key]
            
            self.cache[key] = (value, time.time())
    
    def clear(self):
        with self.lock:
            self.cache.clear()

# 创建缓存实例
price_history_cache = SimpleCache(ttl_seconds=60, max_size=500)  # 1分钟缓存
latest_data_cache = SimpleCache(ttl_seconds=30, max_size=100)    # 30秒缓存

# 最大重试次数
MAX_RETRIES = 3
# 重试延迟（秒）
RETRY_DELAY = 0.5

@contextmanager
def get_db_session():
    """数据库会话上下文管理器，带重试机制"""
    session = Session()
    retries = 0
    while True:
        try:
            yield session
            session.commit()
            break
        except OperationalError as e:
            session.rollback()
            retries += 1
            if retries >= MAX_RETRIES:
                logger.error(f"Database connection error after {MAX_RETRIES} retries: {str(e)}", exc_info=True)
                raise
            logger.warning(f"Database connection error, retrying ({retries}/{MAX_RETRIES}): {str(e)}")
            time.sleep(RETRY_DELAY * (2 ** (retries - 1)))  # 指数退避
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
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
    if not data_list:
        logger.info("No price data to save")
        return
        
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
            
            # 保存后清除缓存
            price_history_cache.clear()
            latest_data_cache.clear()
    except Exception as e:
        logger.error(f"Error saving prices: {str(e)}", exc_info=True)
        raise

def save_open_interest(data_list: List[Dict[str, Any]], batch_size: int = 1000) -> None:
    """批量保存持仓量数据"""
    if not data_list:
        logger.info("No open interest data to save")
        return
        
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
    """获取指定时间前的价格数据，带缓存"""
    cache_key = f"{symbol}_{minutes_ago}"
    
    # 先查缓存
    cached_result = price_history_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        with get_db_session() as session:
            target_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
            
            # 先尝试从 prices 表查询
            try:
                result = session.query(Price).filter(
                    Price.symbol == symbol,
                    Price.timestamp <= target_time
                ).order_by(desc(Price.timestamp)).first()
                
                if result:
                    price = result.price
                    price_history_cache.set(cache_key, price)
                    return price
            except Exception as e:
                logger.warning(f"从 prices 表查询失败: {str(e)}")
            
            # 如果 prices 表查询失败，尝试使用原始 SQL 查询 price 表
            try:
                sql = text("""
                    SELECT price FROM prices 
                    WHERE symbol = :symbol AND timestamp <= :target_time 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                result = session.execute(sql, {"symbol": symbol, "target_time": target_time})
                row = result.fetchone()
                if row:
                    price = row[0]
                    price_history_cache.set(cache_key, price)
                    return price
            except Exception as e:
                logger.warning(f"从 prices 表查询失败: {str(e)}")
            
            # 如果都没有找到数据，返回 None
            return None
    except Exception as e:
        logger.error(f"Error getting price history for {symbol}: {str(e)}", exc_info=True)
        return None

def get_closest_price_history(symbol: str, minutes_ago: int, tolerance_minutes: int = 5) -> Dict[str, Any]:
    """
    获取最接近指定时间的价格数据，带容差
    
    Args:
        symbol: 交易对符号
        minutes_ago: 目标时间（几分钟前）
        tolerance_minutes: 容差范围（分钟）
        
    Returns:
        包含价格和实际时间差的字典，如果没有找到数据则返回None
    """
    cache_key = f"closest_{symbol}_{minutes_ago}_{tolerance_minutes}"
    
    # 先查缓存
    cached_result = price_history_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        with get_db_session() as session:
            target_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
            min_time = target_time - timedelta(minutes=tolerance_minutes)
            max_time = target_time + timedelta(minutes=tolerance_minutes)
            
            # 查询指定时间范围内的价格数据
            try:
                # 先查询目标时间之前的最近数据
                before_result = session.query(Price).filter(
                    Price.symbol == symbol,
                    Price.timestamp <= target_time,
                    Price.timestamp >= min_time
                ).order_by(desc(Price.timestamp)).first()
                
                # 再查询目标时间之后的最近数据
                after_result = session.query(Price).filter(
                    Price.symbol == symbol,
                    Price.timestamp > target_time,
                    Price.timestamp <= max_time
                ).order_by(Price.timestamp).first()
                
                # 确定哪个结果更接近目标时间
                result = None
                if before_result and after_result:
                    before_diff = (target_time - before_result.timestamp).total_seconds()
                    after_diff = (after_result.timestamp - target_time).total_seconds()
                    result = before_result if before_diff <= after_diff else after_result
                elif before_result:
                    result = before_result
                elif after_result:
                    result = after_result
                
                if result:
                    time_diff = abs((result.timestamp - target_time).total_seconds()) / 60  # 转换为分钟
                    data = {
                        "price": result.price,
                        "actual_minutes_ago": (datetime.utcnow() - result.timestamp).total_seconds() / 60,
                        "time_diff": time_diff,
                        "timestamp": result.timestamp
                    }
                    price_history_cache.set(cache_key, data)
                    return data
            except Exception as e:
                logger.warning(f"从 prices 表查询最接近的数据失败: {str(e)}")
            
            # 如果没有找到数据，返回None
            return None
    except Exception as e:
        logger.error(f"Error getting closest price history for {symbol}: {str(e)}", exc_info=True)
        return None

def get_available_price_history(symbol: str) -> Dict[str, Any]:
    """
    获取指定交易对的所有可用历史价格数据点
    
    Args:
        symbol: 交易对符号
        
    Returns:
        包含各个时间点价格的字典
    """
    cache_key = f"available_history_{symbol}"
    
    # 先查缓存
    cached_result = price_history_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        with get_db_session() as session:
            # 获取当前时间
            now = datetime.utcnow()
            
            # 查询该交易对的所有价格数据
            results = session.query(Price).filter(
                Price.symbol == symbol
            ).order_by(desc(Price.timestamp)).all()
            
            if not results:
                return {}
                
            # 整理数据，计算每个数据点距离现在的分钟数
            data_points = {}
            for result in results:
                minutes_ago = round((now - result.timestamp).total_seconds() / 60)
                # 只保留整数分钟的数据点
                if minutes_ago >= 0:
                    data_points[minutes_ago] = result.price
            
            # 缓存并返回结果
            price_history_cache.set(cache_key, data_points)
            return data_points
    except Exception as e:
        logger.error(f"Error getting available price history for {symbol}: {str(e)}", exc_info=True)
        return {}

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
    """获取最新数据，带缓存"""
    cache_key = f"latest_data_{symbol}_{limit}"
    
    # 先查缓存
    cached_result = latest_data_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        with get_db_session() as session:
            try:
                # 先尝试从 prices 表查询
                query = session.query(Price)
                if symbol:
                    query = query.filter(Price.symbol == symbol)
                results = query.order_by(desc(Price.timestamp)).limit(limit).all()
                
                if results:
                    data = [
                        {
                            "symbol": r.symbol,
                            "price": r.price,
                            "timestamp": r.timestamp.isoformat()
                        }
                        for r in results
                    ]
                    latest_data_cache.set(cache_key, data)
                    return data
            except Exception as e:
                logger.warning(f"从 prices 表查询最新数据失败: {str(e)}")
                
            # 如果 prices 表查询失败，尝试使用原始 SQL 查询 price 表
            try:
                sql = text("""
                    SELECT symbol, price, timestamp FROM prices 
                    WHERE symbol = :symbol OR :symbol IS NULL
                    ORDER BY timestamp DESC 
                    LIMIT :limit
                """)
                results = session.execute(sql, {"symbol": symbol, "limit": limit})
                data = [
                    {
                        "symbol": row[0],
                        "price": row[1],
                        "timestamp": row[2].isoformat()
                    }
                    for row in results
                ]
                latest_data_cache.set(cache_key, data)
                return data
            except Exception as e:
                logger.warning(f"从 prices 表查询最新数据失败: {str(e)}")
            
            # 如果都没有找到数据，返回空列表
            return []
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
            try:
                price_deleted = session.query(Price).filter(
                    Price.timestamp < cutoff_date
                ).delete(synchronize_session=False)
                logger.info(f"从 prices 表删除了 {price_deleted} 条记录")
            except Exception as e:
                logger.warning(f"清理 prices 表失败: {str(e)}")
                
                # 尝试使用原始 SQL 清理 price 表
                try:
                    sql = text("DELETE FROM prices WHERE timestamp < :cutoff_date")
                    result = session.execute(sql, {"cutoff_date": cutoff_date})
                    logger.info(f"从 prices 表删除了记录")
                except Exception as e:
                    logger.warning(f"清理 prices 表失败: {str(e)}")
            
            # 清理持仓量数据
            try:
                oi_deleted = session.query(OpenInterest).filter(
                    OpenInterest.timestamp < cutoff_date
                ).delete(synchronize_session=False)
                logger.info(f"从 open_interest 表删除了 {oi_deleted} 条记录")
            except Exception as e:
                logger.warning(f"清理 open_interest 表失败: {str(e)}")
            
            # 清理价格变化数据
            try:
                pc_deleted = session.query(PriceChange).filter(
                    PriceChange.timestamp < cutoff_date
                ).delete(synchronize_session=False)
                logger.info(f"从 price_changes 表删除了 {pc_deleted} 条记录")
            except Exception as e:
                logger.warning(f"清理 price_changes 表失败: {str(e)}")
            
            # 清除所有缓存
            price_history_cache.clear()
            latest_data_cache.clear()
            
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}", exc_info=True)
        raise

def save_trades(trades_data: List[Dict[str, Any]], batch_size: int = 100) -> int:
    """批量保存交易数据"""
    if not trades_data:
        logger.info("No trade data to save")
        return 0
        
    try:
        saved_count = 0
        current_time = datetime.utcnow()
        
        with get_db_session() as session:
            for i in range(0, len(trades_data), batch_size):
                batch = trades_data[i:i + batch_size]
                
                for trade_data in batch:
                    # 检查交易是否已存在
                    existing = session.query(Trade).filter(
                        Trade.trader_id == trade_data["trader_id"],
                        Trade.symbol == trade_data["symbol"],
                        Trade.entry_time == trade_data["entry_time"],
                        Trade.entry_price == trade_data["entry_price"]
                    ).first()
                    
                    if existing:
                        # 如果已存在，更新状态
                        if "status" in trade_data and existing.status != trade_data["status"]:
                            existing.status = trade_data["status"]
                            if trade_data["status"] == "CLOSED" and "exit_time" in trade_data:
                                existing.exit_time = trade_data["exit_time"]
                            if "pnl" in trade_data:
                                existing.pnl = trade_data["pnl"]
                            if "pnl_percentage" in trade_data:
                                existing.pnl_percentage = trade_data["pnl_percentage"]
                            # 更新updated_at字段
                            existing.updated_at = current_time
                            saved_count += 1
                    else:
                        # 如果不存在，创建新交易
                        trade = Trade(
                            trader_id=trade_data["trader_id"],
                            symbol=trade_data["symbol"],
                            direction=trade_data["direction"],
                            entry_price=trade_data["entry_price"],
                            take_profit=trade_data.get("take_profit"),
                            stop_loss=trade_data.get("stop_loss"),
                            leverage=trade_data.get("leverage"),
                            position_size=trade_data.get("position_size"),
                            status=trade_data["status"],
                            entry_time=trade_data["entry_time"],
                            exit_time=trade_data.get("exit_time"),
                            notes=trade_data.get("notes"),
                            source_data=trade_data.get("source_data"),
                            created_at=current_time,
                            updated_at=current_time
                        )
                        session.add(trade)
                        saved_count += 1
                
                session.flush()
            
            logger.info(f"Successfully saved/updated {saved_count} trade records")
            return saved_count
    except Exception as e:
        logger.error(f"Error saving trades: {str(e)}", exc_info=True)
        raise
