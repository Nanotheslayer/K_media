"""
Менеджер API ключей с оригинальной логикой ротации из webapp_kyrov_server.py
"""
import os
import json
import time
import random
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class KeyManager:
    """Менеджер API ключей с персистентным хранением состояния"""

    def __init__(self):
        self.keys_file = 'api_keys_state.json'
        self.keys = self._load_keys()
        self.current_key_index = 0
        self.blocked_keys: Set[str] = set()
        self.key_cooldowns: Dict[str, float] = {}  # key -> end_time
        self._load_state()

    def _load_keys(self) -> List[str]:
        """Загрузка API ключей из конфигурации или переменных окружения"""
        # Сначала пробуем загрузить из config
        from webapp_server.config import PREMIUM_UNLIMITED_KEYS
        
        keys = PREMIUM_UNLIMITED_KEYS.copy()
        
        # Добавляем ключи из переменных окружения если есть
        env_keys = os.getenv('GEMINI_API_KEYS', '').split(',')
        for key in env_keys:
            key = key.strip()
            if key and key not in keys:
                keys.append(key)
        
        logger.info(f"📋 Загружено {len(keys)} API ключей")
        return keys

    def _load_state(self):
        """Загрузка сохраненного состояния ключей"""
        try:
            if os.path.exists(self.keys_file):
                with open(self.keys_file, 'r') as f:
                    state = json.load(f)
                    self.blocked_keys = set(state.get('blocked_keys', []))
                    self.key_cooldowns = {
                        k: v for k, v in state.get('key_cooldowns', {}).items()
                        if v > time.time()  # Загружаем только активные кулдауны
                    }
                    logger.info(f"✅ Загружено состояние: {len(self.blocked_keys)} заблокированных, "
                               f"{len(self.key_cooldowns)} в кулдауне")
        except Exception as e:
            logger.error(f"Ошибка загрузки состояния ключей: {e}")

    def _save_state(self):
        """Сохранение состояния ключей"""
        try:
            state = {
                'blocked_keys': list(self.blocked_keys),
                'key_cooldowns': self.key_cooldowns,
                'last_updated': time.time()
            }
            with open(self.keys_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния ключей: {e}")

    def get_next_available_key(self) -> Optional[str]:
        """Получение следующего доступного API ключа - ОРИГИНАЛЬНАЯ ЛОГИКА"""
        if not self.keys:
            logger.error("Нет доступных API ключей")
            return None

        current_time = time.time()
        
        # Очищаем истекшие кулдауны
        self.key_cooldowns = {
            key: end_time for key, end_time in self.key_cooldowns.items()
            if end_time > current_time
        }

        # ОРИГИНАЛЬНАЯ ЛОГИКА: простой перебор ключей по кругу
        attempts = 0
        max_attempts = len(self.keys)

        while attempts < max_attempts:
            # Получаем текущий ключ
            key = self.keys[self.current_key_index]
            
            # Переходим к следующему ключу для следующего вызова
            self.current_key_index = (self.current_key_index + 1) % len(self.keys)
            attempts += 1
            
            # Проверяем блокировку
            if key in self.blocked_keys:
                continue
                
            # Проверяем кулдаун
            if key in self.key_cooldowns:
                remaining = int(self.key_cooldowns[key] - current_time)
                if remaining > 0:
                    logger.debug(f"Ключ в кулдауне еще {remaining} сек")
                    continue
            
            logger.debug(f"Используем ключ ...{key[-10:]}")
            return key

        logger.error("Все API ключи недоступны")
        return None

    def block_key(self, key: str, duration_minutes: int = 10):
        """Временная блокировка ключа на 10 минут (оригинальная логика)"""
        if key in self.keys:
            self.key_cooldowns[key] = time.time() + (duration_minutes * 60)
            logger.warning(f"🔒 Ключ ...{key[-10:]} заблокирован на {duration_minutes} минут")
            self._save_state()

    def permanently_block_key(self, key: str):
        """Постоянная блокировка ключа"""
        if key in self.keys:
            self.blocked_keys.add(key)
            logger.error(f"⛔ Ключ ...{key[-10:]} заблокирован навсегда")
            self._save_state()

    def unblock_key(self, key: str):
        """Разблокировка ключа"""
        if key in self.blocked_keys:
            self.blocked_keys.remove(key)
        if key in self.key_cooldowns:
            del self.key_cooldowns[key]
        logger.info(f"🔓 Ключ ...{key[-10:]} разблокирован")
        self._save_state()

    def report_key_error(self, key: str, error_code: Optional[int] = None):
        """Сообщить об ошибке использования ключа - ОРИГИНАЛЬНАЯ ЛОГИКА"""
        if error_code == 429:  # Rate limit - блокируем на 10 минут
            self.block_key(key, duration_minutes=10)
        elif error_code == 403:  # Forbidden - возможно ключ невалидный
            self.permanently_block_key(key)
        elif error_code == 400:  # Bad request - временная блокировка на 5 минут
            self.block_key(key, duration_minutes=5)

    def get_keys_status(self) -> Dict:
        """Получение статуса всех ключей"""
        current_time = time.time()
        
        available_keys = 0
        blocked_keys = len(self.blocked_keys)
        cooldown_keys = 0
        
        for key in self.keys:
            if key in self.blocked_keys:
                continue
            elif key in self.key_cooldowns and self.key_cooldowns[key] > current_time:
                cooldown_keys += 1
            else:
                available_keys += 1
        
        return {
            'total_keys': len(self.keys),
            'available_keys': available_keys,
            'blocked_keys': blocked_keys,
            'cooldown_keys': cooldown_keys,
            'all_keys_unavailable': available_keys == 0,
            'details': self._get_detailed_status()
        }

    def _get_detailed_status(self) -> List[Dict]:
        """Получение детальной информации о каждом ключе"""
        current_time = time.time()
        details = []
        
        for i, key in enumerate(self.keys):
            status = 'available'
            cooldown_remaining = 0
            
            if key in self.blocked_keys:
                status = 'blocked'
            elif key in self.key_cooldowns:
                if self.key_cooldowns[key] > current_time:
                    status = 'cooldown'
                    cooldown_remaining = int(self.key_cooldowns[key] - current_time)
            
            details.append({
                'index': i,
                'key_suffix': f"...{key[-10:]}",
                'status': status,
                'cooldown_remaining': cooldown_remaining
            })
        
        return details

    def cleanup_cooldowns(self):
        """Очистка истекших кулдаунов"""
        current_time = time.time()
        before = len(self.key_cooldowns)
        
        self.key_cooldowns = {
            key: end_time for key, end_time in self.key_cooldowns.items()
            if end_time > current_time
        }
        
        after = len(self.key_cooldowns)
        if before != after:
            logger.info(f"🧹 Очищено {before - after} истекших кулдаунов")
            self._save_state()

    def rotate_keys(self):
        """Принудительная ротация ключей - просто сброс индекса"""
        self.current_key_index = 0
        logger.info("🔄 Выполнена ротация ключей")
