
# update_data_job.py

import sys
import os

# 设置 Python 导入路径为当前目录
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal
from app import update_price_data, update_open_interest_data

if __name__ == "__main__":
    try:

        update_price_data()
        update_open_interest_data()
        print("✅ 数据更新完成")
    except Exception as e:
        print(f"❌ 更新失败: {e}")
