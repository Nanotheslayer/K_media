#!/bin/bash
cd ~/news_bot
source venv/bin/activate
export FLASK_ENV=production
export WEBAPP_PORT=5000
python3 webapp_kyrov_server.py
