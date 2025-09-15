"""
База данных для Web App с поддержкой миграций
"""
import sqlite3
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WebAppDatabase:
    """Класс для работы с базой данных Web App"""
    
    def __init__(self, db_name: str = 'webapp_kyrov.db'):
        self.db_name = db_name
        self.init_db()
        self.migrate_db()  # Добавляем миграцию существующих таблиц
    
    def migrate_db(self):
        """Миграция существующей базы данных - добавление недостающих колонок"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Проверяем структуру таблицы newspaper_articles
            cursor.execute("PRAGMA table_info(newspaper_articles)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Добавляем недостающие колонки в newspaper_articles
            if 'published_date' not in columns:
                logger.info("Добавление колонки published_date в newspaper_articles")
                cursor.execute('''
                    ALTER TABLE newspaper_articles 
                    ADD COLUMN published_date TEXT DEFAULT CURRENT_TIMESTAMP
                ''')
            
            if 'views' not in columns:
                logger.info("Добавление колонки views в newspaper_articles")
                cursor.execute('''
                    ALTER TABLE newspaper_articles 
                    ADD COLUMN views INTEGER DEFAULT 0
                ''')
            
            if 'image_url' not in columns:
                logger.info("Добавление колонки image_url в newspaper_articles")
                cursor.execute('''
                    ALTER TABLE newspaper_articles 
                    ADD COLUMN image_url TEXT
                ''')
            
            # Проверяем структуру таблицы calendar_events
            cursor.execute("PRAGMA table_info(calendar_events)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'is_recurring' not in columns:
                logger.info("Добавление колонки is_recurring в calendar_events")
                cursor.execute('''
                    ALTER TABLE calendar_events 
                    ADD COLUMN is_recurring BOOLEAN DEFAULT 0
                ''')
            
            if 'recurrence_pattern' not in columns:
                logger.info("Добавление колонки recurrence_pattern в calendar_events")
                cursor.execute('''
                    ALTER TABLE calendar_events 
                    ADD COLUMN recurrence_pattern TEXT
                ''')
            
            # Проверяем структуру таблицы feedback
            cursor.execute("PRAGMA table_info(feedback)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'status' not in columns:
                logger.info("Добавление колонки status в feedback")
                cursor.execute('''
                    ALTER TABLE feedback 
                    ADD COLUMN status TEXT DEFAULT 'new'
                ''')
            
            if 'response' not in columns:
                logger.info("Добавление колонки response в feedback")
                cursor.execute('''
                    ALTER TABLE feedback 
                    ADD COLUMN response TEXT
                ''')
            
            if 'responded_at' not in columns:
                logger.info("Добавление колонки responded_at в feedback")
                cursor.execute('''
                    ALTER TABLE feedback 
                    ADD COLUMN responded_at TIMESTAMP
                ''')
            
            conn.commit()
            logger.info("✅ Миграция базы данных завершена")
            
        except Exception as e:
            logger.error(f"Ошибка при миграции базы данных: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def init_db(self):
        """Инициализация базы данных для Web App"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Таблица для статей газеты
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS newspaper_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author TEXT,
                    category TEXT,
                    image_url TEXT,
                    published_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    views INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для событий календаря
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    event_date TEXT NOT NULL,
                    event_time TEXT,
                    location TEXT,
                    category TEXT,
                    is_recurring BOOLEAN DEFAULT 0,
                    recurrence_pattern TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для обратной связи
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    department TEXT,
                    phone TEXT,
                    message TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    status TEXT DEFAULT 'new',
                    response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    responded_at TIMESTAMP
                )
            ''')
            
            # Таблица для аналитики использования
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    action TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для настроек приложения
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            
            # Создаем индексы только после того, как убедились что колонки существуют
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_date ON newspaper_articles(published_date DESC)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_date ON calendar_events(event_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_user ON usage_analytics(user_id)')
                conn.commit()
            except sqlite3.OperationalError as e:
                logger.warning(f"Не удалось создать индекс: {e}")
            
            logger.info(f"✅ База данных {self.db_name} инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
        finally:
            conn.close()
    
    # ==================== МЕТОДЫ ДЛЯ ГАЗЕТЫ ====================
    
    def add_article(self, title: str, content: str, author: str = None, 
                   category: str = None, image_url: str = None, 
                   published_date: str = None) -> int:
        """Добавление новой статьи"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        if not published_date:
            published_date = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO newspaper_articles 
            (title, content, author, category, image_url, published_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, content, author, category, image_url, published_date))
        
        article_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"📰 Добавлена статья #{article_id}: {title}")
        return article_id
    
    def get_newspaper_articles(self, limit: int = 10, offset: int = 0, 
                              category: str = None) -> List[Dict]:
        """Получение статей газеты"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if category:
                cursor.execute('''
                    SELECT * FROM newspaper_articles 
                    WHERE category = ?
                    ORDER BY published_date DESC 
                    LIMIT ? OFFSET ?
                ''', (category, limit, offset))
            else:
                cursor.execute('''
                    SELECT * FROM newspaper_articles 
                    ORDER BY published_date DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            
            articles = [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.OperationalError as e:
            # Если колонка published_date не существует, используем created_at
            logger.warning(f"Ошибка при запросе статей: {e}, пробуем альтернативный запрос")
            
            if category:
                cursor.execute('''
                    SELECT * FROM newspaper_articles 
                    WHERE category = ?
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (category, limit, offset))
            else:
                cursor.execute('''
                    SELECT * FROM newspaper_articles 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            
            articles = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return articles
    
    def get_article_by_id(self, article_id: int) -> Optional[Dict]:
        """Получение статьи по ID"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM newspaper_articles WHERE id = ?', (article_id,))
        row = cursor.fetchone()
        
        # Увеличиваем счётчик просмотров если колонка существует
        if row:
            try:
                cursor.execute('UPDATE newspaper_articles SET views = views + 1 WHERE id = ?', (article_id,))
                conn.commit()
            except sqlite3.OperationalError:
                # Колонка views не существует
                pass
        
        conn.close()
        
        return dict(row) if row else None
    
    def update_article(self, article_id: int, **kwargs) -> bool:
        """Обновление статьи"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        allowed_fields = ['title', 'content', 'author', 'category', 'image_url']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [article_id]
        
        cursor.execute(f'UPDATE newspaper_articles SET {set_clause} WHERE id = ?', values)
        conn.commit()
        
        success = cursor.rowcount > 0
        conn.close()
        
        return success
    
    def delete_article(self, article_id: int) -> bool:
        """Удаление статьи"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM newspaper_articles WHERE id = ?', (article_id,))
        conn.commit()
        
        success = cursor.rowcount > 0
        conn.close()
        
        if success:
            logger.info(f"🗑️ Удалена статья #{article_id}")
        
        return success
    
    # ==================== МЕТОДЫ ДЛЯ КАЛЕНДАРЯ ====================
    
    def add_event(self, title: str, event_date: str, description: str = None,
                 event_time: str = None, location: str = None, 
                 category: str = None, is_recurring: bool = False,
                 recurrence_pattern: str = None) -> int:
        """Добавление события в календарь"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO calendar_events 
                (title, description, event_date, event_time, location, category, 
                 is_recurring, recurrence_pattern)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, event_date, event_time, location, category,
                  is_recurring, recurrence_pattern))
        except sqlite3.OperationalError:
            # Если новые колонки не существуют, используем упрощенный запрос
            cursor.execute('''
                INSERT INTO calendar_events 
                (title, description, event_date, event_time, location, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, description, event_date, event_time, location, category))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"📅 Добавлено событие #{event_id}: {title} на {event_date}")
        return event_id
    
    def get_events(self, start_date: str = None, end_date: str = None,
                  category: str = None) -> List[Dict]:
        """Получение событий из календаря"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM calendar_events WHERE 1=1'
        params = []
        
        if start_date:
            query += ' AND event_date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND event_date <= ?'
            params.append(end_date)
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        query += ' ORDER BY event_date, event_time'
        
        cursor.execute(query, params)
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return events
    
    def get_upcoming_events(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Получение предстоящих событий"""
        today = datetime.now().date().isoformat()
        end_date = (datetime.now() + timedelta(days=days)).date().isoformat()
        
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM calendar_events 
            WHERE event_date >= ? AND event_date <= ?
            ORDER BY event_date, event_time
            LIMIT ?
        ''', (today, end_date, limit))
        
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return events
    
    def update_event(self, event_id: int, **kwargs) -> bool:
        """Обновление события"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Получаем список существующих колонок
        cursor.execute("PRAGMA table_info(calendar_events)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        allowed_fields = ['title', 'description', 'event_date', 'event_time',
                         'location', 'category', 'is_recurring', 'recurrence_pattern']
        
        # Фильтруем только существующие колонки
        updates = {k: v for k, v in kwargs.items() 
                  if k in allowed_fields and k in existing_columns}
        
        if not updates:
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [event_id]
        
        cursor.execute(f'UPDATE calendar_events SET {set_clause} WHERE id = ?', values)
        conn.commit()
        
        success = cursor.rowcount > 0
        conn.close()
        
        return success
    
    def delete_event(self, event_id: int) -> bool:
        """Удаление события"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM calendar_events WHERE id = ?', (event_id,))
        conn.commit()
        
        success = cursor.rowcount > 0
        conn.close()
        
        if success:
            logger.info(f"🗑️ Удалено событие #{event_id}")
        
        return success
    
    # ==================== МЕТОДЫ ДЛЯ ОБРАТНОЙ СВЯЗИ ====================
    
    def save_feedback(self, user_name: str = None, department: str = None,
                     phone: str = None, message: str = None, 
                     category: str = 'general') -> int:
        """Сохранение обратной связи"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (user_name, department, phone, message, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_name, department, phone, message, category))
        
        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"💬 Сохранена обратная связь #{feedback_id} от {user_name} ({department})")
        return feedback_id
    
    def get_feedback(self, status: str = None, limit: int = 50) -> List[Dict]:
        """Получение списка обратной связи"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if status:
                cursor.execute('''
                    SELECT * FROM feedback 
                    WHERE status = ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT * FROM feedback 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
        except sqlite3.OperationalError:
            # Если колонка status не существует
            cursor.execute('''
                SELECT * FROM feedback 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
        
        feedback = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return feedback
    
    def update_feedback_status(self, feedback_id: int, status: str, 
                              response: str = None) -> bool:
        """Обновление статуса обратной связи"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if response:
                cursor.execute('''
                    UPDATE feedback 
                    SET status = ?, response = ?, responded_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, response, feedback_id))
            else:
                cursor.execute('''
                    UPDATE feedback 
                    SET status = ?
                    WHERE id = ?
                ''', (status, feedback_id))
        except sqlite3.OperationalError:
            # Если новые колонки не существуют
            logger.warning("Не удалось обновить статус обратной связи - колонки не существуют")
            return False
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success
    
    # ==================== МЕТОДЫ ДЛЯ АНАЛИТИКИ ====================
    
    def log_action(self, user_id: str = None, action: str = None,
                   details: str = None, ip_address: str = None,
                   user_agent: str = None):
        """Логирование действия пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO usage_analytics (user_id, action, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, ip_address, user_agent))
        
        conn.commit()
        conn.close()
    
    def get_analytics(self, user_id: str = None, action: str = None,
                     days: int = 7) -> List[Dict]:
        """Получение аналитики"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = 'SELECT * FROM usage_analytics WHERE created_at >= ?'
        params = [cutoff_date]
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        if action:
            query += ' AND action = ?'
            params.append(action)
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        analytics = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return analytics
    
    def get_analytics_summary(self, days: int = 7) -> Dict:
        """Получение сводки аналитики"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Общее количество действий
        cursor.execute('''
            SELECT COUNT(*) as total_actions,
                   COUNT(DISTINCT user_id) as unique_users,
                   COUNT(DISTINCT DATE(created_at)) as active_days
            FROM usage_analytics
            WHERE created_at >= ?
        ''', (cutoff_date,))
        
        summary = dict(cursor.fetchone())
        
        # Топ действий
        cursor.execute('''
            SELECT action, COUNT(*) as count
            FROM usage_analytics
            WHERE created_at >= ?
            GROUP BY action
            ORDER BY count DESC
            LIMIT 10
        ''', (cutoff_date,))
        
        summary['top_actions'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return summary
    
    # ==================== МЕТОДЫ ДЛЯ НАСТРОЕК ====================
    
    def get_setting(self, key: str) -> Optional[str]:
        """Получение настройки"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM app_settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def set_setting(self, key: str, value: str):
        """Установка настройки"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value))
        
        conn.commit()
        conn.close()
    
    def get_all_settings(self) -> Dict[str, str]:
        """Получение всех настроек"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT key, value FROM app_settings')
        settings = {row['key']: row['value'] for row in cursor.fetchall()}
        conn.close()
        
        return settings
