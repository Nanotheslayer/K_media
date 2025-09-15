#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт тестирования прокси серверов для Кировец Медиа
Создайте файл test_proxy.py и запустите: python test_proxy.py
"""

import json
import time
import requests
import os
from typing import Dict, List, Optional

def test_proxy(proxy_config: Dict, timeout: int = 10) -> Dict:
    """Тестирование одного прокси сервера"""
    proxy_name = proxy_config.get('name', 'Unknown')
    proxies = {
        'http': proxy_config.get('http'),
        'https': proxy_config.get('https')
    }
    
    print(f"🧪 Тестируем прокси: {proxy_name}")
    
    test_results = {
        'name': proxy_name,
        'status': 'unknown',
        'response_time': None,
        'error': None,
        'ip_info': None
    }
    
    try:
        # Тест 1: Проверка доступности через httpbin.org
        start_time = time.time()
        
        response = requests.get(
            'https://httpbin.org/ip',
            proxies=proxies,
            timeout=timeout
        )
        
        response_time = round((time.time() - start_time) * 1000, 2)  # в миллисекундах
        
        if response.status_code == 200:
            ip_data = response.json()
            test_results.update({
                'status': 'working',
                'response_time': response_time,
                'ip_info': ip_data.get('origin', 'Unknown IP')
            })
            print(f"   ✅ Работает! Время ответа: {response_time}ms, IP: {ip_data.get('origin')}")
        else:
            test_results.update({
                'status': 'error',
                'response_time': response_time,
                'error': f'HTTP {response.status_code}'
            })
            print(f"   ❌ Ошибка HTTP: {response.status_code}")
            
    except requests.exceptions.ProxyError as e:
        test_results.update({
            'status': 'proxy_error',
            'error': str(e)
        })
        print(f"   ❌ Ошибка прокси: {e}")
        
    except requests.exceptions.Timeout:
        test_results.update({
            'status': 'timeout',
            'error': f'Timeout after {timeout}s'
        })
        print(f"   ⏱️ Таймаут после {timeout} секунд")
        
    except requests.exceptions.ConnectionError as e:
        test_results.update({
            'status': 'connection_error',
            'error': str(e)
        })
        print(f"   ❌ Ошибка соединения: {e}")
        
    except Exception as e:
        test_results.update({
            'status': 'unknown_error',
            'error': str(e)
        })
        print(f"   ❌ Неизвестная ошибка: {e}")
    
    return test_results

def test_gemini_api_through_proxy(proxy_config: Dict, api_key: str, timeout: int = 30) -> Dict:
    """Тестирование доступности Gemini API через прокси"""
    proxy_name = proxy_config.get('name', 'Unknown')
    proxies = {
        'http': proxy_config.get('http'),
        'https': proxy_config.get('https')
    }
    
    print(f"🤖 Тестируем Gemini API через {proxy_name}...")
    
    test_payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Hello, test message"}]
            }
        ]
    }
    
    headers = {
        'x-goog-api-key': api_key,
        'Content-Type': 'application/json'
    }
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
    
    try:
        start_time = time.time()
        
        response = requests.post(
            url,
            headers=headers,
            json=test_payload,
            proxies=proxies,
            timeout=timeout
        )
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if response.status_code == 200:
            print(f"   ✅ Gemini API работает! Время ответа: {response_time}ms")
            return {
                'status': 'working',
                'response_time': response_time,
                'api_accessible': True
            }
        elif response.status_code == 403:
            print(f"   ❌ API ключ заблокирован или недействителен (403)")
            return {
                'status': 'api_key_error',
                'response_time': response_time,
                'api_accessible': False,
                'error': 'Invalid API key'
            }
        elif response.status_code == 429:
            print(f"   ⏰ Превышен лимит запросов (429)")
            return {
                'status': 'rate_limited',
                'response_time': response_time,
                'api_accessible': True,
                'error': 'Rate limited'
            }
        else:
            print(f"   ❌ Ошибка API: {response.status_code}")
            return {
                'status': 'api_error',
                'response_time': response_time,
                'error': f'HTTP {response.status_code}'
            }
            
    except Exception as e:
        print(f"   ❌ Ошибка при тестировании API: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'api_accessible': False
        }

def test_direct_connection(timeout: int = 10) -> Dict:
    """Тестирование прямого соединения без прокси"""
    print("🌐 Тестируем прямое соединение...")
    
    try:
        start_time = time.time()
        
        response = requests.get(
            'https://httpbin.org/ip',
            timeout=timeout
        )
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if response.status_code == 200:
            ip_data = response.json()
            print(f"   ✅ Прямое соединение работает! Время: {response_time}ms, IP: {ip_data.get('origin')}")
            return {
                'status': 'working',
                'response_time': response_time,
                'ip_info': ip_data.get('origin')
            }
        else:
            print(f"   ❌ Ошибка прямого соединения: HTTP {response.status_code}")
            return {
                'status': 'error',
                'error': f'HTTP {response.status_code}'
            }
            
    except Exception as e:
        print(f"   ❌ Ошибка прямого соединения: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования прокси серверов для Кировец Медиа\n")
    
    # Загружаем конфигурацию
    config_file = 'proxy_config.json'
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Файл конфигурации {config_file} не найден!")
        print("Создайте файл proxy_config.json с настройками прокси.")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON в {config_file}: {e}")
        return
    
    proxies = config.get('proxies', [])
    settings = config.get('settings', {})
    timeout = settings.get('proxy_timeout', 10)
    
    if not proxies:
        print("❌ Нет прокси для тестирования в конфигурации!")
        return
    
    print(f"📋 Найдено {len(proxies)} прокси в конфигурации")
    print(f"⏱️ Таймаут тестирования: {timeout} секунд\n")
    
    # Тестируем прямое соединение
    direct_result = test_direct_connection(timeout)
    print()
    
    # Тестируем каждый прокси
    test_results = []
    
    for proxy in proxies:
        if not proxy.get('enabled', True):
            print(f"⏭️ Пропускаем отключенный прокси: {proxy.get('name', 'Unknown')}")
            continue
            
        result = test_proxy(proxy, timeout)
        test_results.append(result)
        print()
    
    # Суммарные результаты
    print("=" * 60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print("=" * 60)
    
    # Прямое соединение
    direct_status = "✅ Работает" if direct_result['status'] == 'working' else "❌ Не работает"
    print(f"🌐 Прямое соединение: {direct_status}")
    
    if direct_result.get('response_time'):
        print(f"   Время ответа: {direct_result['response_time']}ms")
    if direct_result.get('ip_info'):
        print(f"   Ваш IP: {direct_result['ip_info']}")
    
    print()
    
    # Результаты прокси
    working_proxies = 0
    total_tested = len(test_results)
    
    for result in test_results:
        status_emoji = "✅" if result['status'] == 'working' else "❌"
        print(f"{status_emoji} {result['name']}: {result['status']}")
        
        if result['status'] == 'working':
            working_proxies += 1
            if result['response_time']:
                print(f"   Время ответа: {result['response_time']}ms")
            if result['ip_info']:
                print(f"   IP через прокси: {result['ip_info']}")
        else:
            if result['error']:
                print(f"   Ошибка: {result['error']}")
    
    print()
    print(f"📈 Статистика: {working_proxies}/{total_tested} прокси работают")
    
    if working_proxies == 0:
        print("⚠️ ВНИМАНИЕ: Ни один прокси не работает!")
        if direct_result['status'] == 'working':
            print("💡 Рекомендация: Включите direct_connection_fallback в настройках")
        else:
            print("🚨 Критично: Нет доступа к интернету!")
    elif working_proxies < total_tested:
        print("⚠️ Некоторые прокси недоступны - проверьте настройки")
    else:
        print("🎉 Все прокси работают отлично!")
    
    # Тест Gemini API (если есть ключ)
    print("\n" + "=" * 60)
    print("🤖 ТЕСТИРОВАНИЕ GEMINI API:")
    print("=" * 60)
    
    # Попробуем найти API ключ в переменных окружения или попросим ввести
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("🔑 Введите Gemini API ключ для тестирования (или нажмите Enter для пропуска):")
        api_key = input("API Key: ").strip()
    
    if api_key:
        print(f"🧪 Тестируем Gemini API с ключом ...{api_key[-10:]}")
        print()
        
        # Тестируем API через рабочие прокси
        api_tests_performed = 0
        for result in test_results:
            if result['status'] == 'working' and api_tests_performed < 2:  # Тестируем только 2 лучших прокси
                proxy = next((p for p in proxies if p['name'] == result['name']), None)
                if proxy:
                    api_result = test_gemini_api_through_proxy(proxy, api_key, 30)
                    api_tests_performed += 1
                    print()
        
        # Тестируем API через прямое соединение
        if direct_result['status'] == 'working':
            print("🤖 Тестируем Gemini API через прямое соединение...")
            try:
                start_time = time.time()
                
                test_payload = {
                    "contents": [
                        {
                            "role": "user", 
                            "parts": [{"text": "Test direct connection"}]
                        }
                    ]
                }
                
                headers = {
                    'x-goog-api-key': api_key,
                    'Content-Type': 'application/json'
                }
                
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=test_payload,
                    timeout=30
                )
                
                response_time = round((time.time() - start_time) * 1000, 2)
                
                if response.status_code == 200:
                    print(f"   ✅ Gemini API работает через прямое соединение! Время: {response_time}ms")
                elif response.status_code == 403:
                    print(f"   ❌ API ключ недействителен (403)")
                elif response.status_code == 429:
                    print(f"   ⏰ Превышен лимит запросов (429)")
                else:
                    print(f"   ❌ Ошибка API: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Ошибка тестирования прямого API: {e}")
    else:
        print("⏭️ Пропускаем тестирование Gemini API (нет ключа)")
    
    # Итоговые рекомендации
    print("\n" + "=" * 60)
    print("💡 РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    
    if working_proxies >= 2:
        print("✅ У вас достаточно рабочих прокси для стабильной работы")
    elif working_proxies == 1:
        print("⚠️ Работает только один прокси - добавьте резервные для надежности")
    else:
        print("🚨 Нет рабочих прокси - проверьте настройки аутентификации")
    
    if direct_result['status'] == 'working':
        print("✅ Прямое соединение работает - можно использовать как fallback")
    else:
        print("❌ Прямое соединение не работает - проверьте интернет соединение")
    
    print("\n🔧 Для применения изменений:")
    print("1. Отредактируйте proxy_config.json при необходимости")
    print("2. Перезапустите webapp_kyrov_server.py")
    print("3. Или используйте POST /api/admin/proxy/reload для горячей перезагрузки")
    
    print("\n🏁 Тестирование завершено!")

if __name__ == "__main__":
    main()
