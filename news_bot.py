import os
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))  # Ваш Telegram ID

# Типы реакций
REACTIONS = {
    "👍": "like",
    "❤️": "love",
    "😂": "laugh",
    "😮": "wow",
    "😢": "sad",
    "😡": "angry"
}


class NewsBot:
    def __init__(self):
        self.db_name = 'news_bot.db'
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_subscribed BOOLEAN DEFAULT FALSE,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица новостей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_to_users BOOLEAN DEFAULT FALSE
            )
        ''')

        # Проверяем и добавляем новые столбцы в таблицу news
        cursor.execute("PRAGMA table_info(news)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'media_type' not in columns:
            cursor.execute('ALTER TABLE news ADD COLUMN media_type TEXT')
            print("✅ Добавлен столбец media_type")

        if 'media_id' not in columns:
            cursor.execute('ALTER TABLE news ADD COLUMN media_id TEXT')
            print("✅ Добавлен столбец media_id")

        # Таблица реакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                news_id INTEGER NOT NULL,
                reaction_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (news_id) REFERENCES news (id) ON DELETE CASCADE,
                UNIQUE(user_id, news_id)
            )
        ''')

        # Таблица отправленных сообщений для синхронизации
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                news_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (news_id) REFERENCES news (id) ON DELETE CASCADE,
                UNIQUE(user_id, news_id)
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")

    def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Добавление нового пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))

        conn.commit()
        conn.close()

    def subscribe_user(self, user_id: int):
        """Подписка пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET is_subscribed = TRUE WHERE user_id = ?
        ''', (user_id,))

        conn.commit()
        conn.close()

    def is_user_subscribed(self, user_id: int) -> bool:
        """Проверка подписки пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT is_subscribed FROM users WHERE user_id = ?
        ''', (user_id,))

        result = cursor.fetchone()
        conn.close()

        return result and result[0]

    def get_subscribed_users(self) -> List[int]:
        """Получение списка подписанных пользователей"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_id FROM users WHERE is_subscribed = TRUE
        ''')

        users = [row[0] for row in cursor.fetchall()]
        conn.close()

        return users

    def add_news(self, content: str, media_type: str = None, media_id: str = None) -> int:
        """Добавление новости"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO news (content, media_type, media_id) VALUES (?, ?, ?)
        ''', (content, media_type, media_id))

        news_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return news_id

    def get_all_news(self) -> List[tuple]:
        """Получение всех новостей в порядке создания"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, content, media_type, media_id, created_at FROM news 
            ORDER BY created_at ASC
        ''')

        news = cursor.fetchall()
        conn.close()

        return news

    def get_news_for_edit(self) -> List[tuple]:
        """Получение новостей для редактирования"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, content, created_at FROM news ORDER BY created_at DESC
        ''')

        news = cursor.fetchall()
        conn.close()

        return news

    def update_news(self, news_id: int, new_content: str) -> bool:
        """Обновление новости"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE news SET content = ? WHERE id = ?
        ''', (new_content, news_id))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def delete_news(self, news_id: int) -> bool:
        """Удаление новости"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM news WHERE id = ?
        ''', (news_id,))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def add_reaction(self, user_id: int, news_id: int, reaction_type: str) -> bool:
        """Добавление или изменение реакции"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO reactions (user_id, news_id, reaction_type)
            VALUES (?, ?, ?)
        ''', (user_id, news_id, reaction_type))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def remove_reaction(self, user_id: int, news_id: int) -> bool:
        """Удаление реакции"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM reactions WHERE user_id = ? AND news_id = ?
        ''', (user_id, news_id))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def get_reactions_for_news(self, news_id: int) -> Dict[str, int]:
        """Получение счетчиков реакций для новости"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT reaction_type, COUNT(*) FROM reactions 
            WHERE news_id = ? 
            GROUP BY reaction_type
        ''', (news_id,))

        reactions_count = dict(cursor.fetchall())
        conn.close()

        return reactions_count

    def get_user_reaction(self, user_id: int, news_id: int) -> str:
        """Получение реакции пользователя на новость"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT reaction_type FROM reactions 
            WHERE user_id = ? AND news_id = ?
        ''', (user_id, news_id))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def save_sent_message(self, user_id: int, news_id: int, message_id: int):
        """Сохранение ID отправленного сообщения"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO sent_messages (user_id, news_id, message_id)
            VALUES (?, ?, ?)
        ''', (user_id, news_id, message_id))

        conn.commit()
        conn.close()

    def get_sent_messages_for_news(self, news_id: int) -> List[Tuple[int, int]]:
        """Получение всех отправленных сообщений для новости"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_id, message_id FROM sent_messages 
            WHERE news_id = ?
        ''', (news_id,))

        messages = cursor.fetchall()
        conn.close()

        return messages

    def remove_sent_message(self, user_id: int, news_id: int):
        """Удаление записи об отправленном сообщении"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM sent_messages 
            WHERE user_id = ? AND news_id = ?
        ''', (user_id, news_id))

        conn.commit()
        conn.close()


