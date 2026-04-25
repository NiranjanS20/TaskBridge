@echo off
cd /d "C:\Users\hp\OneDrive\Documents\FAANG companies\TaskBridge\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000