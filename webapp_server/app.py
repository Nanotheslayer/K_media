"""
Главное Flask приложение для Telegram Web App Кировец Медиа
"""
import os
import sys
import logging
from flask import Flask
from flask_cors import CORS

# Добавляем родительскую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp_server.config import (
    PORT, DEBUG, SECRET_KEY, MAX_CONTENT_LENGTH, 
    UPLOAD_FOLDER, CORS_ORIGINS, CORS_METHODS, CORS_HEADERS,
    LOG_FILE, LOG_LEVEL, LOG_FORMAT,
    APP_NAME, APP_VERSION
)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler(LOG_FILE, encoding='utf-8')  # Вывод в файл
    ]
)
logger = logging.getLogger(__name__)


def create_app():
    """Фабрика приложения Flask"""
    logger.info(f"🚀 Создание приложения {APP_NAME} v{APP_VERSION}")
    
    # Создаем приложение Flask
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static',
                static_url_path='/static')
    
    # Конфигурация приложения
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # Настройка CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": CORS_ORIGINS,
            "methods": CORS_METHODS,
            "allow_headers": CORS_HEADERS
        }
    })
    
    # Инициализация компонентов
    initialize_components(app)
    
    # Регистрация blueprints
    register_blueprints(app)
    
    # Настройка middleware и обработчиков ошибок
    setup_app_handlers(app)
    
    logger.info(f"✅ Приложение {APP_NAME} создано успешно")
    
    return app


def initialize_components(app):
    """Инициализация компонентов приложения"""
    logger.info("🔧 Инициализация компонентов...")
    
    # Импортируем и инициализируем менеджеры
    from webapp_server.managers import key_manager, proxy_manager, user_manager
    from webapp_server.services import gemini_client
    from webapp_server.database import webapp_db
    
    # Проверяем состояние компонентов
    with app.app_context():
        # Проверка ключей
        keys_status = key_manager.get_keys_status()
        logger.info(f"🔑 API ключи: {keys_status['available_keys']}/{keys_status['total_keys']} доступно")
        
        # Проверка прокси
        proxy_stats = proxy_manager.get_proxy_stats()
        logger.info(f"🌐 Прокси: {proxy_stats['available_proxies']}/{proxy_stats['total_proxies']} доступно")
        
        # Проверка базы данных
        try:
            test_setting = webapp_db.get_setting('test')
            logger.info("✅ База данных подключена")
        except Exception as e:
            logger.warning(f"⚠️ Проблема с базой данных: {e}")
    
    # Сохраняем ссылки на компоненты в app.config для доступа из маршрутов
    app.config['key_manager'] = key_manager
    app.config['proxy_manager'] = proxy_manager
    app.config['user_manager'] = user_manager
    app.config['gemini_client'] = gemini_client
    app.config['webapp_db'] = webapp_db


def register_blueprints(app):
    """Регистрация всех blueprints"""
    logger.info("📝 Регистрация маршрутов...")
    
    from webapp_server.routes.main_routes import main_bp
    from webapp_server.routes.chat_routes import chat_bp
    from webapp_server.routes.admin_routes import admin_bp
    from webapp_server.routes.api_routes import api_bp
    
    # Регистрируем blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Логируем зарегистрированные маршруты
    logger.info(f"✅ Зарегистрировано маршрутов: {len(app.url_map._rules)}")
    
    # Выводим список маршрутов в debug режиме
    if DEBUG:
        logger.debug("📋 Список маршрутов:")
        for rule in app.url_map.iter_rules():
            logger.debug(f"  {rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")


def setup_app_handlers(app):
    """Настройка middleware и обработчиков ошибок"""
    logger.info("⚙️ Настройка обработчиков...")
    
    from webapp_server.utils.helpers import register_error_handlers, setup_middleware
    
    # Регистрируем обработчики ошибок
    register_error_handlers(app)
    
    # Настраиваем middleware
    setup_middleware(app)
    
    logger.info("✅ Обработчики настроены")


def check_environment():
    """Проверка окружения перед запуском"""
    logger.info("🔍 Проверка окружения...")
    
    # Проверяем необходимые директории
    from webapp_server.utils.helpers import ensure_directories
    ensure_directories()
    
    # Проверяем наличие необходимых файлов
    required_files = [
        'templates/index.html',
        'static/js/app.js',
        'static/js/chat.js',
        'static/css/styles.css'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.warning(f"⚠️ Отсутствуют файлы: {', '.join(missing_files)}")
    
    # Проверяем переменные окружения
    env_warnings = []
    
    if not os.getenv('BOT_TOKEN'):
        env_warnings.append("BOT_TOKEN не установлен (бот не будет работать)")
    
    if not os.getenv('ADMIN_ID'):
        env_warnings.append("ADMIN_ID не установлен (админ функции недоступны)")
    
    for warning in env_warnings:
        logger.warning(f"⚠️ {warning}")
    
    logger.info("✅ Проверка окружения завершена")


def print_startup_info():
    """Вывод информации при запуске"""
    from webapp_server.managers import key_manager, proxy_manager
    
    print("\n" + "="*60)
    print(f"🚀 {APP_NAME} v{APP_VERSION}")
    print("="*60)
    print(f"📍 Порт: {PORT}")
    print(f"🔧 Режим отладки: {DEBUG}")
    print(f"🕵️ Модель чата: Gemini 2.5 Pro")
    print("="*60)
    
    # Статус ключей
    keys_status = key_manager.get_keys_status()
    print(f"🔑 API ключи: {keys_status['available_keys']}/{keys_status['total_keys']} доступно")
    
    if keys_status['all_keys_unavailable']:
        print("   ⚠️ ВНИМАНИЕ: Все API ключи недоступны!")
    
    # Статус прокси
    proxy_stats = proxy_manager.get_proxy_stats()
    print(f"🌐 Прокси серверы: {proxy_stats['available_proxies']}/{proxy_stats['total_proxies']} доступно")
    
    for proxy_detail in proxy_stats['details'][:3]:  # Показываем первые 3
        status_emoji = "✅" if proxy_detail['status'] == 'available' else "⏰" if proxy_detail['status'] == 'cooldown' else "🚫"
        print(f"   {status_emoji} {proxy_detail['name']}: {proxy_detail['status']}")
    
    if len(proxy_stats['details']) > 3:
        print(f"   ... и ещё {len(proxy_stats['details']) - 3} прокси")
    
    print("="*60)
    print("📋 Доступные команды:")
    print("  🏠 /            - Главная страница")
    print("  💬 /api/chat    - API чата Шестерёнкин")
    print("  📰 /api/newspaper - Газета Кировец")
    print("  📅 /api/events  - Календарь событий")
    print("  📝 /api/feedback - Обратная связь")
    print("  🔧 /health      - Статус системы")
    print("="*60)
    
    if proxy_stats['available_proxies'] == 0:
        print("⚠️ ВНИМАНИЕ: Все прокси недоступны! Используется прямое соединение.")
    
    print("✅ Сервер готов к работе!")
    print(f"🌐 Откройте http://localhost:{PORT} в браузере")
    print("="*60 + "\n")


def run_server():
    """Запуск сервера"""
    try:
        # Проверяем окружение
        check_environment()
        
        # Создаем приложение
        app = create_app()
        
        # Выводим информацию о запуске
        print_startup_info()
        
        # Запускаем сервер
        logger.info(f"🌐 Запуск сервера на http://0.0.0.0:{PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
        
    except KeyboardInterrupt:
        logger.info("⚠️ Сервер остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    run_server()
