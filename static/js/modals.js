/**
 * Управление модальными окнами
 * Обработка всех модальных окон приложения
 */

/**
 * Основной класс для управления модальными окнами
 */
class ModalManager {
    constructor() {
        this.activeModal = null;
        this.initialize();
    }

    /**
     * Инициализация менеджера модальных окон
     */
    initialize() {
        console.log('🪟 Инициализация менеджера модальных окон...');
        
        // Обработка закрытия модальных окон по клику вне области
        this.setupOutsideClickHandlers();
        
        // Обработка клавиатурных сокращений
        this.setupKeyboardHandlers();
        
        // Инициализация формы обратной связи
        this.initializeFeedbackForm();
        
        console.log('✅ Менеджер модальных окон готов');
    }

    /**
     * Обработка кликов вне модальных окон
     */
    setupOutsideClickHandlers() {
        window.onclick = (event) => {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                if (event.target === modal) {
                    this.closeModal(modal.id);
                }
            });
        };
    }

    /**
     * Обработка клавиатурных сокращений
     */
    setupKeyboardHandlers() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal[style*="block"]');
                if (openModal) {
                    this.closeModal(openModal.id);
                }
            }
        });
    }

    /**
     * Открытие газеты
     */
    async openNewspaper() {
        try {
            this.openModal('newspaperModal');
            this.showLoading('newspaperContent');
            
            const data = await window.API.Newspaper.getArticles();
            
            const content = document.getElementById('newspaperContent');
            
            if (data.success && data.articles.length > 0) {
                content.innerHTML = data.articles.map(article => `
                    <div class="item-card">
                        <div class="item-title">${article.title}</div>
                        <div class="item-description">${article.short_content}</div>
                        <div class="item-meta">
                            📅 ${article.date} ${article.author ? '• ✍️ ' + article.author : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                content.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #aaaaaa;">
                        📰 Архив публикаций скоро будет доступен
                    </div>
                `;
            }
            
            console.log('📰 Газета загружена');
        } catch (error) {
            console.error('❌ Ошибка загрузки газеты:', error);
            document.getElementById('newspaperContent').innerHTML = `
                <div style="text-align: center; padding: 40px; color: #c62828;">
                    ❌ Ошибка загрузки публикаций
                </div>
            `;
        }
        
        // Haptic feedback
        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('light');
        }
    }

    /**
     * Открытие календаря
     */
    async openCalendar() {
        try {
            this.openModal('calendarModal');
            this.showLoading('calendarContent');
            
            const data = await window.API.Events.getEvents();
            
            const content = document.getElementById('calendarContent');
            
            if (data.success && data.events.length > 0) {
                content.innerHTML = data.events.map(event => `
                    <div class="item-card">
                        <div class="item-title">${event.icon} ${event.title}</div>
                        <div class="item-description">${event.description || 'Подробности будут сообщены дополнительно'}</div>
                        <div class="item-meta">
                            📅 ${event.date} ${event.time ? '• ⏰ ' + event.time : ''} ${event.location ? '• 📍 ' + event.location : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                content.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #aaaaaa;">
                        🗓️ Производственные мероприятия будут добавлены
                    </div>
                `;
            }
            
            console.log('📅 Календарь загружен');
        } catch (error) {
            console.error('❌ Ошибка загрузки календаря:', error);
            document.getElementById('calendarContent').innerHTML = `
                <div style="text-align: center; padding: 40px; color: #c62828;">
                    ❌ Ошибка загрузки календаря мероприятий
                </div>
            `;
        }
        
        // Haptic feedback
        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('light');
        }
    }

    /**
     * Открытие формы обратной связи
     */
    openFeedback() {
        this.openModal('feedbackModal');
        
        // Haptic feedback
        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('light');
        }
        
        console.log('📧 Форма обратной связи открыта');
    }

    /**
     * Универсальное открытие модального окна
     */
    openModal(modalId) {
        // Закрываем текущее модальное окно если есть
        if (this.activeModal && this.activeModal !== modalId) {
            this.closeModal(this.activeModal);
        }
        
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            this.activeModal = modalId;
            
            // Блокируем прокрутку страницы
            document.body.style.overflow = 'hidden';
            
            console.log('🪟 Модальное окно открыто:', modalId);
        }
    }

    /**
     * Универсальное закрытие модального окна
     */
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            
            // При закрытии чата сбрасываем состояние клавиатуры
            if (modalId === 'chatModal') {
                this.resetChatState();
            }
            
            // Восстанавливаем прокрутку страницы
            document.body.style.overflow = 'auto';
            
            this.activeModal = null;
            
            console.log('🪟 Модальное окно закрыто:', modalId);
        }
        
        // Haptic feedback
        if (window.TelegramWebApp) {
            window.TelegramWebApp.triggerHapticFeedback('light');
        }
    }

    /**
     * Сброс состояния чата при закрытии
     */
    resetChatState() {
        if (window.TelegramWebApp) {
            // Сбрасываем состояние клавиатуры
            const chatHeader = document.getElementById('chatHeader');
            const chatMessages = document.getElementById('chatMessages');
            const inputContainer = document.getElementById('chatInputContainer');

            if (chatHeader) {
                chatHeader.classList.remove('keyboard-hidden');
            }
            if (chatMessages) {
                chatMessages.classList.remove('header-hidden', 'keyboard-open', 'has-preview');
            }
            if (inputContainer) {
                inputContainer.classList.remove('keyboard-open', 'has-preview');
            }
            
            console.log('🔄 Состояние чата сброшено');
        }
    }

    /**
     * Показ индикатора загрузки
     */
    showLoading(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="loading">
                    <div class="loading-spinner"></div>
                    Загрузка...
                </div>
            `;
        }
    }

    /**
     * Инициализация формы обратной связи
     */
    initializeFeedbackForm() {
        const form = document.getElementById('feedbackForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFeedbackSubmit(e));
        }
    }

    /**
     * Обработка отправки формы обратной связи
     */
    async handleFeedbackSubmit(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('.submit-btn');
        const formData = new FormData(form);

        // Блокируем кнопку
        submitBtn.disabled = true;
        submitBtn.textContent = 'Отправляется в редакцию...';

        try {
            const feedbackData = {
                name: formData.get('name'),
                department: formData.get('department'),
                phone: formData.get('phone'),
                message: formData.get('message'),
                category: formData.get('category')
            };

            console.log('📧 Отправляем обратную связь:', feedbackData);

            const data = await window.API.Feedback.submitFeedback(feedbackData);

            if (data.success) {
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.showAlert('✅ Благодарим! Ваше обращение передано в редакцию.');
                    window.TelegramWebApp.triggerHapticFeedback('success');
                } else {
                    alert('✅ Благодарим! Ваше обращение передано в редакцию.');
                }

                form.reset();
                this.closeModal('feedbackModal');
                
                console.log('✅ Обратная связь отправлена успешно');
            } else {
                if (window.TelegramWebApp) {
                    window.TelegramWebApp.showAlert('❌ ' + data.error);
                    window.TelegramWebApp.triggerHapticFeedback('error');
                } else {
                    alert('❌ ' + data.error);
                }
            }
        } catch (error) {
            console.error('❌ Ошибка отправки обратной связи:', error);
            
            const errorMessage = window.API.Utils.handleApiError(error, 'Feedback');
            
            if (window.TelegramWebApp) {
                window.TelegramWebApp.showAlert('❌ ' + errorMessage);
                window.TelegramWebApp.triggerHapticFeedback('error');
            } else {
                alert('❌ ' + errorMessage);
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Отправить в редакцию';
        }
    }

    /**
     * Проверка, открыто ли модальное окно
     */
    isModalOpen(modalId = null) {
        if (modalId) {
            const modal = document.getElementById(modalId);
            return modal && modal.style.display === 'block';
        }
        return this.activeModal !== null;
    }

    /**
     * Получение активного модального окна
     */
    getActiveModal() {
        return this.activeModal;
    }

    /**
     * Закрытие всех модальных окон
     */
    closeAllModals() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (modal.style.display === 'block') {
                this.closeModal(modal.id);
            }
        });
    }
}

// Создаем глобальный экземпляр менеджера модальных окон
const modalManager = new ModalManager();

// Глобальные функции для использования в HTML
window.openNewspaper = () => modalManager.openNewspaper();
window.openCalendar = () => modalManager.openCalendar();
window.openFeedback = () => modalManager.openFeedback();
window.closeModal = (modalId) => modalManager.closeModal(modalId);

// Экспорт для использования в других модулях
window.ModalManager = modalManager;
