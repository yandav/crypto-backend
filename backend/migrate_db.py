from sqlalchemy import create_engine, text
from config import config

def migrate_database():
    """添加 funding_rate 列到 open_interest 表"""
    print("开始数据库迁移...")
    
    # 获取数据库连接信息
    db_config = config.get_db_config()
    
    try:
        # 创建数据库引擎
        engine = create_engine(**db_config)
        
        # 创建连接
        with engine.connect() as conn:
            # 检查列是否已存在
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='open_interest' AND column_name='funding_rate'
            """))
            
            if result.fetchone() is None:
                print("添加 funding_rate 列到 open_interest 表...")
                conn.execute(text("""
                    ALTER TABLE open_interest 
                    ADD COLUMN funding_rate FLOAT
                """))
                conn.commit()
                print("列已添加成功！")
            else:
                print("funding_rate 列已存在，无需添加。")
        
        print("数据库迁移完成！")
        
    except Exception as e:
        print(f"迁移失败: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_database() 