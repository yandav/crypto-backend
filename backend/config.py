import os
from typing import Dict, Any

class Config:
    # 数据库配置
    DATABASE_URL = os.getenv('DATABASE_URL', "postgresql+psycopg2://postgres:123456@localhost:5432/crypto_monitor")
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', "5"))
    DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', "10"))
    DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', "60"))
    DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', "1800"))

    # API配置
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', "100"))  # 每分钟请求限制
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', "30"))  # API请求超时时间（秒）

    # 数据清理配置
    DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', "30"))

    # 定时任务配置
    PRICE_UPDATE_INTERVAL = int(os.getenv('PRICE_UPDATE_INTERVAL', "1"))  # 分钟
    OPEN_INTEREST_UPDATE_INTERVAL = int(os.getenv('OPEN_INTEREST_UPDATE_INTERVAL', "1"))  # 分钟

    @classmethod
    def get_db_config(cls) -> Dict[str, Any]:
        return {
            "url": cls.DATABASE_URL,
            "pool_size": cls.DB_POOL_SIZE,
            "max_overflow": cls.DB_MAX_OVERFLOW,
            "pool_timeout": cls.DB_POOL_TIMEOUT,
            "pool_recycle": cls.DB_POOL_RECYCLE,
            "pool_pre_ping": True
        }

config = Config() 