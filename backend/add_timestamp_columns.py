# add_timestamp_columns.py

import logging
from datetime import datetime
from sqlalchemy import Column, DateTime, text
from sqlalchemy.exc import SQLAlchemyError
from database import get_db_session, engine
from models import Trade, Base

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_timestamp_columns():
    """为Trade表添加created_at和updated_at字段"""
    try:
        # 检查列是否已存在
        with get_db_session() as session:
            # 使用原始SQL查询检查列是否存在
            inspector = engine.dialect.inspector(engine)
            columns = [col['name'] for col in inspector.get_columns('trades')]
            
            need_created_at = 'created_at' not in columns
            need_updated_at = 'updated_at' not in columns
            
            if not need_created_at and not need_updated_at:
                logger.info("Trade表已有created_at和updated_at字段，无需添加")
                return
            
            # 添加缺失的列
            if need_created_at:
                logger.info("添加created_at字段...")
                session.execute(text("ALTER TABLE trades ADD COLUMN created_at TIMESTAMP"))
            
            if need_updated_at:
                logger.info("添加updated_at字段...")
                session.execute(text("ALTER TABLE trades ADD COLUMN updated_at TIMESTAMP"))
            
            # 更新现有数据
            logger.info("更新现有数据的时间戳...")
            current_time = datetime.utcnow()
            session.execute(
                text("UPDATE trades SET created_at = :time, updated_at = :time WHERE created_at IS NULL OR updated_at IS NULL"),
                {"time": current_time}
            )
            
            logger.info("时间戳字段添加并更新完成")
            
    except SQLAlchemyError as e:
        logger.error(f"数据库错误: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"未预期的错误: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        add_timestamp_columns()
        logger.info("迁移成功完成")
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}") 