# Инициализация бота
news_bot = NewsBot()


def determine_post_size(content: str, media_type: str = None) -> str:
    """📏 Определение размера поста для адаптивного отображения реакций"""

    # Базовая оценка размера контента
    content_length = len(content) if content else 0

    if media_type:
        # Посты с медиа обычно занимают больше места
        if content_length < 50:
            return "small"  # Короткий текст + медиа = маленький пост
        elif content_length < 200:
            return "normal"  # Средний текст + медиа = обычный пост
        else:
            return "large"  # Длинный текст + медиа = большой пост
    else:
        # Только текстовые посты
        if content_length < 100:
            return "small"  # Короткий текст = маленький пост
        elif content_length < 400:
            return "normal"  # Средний текст = обычный пост
        else:
            return "large"  # Длинный текст = большой пост


def determine_button_format(post_size: str, total_reactions: int) -> str:
    """🎯 Определение оптимального формата кнопок для универсального отображения"""
    
    # Базовые критерии для разных форматов
    if post_size == "small":
        if total_reactions > 100:
            return "minimal"      # Только эмодзи для активных, эмодзи+число для остальных
        elif total_reactions > 20:
            return "compact"      # Эмодзи + компактные числа
        else:
            return "standard"     # Стандартное отображение
            
    elif post_size == "large":
        if total_reactions > 200:
            return "compact"      # Даже для больших постов при многих реакциях используем компактный режим
        else:
            return "standard"     # Стандартное отображение
    else:  # normal
        if total_reactions > 150:
            return "compact"
        else:
            return "standard"


def format_reaction_button_text(emoji: str, count: int, is_user_reaction: bool, format_type: str) -> str:
    """🎨 Форматирование текста кнопки реакции для оптимального отображения"""
    
    # Компактное отображение больших чисел
    def compact_number(num):
        if num >= 1000000:
            return f"{num // 1000000}M"
        elif num >= 1000:
            return f"{num // 1000}K"
        return str(num)
    
    compact_count = compact_number(count) if count > 999 else str(count)
    
    if format_type == "minimal":
        # Минимальный формат: только эмодзи или эмодзи+число
        if is_user_reaction:
            return f"•{emoji}•" if count <= 1 else f"•{emoji}{compact_count}•"
        else:
            return emoji if count == 0 else f"{emoji}{compact_count}"
            
    elif format_type == "compact":
        # Компактный формат: оптимизированный для средних чисел
        if is_user_reaction:
            return f"{emoji}★" if count <= 1 else f"{emoji}{compact_count}★"
        else:
            return emoji if count == 0 else f"{emoji}{compact_count}"
            
    else:  # standard
        # Стандартный формат: полное отображение
        if is_user_reaction:
            return f"{emoji}★" if count <= 1 else f"{emoji} {count}★"
        else:
            return emoji if count == 0 else f"{emoji} {count}"


def create_universal_reactions_keyboard(news_id: int, user_reaction: str = None, post_size: str = "normal") -> InlineKeyboardMarkup:
    """🌍 Универсальная клавиатура реакций - ВСЕГДА один ряд, адаптивный размер"""
    
    reactions_count = news_bot.get_reactions_for_news(news_id)
    total_reactions = sum(reactions_count.values())
    
    # Определяем оптимальный формат кнопок
    button_format = determine_button_format(post_size, total_reactions)
    
    keyboard_row = []
    
    for emoji, reaction_type in REACTIONS.items():
        count = reactions_count.get(reaction_type, 0)
        is_user_reaction = (user_reaction == reaction_type)
        
        # Форматируем текст кнопки
        button_text = format_reaction_button_text(
            emoji, count, is_user_reaction, button_format
        )
        
        keyboard_row.append(InlineKeyboardButton(
            button_text,
            callback_data=f"reaction_{news_id}_{reaction_type}"
        ))
    
    # ВСЕГДА возвращаем ОДИН ряд для универсальной совместимости
    return InlineKeyboardMarkup([keyboard_row])


