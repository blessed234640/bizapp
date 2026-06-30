from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    INTERN = "intern"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# --- Auth ---

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


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
    password: Optional[str] = None


class UpgradeRequestCreate(BaseModel):
    requested_role: UserRole
    reason: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


# --- Tasks ---

class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    priority: int = 0
    assigned_to: Optional[int] = None
    deadline: Optional[str] = None
    is_critical: bool = False


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[int] = None
    assigned_to: Optional[int] = None
    deadline: Optional[datetime] = None


class TaskComplete(BaseModel):
    completion_note: str


class TaskResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: int
    assigned_to: Optional[int] = None
    assigned_username: Optional[str] = None
    deadline: Optional[datetime] = None
    is_critical: bool
    ai_generated: bool
    completed_at: Optional[datetime] = None
    ai_score: Optional[int] = None
    ai_feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# --- AI ---

class AIGenerateRequest(BaseModel):
    description: str


class AIGeneratedTask(BaseModel):
    title: str
    description: str
    priority: int
    deadline_days: int


class AIGenerateResponse(BaseModel):
    tasks: List[AIGeneratedTask]


class AIReportResponse(BaseModel):
    id: int
    project_id: int
    project_title: str
    report_date: date
    content: dict
    created_at: datetime


# --- Employee stats ---

class EmployeeStatsResponse(BaseModel):
    user_id: int
    username: str
    total_completed: int
    completed_on_time: int
    completed_overdue: int
    avg_score: Decimal
    updated_at: datetime
