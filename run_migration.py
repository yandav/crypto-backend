#!/usr/bin/env python3
# run_migration.py - 用于在 Render 上运行数据库迁移

import os
import sys

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入迁移函数
from backend.migrate_db import migrate_database

if __name__ == "__main__":
    print("开始在 Render 上运行数据库迁移...")
    try:
        migrate_database()
        print("迁移成功完成！")
    except Exception as e:
        print(f"迁移失败: {str(e)}")
        sys.exit(1) 