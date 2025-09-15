"""
Маршруты для чата Шестерёнкин
"""
import logging
from flask import Blueprint, request, jsonify
from webapp_server.managers import key_manager, user_manager, proxy_manager
from webapp_server.services import gemini_client
from webapp_server.services.image_processor import ImageProcessor
from webapp_server.database import webapp_db

logger = logging.getLogger(__name__)

# Создаем Blueprint для чата
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat', methods=['POST'])
def chat_endpoint():
    """API для чата с Шестерёнкиным с уникальной идентификацией пользователей"""
    try:
        logger.info(f"Получен запрос к чату")
        logger.info(f"Content-Type: {request.content_type}")

        # Проверяем наличие файлов в запросе
        has_image = 'image' in request.files
        logger.info(f"Наличие изображения: {has_image}")

        # Получаем данные в зависимости от типа запроса
        message = None
        user_id = None

        # Проверяем разные способы получения данных
        if request.is_json:
            # JSON запрос
            data = request.get_json(force=True) or {}
            message = data.get('message', '')
            # Поддерживаем оба варианта параметра
            user_id = data.get('user_id') or data.get('telegram_user_id', '')
            logger.info("Данные получены из JSON")

        elif request.form:
            # Form data (multipart/form-data или application/x-www-form-urlencoded)
            message = request.form.get('message', '')
            # Поддерживаем оба варианта параметра
            user_id = request.form.get('user_id') or request.form.get('telegram_user_id', '')
            logger.info("Данные получены из form data")
            logger.info(f"Form data keys: {list(request.form.keys())}")
            logger.info(f"Form values: message='{message[:50] if message else 'empty'}', user_id='{user_id}'")

        else:
            # Пробуем принудительно получить JSON даже без правильного Content-Type
            try:
                data = request.get_json(force=True, silent=True) or {}
                message = data.get('message', '')
                # Поддерживаем оба варианта параметра
                user_id = data.get('user_id') or data.get('telegram_user_id', '')
                logger.info("Данные получены принудительно как JSON")
            except:
                # Если ничего не получилось, пробуем получить raw data
                import json
                try:
                    raw_data = request.get_data(as_text=True)
                    if raw_data:
                        data = json.loads(raw_data)
                        message = data.get('message', '')
                        # Поддерживаем оба варианта параметра
                        user_id = data.get('user_id') or data.get('telegram_user_id', '')
                        logger.info("Данные получены из raw data")
                except Exception as parse_error:
                    logger.error(f"Ошибка парсинга raw data: {parse_error}")
                    pass

        # Дополнительно проверяем заголовки для user_id
        if not user_id:
            user_id = request.headers.get('X-Telegram-User-Id')
            if user_id:
                logger.info("User ID получен из заголовка X-Telegram-User-Id")

        # Валидация входных данных
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Не указан user_id или telegram_user_id'
            }), 400

        if not message and not has_image:
            return jsonify({
                'success': False,
                'error': 'Отправьте сообщение или изображение'
            }), 400

        # Логирование для диагностики
        logger.info(
            f"🔍 Обработка запроса: user_id={user_id}, message_length={len(message) if message else 0}, has_image={has_image}")

        # Обработка изображения если есть
        image_data = None
        if has_image:
            try:
                image_file = request.files['image']
                logger.info(f"🖼️ Обработка изображения: {image_file.filename}")

                # Логируем размер файла если возможно
                try:
                    image_file.seek(0, 2)  # Перемещаемся в конец
                    file_size = image_file.tell()
                    image_file.seek(0)  # Возвращаемся в начало
                    logger.info(f"📏 Размер изображения: {file_size} байт ({file_size / (1024 * 1024):.2f} MB)")
                except:
                    logger.info("📏 Не удалось определить размер файла")

                # Используем правильный статический метод
                image_data, error = ImageProcessor.process_uploaded_image(image_file)

                if error:
                    logger.error(f"❌ Ошибка обработки изображения: {error}")
                    return jsonify({
                        'success': False,
                        'error': f'Ошибка обработки изображения: {error}'
                    }), 400

                if image_data:
                    # Получаем информацию об обработанном изображении
                    image_info = ImageProcessor.get_image_info(image_data)
                    logger.info(f"✅ Изображение обработано: {image_info}")
                else:
                    logger.error("❌ Изображение не было обработано")
                    return jsonify({
                        'success': False,
                        'error': 'Не удалось обработать изображение'
                    }), 400

            except Exception as e:
                logger.error(f"💥 Критическая ошибка обработки изображения: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': 'Ошибка обработки изображения'
                }), 400

        # Проверяем доступность системы
        keys_status = key_manager.get_keys_status()
        if keys_status['all_keys_unavailable']:
            return jsonify({
                'success': False,
                'error': 'Шестерёнкин временно недоступен, попробуйте позже'
            }), 503

        # Получаем настройки и историю пользователя
        settings = user_manager.get_user_settings(user_id)
        history = user_manager.get_gemini_formatted_history(user_id, limit=10)
        logger.info(f"User settings: {settings}")
        logger.info(f"History length: {len(history)}")

        logger.info(f"🕵️ Обрабатываем запрос от {user_id}: {message[:50] if message else 'изображение'}...")

        # Отправляем запрос к Gemini
        response_text, error = gemini_client.send_message(
            user_history=history,
            message=message,
            image_data=image_data,
            use_google_search=settings['use_google_search'],
            use_url_context=settings['use_url_context'],
            use_persona=settings['use_persona']
        )

        logger.info(f"Gemini response: error={error}, response_length={len(response_text) if response_text else 0}")

        if response_text and len(response_text) > 0:
            logger.info(f"🔍 FALLBACK DEBUG - первые 100 символов ответа: {repr(response_text[:100])}")

        if error:
            error_messages = {
                "all_keys_unavailable": ("Шестерёнкин временно недоступен, попробуйте позже", 503),
                "key_blocked": ("Попробуйте повторить запрос", 429),
                "max_retries_exceeded": ("Не удалось получить ответ, попробуйте позже", 503),
                "proxy_unavailable": ("Проблема с соединением, попробуйте позже", 503),
                "empty_message": ("Пожалуйста, введите сообщение или прикрепите изображение", 400),
                "empty_response": ("Не удалось сгенерировать ответ, попробуйте переформулировать вопрос", 500),
                "safety_block": ("Ваш запрос был заблокирован системой безопасности", 400),
                "invalid_request": ("Неверный формат запроса", 400)
            }

            error_msg, status_code = error_messages.get(error, ("Произошла ошибка при обработке запроса", 500))
            logger.error(f"Ошибка обработки: {error} - {error_msg}")

            return jsonify({
                'success': False,
                'error': error_msg
            }), status_code

        # Сохраняем в историю
        user_manager.add_to_history(user_id, message if message else "[Изображение]", response_text)

        # Обновляем статистику
        user_manager.update_stats(user_id)

        return jsonify({
            'success': True,
            'response': response_text,
            'user_id': user_id
        })

    except Exception as e:
        logger.error(f"Критическая ошибка в chat_endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Произошла внутренняя ошибка сервера'
        }), 500


