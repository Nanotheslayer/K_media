"""
Менеджер прокси серверов с автоматическим переключением и конфигурацией
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ProxyManager:
    """Менеджер прокси серверов с автоматическим переключением и конфигурацией"""
    
    def __init__(self, config_file: str = "proxy_config.json"):
        self.config_file = config_file
        self.proxies = []
        self.settings = {}
        self.proxy_stats = {}
        self.current_proxy_index = 0
        self.blocked_proxies: Set[int] = set()
        self.proxy_cooldowns: Dict[str, float] = {}  # proxy_name -> end_time
        
        # Загружаем конфигурацию
        self._load_config()
        
        # Инициализируем статистику
        self._initialize_stats()
    
    def _load_config(self):
        """Загрузка конфигурации прокси"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # Загружаем только включенные прокси
                self.proxies = [
                    proxy for proxy in config.get('proxies', [])
                    if proxy.get('enabled', True)
                ]
                
                # Сортируем по приоритету
                self.proxies.sort(key=lambda x: x.get('priority', 999))
                
                # Загружаем настройки
                self.settings = config.get('settings', {})
                
                logger.info(f"✅ Загружено {len(self.proxies)} прокси из конфигурации")
            else:
                # Создаем дефолтную конфигурацию
                self._create_default_config()
                self._load_config()  # Рекурсивно загружаем созданную конфигурацию
                
        except Exception as e:
            logger.error(f"⌛ Ошибка загрузки конфигурации прокси: {e}")
            # Используем базовый прокси если конфигурация не загрузилась
            self._use_fallback_config()
    
    def _create_default_config(self):
        """Создание дефолтной конфигурации - ОРИГИНАЛЬНАЯ"""
        default_config = {
            "proxies": [
                {
                    "name": "Primary Proxy",
                    "http": "http://motuoom:123456@179.60.183.214:50101",
                    "https": "http://motuoom:123456@179.60.183.214:50101",
                    "enabled": True,
                    "priority": 1
                }
            ],
            "settings": {
                "enable_direct_connection_fallback": True,
                "proxy_rotation_enabled": True,
                "max_consecutive_errors": 3,
                "cooldown_duration_seconds": 600,  # 10 минут
                "success_score_bonus": 1,
                "error_score_penalty": -5
            }
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Создана дефолтная конфигурация: {self.config_file}")
        except Exception as e:
            logger.error(f"⌛ Ошибка создания дефолтной конфигурации: {e}")
    
    def _use_fallback_config(self):
        """Использование базовой конфигурации при ошибке"""
        self.proxies = [
            {
                "name": "Fallback Proxy",
                "http": "http://motuoom:123456@179.60.183.214:50101",
                "https": "http://motuoom:123456@179.60.183.214:50101",
                "enabled": True,
                "priority": 1
            }
        ]
        self.settings = {
            "enable_direct_connection_fallback": True,
            "proxy_rotation_enabled": True,
            "max_consecutive_errors": 3,
            "cooldown_duration_seconds": 600
        }
        logger.warning("⚠️ Используется fallback конфигурация прокси")
    
    def _initialize_stats(self):
        """Инициализация статистики для каждого прокси"""
        for index, proxy in enumerate(self.proxies):
            self.proxy_stats[index] = {
                'name': proxy.get('name', f'Proxy_{index}'),
                'requests': 0,
                'errors': 0,
                'consecutive_errors': 0,
                'last_success': None,
                'last_error': None,
                'score': 100  # Начальный рейтинг
            }
    
    def get_next_proxy(self) -> Optional[Dict]:
        """Получение следующего доступного прокси с учетом статистики и кулдаунов"""
        if not self.proxies:
            logger.warning("⚠️ Нет доступных прокси в конфигурации")
            return self._get_direct_connection()
        
        current_time = time.time()
        
        # Очищаем истекшие кулдауны
        self.proxy_cooldowns = {
            name: end_time for name, end_time in self.proxy_cooldowns.items()
            if end_time > current_time
        }
        
        # Пробуем найти доступный прокси
        attempts = 0
        max_attempts = len(self.proxies) * 2
        
        while attempts < max_attempts:
            attempts += 1
            
            # Если включена ротация, переходим к следующему
            if self.settings.get('proxy_rotation_enabled', True):
                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            
            proxy_index = self.current_proxy_index
            proxy = self.proxies[proxy_index]
            proxy_name = self.proxy_stats[proxy_index]['name']
            
            # Проверяем, не заблокирован ли прокси
            if proxy_index in self.blocked_proxies:
                logger.debug(f"🚫 Прокси {proxy_name} заблокирован")
                continue
            
            # Проверяем кулдаун
            if proxy_name in self.proxy_cooldowns:
                remaining = int(self.proxy_cooldowns[proxy_name] - current_time)
                logger.debug(f"⏰ Прокси {proxy_name} в кулдауне еще {remaining} сек")
                continue
            
            # Возвращаем прокси
            logger.info(f"✅ Используем прокси: {proxy_name}")
            return {
                'index': proxy_index,
                'name': proxy_name,
                'proxies': {
                    'http': proxy.get('http'),
                    'https': proxy.get('https')
                }
            }
        
        # Если все прокси недоступны, пробуем прямое соединение
        logger.warning("⚠️ Все прокси недоступны")
        return self._get_direct_connection()
    
    def _get_direct_connection(self) -> Optional[Dict]:
        """Получение конфигурации для прямого соединения"""
        if self.settings.get('enable_direct_connection_fallback', True):
            logger.info("🔄 Используем прямое соединение (без прокси)")
            return {
                'index': -1,
                'name': 'Direct Connection',
                'proxies': None  # None означает прямое соединение
            }
        return None
    
    def report_success(self, proxy_index: int):
        """Сообщить об успешном запросе через прокси"""
        if proxy_index == -1:  # Прямое соединение
            return
            
        if proxy_index in self.proxy_stats:
            stats = self.proxy_stats[proxy_index]
            stats['requests'] += 1
            stats['consecutive_errors'] = 0
            stats['last_success'] = time.time()
            stats['score'] = min(100, stats['score'] + self.settings.get('success_score_bonus', 1))
            
            # Удаляем из заблокированных если был там
            self.blocked_proxies.discard(proxy_index)
            
            logger.debug(f"✅ Прокси {stats['name']} успешно обработал запрос")
    
    def report_error(self, proxy_index: int, error_code: Optional[int] = None):
        """Сообщить об ошибке при использовании прокси"""
        if proxy_index == -1:  # Прямое соединение
            return
            
        if proxy_index in self.proxy_stats:
            stats = self.proxy_stats[proxy_index]
            stats['requests'] += 1
            stats['errors'] += 1
            stats['consecutive_errors'] += 1
            stats['last_error'] = time.time()
            stats['score'] = max(0, stats['score'] + self.settings.get('error_score_penalty', -5))
            
            # Проверяем, нужно ли заблокировать прокси
            max_errors = self.settings.get('max_consecutive_errors', 3)
            
            if stats['consecutive_errors'] >= max_errors:
                self.blocked_proxies.add(proxy_index)
                logger.warning(f"🚫 Прокси {stats['name']} заблокирован после {max_errors} ошибок подряд")
            
            # Добавляем в кулдаун при ошибке 429
            if error_code == 429:
                cooldown_duration = self.settings.get('cooldown_duration_seconds', 600)
                self.proxy_cooldowns[stats['name']] = time.time() + cooldown_duration
                logger.warning(f"⏰ Прокси {stats['name']} в кулдауне на {cooldown_duration} секунд (429 error)")
    
    def get_proxy_stats(self) -> Dict:
        """Получение статистики по всем прокси"""
        current_time = time.time()
        
        stats_summary = {
            'total_proxies': len(self.proxies),
            'available_proxies': 0,
            'blocked_proxies': len(self.blocked_proxies),
            'cooldown_proxies': len(self.proxy_cooldowns),
            'direct_connection_enabled': self.settings.get('enable_direct_connection_fallback', True),
            'details': []
        }
        
        for index, stats in self.proxy_stats.items():
            is_blocked = index in self.blocked_proxies
            is_cooldown = stats['name'] in self.proxy_cooldowns
            is_available = not (is_blocked or is_cooldown)
            
            if is_available:
                stats_summary['available_proxies'] += 1
            
            cooldown_remaining = 0
            if is_cooldown:
                cooldown_remaining = max(0, self.proxy_cooldowns[stats['name']] - current_time)
            
            stats_summary['details'].append({
                'name': stats['name'],
                'index': index,
                'requests': stats['requests'],
                'errors': stats['errors'],
                'success_rate': round((stats['requests'] - stats['errors']) / max(stats['requests'], 1) * 100, 1) if stats['requests'] > 0 else 100,
                'consecutive_errors': stats['consecutive_errors'],
                'status': 'blocked' if is_blocked else 'cooldown' if is_cooldown else 'available',
                'cooldown_remaining': int(cooldown_remaining) if cooldown_remaining > 0 else 0,
                'last_success': time.strftime('%H:%M:%S', time.localtime(stats['last_success'])) if stats['last_success'] else 'Never',
                'last_error': time.strftime('%H:%M:%S', time.localtime(stats['last_error'])) if stats['last_error'] else 'Never'
            })
        
        return stats_summary
    
    def reload_config(self):
        """Перезагрузка конфигурации прокси"""
        logger.info("🔄 Перезагружаем конфигурацию прокси...")
        old_proxy_count = len(self.proxies)
        
        self._load_config()
        self._initialize_stats()
        
        # Сбрасываем состояние
        self.current_proxy_index = 0
        self.blocked_proxies.clear()
        self.proxy_cooldowns.clear()
        
        logger.info(f"✅ Конфигурация перезагружена: {old_proxy_count} -> {len(self.proxies)} прокси")
