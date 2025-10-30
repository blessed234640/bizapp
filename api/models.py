from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

# ПЕРЕЧИСЛЕНИЕ РОЛЕЙ - оставляем для проверки в JWT
class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager" 
    USER = "user"
    GUEST = "guest"

# МОДЕЛЬ ДЛЯ РЕГИСТРАЦИИ (упрощенная)
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    # Убираем лишние поля - они в Django админке

# МОДЕЛЬ ДЛЯ ВХОДА
class UserLogin(BaseModel):
    username: str
    password: str

# МОДЕЛЬ ОТВЕТА С ДАННЫМИ ПОЛЬЗОВАТЕЛЯ (упрощенная)
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    # Убираем full_name, position, department - это в Django

# МОДЕЛЬ ДЛЯ JWT ТОКЕНОВ
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'

# МОДЕЛЬ ДЛЯ ОБНОВЛЕНИЯ ТОКЕНОВ
class TokenRefresh(BaseModel):
    refresh_token: str