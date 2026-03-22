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
    email: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    avatar_url: Optional[str] = None

class ProfileUpdate(BaseModel):
    email: Optional[str] = None
    avatar_url: Optional[str] = None

class UpgradeRequestCreate(BaseModel):
    requested_role: UserRole
    reason: str

# МОДЕЛЬ ДЛЯ JWT ТОКЕНОВ
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'

# МОДЕЛЬ ДЛЯ ОБНОВЛЕНИЯ ТОКЕНОВ
class TokenRefresh(BaseModel):
    refresh_token: str