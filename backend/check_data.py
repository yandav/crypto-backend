from sqlalchemy import create_engine, text
from config import config
import datetime

def check_price_data():
    """检查价格历史数据"""
    print("检查价格历史数据...")
    
    # 获取数据库配置
    db_config = config.get_db_config()
    
    try:
        # 创建数据库引擎
        engine = create_engine(**db_config)
        
        # 创建连接
        with engine.connect() as conn:
            # 检查价格表中的数据
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM prices
            """))
            
            price_count = result.fetchone()[0]
            print(f"价格表中有 {price_count} 条记录")
            
            # 检查最近的价格数据
            result = conn.execute(text("""
                SELECT symbol, timestamp, price 
                FROM prices 
                ORDER BY timestamp DESC 
                LIMIT 5
            """))
            
            print("\n最近的价格数据:")
            for row in result:
                print(f"Symbol: {row[0]}, Time: {row[1]}, Price: {row[2]}")
            
            # 检查每个交易对的数据量
            result = conn.execute(text("""
                SELECT symbol, COUNT(*) as count 
                FROM prices 
                GROUP BY symbol 
                ORDER BY count DESC 
                LIMIT 10
            """))
            
            print("\n每个交易对的数据量(前10):")
            for row in result:
                print(f"Symbol: {row[0]}, Count: {row[1]}")
            
            # 检查时间范围
            result = conn.execute(text("""
                SELECT MIN(timestamp) as min_time, MAX(timestamp) as max_time 
                FROM prices
            """))
            
            row = result.fetchone()
            if row[0] and row[1]:
                print(f"\n数据时间范围: {row[0]} 到 {row[1]}")
                time_diff = row[1] - row[0]
                print(f"总时间跨度: {time_diff}")
            else:
                print("\n没有找到时间范围数据")
        
        print("\n检查完成!")
        
    except Exception as e:
        print(f"检查失败: {str(e)}")
        raise

if __name__ == "__main__":
    check_price_data() 