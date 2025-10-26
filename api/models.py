from pydantic import BaseModel, EmailStr #BaseModel от Pydantic - автоматическая валидация данных EmailStr - проверяет что email валидный
from typing import Optional #Optional - поле может быть пустым
from datetime import datetime
from enum import Enum #Enum - ограничивает возможные значения (роли, статусы)

# ПЕРЕЧИСЛЕНИЕ РОЛЕЙ ПОЛЬЗОВАТЕЛЕЙ
class UserRole(str, Enum):
    """
    Роли пользователей в системе:
    - admin:    Полный доступ, управление пользователями
    - manager:  Создание проектов, управление командой  
    - user:     Выполнение задач, просмотр проектов
    - guest:    Только общая информация, подача заявок
    """
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"

#СТАТУСЫ ЗАЯВОК НА ПОВЫШЕНИЕ
class RequestStatus(str, Enum):
    """
    Статусы заявок на повышение роли:
    - pending:  Ожидает рассмотрения
    - approved: Одобрена (роль изменена)
    - rejected: Отклонена
    """
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"

# МОДЕЛЬ ДЛЯ СОЗДАНИЯ ПОЛЬЗОВАТЕЛЯ (РЕГИСТРАЦИЯ)
class UserCreate(BaseModel):
    """
    Модель для регистрации нового пользователя.
    При регистрации все новые пользователи автоматически 
    получают роль 'guest' для безопасности.
    """
    username: str           # Уникальное имя пользователя
    email: EmailStr         # Валидный email (проверяется автоматически)
    password: str           # Пароль (будет хеширован)
    full_name: Optional[str] = None     # Полное имя
    position: Optional[str] = None      # Должность
    department: Optional[str] = None    # Отдел
    # role НЕ включаем - при регистрации всегда 'guest'

# МОДЕЛЬ ДЛЯ ВХОДА ПОЛЬЗОВАТЕЛЯ
class UserLogin(BaseModel):
    """
    Модель для авторизации пользователя.
    Используется в эндпоинте /auth/login
    """
    username: str
    password: str

# МОДЕЛЬ ОТВЕТА С ДАННЫМИ ПОЛЬЗОВАТЕЛЯ
class UserResponse(BaseModel):
    """
    Модель для ответа API с данными пользователя.
    ВАЖНО: Никогда не включаем пароль в ответ!
    """
    id: int
    username: str
    email: str
    role: UserRole
    full_name: Optional[str]
    position: Optional[str]
    department: Optional[str]
    is_actibe: bool
    created_at: datetime

# МОДЕЛЬ ДЛЯ JWT ТОКЕНОВ
class Token(BaseModel):
    """
    Модель для ответа с JWT токенами после успешного входа.
    - access_token:  Для доступа к API (короткоживущий)
    - refresh_token: Для обновления access token (долгоживущий)
    - token_type:    Всегда 'bearer' (стандарт)
    """
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'

# МОДЕЛЬ ДЛЯ ОБНОВЛЕНИЯ ТОКЕНОВ
class TokenRefresh(BaseModel):
    """
    Модель для запроса обновления access token.
    Используется в эндпоинте /auth/refresh
    """
    refresh_token: str

# МОДЕЛЬ ДЛЯ ЗАЯВКИ НА ПОВЫШЕНИЕ РОЛИ
class RoleRequestCreate(BaseModel):
    """
    Модель для подачи заявки на повышение роли.
    - guest может запросить user или manager
    - user может запросить manager
    """
    requested_role: UserRole  # Какую роль запрашивает
    message: Optional[str] = None  # Обоснование заявки может быть пустым в теории

#  МОДЕЛЬ ОТВЕТА С ДАННЫМИ ЗАЯВКИ
class RoleRequestResponse(BaseModel):
    """
    Модель для ответа с данными заявки на повышение.
    """
    id: int
    user_id: int
    requested_role: UserRole
    current_role: UserRole  
    status: RequestStatus
    message: Optional[str]
    admin_notes: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[int]

# МОДЕЛЬ ДЛЯ РАССМОТРЕНИЯ ЗАЯВКИ АДМИНОМ
class RoleRequestReview(BaseModel):
    """
    Модель для рассмотрения заявки администратором.
    """
    status: RequestStatus
    admin_notes: Optional[str] = None