async def send_news_with_reactions(context: ContextTypes.DEFAULT_TYPE, chat_id: int, news_data: tuple,
                                   user_id: int = None, save_message_id: bool = False):
    """📤 Отправка новости с универсальными реакциями"""
    news_id, content, media_type, media_id, created_at = news_data

    # Форматируем дату по московскому времени (UTC+3)
    if isinstance(created_at, str):
        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if date_obj.tzinfo is None:
            moscow_tz = timezone(timedelta(hours=3))
            date_obj = date_obj.replace(tzinfo=moscow_tz)
        formatted_date = date_obj.strftime("%d.%m.%Y в %H:%M")
    else:
        formatted_date = created_at.strftime("%d.%m.%Y в %H:%M")

    # Получаем реакцию пользователя
    user_reaction = news_bot.get_user_reaction(user_id, news_id) if user_id else None

    # Определяем размер поста
    post_size = determine_post_size(content, media_type)

    # Создаем универсальную клавиатуру (всегда один ряд)
    reply_markup = create_universal_reactions_keyboard(news_id, user_reaction, post_size)

    message_text = f"📅 {formatted_date}\n\n{content}" if content else f"📅 {formatted_date}"

    try:
        sent_message = None

        if media_type and media_id:
            if media_type == "photo":
                sent_message = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=media_id,
                    caption=message_text,
                    reply_markup=reply_markup
                )
            elif media_type == "video":
                sent_message = await context.bot.send_video(
                    chat_id=chat_id,
                    video=media_id,
                    caption=message_text,
                    reply_markup=reply_markup
                )
            elif media_type == "document":
                sent_message = await context.bot.send_document(
                    chat_id=chat_id,
                    document=media_id,
                    caption=message_text,
                    reply_markup=reply_markup
                )
        else:
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=reply_markup
            )

        # Сохраняем message_id для синхронизации
        if save_message_id and sent_message and user_id:
            news_bot.save_sent_message(user_id, news_id, sent_message.message_id)

        return sent_message

    except Exception as e:
        logger.error(f"Ошибка отправки новости {news_id} пользователю {chat_id}: {e}")
        return None


async def update_all_reactions_for_news(context: ContextTypes.DEFAULT_TYPE, news_id: int):
    """🔄 Синхронизация реакций во всех сообщениях с универсальными клавиатурами"""

    # Получаем информацию о новости для определения размера поста
    conn = sqlite3.connect(news_bot.db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT content, media_type FROM news WHERE id = ?', (news_id,))
    news_info = cursor.fetchone()
    conn.close()

    if not news_info:
        logger.error(f"Новость {news_id} не найдена для обновления реакций")
        return

    content, media_type = news_info
    post_size = determine_post_size(content, media_type)

    sent_messages = news_bot.get_sent_messages_for_news(news_id)

    updated_count = 0
    failed_count = 0

    logger.info(f"🔄 Начинаем обновление реакций для новости {news_id} (размер: {post_size}). Сообщений: {len(sent_messages)}")

    for user_id, message_id in sent_messages:
        try:
            user_reaction = news_bot.get_user_reaction(user_id, news_id)
            # Используем универсальную клавиатуру
            new_keyboard = create_universal_reactions_keyboard(news_id, user_reaction, post_size)

            await context.bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=message_id,
                reply_markup=new_keyboard
            )
            updated_count += 1

            await asyncio.sleep(0.05)

        except Exception as e:
            failed_count += 1
            error_msg = str(e).lower()

            if "message to edit not found" in error_msg or "message is not modified" in error_msg:
                news_bot.remove_sent_message(user_id, news_id)
                logger.info(f"📝 Удалена запись о несуществующем сообщении для пользователя {user_id}")
            else:
                logger.error(f"❌ Ошибка обновления реакций для пользователя {user_id}, сообщение {message_id}: {e}")

    logger.info(f"✅ Синхронизация реакций завершена для новости {news_id}: обновлено {updated_count}, ошибок {failed_count}")


