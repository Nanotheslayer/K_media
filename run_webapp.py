#!/usr/bin/env python3
"""
Главный файл для запуска Telegram Web App Кировец Медиа
"""
import sys
import os

# Добавляем корневую директорию проекта в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp_server.app import run_server

if __name__ == '__main__':
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n⚠️ Сервер остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске сервера: {e}")
        sys.exit(1)
