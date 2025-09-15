/**
 * Логика чата с Шестерёнкиным с поддержкой уникальной идентификации пользователей
 */

// Глобальные переменные чата
let currentImage = null;
let chatHistory = [];
let isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
let currentUserId = null; // Отслеживаем текущий ID пользователя

// Массив сообщений для индикатора активности Шестерёнкина
const typingMessages = [
    '🕵️ Шестерёнкин проводит исследование',
    '🔍 Шестерёнкин анализирует данные',
    '⚙️ Шестерёнкин изучает механизмы',
    '📊 Шестерёнкин обрабатывает информацию',
    '🔎 Шестерёнкин ведёт поиск',
    '💡 Шестерёнкин размышляет',
    '📝 Шестерёнкин готовит ответ',
    '🏭 Шестерёнкин консультируется с заводчанами',
    '📚 Шестерёнкин изучает документацию',
    '🔧 Шестерёнкин проверяет техническую информацию'
];

/**
 * Основной класс для управления чатом
 */
class ChatManager {
    constructor() {
        this.isProcessing = false;
        this.typingIndicatorTimeout = null;
        this.isHistoryLoaded = false;
    }

    /**
     * Инициализация чата
     */
    initialize() {
        console.log('💬 Инициализация чата Шестерёнкин...');
        
        // Получаем идентификатор пользователя
        this.updateUserId();
        
        console.log('✅ Чат инициализирован');
    }

    /**
     * Обновление идентификатора пользователя
     */
    updateUserId() {
        if (window.TelegramWebApp && window.TelegramWebApp.isInTelegram()) {
            const user = window.TelegramWebApp.getTelegramUser();
            if (user && user.id) {
                const newUserId = `tg_${user.id}`;
                if (currentUserId !== newUserId) {
                    console.log('👤 Обновлен пользователь:', newUserId);
                    currentUserId = newUserId;
                    this.isHistoryLoaded = false; // Сбрасываем флаг загрузки истории
                }
            }
        } else {
            // Для веб-браузера используем session-based ID
            if (!currentUserId) {
                currentUserId = `web_session_${Date.now()}`;
                console.log('👤 Создан веб-идентификатор:', currentUserId);
            }
        }
    }

    /**
     * Открытие чата
     */
    openChat() {
        const modal = document.getElementById('chatModal');
        modal.style.display = 'block';

        // Принудительная прокрутка к верху страницы
        window.scrollTo(0, 0);
        document.body.scrollTop = 0;

        // Фиксируем размеры чата - ПОЛНОЭКРАННЫЙ
        const chatModalContent = modal.querySelector('.modal-content.chat-modal');
        if (chatModalContent) {
            chatModalContent.style.height = '100vh';
            chatModalContent.style.maxHeight = '100vh';
            chatModalContent.style.minHeight = '100vh';
            chatModalContent.style.overflow = 'hidden';
            chatModalContent.style.margin = '0';
            chatModalContent.style.borderRadius = '0';
        }

        // Фокус на input после анимации
        setTimeout(() => {
            // Принудительно показываем поле ввода
            if (window.TelegramWebApp) {
                window.TelegramWebApp.ensureInputVisible();
            }

            const input = document.getElementById('chatInput');
            if (input && !isMobile) {
                input.focus();
            }

            // Скроллим к концу сообщений
            this.scrollToBottom();
        }, 200);

        // Загружаем историю если не загружена для текущего пользователя
        if (!this.isHistoryLoaded) {
            this.loadChatHistory();
        }

        // Haptic feedback
        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('light');
        }

