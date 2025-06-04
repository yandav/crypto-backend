import os
import sys
import json
from typing import Dict, Any

class Config:
    # 尝试从项目根目录的config.js加载配置
    try:
        # 检查是否存在config.local.js（优先使用本地配置）
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.local.js')
        if not os.path.exists(config_file):
            # 如果本地配置不存在，使用默认配置
            config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.js')
        
        if os.path.exists(config_file):
            # 读取JS配置文件内容
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 提取JSON部分（简单处理，仅适用于当前格式）
            start = content.find('const config = ')
            if start > 0:
                json_str = content[start + 14:]
                end = json_str.find('};')
                if end > 0:
                    json_str = json_str[:end+1]
                    
                    # 替换JS对象键名格式为JSON格式
                    import re
                    json_str = re.sub(r'\[ENV\.(\w+)\]', r'"\1"', json_str)
                    
                    # 解析JSON
                    try:
                        import json5
                        config_data = json5.loads(json_str)
                        
                        # 获取当前环境
                        current_env = os.getenv('NODE_ENV', 'development')
                        if current_env in config_data:
                            env_config = config_data[current_env]
                            
                            # 从配置文件中加载数据库配置
                            if 'database' in env_config:
                                db_config = env_config['database']
                                DATABASE_URL = os.getenv('DATABASE_URL', db_config.get('url'))
                                DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', str(db_config.get('poolSize', 5))))
                                DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', str(db_config.get('maxOverflow', 10))))
                                DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', str(db_config.get('poolTimeout', 60))))
                                DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', str(db_config.get('poolRecycle', 3600))))
                            
                            # 从配置文件中加载API配置
                            if 'api' in env_config:
                                api_config = env_config['api']
                                API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', str(api_config.get('rateLimit', 100))))
                                API_TIMEOUT = int(os.getenv('API_TIMEOUT', str(api_config.get('timeout', 30))))
                            
                            # 从配置文件中加载数据保留配置
                            if 'dataRetention' in env_config:
                                DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', str(env_config['dataRetention'].get('days', 30))))
                            
                            # 从配置文件中加载调度器配置
                            if 'scheduler' in env_config:
                                scheduler_config = env_config['scheduler']
                                PRICE_UPDATE_INTERVAL = int(os.getenv('PRICE_UPDATE_INTERVAL', str(scheduler_config.get('priceUpdateInterval', 1))))
                                OPEN_INTEREST_UPDATE_INTERVAL = int(os.getenv('OPEN_INTEREST_UPDATE_INTERVAL', str(scheduler_config.get('openInterestUpdateInterval', 1))))
                            
                            # 从配置文件中加载CORS配置
                            if 'cors' in env_config:
                                CORS_ORIGIN = os.getenv('CORS_ORIGIN', env_config['cors'].get('origin', '*'))
                    except Exception as e:
                        print(f"无法解析配置文件JSON: {e}")
    except Exception as e:
        print(f"加载配置文件失败: {e}")

    # 数据库配置（如果上面没有成功加载，则使用这些默认值）
    DATABASE_URL = os.getenv('DATABASE_URL', "postgresql+psycopg2://postgres:123456@localhost:5432/crypto_monitor")
    # 如果是Render的PostgreSQL，需要处理sslmode
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # 在Render环境中，确保使用环境变量中的DATABASE_URL
    if os.getenv("RENDER"):
        print(f"Running in Render environment, using DATABASE_URL from environment")
        DATABASE_URL = os.getenv('DATABASE_URL')
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        print(f"Configured DATABASE_URL: {DATABASE_URL}")
    
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', "5"))
    DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', "10"))
    DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', "60"))
    DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', "3600"))

    # API配置
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', "100"))  # 每分钟请求限制
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', "30"))  # API请求超时时间（秒）

    # 数据清理配置
    DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', "30"))

    # 定时任务配置
    PRICE_UPDATE_INTERVAL = int(os.getenv('PRICE_UPDATE_INTERVAL', "1"))  # 分钟
    OPEN_INTEREST_UPDATE_INTERVAL = int(os.getenv('OPEN_INTEREST_UPDATE_INTERVAL', "1"))  # 分钟

    # CORS配置
    CORS_ORIGIN = os.getenv('CORS_ORIGIN', '*')

    @classmethod
    def get_db_config(cls) -> Dict[str, Any]:
        is_render = os.getenv("RENDER") == "true"
        
        config = {
            "url": cls.DATABASE_URL,
            "pool_size": cls.DB_POOL_SIZE,
            "max_overflow": cls.DB_MAX_OVERFLOW,
            "pool_timeout": cls.DB_POOL_TIMEOUT,
            "pool_recycle": cls.DB_POOL_RECYCLE,
            "pool_pre_ping": True,
        }
        
        # 在Render环境中启用SSL
        if is_render:
            config["connect_args"] = {"sslmode": "require"}
            print("Enabled SSL for database connection in Render environment")
        
        return config

config = Config() 