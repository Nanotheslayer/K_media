/**
 * Основная логика приложения Кировец Медиа
 * Координация работы всех модулей
 */

/**
 * Главный класс приложения
 */
class KirovetsMediaApp {
    constructor() {
        this.isInitialized = false;
        this.version = '2.0.0';
        this.buildDate = new Date().toISOString();
    }

    /**
     * Инициализация приложения
     */
    async initialize() {
        console.log('🚀 Запуск приложения Кировец Медиа v' + this.version);
        
        try {
            // 1. Инициализация Telegram WebApp
            if (window.TelegramWebApp) {
                window.TelegramWebApp.initialize();
            }

            // 2. Проверка статуса сервера
            await this.checkServerHealth();

            // 3. Инициализация чата
            if (window.ChatManager) {
                window.ChatManager.initialize();
            }

            // 4. Настройка touch обратной связи для мобильных устройств
            this.setupTouchFeedback();

            // 5. Логирование информации о среде
            this.logAppInfo();

            // 6. Уведомление о готовности
            this.notifyReady();

            this.isInitialized = true;
            console.log('✅ Приложение полностью инициализировано');

        } catch (error) {
            console.error('❌ Ошибка инициализации приложения:', error);
            this.showInitializationError(error);
        }
    }

    /**
     * Проверка здоровья сервера
     */
    async checkServerHealth() {
        try {
            console.log('🔍 Проверяем состояние сервера...');
            
            const healthData = await window.API.Test.health();
            
            console.log('💚 Сервер здоров:', healthData);
            
            // Проверяем доступность чата
            if (!healthData.chat_available) {
                console.warn('⚠️ Чат временно недоступен');
                this.showChatUnavailableWarning();
            }
            
            return healthData;
        } catch (error) {
            console.error('❌ Сервер недоступен:', error);
            this.showServerUnavailableWarning();
            throw error;
        }
    }

    /**
     * Настройка тактильной обратной связи для мобильных устройств
     */
    setupTouchFeedback() {
        console.log('📱 Настройка тактильной обратной связи...');
        
        // Добавляем обратную связь для карточек разделов
        document.querySelectorAll('.section-card').forEach(card => {
            card.addEventListener('touchstart', () => {
                card.style.transform = 'translateY(-2px) scale(1.01)';
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.triggerHapticFeedback('light');
                }
            });

            card.addEventListener('touchend', () => {
                card.style.transform = '';
            });

            // Предотвращаем двойное срабатывание на touch и click
            card.addEventListener('touchend', (e) => {
                e.preventDefault();
                // Имитируем клик после небольшой задержки
                setTimeout(() => {
                    card.click();
                }, 10);
            });
        });