        console.log('📱 Чат открыт для пользователя:', currentUserId);
    }

    /**
     * Загрузка истории чата с сервера
     */
    async loadChatHistory() {
        try {
            console.log('📚 Загружаем историю чата для пользователя:', currentUserId);
            
            // Обновляем ID пользователя перед загрузкой
            this.updateUserId();
            
            const data = await window.API.Chat.getHistory();

            console.log('📜 Ответ сервера:', data);

            if (data.success) {
                // Проверяем что история действительно для нашего пользователя
                if (data.user_id) {
                    console.log('👤 История загружена для пользователя:', data.user_id);
                    currentUserId = data.user_id; // Обновляем локальный ID
                }

                if (data.history && data.history.length > 0) {
                    console.log('📜 История найдена:', data.history.length, 'сообщений');

                    // Очищаем текущий чат (кроме приветственного сообщения)
                    const messagesContainer = document.getElementById('chatMessages');
                    const welcomeMessage = messagesContainer.querySelector('.chat-message.bot');
                    messagesContainer.innerHTML = '';
                    if (welcomeMessage) {
                        messagesContainer.appendChild(welcomeMessage);
                    }

                    // Отображаем историю
                    data.history.forEach(msg => {
                        if (msg.role === 'user') {
                            // Проверяем есть ли изображение
                            let imageUrl = null;
                            if (msg.parts) {
                                const imagePart = msg.parts.find(part => part.inline_data);
                                if (imagePart) {
                                    imageUrl = `data:${imagePart.inline_data.mime_type};base64,${imagePart.inline_data.data}`;
                                }
                            }

                            const textPart = msg.parts ? msg.parts.find(part => part.text) : null;
                            const messageText = textPart ? textPart.text : '';

                            this.addMessageToChat('user', messageText, imageUrl);
                        } else if (msg.role === 'model') {
                            const textPart = msg.parts ? msg.parts.find(part => part.text) : null;
                            const messageText = textPart ? textPart.text : '';
                            this.addMessageToChat('bot', messageText);
                        }
                    });

                    // Обновляем локальную историю
                    chatHistory = data.history.map(msg => ({
                        role: msg.role === 'model' ? 'bot' : msg.role,
                        content: msg.parts && msg.parts.find(part => part.text) ? msg.parts.find(part => part.text).text : ''
                    }));

                    console.log('✅ История загружена и отображена');
                } else {
                    console.log('📭 История пуста для пользователя:', data.user_id || currentUserId);
                }

                this.isHistoryLoaded = true;
            } else {
                console.log('⚠️ Не удалось загрузить историю:', data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('❌ Ошибка загрузки истории:', error);
            // Не показываем ошибку пользователю, просто логируем
        }
    }

    /**
     * Очистка истории чата
     */
    async clearChatHistory() {
        const confirmMessage = 'Очистить всю историю диалога с Шестерёнкиным?';
        
        if (window.TelegramWebApp) {
            window.TelegramWebApp.showConfirm(confirmMessage, async (confirmed) => {
                if (confirmed) {
                    await this.performClearHistory();
                }
            });
        } else if (confirm(confirmMessage)) {
            await this.performClearHistory();
        }
    }

    /**
     * Выполнение очистки истории
     */
    async performClearHistory() {
        try {
            console.log('🗑️ Очищаем историю для пользователя:', currentUserId);
            
            const data = await window.API.Chat.clearHistory();

            if (data.success) {
                console.log('✅ История очищена на сервере для пользователя:', data.user_id || currentUserId);
                
                // Очищаем локальную историю
                chatHistory = [];

                // Очищаем отображение чата но оставляем приветственное сообщение
                const messagesContainer = document.getElementById('chatMessages');
                messagesContainer.innerHTML = `
                    <div class="chat-message bot">
                        <div class="message-header">🕵️ Шестерёнкин</div>
                        Привет! Я добрый и всегда желающий помочь сотрудникам Кировского завода сыщик.
                        Моё имя Шестерёнкин. Мне нравятся отечественные тракторы «Кировец» и сложные механизмы,
                        сила и профессионализм наших заводчан, а моё самое любимое занятие - это поиск информации.<br><br>
                        📸 Я умею анализировать изображения - просто отправьте фото с вопросом!<br>
                        🔍 Задавайте любые вопросы, и я найду ответы!
                    </div>
                `;

                // Сбрасываем флаг загрузки истории
                this.isHistoryLoaded = true;

                // Feedback
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.triggerHapticFeedback('success');
                    window.TelegramWebApp.showAlert('✅ История диалога очищена');
                } else {
                    alert('✅ История диалога очищена');
                }

                console.log('🗑️ История чата очищена');
            } else {
                console.error('❌ Ошибка очистки истории:', data.error);
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.showAlert('❌ Ошибка очистки истории');
                } else {
                    alert('❌ Ошибка очистки истории');
                }
            }
        } catch (error) {
            console.error('❌ Ошибка очистки истории:', error);
            if (window.TelegramWebApp) {
                window.TelegramWebApp.showAlert('❌ Ошибка соединения');
            } else {
                alert('❌ Ошибка соединения');
            }
        }
    }

    /**
     * Отправка сообщения
     */
    async sendMessage() {
        if (this.isProcessing) return;

        const input = document.getElementById('chatInput');
        const message = input.value.trim();

        console.log('📤 Отправка сообщения от пользователя:', currentUserId, {
            message: message,
            messageLength: message.length,
            hasImage: !!currentImage,
            imageFile: currentImage?.file
        });

        if (!message && !currentImage) {
            console.warn('⚠️ Нет сообщения и изображения для отправки');
            return;
        }

        // Обновляем ID пользователя перед отправкой
        this.updateUserId();

        this.isProcessing = true;
        const sendBtn = document.getElementById('chatSendBtn');
        sendBtn.disabled = true;

        // Haptic feedback
        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('medium');
        }

        try {
            // Добавляем сообщение пользователя в чат
            this.addMessageToChat('user', message, currentImage ? currentImage.dataUrl : null);

            // Подготавливаем данные для отправки
            let imageFile = null;
            if (currentImage) {
                console.log('📤 Отправляем файл, размер:', (currentImage.file.size / 1024 / 1024).toFixed(2), 'MB');
                imageFile = currentImage.file;
            }

            // Очищаем поле ввода
            input.value = '';
            this.removeImage();
            this.autoResize(input);

            // Показываем индикатор набора
            console.log('⌨️ Показываем индикатор активности...');
            this.showTypingIndicator();

            // Отправляем запрос к API
            console.log('📡 Отправляем запрос к серверу...');
            const data = await window.API.Chat.sendMessage(message, imageFile);

            console.log('📨 Получен ответ:', data);

            if (data.success) {
                // Проверяем что ответ для нашего пользователя
                if (data.user_id) {
                    console.log('✅ Ответ получен для пользователя:', data.user_id);
                    currentUserId = data.user_id; // Обновляем локальный ID
                }

                this.addMessageToChat('bot', data.response);

                // Обновляем историю чата
                chatHistory.push(
                    { role: 'user', content: message },
                    { role: 'bot', content: data.response }
                );

                // Success haptic feedback
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.triggerHapticFeedback('success');
                }

                console.log('✅ Сообщение успешно отправлено');
            } else {
                this.addMessageToChat('bot', '❌ Извините, произошла ошибка: ' + data.error);

                // Error haptic feedback
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.triggerHapticFeedback('error');
                }
            }
        } catch (error) {
            console.error('❌ Ошибка чата:', error);
            const errorMessage = window.API.Utils.handleApiError(error, 'Chat');
            this.addMessageToChat('bot', '❌ ' + errorMessage);

            // Error haptic feedback
            if (window.TelegramWebApp) {
                window.TelegramWebApp.triggerHapticFeedback('error');
            }
        } finally {
            console.log('🏁 Завершаем обработку сообщения...');
            this.hideTypingIndicator();
            this.isProcessing = false;
            sendBtn.disabled = false;

            // Автопрокрутка и фокус
            setTimeout(() => {
                this.scrollToBottom();

                // Убеждаемся что поле ввода зафиксировано
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.ensureInputVisible();
                }

                if (!isMobile) {
                    const input = document.getElementById('chatInput');
                    if (input) {
                        input.focus();
                    }
                }
            }, 100);
        }
    }

    /**
     * Добавление сообщения в чат
     */
    addMessageToChat(role, message, imageUrl = null) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;

        if (role === 'bot') {
            messageDiv.innerHTML = `
                <div class="message-header">🕵️ Шестерёнкин</div>
                ${message.replace(/\n/g, '<br>')}
            `;
        } else {
            let content = message.replace(/\n/g, '<br>');
            if (imageUrl) {
                content = `<img src="${imageUrl}" alt="Uploaded image">${content ? '<br>' + content : ''}`;
            }
            messageDiv.innerHTML = content;
        }

        messagesContainer.appendChild(messageDiv);

        // Принудительный скролл с учетом фиксированного поля ввода
        setTimeout(() => {
            this.scrollToBottom();
        }, 50);
    }

    /**
     * Получение информации о текущем пользователе
     */
    getCurrentUserInfo() {
        const telegramUser = window.TelegramWebApp ? window.TelegramWebApp.getTelegramUser() : null;
        
        return {
            userId: currentUserId,
            telegram: telegramUser,
            isInTelegram: window.TelegramWebApp ? window.TelegramWebApp.isInTelegram() : false,
            historyLoaded: this.isHistoryLoaded
        };
    }

    /**
     * Тестирование идентификации пользователя
     */
    async testUserIdentification() {
        console.log('🧪 Тестируем идентификацию пользователя в чате...');
        
        const userInfo = this.getCurrentUserInfo();
        console.log('👤 Информация о пользователе:', userInfo);
        
        try {
            // Получаем историю для проверки
            const history = await window.API.Chat.getHistory();
            console.log('📚 Тест загрузки истории:', {
                success: history.success,
                user_id: history.user_id,
                messages: history.history ? history.history.length : 0
            });
            
            return userInfo;
        } catch (error) {
            console.error('❌ Ошибка тестирования:', error);
            return null;
        }
    }

    // Остальные методы остаются без изменений...
    /**
     * Прокрутка к последнему сообщению
     */
    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    /**
     * Показ индикатора набора текста
     */
    showTypingIndicator() {
        console.log('👀 Показываем индикатор активности...');
        
        // Скрываем предыдущий если есть
        this.hideTypingIndicator();
        
        const indicator = document.getElementById('typingIndicator');
        const typingText = document.getElementById('typingText');
        
        if (indicator) {
            // Устанавливаем случайное сообщение
            if (typingText) {
                const message = this.getRandomTypingMessage();
                typingText.textContent = message;
                console.log('📝 Установлено сообщение:', message);
            }
            
            // Принудительно показываем элемент
            indicator.classList.add('show');
            indicator.style.display = 'flex';
            indicator.style.visibility = 'visible';
            indicator.style.opacity = '1';
            
            console.log('✅ Основной индикатор показан');
            
            // Проверяем что элемент действительно виден
            setTimeout(() => {
                const computedStyle = window.getComputedStyle(indicator);
                console.log('🔍 Стили индикатора после показа:', {
                    display: computedStyle.display,
                    visibility: computedStyle.visibility,
                    opacity: computedStyle.opacity,
                    hasShowClass: indicator.classList.contains('show')
                });
                
                if (computedStyle.display === 'none') {
                    console.warn('⚠️ Основной индикатор не виден, используем альтернативный');
                    this.showTypingIndicatorAsMessage();
                }
            }, 100);
            
        } else {
            console.error('❌ Элемент typingIndicator не найден, используем альтернативный метод');
            this.showTypingIndicatorAsMessage();
        }
        
        // Прокручиваем к индикатору
        setTimeout(() => {
            this.scrollToBottom();
        }, 50);
    }

    /**
     * Скрытие индикатора набора текста
     */
    hideTypingIndicator() {
        console.log('🛑 Скрываем индикатор активности');
        
        // Скрываем основной индикатор
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.classList.remove('show');
            indicator.style.display = 'none';
            indicator.style.visibility = 'hidden';
            indicator.style.opacity = '0';
            console.log('✅ Основной индикатор скрыт');
        }
        
        // Скрываем альтернативный индикатор
        this.hideTypingIndicatorMessage();
    }

    /**
     * Альтернативный метод показа индикатора через сообщение
     */
    showTypingIndicatorAsMessage() {
        const messagesContainer = document.getElementById('chatMessages');
        
        // Удаляем предыдущий индикатор-сообщение если есть
        const existingIndicator = messagesContainer.querySelector('.typing-message');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        // Создаем новое сообщение-индикатор
        const typingMessage = document.createElement('div');
        typingMessage.className = 'chat-message bot typing-message';
        typingMessage.style.opacity = '0.8';
        typingMessage.style.fontStyle = 'italic';
        
        const message = this.getRandomTypingMessage();
        typingMessage.innerHTML = `
            <div class="message-header">🕵️ Шестерёнкин</div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>${message}</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingMessage);
        this.scrollToBottom();
        
        console.log('📨 Альтернативный индикатор добавлен как сообщение');
    }

    /**
     * Скрытие альтернативного индикатора
     */
    hideTypingIndicatorMessage() {
        const messagesContainer = document.getElementById('chatMessages');
        const typingMessage = messagesContainer.querySelector('.typing-message');
        
        if (typingMessage) {
            typingMessage.remove();
            console.log('📨 Альтернативный индикатор удален');
        }
    }

    /**
     * Получение случайного сообщения для индикатора
     */
    getRandomTypingMessage() {
        return typingMessages[Math.floor(Math.random() * typingMessages.length)];
    }

    /**
     * Тест индикатора активности
     * Доступен для отладки через консоль: window.ChatManager.testTypingIndicator()
     */
    testTypingIndicator() {
        console.log('🧪 Запускаем тест индикатора активности');
        
        // Проверяем элемент
        const indicator = document.getElementById('typingIndicator');
        console.log('🔍 Элемент индикатора:', indicator);
        
        if (indicator) {
            console.log('📏 Начальные стили:', {
                display: window.getComputedStyle(indicator).display,
                visibility: window.getComputedStyle(indicator).visibility,
                opacity: window.getComputedStyle(indicator).opacity
            });
        }
        
        this.showTypingIndicator();
        
        // Автоматически скрываем через 3 секунды
        setTimeout(() => {
            console.log('🧪 Скрываем индикатор через 3 секунды');
            this.hideTypingIndicator();
        }, 3000);
        
        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('light');
        }
    }

    /**
     * Выбор изображения
     */
    selectImage() {
        document.getElementById('imageInput').click();
        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('light');
        }
    }

    /**
     * Обработка выбранного изображения
     */
    async handleImageSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            console.log('📷 Выбрано изображение:', {
                name: file.name,
                type: file.type,
                size: (file.size / 1024 / 1024).toFixed(2) + 'MB'
            });

            // Проверяем тип файла
            if (!file.type.startsWith('image/')) {
                const errorMessage = 'Пожалуйста, выберите файл изображения';
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.showAlert(errorMessage);
                } else {
                    alert(errorMessage);
                }
                return;
            }

            // Показываем индикатор загрузки
            const preview = document.getElementById('imagePreview');
            preview.innerHTML = '<div style="padding: 8px; text-align: center; font-size: 10px; color: #aaa;">📷 Обработка...</div>';
            preview.style.display = 'block';

            // Добавляем классы для адаптивной верстки
            this.setPreviewMode(true);

            // ИСПРАВЛЕНИЕ: Используем новую функцию подготовки файла
            const processedFile = await window.API.Utils.prepareImageFile(file);

            // Создаем URL для превью (используем оригинальный файл для превью)
            const reader = new FileReader();
            reader.onload = (e) => {
                currentImage = {
                    file: processedFile, // Используем обработанный файл для отправки
                    dataUrl: e.target.result,
                    originalName: file.name, // Сохраняем оригинальное имя для отображения
                    processedName: processedFile.name,
                    originalSize: file.size,
                    processedSize: processedFile.size
                };

                // Обновляем превью
                const sizeInfo = processedFile.size !== file.size ?
                    ` (сжато с ${(file.size/1024/1024).toFixed(1)}MB до ${(processedFile.size/1024/1024).toFixed(1)}MB)` : '';

                preview.innerHTML = `
                <div style="position: relative;">
                    <img src="${e.target.result}" alt="Preview" style="max-width: 100%; max-height: 120px; border-radius: 4px;">
                    <button onclick="removeImage()" style="position: absolute; top: -5px; right: -5px; width: 20px; height: 20px; border-radius: 50%; background: #ff4444; color: white; border: none; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
                    <div style="font-size: 10px; color: #aaa; margin-top: 4px; text-align: center;">
                        ${file.name}${sizeInfo}
                    </div>
                </div>
            `;

                console.log('✅ Превью изображения создано:', {
                    originalFile: file.name,
                    processedFile: processedFile.name,
                    compression: processedFile.size !== file.size ?
                        ((1 - processedFile.size / file.size) * 100).toFixed(1) + '%' : 'не требуется'
                });
            };

            // Читаем файл для превью (используем оригинальный файл)
            reader.readAsDataURL(file);

            // Haptic feedback
            if (window.TelegramWebApp) {
                window.TelegramWebApp.triggerHapticFeedback('light');
            }

        } catch (error) {
            console.error('❌ Ошибка обработки изображения:', error);

            // Скрываем превью при ошибке
            const preview = document.getElementById('imagePreview');
            preview.style.display = 'none';
            this.setPreviewMode(false);

            // Показываем ошибку пользователю
            const errorMessage = error.message || 'Ошибка обработки изображения';
            if (window.TelegramWebApp) {
                window.TelegramWebApp.showAlert(errorMessage);
            } else {
                alert(errorMessage);
            }

            // Error haptic feedback
            if (window.TelegramWebApp) {
                window.TelegramWebApp.triggerHapticFeedback('error');
            }
        } finally {
            // Очищаем input для возможности выбора того же файла
            event.target.value = '';
        }
    }

    /**
     * Удаление изображения
     */
    removeImage() {
        currentImage = null;
        document.getElementById('imagePreview').style.display = 'none';
        document.getElementById('imageInput').value = '';

        // Убираем классы адаптивной верстки
        this.setPreviewMode(false);

        // Убеждаемся что поле ввода остается видимым
        if (window.TelegramWebApp) {
            window.TelegramWebApp.ensureInputVisible();
        }

        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('light');
        }

        console.log('🗑️ Изображение удалено');
    }

    /**
     * Установка/снятие режима превью изображения
     */
    setPreviewMode(enabled) {
        const inputContainer = document.getElementById('chatInputContainer');
        const chatMessages = document.getElementById('chatMessages');

        if (enabled) {
            if (inputContainer) {
                inputContainer.classList.add('has-preview');
            }
            if (chatMessages) {
                chatMessages.classList.add('has-preview');
            }
        } else {
            if (inputContainer) {
                inputContainer.classList.remove('has-preview');
            }
            if (chatMessages) {
                chatMessages.classList.remove('has-preview');
            }
        }
    }

    /**
     * Автоматическое изменение размера textarea
     */
    autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
    }

    /**
     * Обработка нажатия клавиш
     */
    handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }
}

// Создаем глобальный экземпляр менеджера чата
const chatManager = new ChatManager();

// Глобальные функции для использования в HTML
window.openChat = () => chatManager.openChat();
window.clearChatHistory = () => chatManager.clearChatHistory();
window.sendMessage = () => chatManager.sendMessage();
window.selectImage = () => chatManager.selectImage();
window.handleImageSelect = (event) => chatManager.handleImageSelect(event);
window.removeImage = () => chatManager.removeImage();
window.autoResize = (textarea) => chatManager.autoResize(textarea);
window.handleKeyDown = (event) => chatManager.handleKeyDown(event);
window.hideKeyboard = () => {
    if (window.TelegramWebApp) {
        window.TelegramWebApp.hideKeyboard();
    }
};

// Глобальные функции для отладки
window.testUserIdentification = () => chatManager.testUserIdentification();
window.getCurrentUserInfo = () => chatManager.getCurrentUserInfo();

// Экспорт для использования в других модулях
window.ChatManager = chatManager;
