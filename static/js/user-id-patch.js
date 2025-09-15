/**
 * Патч для автоматического добавления user_id во все запросы к чату
 * Добавьте этот скрипт в index.html перед chat.js
 */

(function() {
    'use strict';
    
    // Функция получения или генерации user_id
    window.getUserId = function() {
        // 1. Пробуем получить из Telegram WebApp
        if (window.Telegram && window.Telegram.WebApp) {
            const tgUser = window.Telegram.WebApp.initDataUnsafe?.user;
            if (tgUser && tgUser.id) {
                return 'tg_' + tgUser.id.toString();
            }
        }
        
        // 2. Получаем из localStorage
        let userId = localStorage.getItem('chat_user_id');
        if (!userId) {
            // 3. Генерируем новый ID
            const timestamp = Date.now();
            const random = Math.random().toString(36).substring(2, 15);
            userId = `web_${timestamp}_${random}`;
            localStorage.setItem('chat_user_id', userId);
            console.log('Generated new user_id:', userId);
        }
        
        return userId;
    };
    
    // Перехватываем оригинальный fetch для добавления user_id
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        // Проверяем, что это запрос к чату
        if (url.includes('/api/chat') && options.method === 'POST') {
            // Если это FormData
            if (options.body instanceof FormData) {
                // Добавляем user_id если его нет
                if (!options.body.has('user_id')) {
                    options.body.append('user_id', getUserId());
                    console.log('Added user_id to FormData:', getUserId());
                }
            }
            // Если это JSON
            else if (options.headers && options.headers['Content-Type'] === 'application/json') {
                try {
                    const data = JSON.parse(options.body);
                    if (!data.user_id) {
                        data.user_id = getUserId();
                        options.body = JSON.stringify(data);
                        console.log('Added user_id to JSON:', getUserId());
                    }
                } catch (e) {
                    console.error('Error parsing JSON body:', e);
                }
            }
        }
        
        return originalFetch.call(this, url, options);
    };
    
    // Также перехватываем XMLHttpRequest для старых браузеров
    const originalXHRSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(body) {
        if (this._url && this._url.includes('/api/chat')) {
            if (body instanceof FormData && !body.has('user_id')) {
                body.append('user_id', getUserId());
                console.log('Added user_id to XMLHttpRequest FormData:', getUserId());
            }
        }
        return originalXHRSend.call(this, body);
    };
    
    const originalXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        this._url = url;
        return originalXHROpen.apply(this, arguments);
    };
    
    // Логируем текущий user_id при загрузке
    console.log('Current user_id:', getUserId());
    
    // Добавляем информацию в интерфейс если есть элемент
    document.addEventListener('DOMContentLoaded', function() {
        const userId = getUserId();
        console.log('Chat initialized with user_id:', userId);
        
        // Если есть элемент для отображения user_id
        const userIdDisplay = document.getElementById('current-user-id');
        if (userIdDisplay) {
            userIdDisplay.textContent = userId;
        }
    });
})();
