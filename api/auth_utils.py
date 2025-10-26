from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
# =============================================
# КОНСТАНТЫ ДЛЯ НАСТРОЙКИ JWT
# =============================================

# Секретный ключ для подписи JWT токенов
# ВНИМАНИЕ: В продакшн хранить в .env файле!
SECRET_KEY = "bizapp-super-secret-key-2025-change-in-production"

# Алгоритм шифрования для JWT (HS256 - самый распространенный)
ALGORITHM = "HS256"

# Время жизни access token (30 минут)
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Время жизни refresh token (7 дней)
REFRESH_TOKEN_EXPIRE_DAYS = 7


# =============================================
# НАСТРОЙКА ДЛЯ ХЕШИРОВАНИЯ ПАРОЛЕЙ
# =============================================

# Создаем контекст для работы с паролями
# bcrypt - современный безопасный алгоритм
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПАРОЛЯМИ
# =============================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет совпадает ли введенный пароль с хешем из базы данных.
    Как работает:
    1. Пользователь вводит пароль при входе
    2. Мы находим хеш пароля в базе данных
    3. Функция сравнивает введенный пароль с хешем
    Args:
        plain_password: Пароль в чистом виде (от пользователя)
        hashed_password: Хешированный пароль (из базы данных)
    Returns:
        bool: True если пароли совпадают, False если нет
    Пример:
        verify_password("my_password", "$2b$12$LXoFyXK3Yp7p7W6Q6zQ6Oe")
        → True (если пароль верный)
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Создает безопасный хеш пароля для хранения в базе данных.
    Почему bcrypt безопасен:
    - Добавляет "соль" (salt) - случайные данные к паролю
    - Делает каждый хеш уникальным (даже для одинаковых паролей)
    - Защищает от rainbow table атак
    Args:
        password: Пароль в чистом виде
    Returns:
        str: Безопасный хеш пароля
    Пример:
        get_password_hash("my_password")
        → "$2b$12$LXoFyXK3Yp7p7W6Q6zQ6Oe" (уникальный хеш)
    """
    return pwd_context.hash(password)

# =============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С JWT ТОКЕНАМИ
# =============================================
def create_access_token(data: dict, expires_delta: timedelta=None) -> str:
    """
    Создает JWT access token с коротким временем жизни.
    Структура access token:
    {
        "user_id": 1,
        "username": "testuser", 
        "role": "user",
        "exp": 1729900000  # Timestamp истечения
    }
    Args:
        data: Данные для кодирования (user_id, username, role)
        expires_delta: Время жизни токена (если не указано - 30 минут)
    Returns:
        str: Закодированный JWT токен
    Пример:
        create_access_token({"user_id": 1, "username": "test"})
        → "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    # Создаем копию данных чтобы не изменять оригинал
    to_encode = data.copy()
    
    # Устанавливаем время expiration токена
    if expires_delta:
        # Если передано явное время - используем его
        expire = datetime.utcnow() + expires_delta
    else:
        # Иначе используем дефолтное время (30 минут)
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Добавляем поле exp (expiration) в данные
    to_encode.update({"exp": expire})
    
    # Кодируем данные в JWT токен с нашей подписью
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """
    Создает JWT refresh token с длительным временем жизни.
    Refresh token используется для получения новой пары токенов
    когда access token истек.
    Структура refresh token:
    {
        "user_id": 1,
        "username": "testuser",
        "role": "user", 
        "type": "refresh",  # Помечаем что это refresh token
        "exp": 1730500000   # На 7 дней позже
    }
    Args:
        data: Данные для кодирования (user_id, username, role)
    Returns:
        str: Закодированный JWT refresh token
    """
    to_encode = data.copy()
    
    # Устанавливаем время жизни 7 дней для refresh token
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Добавляем expiration и тип токена
    to_encode.update({
        "exp": expire,
        "type": "refresh"  # Важно: помечаем тип токена
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """
    Проверяет JWT токен и возвращает данные из него.
    Как работает проверка:
    1. Декодирует токен с нашим SECRET_KEY
    2. Проверяет подпись (не был ли токен изменен)
    3. Проверяет expiration time (не истек ли токен)
    4. Возвращает данные если все ок
    Args:
        token: JWT токен для проверки
    Returns:
        dict: Данные из токена (user_id, username, role, exp)
    Raises:
        JWTError: Если токен невалидный, просроченный или поддельный
    Пример:
        verify_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        → {"user_id": 1, "username": "test", "role": "user", "exp": 1729900000}
    """
    try:
        # Декодируем токен и проверяем подпись
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        # Если токен невалидный - выбрасываем ошибку
        raise JWTError(f"Невалидный токен: {str(e)}")

def verify_refresh_token(token: str) -> dict:
    """
    Проверяет JWT refresh token и возвращает данные из него.
    Дополнительно проверяет что это действительно refresh token
    (имеет поле type = "refresh")
    Args:
        token: JWT refresh token для проверки
    Returns:
        dict: Данные из токена
    Raises:
        JWTError: Если токен невалидный или не является refresh token
    """
    try:
        # Декодируем токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Проверяем что это действительно refresh token
        if payload.get("type") != "refresh":
            raise JWTError("Неверный тип токена: ожидается refresh token")
            
        return payload
    except JWTError as e:
        raise JWTError(f"Невалидный refresh token: {str(e)}")
    