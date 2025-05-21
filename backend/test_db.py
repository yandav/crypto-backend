from sqlalchemy import inspect
from db import engine, SessionLocal
from models import PriceData

def test_database():
    try:
        # 打印当前连接的数据库信息
        print("✅ 数据库连接成功，当前使用数据库：", engine.url)

        # 使用 SQLAlchemy 的 inspector 检查是否存在 price_data 表
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "price_data" in tables:
            print("✅ 已找到表：price_data")
        else:
            print("❌ 未找到表：price_data，请确认是否执行了 create_tables() 创建表结构。")
            return

        # 查询 price_data 表的前 5 条记录
        session = SessionLocal()
        results = session.query(PriceData).limit(5).all()
        if results:
            print("📦 price_data 表中存在数据，前 5 条如下：")
            for row in results:
                print(f"{row.symbol} - {row.price} - {row.timestamp}")
        else:
            print("⚠️ price_data 表存在，但目前没有数据。")

    except Exception as e:
        print("❌ 数据库测试失败:", e)

if __name__ == "__main__":
    test_database()
