"""
Административные маршруты
"""
import logging
from flask import Blueprint, request, jsonify
from functools import wraps
from webapp_server.managers import user_manager, key_manager, proxy_manager
from webapp_server.database import webapp_db
from webapp_server.config import ADMIN_USER_ID

logger = logging.getLogger(__name__)

# Создаем Blueprint для админских маршрутов
admin_bp = Blueprint('admin', __name__)


def require_admin(f):
    """Декоратор для проверки админских прав"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Получаем токен из заголовка или параметров
        auth_token = request.headers.get('Authorization') or request.args.get('token')
        
        # TODO: Реализовать полноценную аутентификацию
        # Пока проверяем простой токен
        if not auth_token or auth_token != 'admin-secret-token':
            return jsonify({
                'success': False,
                'error': 'Unauthorized'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


# ==================== СТАТИСТИКА ====================

@admin_bp.route('/stats')
@require_admin
def admin_stats():
    """Общая статистика системы"""
    try:
        # Статистика пользователей
        user_stats = user_manager.get_stats()
        
        # Статистика ключей и прокси
        keys_status = key_manager.get_keys_status()
        proxy_stats = proxy_manager.get_proxy_stats()
        
        # Аналитика из БД
        analytics_summary = webapp_db.get_analytics_summary(days=7)
        
        return jsonify({
            'success': True,
            'stats': {
                'users': user_stats,
                'keys': keys_status,
                'proxies': proxy_stats,
                'analytics': analytics_summary
            }
        })
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статистики'
        }), 500


@admin_bp.route('/users')
@require_admin
def admin_users_stats():
    """Статистика пользователей"""
    try:
        stats = user_manager.get_stats()
        
        # Добавляем детальную информацию если запрошено
        if request.args.get('detailed') == 'true':
            # TODO: Добавить список активных пользователей
            pass
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Ошибка получения статистики пользователей: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статистики'
        }), 500


@admin_bp.route('/users/<user_id>')
@require_admin
def admin_user_details(user_id):
    """Детальная информация о пользователе"""
    try:
        user_data = user_manager.export_user_data(user_id)
        
        if not user_data:
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user_data
        })
    except Exception as e:
        logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения данных'
        }), 500


@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@require_admin
def admin_delete_user(user_id):
    """Удаление данных пользователя"""
    try:
        success = user_manager.delete_user_data(user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Данные пользователя {user_id} удалены'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден'
            }), 404
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка удаления'
        }), 500


# ==================== УПРАВЛЕНИЕ ПРОКСИ ====================

@admin_bp.route('/proxy')
@require_admin
def admin_proxy_management():
    """Управление прокси серверами"""
    try:
        proxy_stats = proxy_manager.get_proxy_stats()
        keys_stats = key_manager.get_keys_status()
        
        return jsonify({
            'success': True,
            'detailed_stats': {
                'proxies': proxy_stats,
                'keys': keys_stats,
                'recommendations': _get_system_recommendations(proxy_stats, keys_stats)
            }
        })
    except Exception as e:
        logger.error(f"Ошибка получения данных прокси: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения данных'
        }), 500


@admin_bp.route('/proxy/reload', methods=['POST'])
@require_admin
def admin_proxy_reload():
    """Перезагрузка конфигурации прокси"""
    try:
        proxy_manager.reload_config()
        
        return jsonify({
            'success': True,
            'message': 'Конфигурация прокси перезагружена',
            'stats': proxy_manager.get_proxy_stats()
        })
    except Exception as e:
        logger.error(f"Ошибка перезагрузки конфигурации: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка перезагрузки'
        }), 500


# ==================== УПРАВЛЕНИЕ КЛЮЧАМИ ====================

@admin_bp.route('/keys')
@require_admin
def admin_keys_management():
    """Управление API ключами"""
    try:
        keys_status = key_manager.get_keys_status()
        
        return jsonify({
            'success': True,
            'keys': keys_status
        })
    except Exception as e:
        logger.error(f"Ошибка получения статуса ключей: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статуса'
        }), 500


@admin_bp.route('/keys/rotate', methods=['POST'])
@require_admin
def admin_rotate_keys():
    """Ротация API ключей"""
    try:
        key_manager.rotate_keys()
        
        return jsonify({
            'success': True,
            'message': 'Ротация ключей выполнена',
            'status': key_manager.get_keys_status()
        })
    except Exception as e:
        logger.error(f"Ошибка ротации ключей: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка ротации'
        }), 500


@admin_bp.route('/keys/cleanup', methods=['POST'])
@require_admin
def admin_cleanup_keys():
    """Очистка кулдаунов ключей"""
    try:
        key_manager.cleanup_cooldowns()
        
        return jsonify({
            'success': True,
            'message': 'Кулдауны очищены',
            'status': key_manager.get_keys_status()
        })
    except Exception as e:
        logger.error(f"Ошибка очистки кулдаунов: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка очистки'
        }), 500


# ==================== УПРАВЛЕНИЕ ОБРАТНОЙ СВЯЗЬЮ ====================

@admin_bp.route('/feedback')
@require_admin
def admin_feedback_list():
    """Список обратной связи"""
    try:
        status = request.args.get('status', 'new')
        limit = int(request.args.get('limit', 100))
        
        feedback = webapp_db.get_feedback(status=status, limit=limit)
        
        return jsonify({
            'success': True,
            'feedback': feedback,
            'count': len(feedback)
        })
    except Exception as e:
        logger.error(f"Ошибка получения обратной связи: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения данных'
        }), 500


@admin_bp.route('/feedback/<int:feedback_id>/respond', methods=['POST'])
@require_admin
def admin_respond_feedback(feedback_id):
    """Ответ на обратную связь"""
    try:
        data = request.get_json()
        response = data.get('response')
        status = data.get('status', 'responded')
        
        if not response:
            return jsonify({
                'success': False,
                'error': 'Ответ обязателен'
            }), 400
        
        success = webapp_db.update_feedback_status(
            feedback_id=feedback_id,
            status=status,
            response=response
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Ответ сохранён'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Обращение не найдено'
            }), 404
            
    except Exception as e:
        logger.error(f"Ошибка сохранения ответа: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка сохранения'
        }), 500


# ==================== УПРАВЛЕНИЕ НАСТРОЙКАМИ ====================

@admin_bp.route('/settings')
@require_admin
def admin_get_settings():
    """Получение настроек приложения"""
    try:
        settings = webapp_db.get_all_settings()
        
        return jsonify({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        logger.error(f"Ошибка получения настроек: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения настроек'
        }), 500


@admin_bp.route('/settings', methods=['POST'])
@require_admin
def admin_update_settings():
    """Обновление настроек приложения"""
    try:
        data = request.get_json()
        
        for key, value in data.items():
            webapp_db.set_setting(key, str(value))
        
        return jsonify({
            'success': True,
            'message': 'Настройки обновлены',
            'settings': webapp_db.get_all_settings()
        })
    except Exception as e:
        logger.error(f"Ошибка обновления настроек: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка обновления'
        }), 500


# ==================== СИСТЕМНЫЕ ОПЕРАЦИИ ====================

@admin_bp.route('/system/cleanup', methods=['POST'])
@require_admin
def admin_system_cleanup():
    """Очистка системы"""
    try:
        # Очистка старых пользователей
        days = int(request.get_json().get('days', 30))
        removed_users = user_manager.cleanup_old_users(days=days)
        
        # Очистка кулдаунов
        key_manager.cleanup_cooldowns()
        
        return jsonify({
            'success': True,
            'message': 'Очистка выполнена',
            'removed_users': removed_users
        })
    except Exception as e:
        logger.error(f"Ошибка очистки системы: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка очистки'
        }), 500


@admin_bp.route('/system/logs')
@require_admin
def admin_system_logs():
    """Получение последних логов"""
    try:
        lines = int(request.args.get('lines', 100))
        
        # Читаем последние строки лог-файла
        with open('webapp_kyrov.log', 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            'success': True,
            'logs': recent_lines,
            'count': len(recent_lines)
        })
    except Exception as e:
        logger.error(f"Ошибка чтения логов: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка чтения логов'
        }), 500


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
    
    if not recommendations:
        recommendations.append("✅ Система работает оптимально")
    
    return recommendations
