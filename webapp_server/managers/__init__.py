"""
Инициализация менеджеров
"""
from webapp_server.managers.key_manager import KeyManager
from webapp_server.managers.proxy_manager import ProxyManager
from webapp_server.managers.user_manager import UserManager

key_manager = KeyManager()
proxy_manager = ProxyManager()
user_manager = UserManager()

__all__ = ['key_manager', 'proxy_manager', 'user_manager']
