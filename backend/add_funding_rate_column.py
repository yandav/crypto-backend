import psycopg2
from config import config

def add_funding_rate_column():
    """添加 funding_rate 列到 open_interest 表"""
    print("开始添加 funding_rate 列...")
    
    try:
        # 获取数据库配置
        db_config = config.get_db_config()
        db_url = db_config["url"]
        
        # 解析数据库URL
        # 格式: postgresql+psycopg2://username:password@host:port/dbname
        db_url = db_url.replace("postgresql+psycopg2://", "")
        
        if "@" in db_url:
            auth, conn_info = db_url.split("@")
            if ":" in auth:
                username, password = auth.split(":")
            else:
                username = auth
                password = ""
                
            if "/" in conn_info:
                host_port, dbname = conn_info.split("/")
                if ":" in host_port:
                    host, port = host_port.split(":")
                else:
                    host = host_port
                    port = "5432"
            else:
                host = conn_info
                port = "5432"
                dbname = "postgres"
        else:
            # 默认连接信息
            username = "postgres"
            password = "123456"
            host = "localhost"
            port = "5432"
            dbname = "crypto_monitor"
        
        print(f"连接到数据库: {host}:{port}/{dbname}")
        
        # 连接到PostgreSQL数据库
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=username,
            password=password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 检查列是否已存在
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='open_interest' AND column_name='funding_rate'
        """)
        
        if cursor.fetchone() is None:
            print("添加 funding_rate 列到 open_interest 表...")
            cursor.execute("""
                ALTER TABLE open_interest 
                ADD COLUMN funding_rate FLOAT
            """)
            print("列已成功添加!")
        else:
            print("funding_rate 列已存在，无需添加。")
        
        cursor.close()
        conn.close()
        print("数据库迁移完成！")
        
    except Exception as e:
        print(f"迁移失败: {str(e)}")
        raise

if __name__ == "__main__":
    add_funding_rate_column() 