@chat_bp.route('/chat/settings', methods=['GET', 'POST'])
def chat_settings():
    """API для управления настройками чата пользователя"""
    try:
        # Получаем user_id из разных источников
        user_id = None

        if request.method == 'GET':
            user_id = request.args.get('user_id') or request.args.get('telegram_user_id')
        else:  # POST
            if request.is_json:
                data = request.get_json(force=True) or {}
                user_id = data.get('user_id') or data.get('telegram_user_id')
            elif request.form:
                user_id = request.form.get('user_id') or request.form.get('telegram_user_id')
            else:
                try:
                    data = request.get_json(force=True, silent=True) or {}
                    user_id = data.get('user_id') or data.get('telegram_user_id')
                except:
                    pass

        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Не указан user_id или telegram_user_id'
            }), 400

        if request.method == 'GET':
            settings = user_manager.get_user_settings(user_id)
            return jsonify({
                'success': True,
                'settings': settings,
                'user_id': user_id
            })

        elif request.method == 'POST':
            # Получаем данные настроек
            if request.is_json:
                data = request.get_json(force=True) or {}
            elif request.form:
                data = dict(request.form)
            else:
                try:
                    data = request.get_json(force=True, silent=True) or {}
                except:
                    data = {}

            new_settings = {
                'use_google_search': data.get('use_google_search', True),
                'use_url_context': data.get('use_url_context', True),
                'use_persona': data.get('use_persona', True)
            }

            # Преобразуем строковые значения в boolean если нужно
            for key in new_settings:
                if isinstance(new_settings[key], str):
                    new_settings[key] = new_settings[key].lower() in ['true', '1', 'yes', 'on']

            user_manager.update_user_settings(user_id, new_settings)

            return jsonify({
                'success': True,
                'message': 'Настройки обновлены',
                'settings': new_settings,
                'user_id': user_id
            })

    except Exception as e:
        logger.error(f"Ошибка в chat_settings: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка работы с настройками'
        }), 500


