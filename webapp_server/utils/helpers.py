"""
Вспомогательные функции и утилиты
"""
import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import jsonify, request, make_response
import requests
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ==================== ДЕКОРАТОРЫ ====================

def rate_limit(max_calls: int = 60, window_seconds: int = 60):
    """Декоратор для ограничения частоты запросов"""
    def decorator(f):
        calls = {}
        
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Получаем IP адрес клиента
            client_ip = request.remote_addr or 'unknown'
            now = datetime.now()
            
            # Очищаем старые записи
            cutoff = now - timedelta(seconds=window_seconds)
            calls[client_ip] = [
                call_time for call_time in calls.get(client_ip, [])
                if call_time > cutoff
            ]
            
            # Проверяем лимит
            if len(calls.get(client_ip, [])) >= max_calls:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded'
                }), 429
            
            # Добавляем текущий вызов
            if client_ip not in calls:
                calls[client_ip] = []
            calls[client_ip].append(now)
            
            return f(*args, **kwargs)
        
        return wrapped
    return decorator


def async_task(f):
    """Декоратор для асинхронного выполнения задач"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        # TODO: Реализовать через Celery или threading
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в асинхронной задаче: {e}")
            return None
    return wrapped


def cache_result(ttl_seconds: int = 3600):
    """Декоратор для кэширования результатов"""
    cache = {}
    
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Создаем ключ кэша
            cache_key = f"{f.__name__}:{str(args)}:{str(kwargs)}"
            now = datetime.now()
            
            # Проверяем кэш
            if cache_key in cache:
                cached_value, cached_time = cache[cache_key]
                if now - cached_time < timedelta(seconds=ttl_seconds):
                    logger.debug(f"Возвращаем из кэша: {cache_key}")
                    return cached_value
            
            # Вычисляем результат
            result = f(*args, **kwargs)
            
            # Сохраняем в кэш
            cache[cache_key] = (result, now)
            
            # Очищаем старые записи
            cutoff = now - timedelta(seconds=ttl_seconds * 2)
            for key in list(cache.keys()):
                _, cached_time = cache[key]
                if cached_time < cutoff:
                    del cache[key]
            
            return result
        
        return wrapped
    return decorator


# ==================== ОБРАБОТЧИКИ ОШИБОК ====================

def register_error_handlers(app):
    """Регистрация обработчиков ошибок для Flask приложения"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Неверный запрос'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'Требуется авторизация'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Доступ запрещён'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Страница не найдена'
        }), 404
    
    @app.errorhandler(413)
    def too_large(error):
        return jsonify({
            'success': False,
            'error': 'Файл слишком большой. Максимальный размер: 50MB'
        }), 413
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'success': False,
            'error': 'Слишком много запросов. Попробуйте позже'
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Внутренняя ошибка сервера: {error}")
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"Необработанное исключение: {error}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Произошла непредвиденная ошибка'
        }), 500


# ==================== MIDDLEWARE ====================

def setup_middleware(app):
    """Настройка middleware для Flask приложения"""
    
    @app.before_request
    def handle_preflight():
        """Обработка preflight OPTIONS запросов"""
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
    
    @app.after_request
    def after_request(response):
        """Добавление CORS заголовков к ответам"""
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    @app.before_request
    def log_request():
        """Логирование входящих запросов"""
        logger.debug(f"📥 {request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def log_response(response):
        """Логирование исходящих ответов"""
        logger.debug(f"📤 {response.status_code} for {request.method} {request.path}")
        return response


# ==================== ВАЛИДАЦИЯ ====================

def validate_phone(phone: str) -> bool:
    """Валидация номера телефона"""
    # Убираем все символы кроме цифр
    digits = ''.join(filter(str.isdigit, phone))
    
    # Проверяем длину (российский номер)
    if len(digits) == 11 and digits[0] in ['7', '8']:
        return True
    elif len(digits) == 10:
        return True
    
    return False


def validate_email(email: str) -> bool:
    """Простая валидация email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Очистка пользовательского ввода"""
    if not text:
        return ""
    
    # Обрезаем до максимальной длины
    text = text[:max_length]
    
    # Убираем опасные символы
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    # Убираем лишние пробелы
    text = ' '.join(text.split())
    
    return text.strip()


# ==================== РАБОТА С ФАЙЛАМИ ====================

def ensure_directories():
    """Создание необходимых директорий"""
    directories = [
        'templates',
        'static/css',
        'static/js',
        'static/images',
        'uploads',
        'backups',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"📁 Директория {directory} готова")


def cleanup_old_files(directory: str, days: int = 30):
    """Удаление старых файлов"""
    if not os.path.exists(directory):
        return 0
    
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        
        # Пропускаем директории
        if os.path.isdir(filepath):
            continue
        
        # Проверяем время модификации
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        if mtime < cutoff:
            try:
                os.remove(filepath)
                removed += 1
                logger.info(f"🗑️ Удалён старый файл: {filename}")
            except Exception as e:
                logger.error(f"Ошибка удаления файла {filename}: {e}")
    
    return removed


def get_file_hash(filepath: str) -> str:
    """Получение хеша файла"""
    hash_md5 = hashlib.md5()
    
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    
    return hash_md5.hexdigest()


# ==================== РАБОТА С ДАННЫМИ ====================

def format_datetime(dt: datetime, format: str = '%d.%m.%Y %H:%M') -> str:
    """Форматирование даты и времени"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except:
            return dt
    
    return dt.strftime(format)


def parse_datetime(date_string: str) -> Optional[datetime]:
    """Парсинг строки в datetime"""
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%d.%m.%Y %H:%M:%S',
        '%d.%m.%Y %H:%M',
        '%d.%m.%Y',
        '%d/%m/%Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    return None


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Обрезка текста с добавлением суффикса"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.2f} TB"


# ==================== СЕТЕВЫЕ ФУНКЦИИ ====================

def get_client_ip(request) -> str:
    """Получение реального IP клиента"""
    # Проверяем заголовки прокси
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers['X-Real-IP']
    else:
        return request.remote_addr or 'unknown'


def test_proxy(proxy_url: str, timeout: int = 5) -> bool:
    """Тестирование прокси сервера"""
    try:
        test_url = 'http://httpbin.org/ip'
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        response = requests.get(test_url, proxies=proxies, timeout=timeout)
        return response.status_code == 200
    except:
        return False


# ==================== КРИПТОГРАФИЯ ====================

def generate_token(length: int = 32) -> str:
    """Генерация случайного токена"""
    import secrets
    return secrets.token_hex(length // 2)


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    import bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Проверка пароля"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# ==================== МОНИТОРИНГ ====================

def get_system_info() -> Dict:
    """Получение информации о системе"""
    import platform
    import psutil
    
    return {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'python_version': platform.python_version(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent
    }


def check_dependencies() -> Dict[str, bool]:
    """Проверка зависимостей"""
    dependencies = {
        'flask': False,
        'requests': False,
        'sqlite3': False,
        'logging': False
    }
    
    for module_name in dependencies.keys():
        try:
            __import__(module_name)
            dependencies[module_name] = True
        except ImportError:
            dependencies[module_name] = False
    
    return dependencies