        console.log('✅ Тактильная обратная связь настроена');
    }

    /**
     * Логирование информации о приложении
     */
    logAppInfo() {
        console.log('📋 Информация о приложении:', {
            name: 'Кировец Медиа',
            version: this.version,
            buildDate: this.buildDate,
            initialized: this.isInitialized,
            modules: {
                telegram: !!window.TelegramWebApp,
                api: !!window.API,
                chat: !!window.ChatManager,
                modals: !!window.ModalManager
            }
        });

        // Логируем информацию о среде выполнения
        if (window.TelegramWebApp) {
            window.TelegramWebApp.logEnvironmentInfo();
        }
    }

    /**
     * Уведомление о готовности приложения
     */
    notifyReady() {
        // Уведомляем Telegram что приложение готово
        if (window.TelegramWebApp && window.TelegramWebApp.isInTelegram()) {
            console.log('✅ Telegram Web App полностью загружен');
        } else {
            console.log('✅ Веб-приложение полностью загружено');
        }

        // Проверяем состояние элементов интерфейса
        this.validateInterfaceElements();
    }

    /**
     * Проверка состояния элементов интерфейса
     */
    validateInterfaceElements() {
        const criticalElements = [
            'chatMessages',
            'chatInput',
            'chatInputContainer',
            'typingIndicator'
        ];

        console.log('🔍 Проверка критических элементов интерфейса...');

        criticalElements.forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                console.log(`✅ ${elementId}: найден`);
                
                // Дополнительная проверка для поля ввода чата
                if (elementId === 'chatInputContainer') {
                    const styles = window.getComputedStyle(element);
                    console.log(`📏 ${elementId} стили:`, {
                        display: styles.display,
                        visibility: styles.visibility,
                        opacity: styles.opacity,
                        position: styles.position
                    });
                }
            } else {
                console.error(`❌ ${elementId}: НЕ НАЙДЕН`);
            }
        });
    }

    /**
     * Показ предупреждения о недоступности чата
     */
    showChatUnavailableWarning() {
        console.warn('⚠️ Показываем предупреждение о недоступности чата');
        
        // Можно добавить визуальное предупреждение на интерфейсе
        const chatCard = document.querySelector('.section-card.chat');
        if (chatCard) {
            chatCard.style.opacity = '0.6';
            chatCard.style.pointerEvents = 'none';
            
            const description = chatCard.querySelector('.section-description');
            if (description) {
                description.textContent = 'Временно недоступен. Попробуйте позже.';
            }
        }
    }

    /**
     * Показ предупреждения о недоступности сервера
     */
    showServerUnavailableWarning() {
        console.warn('⚠️ Показываем предупреждение о недоступности сервера');
        
        // Показываем уведомление пользователю
        setTimeout(() => {
            if (window.TelegramWebApp) {
                window.TelegramWebApp.showAlert('⚠️ Проблемы с подключением к серверу. Некоторые функции могут быть недоступны.');
            } else {
                alert('⚠️ Проблемы с подключением к серверу. Некоторые функции могут быть недоступны.');
            }
        }, 1000);
    }

    /**
     * Показ ошибки инициализации
     */
    showInitializationError(error) {
        console.error('💥 Критическая ошибка инициализации:', error);
        
        const errorMessage = `Ошибка запуска приложения: ${error.message}`;
        
        if (window.TelegramWebApp) {
            window.TelegramWebApp.showAlert(errorMessage);
        } else {
            alert(errorMessage);
        }
    }

    /**
     * Обработка ошибок приложения
     */
    handleGlobalError(error, source = 'unknown') {
        console.error(`💥 Глобальная ошибка в ${source}:`, error);
        
        // Логируем в консоль для отладки
        console.trace();
        
        // Можно добавить отправку ошибок на сервер для мониторинга
        this.reportError(error, source);
    }

    /**
     * Отправка отчета об ошибке (заглушка)
     */
    async reportError(error, source) {
        try {
            // Здесь можно добавить отправку ошибок на сервер аналитики
            console.log('📊 Отчет об ошибке:', {
                message: error.message,
                source: source,
                userAgent: navigator.userAgent,
                timestamp: new Date().toISOString(),
                url: window.location.href
            });
        } catch (reportError) {
            console.error('❌ Ошибка отправки отчета:', reportError);
        }
    }

    /**
     * Получение информации о приложении
     */
    getAppInfo() {
        return {
            name: 'Кировец Медиа',
            version: this.version,
            buildDate: this.buildDate,
            initialized: this.isInitialized,
            telegram: window.TelegramWebApp ? window.TelegramWebApp.isInTelegram() : false,
            modules: {
                telegram: !!window.TelegramWebApp,
                api: !!window.API,
                chat: !!window.ChatManager,
                modals: !!window.ModalManager
            }
        };
    }

    /**
     * Перезапуск приложения
     */
    async restart() {
        console.log('🔄 Перезапуск приложения...');
        
        try {
            this.isInitialized = false;
            
            // Закрываем все модальные окна
            if (window.ModalManager) {
                window.ModalManager.closeAllModals();
            }
            
            // Перезапускаем инициализацию
            await this.initialize();
            
            console.log('✅ Приложение успешно перезапущено');
        } catch (error) {
            console.error('❌ Ошибка перезапуска:', error);
            this.handleGlobalError(error, 'restart');
        }
    }
}

// Создаем глобальный экземпляр приложения
const app = new KirovetsMediaApp();

// Обработка глобальных ошибок
window.addEventListener('error', (event) => {
    app.handleGlobalError(event.error, 'window.error');
});

window.addEventListener('unhandledrejection', (event) => {
    app.handleGlobalError(event.reason, 'unhandledrejection');
});

// Экспорт для использования в других модулях и консоли
window.KirovetsMediaApp = app;

// Автоматическая инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM загружен, запускаем приложение...');
    app.initialize();
});

// Дополнительная проверка на случай если DOMContentLoaded уже прошел
if (document.readyState === 'loading') {
    // DOM еще загружается, ждем события DOMContentLoaded
    console.log('⏳ Ожидаем загрузки DOM...');
} else {
    // DOM уже загружен, запускаем немедленно
    console.log('📄 DOM уже загружен, запускаем приложение...');
    app.initialize();
}

// Обработка изменений в состоянии документа
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('👁️ Приложение скрыто');
    } else {
        console.log('👁️ Приложение активно');
        
        // Проверяем состояние при возвращении к приложению
        if (app.isInitialized && window.API) {
            window.API.Utils.checkServerStatus();
        }
    }
});

// Финальное сообщение о загрузке
console.log('🎯 Модуль app.js загружен, ожидаем инициализацию...');