async def update_all_messages_for_news(context: ContextTypes.DEFAULT_TYPE, news_id: int, new_content: str):
    """📝 Обновление контента во всех сообщениях с универсальными клавиатурами"""

    # Получаем информацию о новости
    conn = sqlite3.connect(news_bot.db_name)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT content, media_type, media_id, created_at FROM news WHERE id = ?
    ''', (news_id,))

    news_data = cursor.fetchone()
    conn.close()

    if not news_data:
        logger.error(f"Новость {news_id} не найдена для обновления")
        return

    content, media_type, media_id, created_at = news_data

    # Определяем размер поста с обновленным контентом
    post_size = determine_post_size(new_content, media_type)

    # Форматируем оригинальное время создания (UTC+3)
    if isinstance(created_at, str):
        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if date_obj.tzinfo is None:
            moscow_tz = timezone(timedelta(hours=3))
            date_obj = date_obj.replace(tzinfo=moscow_tz)
        formatted_date = date_obj.strftime("%d.%m.%Y в %H:%M")
    else:
        formatted_date = created_at.strftime("%d.%m.%Y в %H:%M")

    sent_messages = news_bot.get_sent_messages_for_news(news_id)

    updated_count = 0
    failed_count = 0

    logger.info(f"📝 Начинаем обновление контента для новости {news_id} (размер: {post_size}). Сообщений: {len(sent_messages)}")

    for user_id, message_id in sent_messages:
        try:
            user_reaction = news_bot.get_user_reaction(user_id, news_id)
            # Используем универсальную клавиатуру
            new_keyboard = create_universal_reactions_keyboard(news_id, user_reaction, post_size)

            # Формируем новый текст
            message_text = f"📅 {formatted_date}\n\n{new_content}" if new_content else f"📅 {formatted_date}"

            # Обновляем сообщение
            if media_type:
                await context.bot.edit_message_caption(
                    chat_id=user_id,
                    message_id=message_id,
                    caption=message_text,
                    reply_markup=new_keyboard
                )
            else:
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=message_text,
                    reply_markup=new_keyboard
                )

            updated_count += 1
            await asyncio.sleep(0.05)

        except Exception as e:
            failed_count += 1
            error_msg = str(e).lower()

            if "message to edit not found" in error_msg or "message is not modified" in error_msg:
                news_bot.remove_sent_message(user_id, news_id)
                logger.info(f"📝 Удалена запись о несуществующем сообщении для пользователя {user_id}")
            else:
                logger.error(f"❌ Ошибка обновления контента для пользователя {user_id}, сообщение {message_id}: {e}")

    logger.info(f"✅ Обновление контента завершено для новости {news_id}: обновлено {updated_count}, ошибок {failed_count}")
    return updated_count, failed_count


async def delete_all_messages_for_news(context: ContextTypes.DEFAULT_TYPE, news_id: int):
    """🗑 Удаление всех сообщений конкретной новости у всех пользователей"""

    sent_messages = news_bot.get_sent_messages_for_news(news_id)

    if not sent_messages:
        logger.info(f"🗑 Нет сообщений для удаления для новости {news_id}")
        return 0, 0

    deleted_count = 0
    failed_count = 0

    logger.info(f"🗑 Начинаем удаление сообщений для новости {news_id}. Сообщений: {len(sent_messages)}")

    for user_id, message_id in sent_messages:
        try:
            await context.bot.delete_message(
                chat_id=user_id,
                message_id=message_id
            )
            deleted_count += 1
            logger.info(f"✅ Удалено сообщение {message_id} у пользователя {user_id}")

            await asyncio.sleep(0.03)

        except Exception as e:
            failed_count += 1
            error_msg = str(e).lower()

            if "message to delete not found" in error_msg:
                logger.info(f"📝 Сообщение {message_id} для пользователя {user_id} уже удалено")
            elif "chat not found" in error_msg:
                logger.info(f"📝 Чат с пользователем {user_id} не найден")
            elif "bot was blocked" in error_msg:
                logger.info(f"📝 Пользователь {user_id} заблокировал бота")
            else:
                logger.error(f"❌ Ошибка удаления сообщения {message_id} для пользователя {user_id}: {e}")

    # Очищаем записи из базы данных
    conn = sqlite3.connect(news_bot.db_name)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM sent_messages WHERE news_id = ?', (news_id,))
    deleted_messages_records = cursor.rowcount

    cursor.execute('DELETE FROM reactions WHERE news_id = ?', (news_id,))
    deleted_reactions_records = cursor.rowcount

    conn.commit()
    conn.close()

    logger.info(f"✅ Удаление завершено для новости {news_id}:")
    logger.info(f"   📤 Удалено сообщений: {deleted_count}")
    logger.info(f"   ❌ Ошибок: {failed_count}")
    logger.info(f"   🗂 Удалено записей о сообщениях: {deleted_messages_records}")
    logger.info(f"   🎭 Удалено записей о реакциях: {deleted_reactions_records}")

    return deleted_count, failed_count


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏠 Обработчик команды /start"""
    user = update.effective_user

    news_bot.add_user(user.id, user.username, user.first_name)

    if news_bot.is_user_subscribed(user.id):
        await update.message.reply_text(
            f"С возвращением, {user.first_name}! 👋\n\n"
            "Ты уже подписан на новости. Используй /news для просмотра всех новостей."
        )
        return

    welcome_text = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Добро пожаловать в новостной бот Кировского Завода! Здесь ты будешь получать самые свежие и важные новости. "
        "Присоединяйся к нашему сообществу!"
    )

    keyboard = [[InlineKeyboardButton("🚀 Присоединиться", callback_data="subscribe")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Обработчик подписки"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    news_bot.subscribe_user(user_id)

    await query.edit_message_text(
        "🎉 Отлично! Ты успешно подписался на новости Кировского Завода!\n\n"
        "Теперь ты будешь получать все наши обновления. "
        "Ниже все наши публикации в хронологическом порядке:"
    )

    news_list = news_bot.get_all_news()
    if news_list:
        await asyncio.sleep(1)

        for news_data in news_list:
            await send_news_with_reactions(context, query.message.chat_id, news_data, user_id, save_message_id=True)
            await asyncio.sleep(0.3)


async def reaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎭 Обработчик реакций с универсальной синхронизацией"""
    query = update.callback_query

    user_id = query.from_user.id

    try:
        _, news_id, reaction_type = query.data.split('_', 2)
        news_id = int(news_id)
    except (ValueError, IndexError):
        await query.answer("❌ Ошибка обработки реакции")
        return

    if not news_bot.is_user_subscribed(user_id):
        await query.answer("❌ Для реакций нужно подписаться на новости!")
        return

    current_reaction = news_bot.get_user_reaction(user_id, news_id)

    if current_reaction == reaction_type:
        news_bot.remove_reaction(user_id, news_id)
        await query.answer()
    else:
        news_bot.add_reaction(user_id, news_id, reaction_type)
        await query.answer()

    # Синхронизируем реакции у всех пользователей с универсальными клавиатурами
    await update_all_reactions_for_news(context, news_id)


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📰 Команда просмотра всех новостей"""
    user_id = update.effective_user.id

    if not news_bot.is_user_subscribed(user_id):
        await update.message.reply_text(
            "❌ Ты не подписан на новости!\n"
            "Используй /start чтобы подписаться."
        )
        return

    news_list = news_bot.get_all_news()

    if not news_list:
        await update.message.reply_text("📰 Пока что новостей нет.")
        return

    for news_data in news_list:
        await send_news_with_reactions(context, update.message.chat_id, news_data, user_id, save_message_id=True)
        await asyncio.sleep(0.3)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """❓ Помощь"""
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        help_text = (
            "👑 Команды администратора:\n\n"
            "📊 /stats - статистика бота\n"
            "📝 /edit_list - список новостей для редактирования\n"
            "✏️ /edit ID текст - редактировать новость (в реальном времени)\n"
            "🗑 /delete ID - удалить новость у всех пользователей\n"
            "❓ /help - это сообщение\n\n"
            "📤 Публикация новостей:\n"
            "• Любое текстовое сообщение\n"
            "• Фото с подписью или без\n"
            "• Видео с подписью или без\n"
            "• Документы с подписью\n\n"
            "🚀 Возможности синхронизации:\n"
            "• Реакции синхронизируются в реальном времени\n"
            "• Редактирование постов обновляет их у всех пользователей мгновенно\n"
            "• Удаление постов удаляет их у всех пользователей мгновенно\n"
            "• Универсальные клавиатуры для всех устройств (один ряд)"
        )
    else:
        help_text = (
            "📱 Доступные команды:\n\n"
            "🏠 /start - запуск бота и подписка\n"
            "📰 /news - просмотр всех новостей\n"
            "❓ /help - показать эту справку\n\n"
            "💡 Как пользоваться:\n"
            "1. Нажми /start для подписки\n"
            "2. Получай новые публикации автоматически\n"
            "3. Ставь реакции на новости\n"
            "4. Используй /news для просмотра архива\n\n"
            "🔄 Все изменения синхронизируются в реальном времени!"
        )

    await update.message.reply_text(help_text)


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Статистика"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    conn = sqlite3.connect(news_bot.db_name)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE is_subscribed = TRUE')
    subscribers = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM news')
    total_news = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM reactions')
    total_reactions = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM sent_messages')
    tracked_messages = cursor.fetchone()[0]

    cursor.execute('''
        SELECT reaction_type, COUNT(*) as count 
        FROM reactions 
        GROUP BY reaction_type 
        ORDER BY count DESC 
        LIMIT 6
    ''')
    top_reactions = cursor.fetchall()

    conn.close()

    stats_text = (
        "📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Подписчиков: {subscribers}\n"
        f"📰 Опубликовано новостей: {total_news}\n"
        f"🎭 Всего реакций: {total_reactions}\n"
        f"🔄 Отслеживаемых сообщений: {tracked_messages}"
    )

    if top_reactions:
        stats_text += "\n\n🏆 Популярные реакции:\n"
        for reaction_type, count in top_reactions:
            emoji = [emoji for emoji, rtype in REACTIONS.items() if rtype == reaction_type][0]
            stats_text += f"   {emoji} {count}\n"

    await update.message.reply_text(stats_text)


async def admin_edit_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Список новостей для редактирования"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    news_list = news_bot.get_news_for_edit()

    if not news_list:
        await update.message.reply_text("📰 Новостей пока нет.")
        return

    response = "📝 Список новостей для редактирования:\n\n"

    for news_id, content, created_at in news_list:
        preview = content[:50] + "..." if len(content) > 50 else content

        # Исправляем отображение времени (UTC+3)
        if isinstance(created_at, str):
            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if date_obj.tzinfo is None:
                moscow_tz = timezone(timedelta(hours=3))
                date_obj = date_obj.replace(tzinfo=moscow_tz)
            formatted_date = date_obj.strftime("%d.%m.%Y")
        else:
            formatted_date = created_at.strftime("%d.%m.%Y")

        reactions_count = news_bot.get_reactions_for_news(news_id)
        total_reactions = sum(reactions_count.values())

        response += f"🔸 #{news_id} ({formatted_date}) 🎭{total_reactions}\n{preview}\n\n"

    response += "Для редактирования используй:\n"
    response += "📝 /edit 5 новый текст (обновится у всех в реальном времени)\n"
    response += "🗑 /delete 5 (удалится у всех пользователей)"

    await update.message.reply_text(response)


async def admin_edit_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✏️ Редактирование новости с обновлением в реальном времени"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    try:
        parts = update.message.text.split(' ', 2)
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Неправильный формат!\n"
                "Используй: /edit ID новый_текст"
            )
            return

        news_id = int(parts[1])
        new_content = parts[2]

    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")
        return

    # Обновляем новость в базе данных
    success = news_bot.update_news(news_id, new_content)

    if success:
        await update.message.reply_text(f"✅ Новость #{news_id} обновляется...")

        # Обновляем ВСЕ сообщения этой новости у всех пользователей в реальном времени
        updated_count, failed_count = await update_all_messages_for_news(context, news_id, new_content)

        await update.message.reply_text(
            f"🚀 Новость #{news_id} обновлена в реальном времени!\n"
            f"📤 Обновлено сообщений: {updated_count}\n"
            f"❌ Ошибок: {failed_count}\n"
            f"🌍 Режим: универсальная совместимость"
        )
    else:
        await update.message.reply_text(f"❌ Новость #{news_id} не найдена!")


async def admin_delete_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🗑 Удаление новости с мгновенным удалением у всех пользователей"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            await update.message.reply_text(
                "❌ Неправильный формат!\n"
                "Используй: /delete ID\n"
                "Пример: /delete 5"
            )
            return

        news_id = int(parts[1])

    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")
        return

    # Проверяем, существует ли новость
    conn = sqlite3.connect(news_bot.db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM news WHERE id = ?', (news_id,))
    news_exists = cursor.fetchone()[0] > 0
    conn.close()

    if not news_exists:
        await update.message.reply_text(f"❌ Новость #{news_id} не найдена!")
        return

    # Показываем прогресс
    progress_msg = await update.message.reply_text(f"🗑 Удаляю новость #{news_id} у всех пользователей...")

    # КРИТИЧНО: Удаляем все сообщения у пользователей В РЕАЛЬНОМ ВРЕМЕНИ
    deleted_count, failed_count = await delete_all_messages_for_news(context, news_id)

    # Удаляем новость из базы данных
    success = news_bot.delete_news(news_id)

    if success:
        await progress_msg.edit_text(
            f"✅ Новость #{news_id} полностью удалена!\n"
            f"🗑 Удалено сообщений: {deleted_count}\n"
            f"❌ Ошибок: {failed_count}\n"
            f"📊 Новость удалена из базы данных"
        )
    else:
        await progress_msg.edit_text(
            f"⚠️ Частичное удаление новости #{news_id}\n"
            f"🗑 Удалено сообщений: {deleted_count}\n"
            f"❌ Ошибок: {failed_count}\n"
            f"❌ Не удалось удалить из базы данных"
        )


async def admin_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📤 Публикация новости администратором с универсальными клавиатурами"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    message = update.message
    news_content = ""
    media_type = None
    media_id = None

    # Определяем тип контента
    if message.text:
        news_content = message.text
    elif message.photo:
        media_type = "photo"
        media_id = message.photo[-1].file_id
        news_content = message.caption or ""
    elif message.video:
        media_type = "video"
        media_id = message.video.file_id
        news_content = message.caption or ""
    elif message.document:
        media_type = "document"
        media_id = message.document.file_id
        news_content = message.caption or ""
    else:
        await update.message.reply_text("❌ Поддерживаются только текст, фото, видео и документы.")
        return

    # Получаем московское время (UTC+3)
    moscow_tz = timezone(timedelta(hours=3))
    moscow_time = datetime.now(moscow_tz)

    # Сохраняем новость
    news_id = news_bot.add_news(news_content, media_type, media_id)

    # Обновляем время создания на московское
    conn = sqlite3.connect(news_bot.db_name)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE news SET created_at = ? WHERE id = ?
    ''', (moscow_time.isoformat(), news_id))
    conn.commit()
    conn.close()

    # Получаем подписчиков
    subscribers = news_bot.get_subscribed_users()

    if not subscribers:
        await update.message.reply_text("✅ Новость сохранена, но подписчиков пока нет.")
        return

    # Определяем размер поста
    post_size = determine_post_size(news_content, media_type)

    # Отправляем всем подписчикам
    sent_count = 0
    formatted_time = moscow_time.strftime('%d.%m.%Y в %H:%M')

    for subscriber_id in subscribers:
        try:
            # Используем универсальную клавиатуру
            reply_markup = create_universal_reactions_keyboard(news_id, None, post_size)

            sent_message = None
            message_text = f"📅 {formatted_time}\n\n{news_content}" if news_content else f"📅 {formatted_time}"

            if media_type:
                if media_type == "photo":
                    sent_message = await context.bot.send_photo(
                        chat_id=subscriber_id,
                        photo=media_id,
                        caption=message_text,
                        reply_markup=reply_markup
                    )
                elif media_type == "video":
                    sent_message = await context.bot.send_video(
                        chat_id=subscriber_id,
                        video=media_id,
                        caption=message_text,
                        reply_markup=reply_markup
                    )
                elif media_type == "document":
                    sent_message = await context.bot.send_document(
                        chat_id=subscriber_id,
                        document=media_id,
                        caption=message_text,
                        reply_markup=reply_markup
                    )
            else:
                sent_message = await context.bot.send_message(
                    chat_id=subscriber_id,
                    text=message_text,
                    reply_markup=reply_markup
                )

            # Сохраняем message_id для синхронизации
            if sent_message:
                news_bot.save_sent_message(subscriber_id, news_id, sent_message.message_id)
                sent_count += 1

        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {subscriber_id}: {e}")

        await asyncio.sleep(0.1)

    await update.message.reply_text(
        f"✅ Новость опубликована с универсальными реакциями!\n"
        f"📤 Отправлено {sent_count} из {len(subscribers)} подписчиков.\n"
        f"📏 Размер поста: {post_size}\n"
        f"🌍 Режим: универсальная совместимость (один ряд)"
    )


