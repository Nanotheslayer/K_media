"""
Инициализация сервисов
"""
from webapp_server.services.gemini_client import GeminiClient
from webapp_server.services.image_processor import ImageProcessor
from webapp_server.managers import key_manager, proxy_manager

gemini_client = GeminiClient(key_manager, proxy_manager)

__all__ = ['gemini_client', 'GeminiClient', 'ImageProcessor']
