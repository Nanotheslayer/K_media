/**
 * Интеграция с Telegram WebApp
 * Обработка специфичных для Telegram функций
 */

// Глобальные переменные для Telegram
let tg = window.Telegram?.WebApp;
let isInTelegram = !!tg && !!tg.initData;

// Переменные для отслеживания viewport
let initialViewportHeight = window.innerHeight;
let keyboardDetectionTimeout = null;
let isKeyboardOpen = false;

/**
 * Инициализация Telegram WebApp
 */
function initializeTelegram() {
    console.log('🤖 Инициализация Telegram WebApp...');
    
    // Определяем режим работы
    if (isInTelegram) {
        document.body.classList.add('telegram-mode');
        console.log('🤖 Запуск в режиме Telegram WebApp');
        
        // Основная инициализация Telegram
        tg.ready();
        tg.expand();

        // Настройка цветов
        tg.setHeaderColor('#2c3e50');
        tg.setBackgroundColor('#2c3e50');

        // Настройка viewport
        if (tg.viewportHeight) {
            document.documentElement.style.setProperty('--tg-viewport-height', tg.viewportHeight + 'px');
        }

        if (tg.viewportStableHeight) {
            document.documentElement.style.setProperty('--tg-viewport-stable-height', tg.viewportStableHeight + 'px');
        }

        // Обработка изменений viewport для Telegram
        if (tg.onEvent) {
            tg.onEvent('viewportChanged', handleTelegramViewportChange);
        }

        console.log('✅ Telegram WebApp инициализирован');
    } else {
        document.body.classList.add('standalone');
        console.log('🌐 Запуск в обычном браузере');
    }

    // Инициализация отслеживания viewport
    initializeViewportTracking();
}

/**
 * Обработка изменений viewport в Telegram
 */
function handleTelegramViewportChange() {
    console.log('📱 Telegram viewport changed:', {
        height: tg.viewportHeight,
        stableHeight: tg.viewportStableHeight,
        isExpanded: tg.isExpanded
    });

    setTimeout(() => {
        detectKeyboardState();
        ensureInputVisible();
    }, 100);
}

/**
 * Инициализация отслеживания изменений viewport
 */
function initializeViewportTracking() {
    // Сохраняем начальную высоту
    initialViewportHeight = window.innerHeight;
    console.log('📏 Initial viewport height:', initialViewportHeight);

    // Мониторинг изменений viewport
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', handleViewportChange);
        window.visualViewport.addEventListener('scroll', handleViewportChange);
    }

    // Альтернативный способ для старых браузеров
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('orientationchange', function() {
        setTimeout(() => {
            initialViewportHeight = window.innerHeight;
            detectKeyboardState();
        }, 500);
    });

    // Отслеживание фокуса на поле ввода
    document.addEventListener('focusin', function(e) {
        if (e.target && e.target.id === 'chatInput') {
            setTimeout(() => {
                detectKeyboardState();
                ensureInputVisible();
            }, 300);
        }
    });

    document.addEventListener('focusout', function(e) {
        if (e.target && e.target.id === 'chatInput') {
            setTimeout(detectKeyboardState, 300);
        }
    });
}

/**
 * Обработка изменений размера viewport с дебаунсингом
 */
function handleViewportChange() {
    // Очищаем предыдущий таймаут
    if (keyboardDetectionTimeout) {
        clearTimeout(keyboardDetectionTimeout);
    }

    // Устанавливаем новый таймаут для стабильного определения
    keyboardDetectionTimeout = setTimeout(() => {
        detectKeyboardState();
    }, 150);
}

/**
 * Определение состояния клавиатуры
 */
function detectKeyboardState() {
    const currentHeight = window.innerHeight;
    const heightDifference = initialViewportHeight - currentHeight;
    const keyboardThreshold = 100; // Порог для определения клавиатуры

    const wasKeyboardOpen = isKeyboardOpen;
    isKeyboardOpen = heightDifference > keyboardThreshold;

    // Если состояние клавиатуры изменилось
    if (wasKeyboardOpen !== isKeyboardOpen) {
        console.log('⌨️ Keyboard state changed:', isKeyboardOpen ? 'opened' : 'closed', 
                   'Height diff:', heightDifference, 'Current height:', currentHeight);
        handleKeyboardToggle();
    }
}

/**
 * Обработка открытия/закрытия клавиатуры
 */
function handleKeyboardToggle() {
    const chatModal = document.getElementById('chatModal');
    const chatHeader = document.getElementById('chatHeader');
    const chatMessages = document.getElementById('chatMessages');
    const inputContainer = document.getElementById('chatInputContainer');

    if (chatModal && chatModal.style.display === 'block') {
        if (isKeyboardOpen) {
            // Клавиатура открыта - адаптируем интерфейс
            if (chatHeader) {
                chatHeader.classList.add('keyboard-hidden');
            }
            if (chatMessages) {
                chatMessages.classList.add('header-hidden');
                if (chatMessages.classList.contains('has-preview')) {
                    chatMessages.classList.add('keyboard-open');
                }
            }
            if (inputContainer) {
                inputContainer.classList.add('keyboard-open');
            }

            console.log('🔧 Interface adapted for keyboard');
        } else {
            // Клавиатура закрыта - восстанавливаем интерфейс
            if (chatHeader) {
                chatHeader.classList.remove('keyboard-hidden');
            }
            if (chatMessages) {
                chatMessages.classList.remove('header-hidden', 'keyboard-open');
            }
            if (inputContainer) {
                inputContainer.classList.remove('keyboard-open');
            }

            console.log('🔧 Interface restored - keyboard closed');
        }

        // Прокручиваем к последнему сообщению после изменения размеров
        setTimeout(() => {
            if (chatMessages) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            ensureInputVisible();
        }, 100);
    }
}

