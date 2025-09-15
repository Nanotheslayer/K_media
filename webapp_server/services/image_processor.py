"""
Улучшенный обработчик изображений для чата
Поддерживает файлы без расширения (blob) и определение типа по содержимому
"""
import base64
import logging
from typing import Dict, Optional, Tuple
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Класс для обработки изображений в чате"""

    # Поддерживаемые форматы изображений
    SUPPORTED_FORMATS = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'heic': 'image/heic',
        'heif': 'image/heif',
        'gif': 'image/gif',
        'bmp': 'image/bmp'
    }

    # Поддерживаемые MIME типы
    SUPPORTED_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/heic',
        'image/heif',
        'image/gif',
        'image/bmp'
    }

    # Магические байты для определения типа файла
    FILE_SIGNATURES = {
        b'\xFF\xD8\xFF': 'image/jpeg',  # JPEG
        b'\x89PNG\r\n\x1a\n': 'image/png',  # PNG
        b'RIFF': 'image/webp',  # WebP (проверяется дополнительно)
        b'GIF87a': 'image/gif',  # GIF87a
        b'GIF89a': 'image/gif',  # GIF89a
        b'BM': 'image/bmp',  # BMP
    }

    # Максимальный размер файла (в байтах)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (увеличен лимит)

    @staticmethod
    def detect_file_type_by_content(file_data: bytes) -> Optional[str]:
        """Определение типа файла по содержимому (магические байты)"""
        try:
            # Проверяем PNG
            if file_data.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'image/png'

            # Проверяем JPEG
            if file_data.startswith(b'\xFF\xD8\xFF'):
                return 'image/jpeg'

            # Проверяем WebP
            if file_data.startswith(b'RIFF') and b'WEBP' in file_data[:12]:
                return 'image/webp'

            # Проверяем GIF
            if file_data.startswith(b'GIF87a') or file_data.startswith(b'GIF89a'):
                return 'image/gif'

            # Проверяем BMP
            if file_data.startswith(b'BM'):
                return 'image/bmp'

            # Проверяем HEIC/HEIF (более сложная проверка)
            if b'ftyp' in file_data[:20]:
                if b'heic' in file_data[:20] or b'mif1' in file_data[:20]:
                    return 'image/heic'
                elif b'heif' in file_data[:20]:
                    return 'image/heif'

            logger.warning(f"Неизвестный тип файла, первые 20 байт: {file_data[:20]}")
            return None

        except Exception as e:
            logger.error(f"Ошибка определения типа файла: {e}")
            return None

    @staticmethod
    def get_mime_type_from_extension(filename: str) -> str:
        """Определение MIME типа по расширению файла"""
        if not filename:
            return 'image/jpeg'  # По умолчанию

        # Получаем расширение файла
        extension = filename.split('.')[-1].lower() if '.' in filename else ''

        # Возвращаем соответствующий MIME тип
        return ImageProcessor.SUPPORTED_FORMATS.get(extension, 'image/jpeg')

    @staticmethod
    def determine_mime_type(file: FileStorage, file_data: bytes = None) -> str:
        """Комплексное определение MIME типа файла"""
        # 1. Проверяем Content-Type из заголовков
        if hasattr(file, 'content_type') and file.content_type:
            content_type = file.content_type.lower()
            if content_type in ImageProcessor.SUPPORTED_MIME_TYPES:
                logger.info(f"🔍 MIME тип определен по Content-Type: {content_type}")
                return content_type

        # 2. Проверяем по расширению файла
        if file.filename and '.' in file.filename:
            mime_from_extension = ImageProcessor.get_mime_type_from_extension(file.filename)
            if mime_from_extension != 'image/jpeg':  # Если определился не дефолтный тип
                logger.info(f"🔍 MIME тип определен по расширению: {mime_from_extension}")
                return mime_from_extension

        # 3. Проверяем по содержимому файла
        if file_data:
            mime_from_content = ImageProcessor.detect_file_type_by_content(file_data)
            if mime_from_content:
                logger.info(f"🔍 MIME тип определен по содержимому: {mime_from_content}")
                return mime_from_content

        # 4. Пробуем прочитать данные и определить тип
        if not file_data:
            try:
                current_position = file.tell()
                file.seek(0)
                first_bytes = file.read(20)
                file.seek(current_position)

                mime_from_content = ImageProcessor.detect_file_type_by_content(first_bytes)
                if mime_from_content:
                    logger.info(f"🔍 MIME тип определен по первым байтам: {mime_from_content}")
                    return mime_from_content
            except Exception as e:
                logger.warning(f"Не удалось прочитать первые байты файла: {e}")

        # По умолчанию возвращаем JPEG
        logger.info("🔍 MIME тип установлен по умолчанию: image/jpeg")
        return 'image/jpeg'

    @staticmethod
    def validate_image(file: FileStorage) -> Tuple[bool, Optional[str]]:
        """Улучшенная валидация загруженного изображения"""
        # Проверка наличия файла
        if not file:
            return False, "Файл не выбран"

        # Проверка размера файла
        try:
            file.seek(0, 2)  # Перемещаемся в конец файла
            file_size = file.tell()
            file.seek(0)  # Возвращаемся в начало

            if file_size > ImageProcessor.MAX_FILE_SIZE:
                return False, f"Файл слишком большой. Максимальный размер: {ImageProcessor.MAX_FILE_SIZE // (1024*1024)}MB"

            if file_size == 0:
                return False, "Файл пустой"

        except Exception as e:
            logger.error(f"Ошибка проверки размера файла: {e}")
            return False, "Ошибка чтения файла"

        # Определяем MIME тип комплексно
        mime_type = ImageProcessor.determine_mime_type(file)

        # Проверяем, что MIME тип поддерживается
        if mime_type not in ImageProcessor.SUPPORTED_MIME_TYPES:
            return False, f"Неподдерживаемый формат: {mime_type}. Поддерживаются: {', '.join(ImageProcessor.SUPPORTED_MIME_TYPES)}"

        return True, None

    @staticmethod
    def process_uploaded_image(file: FileStorage) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """Обработка загруженного изображения с улучшенным определением типа"""
        try:
            # Логируем информацию о файле
            logger.info(f"📄 Обработка файла: name='{file.filename}', content_type='{getattr(file, 'content_type', 'unknown')}'")

            # Читаем файл сразу для анализа
            file_data = file.read()
            file.seek(0)  # Возвращаемся в начало для повторного чтения

            # Проверка, что данные прочитались
            if not file_data:
                return None, "Не удалось прочитать файл"

            logger.info(f"📏 Размер файла: {len(file_data)} байт ({len(file_data)/1024/1024:.2f} MB)")

            # Определяем MIME тип с учетом содержимого
            mime_type = ImageProcessor.determine_mime_type(file, file_data)

            # Проверяем, что это изображение
            if mime_type not in ImageProcessor.SUPPORTED_MIME_TYPES:
                return None, f"Неподдерживаемый формат: {mime_type}. Поддерживаются: {', '.join(ImageProcessor.SUPPORTED_MIME_TYPES)}"

            # Валидация (теперь после определения типа)
            is_valid, error_message = ImageProcessor.validate_image(file)
            if not is_valid:
                return None, error_message

            # Кодируем в base64
            base64_data = base64.b64encode(file_data).decode('utf-8')

            # Формируем результат
            image_data = {
                "mime_type": mime_type,
                "data": base64_data
            }

            logger.info(f"✅ Изображение обработано: MIME={mime_type}, base64_size={len(base64_data)} символов")

            return image_data, None

        except Exception as e:
            logger.error(f"Ошибка обработки изображения: {e}", exc_info=True)
            return None, f"Ошибка обработки: {str(e)}"

    @staticmethod
    def encode_image_from_bytes(image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, str]:
        """Кодирование байтов изображения в base64"""
        try:
            base64_data = base64.b64encode(image_bytes).decode('utf-8')
            return {
                "mime_type": mime_type,
                "data": base64_data
            }
        except Exception as e:
            logger.error(f"Ошибка кодирования изображения: {e}")
            raise

    @staticmethod
    def decode_base64_image(base64_data: str) -> bytes:
        """Декодирование base64 обратно в байты"""
        try:
            return base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Ошибка декодирования base64: {e}")
            raise

    @staticmethod
    def get_image_info(image_data: Dict[str, str]) -> Dict:
        """Получение информации об изображении"""
        try:
            base64_length = len(image_data.get('data', ''))
            # Приблизительный размер оригинала (base64 увеличивает размер примерно на 33%)
            approx_size = base64_length * 0.75

            return {
                'mime_type': image_data.get('mime_type', 'unknown'),
                'base64_length': base64_length,
                'approx_size_bytes': int(approx_size),
                'approx_size_mb': round(approx_size / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации об изображении: {e}")
            return {}

    @staticmethod
    def is_image_file(filename: str) -> bool:
        """Проверка, является ли файл изображением по расширению"""
        if not filename or '.' not in filename:
            return False

        extension = filename.split('.')[-1].lower()
        return extension in ImageProcessor.SUPPORTED_FORMATS