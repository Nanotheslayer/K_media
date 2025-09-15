/**
 * API клиент для Кировец Медиа с поддержкой уникальной идентификации пользователей
 */

// Базовый URL для API (можно настроить для разных сред)
const API_BASE_URL = '';

/**
 * Базовый класс для работы с API
 */
class ApiClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    /**
     * Получение Telegram User ID если доступен
     */
    getTelegramUserId() {
        if (window.TelegramWebApp && window.TelegramWebApp.isInTelegram()) {
            const user = window.TelegramWebApp.getTelegramUser();
            if (user && user.id) {
                console.log('👤 Получен Telegram User ID:', user.id);
                return user.id.toString();
            }
        }
        console.log('👤 Telegram User ID недоступен');
        return null;
    }

    /**
     * Получение заголовков с идентификацией пользователя
     */
    getUserHeaders() {
        const headers = {};
        const telegramUserId = this.getTelegramUserId();
        
        if (telegramUserId) {
            headers['X-Telegram-User-Id'] = telegramUserId;
            console.log('📤 Добавлен заголовок X-Telegram-User-Id:', telegramUserId);
        }
        
        return headers;
    }

    /**
     * Базовый метод для выполнения запросов
     */
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: {},
        };

        // Добавляем заголовки идентификации пользователя
        const userHeaders = this.getUserHeaders();
        Object.assign(defaultOptions.headers, userHeaders);

        // Устанавливаем Content-Type только если это не FormData
        if (options.body && !(options.body instanceof FormData)) {
            defaultOptions.headers['Content-Type'] = 'application/json';
        }

        const requestOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers,
            },
        };

        console.log(`🌐 API Request: ${requestOptions.method || 'GET'} ${url}`);
        console.log('📦 Request body type:', options.body ? options.body.constructor.name : 'none');
        console.log('📋 Headers:', requestOptions.headers);

        try {
            const response = await fetch(url, requestOptions);
            
            console.log(`📡 API Response: ${response.status} ${response.statusText}`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error(`❌ API Error for ${url}:`, error);
            throw error;
        }
    }

    /**
     * GET запрос с параметрами пользователя
     */
    async get(endpoint, params = {}) {
        // Добавляем telegram_user_id в параметры URL если доступен
        const telegramUserId = this.getTelegramUserId();
        if (telegramUserId) {
            params.telegram_user_id = telegramUserId;
        }

        const searchParams = new URLSearchParams(params);
        const urlWithParams = searchParams.toString() ? `${endpoint}?${searchParams}` : endpoint;
        
        return this.makeRequest(urlWithParams, { method: 'GET' });
    }

    /**
     * POST запрос с JSON данными
     */
    async post(endpoint, data) {
        // Добавляем telegram_user_id в данные если доступен
        const telegramUserId = this.getTelegramUserId();
        if (telegramUserId && data && typeof data === 'object') {
            data.telegram_user_id = telegramUserId;
        }

        return this.makeRequest(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    /**
     * POST запрос с FormData (для файлов)
     */
    async postFormData(endpoint, formData) {
        // Добавляем telegram_user_id в FormData если доступен
        const telegramUserId = this.getTelegramUserId();
        if (telegramUserId && formData instanceof FormData) {
            formData.append('telegram_user_id', telegramUserId);
            console.log('📤 Добавлен telegram_user_id в FormData:', telegramUserId);
        }

        return this.makeRequest(endpoint, {
            method: 'POST',
            headers: {}, // Не устанавливаем Content-Type для FormData
            body: formData,
        });
    }
}

// Создаем экземпляр API клиента
const apiClient = new ApiClient();

/**
 * API для чата с Шестерёнкиным
 */
class ChatAPI {
    /**
     * Отправка сообщения в чат
     */
    static async sendMessage(message, imageFile = null) {
        const formData = new FormData();

        if (message) {
            formData.append('message', message);
        }

        if (imageFile) {
            formData.append('image', imageFile);
        }

        console.log('💬 Отправляем сообщение в чат...');
        return apiClient.postFormData('/api/chat', formData);
    }

    /**
     * Получение истории чата
     */
    static async getHistory(limit = 10) {
        console.log('📚 Запрашиваем историю чата...');
        return apiClient.get('/api/chat/history', { limit });
    }

    /**
     * Очистка истории чата (используем основной маршрут для совместимости)
     */
    static async clearHistory() {
        console.log('🗑️ Очищаем историю чата...');
        // Используем основной маршрут, но сервер поддерживает оба
        return apiClient.post('/api/chat/clear', {});
    }

    /**
     * Получение настроек чата
     */
    static async getSettings() {
        return apiClient.get('/api/chat/settings');
    }

    /**
     * Обновление настроек чата
     */
    static async updateSettings(settings) {
        return apiClient.post('/api/chat/settings', settings);
    }

    /**
     * Получение статуса чата
     */
    static async getStatus() {
        return apiClient.get('/api/chat/status');
    }
}

/**
 * API для газеты
 */
class NewspaperAPI {
    /**
     * Получение статей газеты
     */
    static async getArticles() {
        return apiClient.get('/api/newspaper');
    }
}

/**
 * API для календаря событий
 */
class EventsAPI {
    /**
     * Получение событий календаря
     */
    static async getEvents() {
        return apiClient.get('/api/events');
    }
}

/**
 * API для обратной связи
 */
class FeedbackAPI {
    /**
     * Отправка обратной связи
     */
    static async submitFeedback(feedbackData) {
        return apiClient.post('/api/feedback', feedbackData);
    }
}

/**
 * API для тестирования
 */
class TestAPI {
    /**
     * Тестовый запрос для проверки связи
     */
    static async test() {
        return apiClient.get('/api/test');
    }

    /**
     * Проверка здоровья сервера
     */
    static async health() {
        return apiClient.get('/health');
    }
}

/**
 * Утилиты для работы с API
 */
class ApiUtils {
    /**
     * Проверка статуса сервера при загрузке страницы
     */
    static async checkServerStatus() {
        try {
            console.log('🔍 Проверяем статус сервера...');
            
            const [testResponse, chatStatus] = await Promise.all([
                TestAPI.test(),
                ChatAPI.getStatus()
            ]);
            
            console.log('✅ Статус сервера:', testResponse);
            console.log('✅ Статус чата:', chatStatus);

            return {
                server: testResponse,
                chat: chatStatus
            };
        } catch (error) {
            console.error('❌ Ошибка проверки статуса сервера:', error);
            return null;
        }
    }

    /**
     * Тестирование уникальности пользователей
     */
    static async testUserIdentification() {
        try {
            console.log('🧪 Тестируем идентификацию пользователя...');
            
            const telegramUserId = apiClient.getTelegramUserId();
            console.log('👤 Текущий Telegram User ID:', telegramUserId);
            
            if (telegramUserId) {
                console.log('✅ Telegram идентификация доступна');
                
                // Получаем историю для проверки
                const history = await ChatAPI.getHistory();
                if (history.success) {
                    console.log('📚 История пользователя:', {
                        user_id: history.user_id,
                        messages: history.history.length
                    });
                }
            } else {
                console.log('⚠️ Telegram идентификация недоступна, используется fallback');
            }
            
            return telegramUserId;
        } catch (error) {
            console.error('❌ Ошибка тестирования идентификации:', error);
            return null;
        }
    }

    /**
     * Обработка ошибок API с пользовательскими сообщениями
     */
    static handleApiError(error, context = 'API') {
        console.error(`❌ ${context} Error:`, error);

        let userMessage = 'Произошла ошибка. Попробуйте позже.';

        if (error.message.includes('Failed to fetch')) {
            userMessage = 'Нет соединения с сервером. Проверьте интернет.';
        } else if (error.message.includes('413')) {
            userMessage = 'Файл слишком большой. Выберите файл меньшего размера.';
        } else if (error.message.includes('404')) {
            userMessage = 'Запрашиваемый ресурс не найден.';
        } else if (error.message.includes('500')) {
            userMessage = 'Внутренняя ошибка сервера. Обратитесь к администратору.';
        }

        return userMessage;
    }

    /**
     * Retry логика для неудачных запросов
     */
    static async retryRequest(requestFunction, maxRetries = 3, delay = 1000) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return await requestFunction();
            } catch (error) {
                console.warn(`⚠️ Attempt ${attempt} failed:`, error.message);
                
                if (attempt === maxRetries) {
                    throw error;
                }
                
                // Экспоненциальная задержка
                const waitTime = delay * Math.pow(2, attempt - 1);
                console.log(`⏳ Waiting ${waitTime}ms before retry...`);
                await new Promise(resolve => setTimeout(resolve, waitTime));
            }
        }
    }

    /**
     * Проверка размера файла перед загрузкой
     */
    static validateFileSize(file, maxSizeMB = 50) {
        const maxSizeBytes = maxSizeMB * 1024 * 1024;
        
        if (file.size > maxSizeBytes) {
            throw new Error(`Файл слишком большой. Максимальный размер: ${maxSizeMB}MB`);
        }
        
        return true;
    }

    /**
     * Проверка типа файла
     */
    static validateFileType(file, allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']) {
        if (!allowedTypes.includes(file.type)) {
            throw new Error('Неподдерживаемый тип файла. Разрешены: ' + allowedTypes.join(', '));
        }
        
        return true;
    }

    /**
     * Сжатие изображения перед отправкой
     */
    static async compressImage(file, maxSizeMB = 2, quality = 0.8) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = function() {
                // Вычисляем новые размеры для сжатия
                let { width, height } = img;
                const maxDimension = 1200; // Максимальная сторона

                if (width > maxDimension || height > maxDimension) {
                    if (width > height) {
                        height = (height * maxDimension) / width;
                        width = maxDimension;
                    } else {
                        width = (width * maxDimension) / height;
                        height = maxDimension;
                    }
                }

                canvas.width = width;
                canvas.height = height;

                // Рисуем изображение на canvas
                ctx.drawImage(img, 0, 0, width, height);

                // Конвертируем в blob с качеством
                canvas.toBlob((blob) => {
                    // ИСПРАВЛЕНИЕ: Создаем новый File объект с правильным именем
                    const originalExtension = file.name.split('.').pop().toLowerCase();
                    const compressedFileName = file.name.replace(/\.[^/.]+$/, '') + '_compressed.jpg';

                    // Создаем новый File объект с именем и типом
                    const compressedFile = new File([blob], compressedFileName, {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    });

                    console.log('🖼️ Изображение сжато:', {
                        originalName: file.name,
                        compressedName: compressedFile.name,
                        originalSize: (file.size / 1024 / 1024).toFixed(2) + 'MB',
                        compressedSize: (compressedFile.size / 1024 / 1024).toFixed(2) + 'MB',
                        compression: ((1 - compressedFile.size / file.size) * 100).toFixed(1) + '%',
                        originalType: file.type,
                        compressedType: compressedFile.type
                    });

                    resolve(compressedFile);
                }, 'image/jpeg', quality);
            };

            img.src = URL.createObjectURL(file);
        });
    }

    /**
     * Форматирование даты для API
     */
    static formatDateForAPI(date) {
        return date.toISOString().split('T')[0];
    }

    /**
     * Парсинг даты из API
     */
    static parseDateFromAPI(dateString) {
        return new Date(dateString);
    }

    /**
     * Проверка нужности сжатия и правильная отправка файла
     */
    static async prepareImageFile(file) {
        try {
            console.log('📷 Подготовка изображения:', {
                name: file.name,
                type: file.type,
                size: (file.size / 1024 / 1024).toFixed(2) + 'MB'
            });

            // Проверяем тип файла
            ApiUtils.validateFileType(file);

            // Проверяем размер
            ApiUtils.validateFileSize(file, 50); // 50MB максимум

            // Сжимаем только если больше 2MB
            if (file.size > 2 * 1024 * 1024) {
                console.log('🗜️ Файл больше 2MB, сжимаем...');
                return await ApiUtils.compressImage(file, 2, 0.85);
            } else {
                console.log('✅ Файл подходящего размера, отправляем как есть');
                return file;
            }
        } catch (error) {
            console.error('❌ Ошибка подготовки изображения:', error);
            throw error;
        }
    }
}

// Экспорт API классов для использования в других модулях
window.API = {
    Chat: ChatAPI,
    Newspaper: NewspaperAPI,
    Events: EventsAPI,
    Feedback: FeedbackAPI,
    Test: TestAPI,
    Utils: ApiUtils
};

// Инициализация проверки статуса при загрузке
document.addEventListener('DOMContentLoaded', () => {
    ApiUtils.checkServerStatus();
    
    // Тестируем идентификацию пользователя при загрузке
    setTimeout(() => {
        ApiUtils.testUserIdentification();
    }, 2000);
});
