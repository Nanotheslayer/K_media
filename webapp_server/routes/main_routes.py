"""
Основные маршруты приложения
"""
import logging
from flask import Blueprint, render_template, send_from_directory, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

# Создаем Blueprint для основных маршрутов
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Главная страница Web App"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Ошибка загрузки главной страницы: {e}")
        return jsonify({
            'error': 'Ошибка загрузки страницы'
        }), 500


@main_bp.route('/static/<path:filename>')
def static_files(filename):
    """Обслуживание статических файлов"""
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        logger.error(f"Ошибка загрузки статического файла {filename}: {e}")
        return jsonify({
            'error': 'Файл не найден'
        }), 404


@main_bp.route('/health')
def health_check():
    """Проверка работоспособности сервера"""
    from webapp_server.managers import key_manager, proxy_manager
    from webapp_server.config import APP_VERSION, APP_NAME
    
    try:
        keys_status = key_manager.get_keys_status()
        proxy_stats = proxy_manager.get_proxy_stats()
        
        # Определяем общее состояние здоровья
        is_healthy = (
            not keys_status['all_keys_unavailable'] and 
            (proxy_stats['available_proxies'] > 0 or 
             proxy_stats.get('direct_connection_enabled', True))
        )
        
        return jsonify({
            'status': 'healthy' if is_healthy else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'service': APP_NAME,
            'version': APP_VERSION,
            'chat_available': is_healthy,
            'details': {
                'api_keys': f"{keys_status['available_keys']}/{keys_status['total_keys']} available",
                'proxies': f"{proxy_stats['available_proxies']}/{proxy_stats['total_proxies']} available",
                'direct_connection': proxy_stats.get('direct_connection_enabled', True),
                'blocked_proxies': proxy_stats['blocked_proxies'],
                'cooldown_proxies': proxy_stats['cooldown_proxies']
            },
            'recommendations': _get_system_recommendations(proxy_stats, keys_status)
        })
    except Exception as e:
        logger.error(f"Ошибка проверки здоровья: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@main_bp.route('/test')
def test_endpoint():
    """Тестовый эндпоинт для проверки"""
    return jsonify({
        'status': 'ok',
        'message': 'Сервер работает',
        'timestamp': datetime.now().isoformat()
    })


@main_bp.route('/version')
def version():
    """Информация о версии приложения"""
    from webapp_server.config import APP_VERSION, APP_NAME, APP_DESCRIPTION, FEATURES
    
    return jsonify({
        'name': APP_NAME,
        'version': APP_VERSION,
        'description': APP_DESCRIPTION,
        'features': FEATURES,
        'timestamp': datetime.now().isoformat()
    })


@main_bp.route('/robots.txt')
def robots_txt():
    """Robots.txt для поисковиков"""
    return """User-agent: *
Disallow: /api/
Disallow: /admin/
Disallow: /static/
Allow: /
""", 200, {'Content-Type': 'text/plain'}


# Вспомогательные функции

def _get_system_recommendations(proxy_stats, keys_stats):
    """Генерация рекомендаций по оптимизации системы"""
    recommendations = []
    
    if proxy_stats['available_proxies'] == 0:
        recommendations.append("🚨 Критично: Все прокси недоступны!")
    elif proxy_stats['available_proxies'] == 1:
        recommendations.append("⚠️ Только один прокси доступен - добавьте резервные")
    
    if keys_stats['all_keys_unavailable']:
        recommendations.append("🚨 Критично: Все API ключи недоступны!")
    elif keys_stats['available_keys'] <= 1:
        recommendations.append("⚠️ Мало доступных ключей - проверьте лимиты")
    
    if proxy_stats['blocked_proxies'] > 2:
        recommendations.append("📊 Много заблокированных прокси - проверьте их работоспособность")
    
    if proxy_stats['cooldown_proxies'] > 0:
        recommendations.append(f"⏰ {proxy_stats['cooldown_proxies']} прокси в кулдауне")
    
    if not recommendations:
        recommendations.append("✅ Система работает оптимально")
    
    return recommendations
