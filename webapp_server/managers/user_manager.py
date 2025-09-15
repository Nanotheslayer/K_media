"""
Менеджер пользователей и их данных
"""
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class UserManager:
    """Менеджер пользователей для отслеживания истории, настроек и статистики"""

    def __init__(self, max_history_length: int = 10):
        self.max_history_length = max_history_length
        self.users_data: Dict[str, Dict] = {}
        self.user_stats: Dict[str, Dict] = defaultdict(lambda: {
            'total_messages': 0,
            'first_seen': None,
            'last_seen': None,
            'total_images': 0,
            'total_chars_sent': 0,
            'total_chars_received': 0,
            'session_count': 0
        })
        self._load_user_data()

    def _load_user_data(self):
        """Загрузка данных пользователей из файла"""
        try:
            with open('users_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.users_data = data.get('users', {})
                self.user_stats = defaultdict(
                    lambda: {
                        'total_messages': 0,
                        'first_seen': None,
                        'last_seen': None,
                        'total_images': 0,
                        'total_chars_sent': 0,
                        'total_chars_received': 0,
                        'session_count': 0
                    },
                    data.get('stats', {})
                )
                logger.info(f"📊 Загружены данные {len(self.users_data)} пользователей")
        except FileNotFoundError:
            logger.info("📁 Файл данных пользователей не найден, создаём новый")
        except Exception as e:
            logger.error(f"Ошибка загрузки данных пользователей: {e}")

    def _save_user_data(self):
        """Сохранение данных пользователей в файл"""
        try:
            data = {
                'users': self.users_data,
                'stats': dict(self.user_stats),
                'last_updated': time.time()
            }
            with open('users_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных пользователей: {e}")

    def get_or_create_user(self, user_id: str) -> Dict:
        """Получение или создание данных пользователя"""
        if user_id not in self.users_data:
            self.users_data[user_id] = {
                'user_id': user_id,
                'history': [],
                'settings': {
                    'use_google_search': True,
                    'use_url_context': True,
                    'use_persona': True,
                    'stream_response': False
                },
                'created_at': time.time(),
                'last_active': time.time()
            }
            
            # Инициализируем статистику
            self.user_stats[user_id]['first_seen'] = time.time()
            self.user_stats[user_id]['session_count'] = 1
            
            logger.info(f"👤 Создан новый пользователь: {user_id}")
            self._save_user_data()
        
        return self.users_data[user_id]

    def get_user_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Получение истории сообщений пользователя"""
        user_data = self.get_or_create_user(user_id)
        history = user_data.get('history', [])
        
        if limit:
            return history[-limit:]
        return history

    def add_to_history(self, user_id: str, user_message: str, assistant_response: str, 
                       image_data: Optional[Dict] = None):
        """Добавление сообщения в историю пользователя"""
        user_data = self.get_or_create_user(user_id)
        
        # Создаём запись истории
        history_entry = {
            'timestamp': time.time(),
            'user': user_message,
            'assistant': assistant_response,
            'has_image': image_data is not None
        }
        
        # Добавляем в историю
        user_data['history'].append(history_entry)
        
        # Ограничиваем размер истории
        if len(user_data['history']) > self.max_history_length:
            user_data['history'] = user_data['history'][-self.max_history_length:]
        
        # Обновляем последнюю активность
        user_data['last_active'] = time.time()
        
        # Обновляем статистику
        stats = self.user_stats[user_id]
        stats['total_messages'] += 1
        stats['last_seen'] = time.time()
        stats['total_chars_sent'] += len(user_message)
        stats['total_chars_received'] += len(assistant_response)
        if image_data:
            stats['total_images'] += 1
        
        self._save_user_data()
        logger.debug(f"📝 Добавлено в историю пользователя {user_id}")

    def clear_user_history(self, user_id: str):
        """Очистка истории пользователя"""
        user_data = self.get_or_create_user(user_id)
        user_data['history'] = []
        user_data['last_active'] = time.time()
        
        # Увеличиваем счётчик сессий
        self.user_stats[user_id]['session_count'] += 1
        
        self._save_user_data()
        logger.info(f"🗑️ История пользователя {user_id} очищена")

    def get_user_settings(self, user_id: str) -> Dict:
        """Получение настроек пользователя"""
        user_data = self.get_or_create_user(user_id)
        return user_data.get('settings', {
            'use_google_search': True,
            'use_url_context': True,
            'use_persona': True,
            'stream_response': False
        })

    def update_user_settings(self, user_id: str, settings: Dict):
        """Обновление настроек пользователя"""
        user_data = self.get_or_create_user(user_id)
        user_data['settings'].update(settings)
        user_data['last_active'] = time.time()
        self._save_user_data()
        logger.info(f"⚙️ Обновлены настройки пользователя {user_id}")

    def update_stats(self, user_id: str, **kwargs):
        """Обновление статистики пользователя"""
        stats = self.user_stats[user_id]
        stats['last_seen'] = time.time()
        
        for key, value in kwargs.items():
            if key in stats:
                if isinstance(stats[key], (int, float)):
                    stats[key] += value
                else:
                    stats[key] = value
        
        self._save_user_data()

    def get_user_stats(self, user_id: str) -> Dict:
        """Получение статистики пользователя"""
        return dict(self.user_stats[user_id])

    def get_all_users_stats(self) -> Dict:
        """Получение общей статистики по всем пользователям"""
        total_users = len(self.users_data)
        active_today = 0
        active_week = 0
        total_messages = 0
        total_images = 0
        
        now = time.time()
        day_ago = now - 86400
        week_ago = now - 604800
        
        for user_id, stats in self.user_stats.items():
            last_seen = stats.get('last_seen', 0)
            if last_seen > day_ago:
                active_today += 1
            if last_seen > week_ago:
                active_week += 1
            total_messages += stats.get('total_messages', 0)
            total_images += stats.get('total_images', 0)
        
        return {
            'total_users': total_users,
            'active_today': active_today,
            'active_week': active_week,
            'total_messages': total_messages,
            'total_images': total_images,
            'average_messages_per_user': round(total_messages / max(total_users, 1), 1)
        }

    def get_stats(self) -> Dict:
        """Получение общей статистики"""
        return self.get_all_users_stats()

    def cleanup_old_users(self, days: int = 30):
        """Очистка данных неактивных пользователей"""
        cutoff_time = time.time() - (days * 86400)
        users_to_remove = []
        
        for user_id, user_data in self.users_data.items():
            if user_data.get('last_active', 0) < cutoff_time:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.users_data[user_id]
            if user_id in self.user_stats:
                del self.user_stats[user_id]
        
        if users_to_remove:
            logger.info(f"🧹 Удалены данные {len(users_to_remove)} неактивных пользователей")
            self._save_user_data()
        
        return len(users_to_remove)

    def export_user_data(self, user_id: str) -> Optional[Dict]:
        """Экспорт всех данных пользователя"""
        if user_id in self.users_data:
            return {
                'user_data': self.users_data[user_id],
                'stats': dict(self.user_stats[user_id]),
                'exported_at': time.time()
            }
        return None

    def delete_user_data(self, user_id: str) -> bool:
        """Полное удаление данных пользователя"""
        if user_id in self.users_data:
            del self.users_data[user_id]
            if user_id in self.user_stats:
                del self.user_stats[user_id]
            self._save_user_data()
            logger.info(f"🗑️ Все данные пользователя {user_id} удалены")
            return True
        return False

    def get_gemini_formatted_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Получение истории в формате, совместимом с Gemini API"""
        user_data = self.get_or_create_user(user_id)
        history = user_data.get('history', [])

        if limit:
            history = history[-limit:]

        # Конвертируем в формат Gemini API
        gemini_history = []

        for entry in history:
            # Пропускаем записи без необходимых полей
            if 'user' not in entry or 'assistant' not in entry:
                continue

            # Добавляем сообщение пользователя
            if entry['user'] and entry['user'].strip():
                user_parts = [{"text": entry['user']}]
                gemini_history.append({
                    "role": "user",
                    "parts": user_parts
                })

            # Добавляем ответ ассистента
            if entry['assistant'] and entry['assistant'].strip():
                model_parts = [{"text": entry['assistant']}]
                gemini_history.append({
                    "role": "model",
                    "parts": model_parts
                })

        logger.debug(
            f"📜 Конвертирована история для {user_id}: {len(history)} записей -> {len(gemini_history)} сообщений")
        return gemini_history