async def setup_commands(application):
    """⚙️ Настройка команд"""
    user_commands = [
        BotCommand("start", "🏠 Запуск бота и подписка"),
        BotCommand("news", "📰 Просмотр всех новостей"),
        BotCommand("help", "❓ Помощь и список команд")
    ]

    admin_commands = [
        BotCommand("start", "🏠 Запуск бота"),
        BotCommand("news", "📰 Просмотр всех новостей"),
        BotCommand("stats", "📊 Статистика бота"),
        BotCommand("edit_list", "📝 Список новостей для редактирования"),
        BotCommand("help", "❓ Помощь и список команд")
    ]

    await application.bot.set_my_commands(user_commands)

    try:
        from telegram import BotCommandScopeChat
        await application.bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=ADMIN_ID)
        )
        print(f"✅ Команды для админа ({ADMIN_ID}) установлены")
    except Exception as e:
        print(f"⚠️ Не удалось установить команды для админа: {e}")


def main():
    """🚀 Запуск бота"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Установи BOT_TOKEN в переменные окружения!")
        return

    if ADMIN_ID == 0:
        print("❌ Установи ADMIN_ID в переменные окружения!")
        return

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("edit_list", admin_edit_list))
    application.add_handler(CommandHandler("edit", admin_edit_news))
    application.add_handler(CommandHandler("delete", admin_delete_news))
    application.add_handler(CallbackQueryHandler(subscribe_callback, pattern="^subscribe$"))
    application.add_handler(CallbackQueryHandler(reaction_callback, pattern="^reaction_"))

    # Обработчик сообщений от админа
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) &
            filters.User(user_id=ADMIN_ID) & ~filters.COMMAND,
            admin_post
        )
    )

    print("🚀 Бот запущен с универсальными реакциями!")
    print(f"👑 ID администратора: {ADMIN_ID}")
    print("🌍 Универсальные клавиатуры оптимизированы для ВСЕХ устройств!")
    print("📱 Реакции ВСЕГДА отображаются в один ряд!")
    print("🔄 Реакции обновляются в реальном времени у всех пользователей!")
    print("📝 Редактирование постов происходит мгновенно у всех пользователей!")
    print("🗑 Удаление постов удаляет их у всех пользователей мгновенно!")
    print("🕐 Время отображается точно по Москве")

    print("\n📋 Команды для администратора:")
    print("  📊 /stats - статистика")
    print("  📝 /edit_list - список новостей для редактирования")
    print("  ✏️ /edit ID текст - редактировать новость (в реальном времени)")
    print("  🗑 /delete ID - удалить новость у всех пользователей")
    print("  ❓ /help - список всех команд")
    print("  📤 Любое сообщение (текст/фото/видео) - публикация")

    print("\n📱 Команды для пользователей:")
    print("  🏠 /start - запуск и подписка")
    print("  📰 /news - просмотр новостей")
    print("  🎭 Реакции на новости")
    print("  ❓ /help - помощь")

    print("\n🌍 Новые возможности универсальных реакций:")
    print("  📏 Автоматическое определение размера поста")
    print("  💻 Идеальная совместимость с мобильными и десктопными устройствами")
    print("  🔄 ВСЕГДА один ряд реакций - никаких многоточий!")
    print("  ⚡ Адаптивное форматирование под размер поста")
    print("  📊 Масштабирование счетчиков (1K, 1M)")
    print("  🎯 3 режима: minimal, compact, standard")

    # Настраиваем команды
    async def post_init(application):
        await setup_commands(application)

    application.post_init = post_init

    # Запускаем
    application.run_polling()


if __name__ == '__main__':
    main()
