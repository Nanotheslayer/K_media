"""
Инициализация базы данных
"""
from webapp_server.database.webapp_database import WebAppDatabase

webapp_db = WebAppDatabase()

__all__ = ['webapp_db', 'WebAppDatabase']
