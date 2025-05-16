# init_db.py
from db import create_tables

if __name__ == "__main__":
    create_tables()
    print("✅ 数据库表创建成功！")
