"""
API маршруты для газеты, календаря и обратной связи
"""
import logging
from flask import Blueprint, request, jsonify
from webapp_server.database import webapp_db
from webapp_server.managers import proxy_manager, key_manager

logger = logging.getLogger(__name__)

# Создаем Blueprint для API
api_bp = Blueprint('api', __name__)


# ==================== ГАЗЕТА ====================

@api_bp.route('/newspaper')
def get_newspaper():
    """API для получения статей газеты"""
    try:
        # Получаем параметры запроса
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        category = request.args.get('category')
        
        # Получаем статьи из базы данных
        articles = webapp_db.get_newspaper_articles(
            limit=limit, 
            offset=offset, 
            category=category
        )
        
        return jsonify({
            'success': True,
            'articles': articles,
            'count': len(articles),
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Ошибка получения статей: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статей'
        }), 500


@api_bp.route('/newspaper/<int:article_id>')
def get_article(article_id):
    """API для получения конкретной статьи"""
    try:
        article = webapp_db.get_article_by_id(article_id)
        
        if not article:
            return jsonify({
                'success': False,
                'error': 'Статья не найдена'
            }), 404
        
        return jsonify({
            'success': True,
            'article': article
        })
    except Exception as e:
        logger.error(f"Ошибка получения статьи {article_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статьи'
        }), 500


@api_bp.route('/newspaper', methods=['POST'])
def create_article():
    """API для создания новой статьи (требует авторизации)"""
    try:
        # TODO: Добавить проверку авторизации
        data = request.get_json()
        
        required_fields = ['title', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Поле {field} обязательно'
                }), 400
        
        article_id = webapp_db.add_article(
            title=data['title'],
            content=data['content'],
            author=data.get('author'),
            category=data.get('category'),
            image_url=data.get('image_url'),
            published_date=data.get('published_date')
        )
        
        return jsonify({
            'success': True,
            'article_id': article_id,
            'message': 'Статья успешно создана'
        })
    except Exception as e:
        logger.error(f"Ошибка создания статьи: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка создания статьи'
        }), 500


# ==================== КАЛЕНДАРЬ ====================

@api_bp.route('/events')
def get_events():
    """API для получения событий календаря"""
    try:
        # Получаем параметры запроса
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        upcoming = request.args.get('upcoming', 'false').lower() == 'true'
        
        if upcoming:
            # Получаем предстоящие события
            days = int(request.args.get('days', 7))
            limit = int(request.args.get('limit', 10))
            events = webapp_db.get_upcoming_events(days=days, limit=limit)
        else:
            # Получаем события по фильтрам
            events = webapp_db.get_events(
                start_date=start_date,
                end_date=end_date,
                category=category
            )
        
        return jsonify({
            'success': True,
            'events': events,
            'count': len(events)
        })
    except Exception as e:
        logger.error(f"Ошибка получения событий: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения событий'
        }), 500


@api_bp.route('/events', methods=['POST'])
def create_event():
    """API для создания нового события (требует авторизации)"""
    try:
        # TODO: Добавить проверку авторизации
        data = request.get_json()
        
        required_fields = ['title', 'event_date']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Поле {field} обязательно'
                }), 400
        
        event_id = webapp_db.add_event(
            title=data['title'],
            event_date=data['event_date'],
            description=data.get('description'),
            event_time=data.get('event_time'),
            location=data.get('location'),
            category=data.get('category'),
            is_recurring=data.get('is_recurring', False),
            recurrence_pattern=data.get('recurrence_pattern')
        )
        
        return jsonify({
            'success': True,
            'event_id': event_id,
            'message': 'Событие успешно создано'
        })
    except Exception as e:
        logger.error(f"Ошибка создания события: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка создания события'
        }), 500


@api_bp.route('/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """API для удаления события (требует авторизации)"""
    try:
        # TODO: Добавить проверку авторизации
        success = webapp_db.delete_event(event_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Событие успешно удалено'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Событие не найдено'
            }), 404
    except Exception as e:
        logger.error(f"Ошибка удаления события {event_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка удаления события'
        }), 500


# ==================== ОБРАТНАЯ СВЯЗЬ ====================

@api_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """API для отправки обратной связи"""
    try:
        data = request.get_json()
        
        # Получаем данные
        user_name = data.get('name', '').strip()
        department = data.get('department', '').strip()
        phone = data.get('phone', '').strip()
        message = data.get('message', '').strip()
        category = data.get('category', 'general')
        
        # Валидация
        if not message:
            return jsonify({
                'success': False,
                'error': 'Сообщение обязательно для заполнения'
            }), 400
        
        if not user_name and not department and not phone:
            return jsonify({
                'success': False,
                'error': 'Укажите имя или контактную информацию'
            }), 400
        
        # Сохраняем в базу данных
        feedback_id = webapp_db.save_feedback(
            user_name=user_name,
            department=department,
            phone=phone,
            message=message,
            category=category
        )
        
        # Логируем действие
        webapp_db.log_action(
            user_id=user_name or 'anonymous',
            action='feedback_submitted',
            details=f'Category: {category}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Спасибо! Ваше обращение передано в редакцию.',
            'feedback_id': feedback_id
        })
        
    except Exception as e:
        logger.error(f"Ошибка отправки обратной связи: {e}")
        return jsonify({
            'success': False,
            'error': 'Произошла ошибка при отправке обращения'
        }), 500


@api_bp.route('/feedback')
def get_feedback_list():
    """API для получения списка обратной связи (требует авторизации)"""
    try:
        # TODO: Добавить проверку авторизации
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
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
            'error': 'Ошибка получения обратной связи'
        }), 500


# ==================== ПРОКСИ СТАТУС ====================

@api_bp.route('/proxy/status')
def proxy_status():
    """API для получения статуса прокси серверов"""
    try:
        proxy_stats = proxy_manager.get_proxy_stats()
        keys_stats = key_manager.get_keys_status()
        
        return jsonify({
            'success': True,
            'proxy_stats': proxy_stats,
            'keys_stats': keys_stats,
            'overall_status': {
                'healthy': proxy_stats['available_proxies'] > 0 and not keys_stats['all_keys_unavailable'],
                'proxy_available': proxy_stats['available_proxies'] > 0,
                'keys_available': not keys_stats['all_keys_unavailable']
            }
        })
    except Exception as e:
        logger.error(f"Ошибка получения статуса прокси: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статуса'
        }), 500


# ==================== ТЕСТОВЫЕ ЭНДПОИНТЫ ====================

@api_bp.route('/test/health')
def test_health():
    """Тестовый эндпоинт для проверки API"""
    from webapp_server.config import APP_VERSION
    
    return jsonify({
        'success': True,
        'status': 'API работает',
        'version': APP_VERSION,
        'endpoints': {
            'newspaper': '/api/newspaper',
            'events': '/api/events',
            'feedback': '/api/feedback',
            'chat': '/api/chat',
            'proxy_status': '/api/proxy/status'
        }
    })


@api_bp.route('/test/echo', methods=['POST'])
def test_echo():
    """Эхо-эндпоинт для тестирования POST запросов"""
    return jsonify({
        'success': True,
        'method': request.method,
        'data': request.get_json(),
        'args': dict(request.args),
        'headers': dict(request.headers)
    })