/**
 * Обеспечение видимости поля ввода
 */
function ensureInputVisible() {
    const inputContainer = document.getElementById('chatInputContainer');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');
    const imageBtn = document.querySelector('.chat-image-btn');
    const inputRow = document.querySelector('.chat-input-row');

    if (inputContainer) {
        // Принудительно делаем видимыми все элементы и фиксируем позицию
        inputContainer.style.display = 'block';
        inputContainer.style.visibility = 'visible';
        inputContainer.style.opacity = '1';
        inputContainer.style.position = 'fixed';
        inputContainer.style.bottom = '0';
        inputContainer.style.left = '0';
        inputContainer.style.right = '0';
        inputContainer.style.width = '100%';
        inputContainer.style.zIndex = '1002';
        inputContainer.style.transform = 'none';
        inputContainer.style.boxSizing = 'border-box';

        // Дополнительно применяем стили к элементам
        [chatInput, sendBtn, imageBtn, inputRow].forEach(element => {
            if (element) {
                element.style.display = element === inputRow ? 'flex' : 'block';
                element.style.visibility = 'visible';
                element.style.opacity = '1';
            }
        });

        console.log('✅ Input container and all elements made visible and fixed');
    } else {
        console.error('❌ Input container not found!');
    }
}

/**
 * Скрытие клавиатуры
 */
function hideKeyboard() {
    const chatInput = document.getElementById('chatInput');
    if (chatInput && document.activeElement === chatInput) {
        chatInput.blur();
        console.log('⌨️ Keyboard hidden by tap');

        // Легкая вибрация для обратной связи
        if (isInTelegram && tg.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('light');
        }
    }
}

/**
 * Haptic Feedback для Telegram
 */
function triggerHapticFeedback(type = 'light') {
    if (isInTelegram && tg.HapticFeedback) {
        switch (type) {
            case 'light':
                tg.HapticFeedback.impactOccurred('light');
                break;
            case 'medium':
                tg.HapticFeedback.impactOccurred('medium');
                break;
            case 'heavy':
                tg.HapticFeedback.impactOccurred('heavy');
                break;
            case 'success':
                tg.HapticFeedback.notificationOccurred('success');
                break;
            case 'warning':
                tg.HapticFeedback.notificationOccurred('warning');
                break;
            case 'error':
                tg.HapticFeedback.notificationOccurred('error');
                break;
        }
    }
}

/**
 * Показ алерта через Telegram или браузер
 */
function showAlert(message) {
    if (isInTelegram && tg.showAlert) {
        tg.showAlert(message);
    } else {
        alert(message);
    }
}

/**
 * Показ подтверждения через Telegram или браузер
 */
function showConfirm(message, callback) {
    if (isInTelegram && tg.showConfirm) {
        tg.showConfirm(message, callback);
    } else {
        const result = confirm(message);
        callback(result);
    }
}

/**
 * Получение информации о пользователе Telegram
 */
function getTelegramUser() {
    if (isInTelegram && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        return {
            id: tg.initDataUnsafe.user.id,
            firstName: tg.initDataUnsafe.user.first_name,
            lastName: tg.initDataUnsafe.user.last_name,
            username: tg.initDataUnsafe.user.username,
            languageCode: tg.initDataUnsafe.user.language_code
        };
    }
    return null;
}

/**
 * Логирование информации о среде выполнения
 */
function logEnvironmentInfo() {
    console.log('🔍 Environment Info:', {
        isInTelegram: isInTelegram,
        userAgent: navigator.userAgent,
        viewport: {
            width: window.innerWidth,
            height: window.innerHeight,
            initialHeight: initialViewportHeight
        },
        telegram: isInTelegram ? {
            version: tg.version,
            platform: tg.platform,
            colorScheme: tg.colorScheme,
            isExpanded: tg.isExpanded,
            viewportHeight: tg.viewportHeight,
            viewportStableHeight: tg.viewportStableHeight
        } : null,
        user: getTelegramUser()
    });
}

// Экспорт функций для использования в других модулях
window.TelegramWebApp = {
    initialize: initializeTelegram,
    isInTelegram: () => isInTelegram,
    hideKeyboard: hideKeyboard,
    triggerHapticFeedback: triggerHapticFeedback,
    showAlert: showAlert,
    showConfirm: showConfirm,
    getTelegramUser: getTelegramUser,
    logEnvironmentInfo: logEnvironmentInfo,
    ensureInputVisible: ensureInputVisible,
    isKeyboardOpen: () => isKeyboardOpen
};
