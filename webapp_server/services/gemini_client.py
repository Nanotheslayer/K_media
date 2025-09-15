"""
Клиент для работы с Gemini API
"""
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Any, Tuple

from webapp_server.config import GEMINI_MODEL, GEMINI_FALLBACK_MODEL, GEMINI_BASE_URL, DEFAULT_SYSTEM_INSTRUCTION
from webapp_server.managers.key_manager import KeyManager
from webapp_server.managers.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)


class GeminiClient:
    """Клиент для работы с Gemini API (синхронная версия для Flask) с поддержкой multiple прокси и fallback модели"""

    def __init__(self, key_manager: KeyManager, proxy_manager: ProxyManager):
        self.key_manager = key_manager
        self.proxy_manager = proxy_manager
        self.session = requests.Session()
        self.current_model = GEMINI_MODEL

    def _make_request(self, endpoint: str, payload: Dict[str, Any],
                     max_retries: int = 3, use_fallback: bool = True) -> Tuple[Optional[Dict], Optional[str]]:
        """Выполнение синхронного запроса к Gemini API с резервными прокси, ключами и fallback моделью"""

        models_to_try = [GEMINI_MODEL]

        # Добавляем fallback модель если разрешено
        if use_fallback and GEMINI_FALLBACK_MODEL != GEMINI_MODEL:
            models_to_try.append(GEMINI_FALLBACK_MODEL)

        for model in models_to_try:
            self.current_model = model

            if model != GEMINI_MODEL:
                logger.warning(f"🔄 Переключение на fallback модель: {model}")

            for attempt in range(max_retries):
                # Получаем API ключ
                api_key = self.key_manager.get_next_available_key()
                if not api_key:
                    logger.error("🔴 Все API ключи недоступны")
                    return None, "all_keys_unavailable"

                # Получаем прокси
                proxy_info = self.proxy_manager.get_next_proxy()
                if not proxy_info:
                    logger.error("🔴 Не удалось получить прокси")
                    return None, "proxy_unavailable"

                proxy_index = proxy_info['index']
                proxy_name = proxy_info['name']
                proxies = proxy_info['proxies']

                url = f"{GEMINI_BASE_URL}/models/{model}:{endpoint}"
                headers = {
                    'x-goog-api-key': api_key,
                    'Content-Type': 'application/json; charset=utf-8',
                    'Accept': 'application/json',
                    'Accept-Charset': 'utf-8'
                }

                try:
                    logger.info(f"🚀 Попытка {attempt + 1}/{max_retries} (модель: {model}): "
                               f"API ключ ...{api_key[-10:]} через {proxy_name}")

                    response = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        proxies=proxies,
                        timeout=60
                    )

                    logger.info(f"📡 Ответ: {response.status_code} {response.reason}")

                    if response.status_code == 200:
                        # Успех!
                        try:
                            result = response.json()
                            logger.info(f"✅ Успешный запрос к {model} через {proxy_name}")
                            self.proxy_manager.report_success(proxy_index)
                            return result, None
                        except ValueError as e:
                            logger.error(f"💥 Ошибка парсинга JSON: {e}")
                            return None, "json_parse_error"

                    elif response.status_code == 503:
                        # Модель перегружена - переход на fallback
                        error_text = response.text[:500]
                        logger.error(f"❌ Модель {model} перегружена (503): {error_text}")

                        if model == GEMINI_MODEL and use_fallback:
                            logger.warning(f"🔄 Модель {model} недоступна (503), переходим к fallback")
                            break  # Переходим к следующей модели

                        self.proxy_manager.report_error(proxy_index, response.status_code)

                    elif response.status_code == 429:
                        # Превышен лимит запросов
                        logger.error(f"⏳ Превышен лимит для ключа ...{api_key[-10:]}")
                        self.key_manager.block_key(api_key, cooldown_minutes=5)
                        self.proxy_manager.report_error(proxy_index, response.status_code)

                    elif response.status_code == 400:
                        # Неправильный запрос - не ретраим
                        logger.error(f"💥 Неправильный запрос (400): {response.text[:200]}")
                        return None, "bad_request"

                    else:
                        # Другая ошибка
                        logger.error(f"❌ Неожиданный ответ {response.status_code}: {response.text[:200]}")
                        self.proxy_manager.report_error(proxy_index, response.status_code)

                except requests.exceptions.ProxyError as e:
                    logger.error(f"🔴 Ошибка прокси {proxy_name}: {e}")
                    self.proxy_manager.report_error(proxy_index)

                except requests.exceptions.Timeout:
                    logger.error(f"⏰ Таймаут при использовании {proxy_name}")
                    self.proxy_manager.report_error(proxy_index)

                except requests.exceptions.ConnectionError as e:
                    logger.error(f"📡 Ошибка соединения через {proxy_name}: {e}")
                    self.proxy_manager.report_error(proxy_index)

                except Exception as e:
                    logger.error(f"💥 Неожиданная ошибка: {e}")
                    self.proxy_manager.report_error(proxy_index)

                # Небольшая задержка перед следующей попыткой
                if attempt < max_retries - 1:
                    time.sleep(1)

        logger.error(f"❌ Все попытки исчерпаны для всех доступных моделей")
        return None, "max_retries_exceeded"

    def send_message(self, user_history: List[Dict], message: str = "",
                    image_data: Optional[Dict] = None,
                    use_google_search: bool = True,
                    use_url_context: bool = True,
                    use_persona: bool = True) -> Tuple[str, Optional[str]]:
        """Отправка сообщения в Gemini API с поддержкой fallback модели"""

        # Формируем содержимое сообщения
        parts = []

        # Добавляем текст если есть
        if message:
            parts.append({"text": message})

        # Добавляем изображение в правильном формате
        if image_data:
            parts.append({
                "inline_data": {
                    "mime_type": image_data["mime_type"],
                    "data": image_data["data"]
                }
            })

        if not parts:
            logger.warning("⚠️ Пустое сообщение, пропускаем запрос")
            return "", "empty_message"

        # Создаем payload
        payload = {
            "contents": user_history + [{"role": "user", "parts": parts}],
            "generationConfig": {
                "maxOutputTokens": 8192,
                "temperature": 1.0,
                "topP": 0.95,
                "topK": 0
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        }

        # Добавляем системную инструкцию если включена персона
        if use_persona and DEFAULT_SYSTEM_INSTRUCTION:
            payload["systemInstruction"] = {
                "role": "user",
                "parts": [{"text": DEFAULT_SYSTEM_INSTRUCTION}]
            }

        # 🔧 ИСПРАВЛЕНО: Используем оригинальный формат инструментов
        tools = []
        if use_google_search:
            tools.append({"google_search": {}})
        if use_url_context:
            tools.append({"url_context": {}})

        if tools:
            payload["tools"] = tools

        # Логирование для отладки
        logger.debug(f"📝 История содержит {len(user_history)} записей")
        for i, entry in enumerate(user_history):
            if 'role' in entry and 'parts' in entry:
                logger.debug(f"  [{i}] {entry['role']}: {len(entry['parts'])} частей")
            else:
                logger.warning(f"  [{i}] ⚠️ Некорректная запись: {list(entry.keys())}")

        logger.debug(f"🚀 Отправляем запрос к модели {self.current_model}")

        try:
            # Выполняем запрос с поддержкой fallback
            response_data, error_code = self._make_request("generateContent", payload, max_retries=3, use_fallback=True)

            if error_code:
                logger.error(f"❌ Ошибка API: {error_code}")
                return "", error_code

            if response_data and 'candidates' in response_data:
                candidate = response_data['candidates'][0]
                content = candidate.get('content', {})
                if 'parts' in content and content['parts']:
                    text = content['parts'][0].get('text', '')
                    if isinstance(text, bytes):
                        text = text.decode('utf-8')

                    # Логируем успешное использование модели
                    if self.current_model != GEMINI_MODEL:
                        logger.info(f"✅ Ответ получен от fallback модели: {self.current_model}")
                    else:
                        logger.info(f"✅ Ответ получен от основной модели: {self.current_model}")

                    return text, None

            return "", "empty_response"

        except Exception as e:
            logger.error(f"💥 Critical error in send_message: {e}")
            return "", "processing_error"

    def test_connection(self, api_key: str = None, proxy_info: Dict = None) -> bool:
        """Тестирование соединения с конкретным ключом и прокси"""
        try:
            test_key = api_key or self.key_manager.get_next_available_key()
            if not test_key:
                return False

            test_proxy = proxy_info or self.proxy_manager.get_next_proxy()
            if not test_proxy:
                return False

            # Тестируем основную модель
            url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent"
            headers = {
                'x-goog-api-key': test_key,
                'Content-Type': 'application/json'
            }

            payload = {
                "contents": [{"role": "user", "parts": [{"text": "test"}]}],
                "generationConfig": {"maxOutputTokens": 1}
            }

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                proxies=test_proxy.get('proxies'),
                timeout=10
            )

            if response.status_code == 200:
                return True
            elif response.status_code == 503:
                # Тестируем fallback модель при 503
                logger.info("⚠️ Основная модель недоступна (503), тестируем fallback")

                url_fallback = f"{GEMINI_BASE_URL}/models/{GEMINI_FALLBACK_MODEL}:generateContent"
                response_fallback = requests.post(
                    url_fallback,
                    headers=headers,
                    json=payload,
                    proxies=test_proxy.get('proxies'),
                    timeout=10
                )

                return response_fallback.status_code == 200

            return False

        except Exception as e:
            logger.error(f"Test connection failed: {e}")
            return False