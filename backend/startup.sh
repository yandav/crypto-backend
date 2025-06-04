#!/bin/bash
# 设置环境变量
export RENDER="true"

# 打印环境信息
echo "Starting application in Render environment"
echo "DATABASE_URL: $DATABASE_URL"

# Initialize the database
python init_db.py

# Start the application with gunicorn
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50 