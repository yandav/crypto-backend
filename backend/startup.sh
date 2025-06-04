#!/bin/bash
# Initialize the database
python init_db.py

# Start the application with gunicorn
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50 