@chat_bp.route('/chat/history', methods=['GET'])
def chat_history():
    """API для получения истории чата пользователя"""
    try:
        # Поддерживаем оба варианта параметра для совместимости
        user_id = request.args.get('user_id') or request.args.get('telegram_user_id')
        limit = int(request.args.get('limit', 10))

        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Не указан user_id или telegram_user_id'
            }), 400

        # Возвращаем оригинальную историю для API (не конвертированную)
        raw_history = user_manager.get_user_history(user_id, limit)

        # Но также можем предоставить конвертированную версию
        gemini_history = user_manager.get_gemini_formatted_history(user_id, limit)

        return jsonify({
            'success': True,
            'history': raw_history,  # Оригинальная история для отображения
            'gemini_history': gemini_history,  # Конвертированная для отладки
            'count': len(raw_history),
            'user_id': user_id
        })

    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения истории'
        }), 500


@chat_bp.route('/chat/clear', methods=['POST'])
@chat_bp.route('/chat/history/clear', methods=['POST'])  # Добавляем альтернативный маршрут
def clear_chat():
    """API для очистки истории чата пользователя"""
    try:
        # Получаем user_id из разных источников
        user_id = None

        if request.is_json:
            data = request.get_json(force=True) or {}
            # Поддерживаем оба варианта параметра
            user_id = data.get('user_id') or data.get('telegram_user_id')
        elif request.form:
            user_id = request.form.get('user_id') or request.form.get('telegram_user_id')
        else:
            try:
                data = request.get_json(force=True, silent=True) or {}
                user_id = data.get('user_id') or data.get('telegram_user_id')
            except:
                import json
                try:
                    raw_data = request.get_data(as_text=True)
                    if raw_data:
                        data = json.loads(raw_data)
                        user_id = data.get('user_id') or data.get('telegram_user_id')
                except:
                    pass

        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Не указан user_id или telegram_user_id'
            }), 400

        user_manager.clear_user_history(user_id)

        return jsonify({
            'success': True,
            'message': 'История чата очищена',
            'user_id': user_id
        })

    except Exception as e:
        logger.error(f"Ошибка очистки истории: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка очистки истории'
        }), 500


@chat_bp.route('/chat/status')
def chat_status():
    """API для получения статуса чата"""
    try:
        keys_status = key_manager.get_keys_status()
        proxy_stats = proxy_manager.get_proxy_stats()
        
        is_available = not keys_status['all_keys_unavailable'] and (
            proxy_stats['available_proxies'] > 0 or 
            proxy_stats.get('direct_connection_enabled', True)
        )
        
        return jsonify({
            'success': True,
            'status': {
                'available': is_available,
                'keys_available': keys_status['available_keys'],
                'total_keys': keys_status['total_keys'],
                'proxies_available': proxy_stats['available_proxies'],
                'total_proxies': proxy_stats['total_proxies'],
                'direct_connection': proxy_stats.get('direct_connection_enabled', True)
            }
        })
    except Exception as e:
        logger.error(f"Ошибка получения статуса чата: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статуса'
        }), 500
