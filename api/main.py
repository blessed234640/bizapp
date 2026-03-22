import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
import redis as redis_lib
import asyncpg
import json
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

# Загружаем переменные окружения
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/bizapp")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:8080,http://web:8080").split(",")

# СОЗДАЕМ ПРИЛОЖЕНИЕ FASTAPI
app = FastAPI(
    title="Business App API", 
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ИМПОРТЫ ДЛЯ JWT АУТЕНТИФИКАЦИИ
from models import (
    UserCreate, UserLogin, UserResponse, Token, TokenRefresh,
    ProfileUpdate, UpgradeRequestCreate
)
from auth_utils import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    verify_refresh_token,
    verify_access_token
)

# ЗАВИСИМОСТИ ДЛЯ АУТЕНТИФИКАЦИИ И АВТОРИЗАЦИИ
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен"
        )
    return payload

async def admin_only(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user

async def admin_or_manager(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора или менеджера"
        )
    return current_user

async def any_worker(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["admin", "manager", "user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права работника"
        )
    return current_user

async def any_authenticated(current_user: dict = Depends(get_current_user)):
    return current_user

# Функция для подключения к БД
async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

# Функция для подключения к Redis
def get_redis():
    redis = redis_lib.from_url(REDIS_URL, decode_responses=True, encoding='utf-8')
    try:
        yield redis
    finally:
        redis.close()

# МОДЕЛИ ДЛЯ CRUD ОПЕРАЦИЙ
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    status: str = 'pending'
    priority: Optional[str] = 'low'  # 'low', 'medium', 'high'
    assignee_id: Optional[int] = None
    metadata: Optional[dict] = None

class TaskResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: Optional[str]
    status: str
    priority: int
    metadata: Optional[dict]
    created_at: str  
    updated_at: str

class ProjectMemberAdd(BaseModel):
    user_id: int
    role: str = "member"

class ProjectMemberResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    joined_at: str

# УПРАВЛЕНИЕ УЧАСТНИКАМИ ПРОЕКТА
@app.post("/projects/{project_id}/members/", response_model=dict)
async def add_project_member(
    project_id: int,
    member_data: ProjectMemberAdd,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker)
):
    """
    ДОБАВЛЕНИЕ УЧАСТНИКА В ПРОЕКТ
    """
    # Проверяем что текущий пользователь - владелец проекта или менеджер
    project = await conn.fetchrow("SELECT owner_id FROM projects WHERE id = $1", project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Только владелец или админ может добавлять участников
    if project["owner_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only project owner (Manager) or Admin can add members")
    
    # Проверяем что пользователь существует
    user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", member_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Добавляем участника
    try:
        await conn.execute("""
            INSERT INTO project_members (project_id, user_id, role) 
            VALUES ($1, $2, $3)
        """, project_id, member_data.user_id, member_data.role)
        
        return {"message": "Member added successfully"}
    
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="User is already a project member")

@app.get("/projects/{project_id}/members/", response_model=List[dict])
async def get_project_members(
    project_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """
    ПОЛУЧЕНИЕ УЧАСТНИКОВ ПРОЕКТА
    """
    # Проверяем доступ к проекту
    has_access = await check_project_access(conn, project_id, current_user)
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this project")
    
    members = await conn.fetch("""
        SELECT u.id, u.username, u.email, pm.role, pm.joined_at
        FROM project_members pm
        JOIN users u ON pm.user_id = u.id
        WHERE pm.project_id = $1
        ORDER BY pm.role DESC, u.username
    """, project_id)
    
    result = []
    for member in members:
        member_dict = dict(member)
        if 'joined_at' in member_dict and member_dict['joined_at']:
            member_dict['joined_at'] = member_dict['joined_at'].isoformat()
        result.append(member_dict)
    
    return result

# Функция проверки доступа к проекту
async def check_project_access(conn, project_id, user_base):
    """Проверяет имеет ли пользователь доступ к проекту"""
    user_id = user_base["user_id"]
    user_role = user_base["role"]
    
    # Админы видят все проекты
    if user_role == "admin":
        return True
    
    # Получаем информацию о пользователе и проекте
    user_info = await conn.fetchrow("SELECT department_id FROM users WHERE id = $1", user_id)
    project = await conn.fetchrow("SELECT department_id, owner_id FROM projects WHERE id = $1", project_id)
    
    if not project:
        return False
        
    # Менеджеры видят проекты своего отдела
    if user_role == "manager":
        if user_info and project["department_id"] == user_info["department_id"] and project["department_id"] is not None:
            return True
        if project["owner_id"] == user_id:
            return True
        # Если проект без отдела, но менеджер его создал - доступ есть (уже проверено выше owner_id)
        # Если менеджер участник проекта
        member = await conn.fetchrow("SELECT id FROM project_members WHERE project_id = $1 AND user_id = $2", project_id, user_id)
        return member is not None

    # Обычные пользователи видят только проекты своего отдела или где они участники
    if user_info and project["department_id"] == user_info["department_id"] and project["department_id"] is not None:
        return True
        
    if project["owner_id"] == user_id:
        return True
    
    # Проверяем является ли пользователь участником проекта
    member = await conn.fetchrow(
        "SELECT id FROM project_members WHERE project_id = $1 AND user_id = $2",
        project_id, user_id
    )
    return member is not None

# 🔐 JWT АУТЕНТИФИКАЦИЯ
@app.post("/auth/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, conn: asyncpg.Connection = Depends(get_db)):
    """
    РЕГИСТРАЦИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ
    """
    # Проверяем уникальность username и email
    existing_user = await conn.fetchrow(
        "SELECT id FROM users WHERE username = $1 OR email = $2",
        user_data.username, user_data.email
    )
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким username или email уже существует"
        )
    
    # Хешируем пароль
    hashed_password = get_password_hash(user_data.password)
    
    try:
        # Сохраняем пользователя с ролью 'guest'
        user_id = await conn.fetchval("""
            INSERT INTO users (username, email, password, role, is_active, is_staff, is_superuser)
            VALUES ($1, $2, $3, 'guest', TRUE, FALSE, FALSE) 
            RETURNING id
        """, user_data.username, user_data.email, hashed_password)
        
        # Возвращаем данные пользователя
        new_user = await conn.fetchrow("""
            SELECT id, username, email, role, is_active, date_joined as created_at
            FROM users WHERE id = $1
        """, user_id)
        
        return dict(new_user)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании пользователя: {str(e)}"
        )

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, conn: asyncpg.Connection = Depends(get_db)):
    """
    АВТОРИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ И ВЫДАЧА JWT ТОКЕНОВ
    """
    # Ищем пользователя в базе данных
    user = await conn.fetchrow("""
        SELECT id, username, password as password_hash, role, is_active 
        FROM users WHERE username = $1
    """, user_data.username)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Неверный username или password",
        )
    
    # Проверяем пароль
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Неверный username или password",
        )
    
    # Проверяем что пользователь активен
    if not user["is_active"]:
        raise HTTPException(
            status_code=403,
            detail="Ваш аккаунт деактивирован. Обратитесь к администратору."
        )
    
    # Генерируем JWT токены
    user_payload = {
        "user_id": user["id"], 
        "username": user["username"],
        "role": user["role"]
    }
    
    access_token = create_access_token(data=user_payload)
    refresh_token = create_refresh_token(data=user_payload)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/auth/refresh", response_model=Token)
async def refresh_token_endpoint(
    token_data: TokenRefresh, 
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    ОБНОВЛЕНИЕ ACCESS TOKEN С ПОМОЩЬЮ REFRESH TOKEN
    """
    try:
        # Проверяем refresh token
        payload = verify_refresh_token(token_data.refresh_token)
        user_id = payload.get("user_id")
        username = payload.get("username")
        
        if not user_id or not username:
            raise HTTPException(
                status_code=401,
                detail="Невалидные данные в refresh token"
            )
        
        # Проверяем что пользователь существует и активен
        user = await conn.fetchrow("""
            SELECT id, username, role, is_active 
            FROM users WHERE id = $1
        """, user_id)
        
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Пользователь не найден"
            )
        
        if not user["is_active"]:
            raise HTTPException(
                status_code=403,
                detail="Ваш аккаунт деактивирован"
            )
        
        # Генерируем новую пару токенов
        user_payload = {
            "user_id": user["id"],
            "username": user["username"], 
            "role": user["role"]
        }
        
        new_access_token = create_access_token(data=user_payload)
        new_refresh_token = create_refresh_token(data=user_payload)
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Невалидный refresh token: {str(e)}"
        )

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    ПОЛУЧЕНИЕ ДАННЫХ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
    """
    # Получаем полные данные пользователя из базы данных
    user_id = current_user.get("user_id")
    
    user = await conn.fetchrow("""
        SELECT u.id, u.username, u.email, u.role, u.is_active, u.date_joined as created_at,
               d.id as department_id, d.name as department_name
        FROM users u
        LEFT JOIN departments d ON u.department_id = d.id
        WHERE u.id = $1
    """, user_id)
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден"
        )
    
    # Преобразуем datetime в строку
    user_dict = dict(user)
    if 'created_at' in user_dict and user_dict['created_at']:
        user_dict['created_at'] = user_dict['created_at'].isoformat()
    
    return user_dict

@app.put("/auth/profile")
async def update_profile(
    profile: ProfileUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """ОБНОВЛЕНИЕ ПРОФИЛЯ"""
    if profile.email is not None:
        await conn.execute("UPDATE users SET email = $1 WHERE id = $2", profile.email, current_user["user_id"])
    if profile.avatar_url is not None:
        await conn.execute("UPDATE users SET avatar_url = $1 WHERE id = $2", profile.avatar_url, current_user["user_id"])
    return {"message": "Профиль обновлен"}

@app.post("/auth/upgrade-request")
async def request_upgrade(
    req: UpgradeRequestCreate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """ЗАПРОС НА ПОВЫШЕНИЕ РОЛИ"""
    await conn.execute("""
        INSERT INTO role_upgrade_requests (user_id, requested_role, current_user_role, reason)
        VALUES ($1, $2, $3, $4)
    """, current_user["user_id"], req.requested_role, current_user["role"], req.reason)
    return {"message": "Заявка отправлена"}

# 📊 CRUD ДЛЯ ПРОЕКТОВ
@app.post("/projects/", response_model=dict)
async def create_project(
    project: ProjectCreate, 
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager)
):
    """
    СОЗДАНИЕ ПРОЕКТА (АВТОМАТИЧЕСКИ ДОБАВЛЯЕТ ВЛАДЕЛЬЦА КАК УЧАСТНИКА)
    """
    # Получаем отдел создателя
    user_info = await conn.fetchrow("SELECT department_id FROM users WHERE id = $1", current_user["user_id"])
    dept_id = user_info["department_id"] if user_info else None

    query = """
    INSERT INTO projects (title, description, owner_id, department_id)
    VALUES ($1, $2, $3, $4) RETURNING id
    """
    
    project_id = await conn.fetchval(
        query, 
        project.title, 
        project.description, 
        current_user["user_id"],
        dept_id
    )
    
    # Автоматически добавляем владельца как участника
    await conn.execute("""
        INSERT INTO project_members (project_id, user_id)
        VALUES ($1, $2)
    """, project_id, current_user["user_id"])
    
    return {"id": project_id, "message": "Project created successfully"}

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

@app.patch("/projects/{id}")
async def update_project(
    id: int,
    proj: ProjectUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager)
):
    """ОБНОВЛЕНИЕ ПРОЕКТА"""
    # Проверяем доступ (только владелец или админ)
    project = await conn.fetchrow("SELECT owner_id FROM projects WHERE id = $1", id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project["owner_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only owner or admin can edit project")

    if proj.title is not None:
        await conn.execute("UPDATE projects SET title = $1 WHERE id = $2", proj.title, id)
    if proj.description is not None:
        await conn.execute("UPDATE projects SET description = $1 WHERE id = $2", proj.description, id)
    
    return {"message": "Project updated"}

@app.put("/projects/{id}/members")
async def add_project_member(
    id: int,
    user_id: int = Query(...),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager)
):
    """ДОБАВЛЕНИЕ УЧАСТНИКА В ПРОЕКТ"""
    try:
        await conn.execute("""
            INSERT INTO project_members (project_id, user_id)
            VALUES ($1, $2)
        """, id, user_id)
        return {"message": "Участник добавлен"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/projects/{id}/members")
async def get_project_members(
    id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """ПОЛУЧЕНИЕ СПИСКА УЧАСТНИКОВ ПРОЕКТА"""
    rows = await conn.fetch("""
        SELECT u.id, u.username, u.role, pm.joined_at
        FROM project_members pm
        JOIN users u ON pm.user_id = u.id
        WHERE pm.project_id = $1
    """, id)
    return [dict(r) for r in rows]

@app.get("/projects/", response_model=List[dict])
async def get_projects(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """
    ПОЛУЧЕНИЕ ПРОЕКТОВ (ТОЛЬКО ТЕХ, К КОТОРЫМ ЕСТЬ ДОСТУП)
    """
    if current_user["role"] in ["admin", "manager"]:
        # Админы и менеджеры видят все проекты
        query = """
        SELECT p.*, d.name as department_name, u.username as owner_name
        FROM projects p 
        LEFT JOIN departments d ON p.department_id = d.id
        LEFT JOIN users u ON p.owner_id = u.id
        ORDER BY p.created_at DESC
        """
        rows = await conn.fetch(query)
    elif current_user["role"] == "user":
        # Пользователи видят проекты своего отдела + те, где они участники
        user_info = await conn.fetchrow("SELECT department_id FROM users WHERE id = $1", current_user["user_id"])
        query = """
        SELECT DISTINCT p.*, d.name as department_name, u.username as owner_name
        FROM projects p
        LEFT JOIN departments d ON p.department_id = d.id
        LEFT JOIN users u ON p.owner_id = u.id
        LEFT JOIN project_members pm ON p.id = pm.project_id
        WHERE (p.department_id = $1 AND $1 IS NOT NULL) OR p.owner_id = $2 OR pm.user_id = $2
        ORDER BY p.created_at DESC
        """
        rows = await conn.fetch(query, user_info["department_id"] if user_info else None, current_user["user_id"])
    else:
        # Гости не видят проектов вообще
        rows = []
    
    # Преобразуем datetime в строки
    result = []
    for row in rows:
        row_dict = dict(row)
        if 'created_at' in row_dict and row_dict['created_at']:
            row_dict['created_at'] = row_dict['created_at'].isoformat()
        result.append(row_dict)
    
    return result

@app.post("/tasks/", response_model=dict)
async def create_task(
    task: TaskCreate, 
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager)
):
    """
    СОЗДАНИЕ ЗАДАЧИ (ТОЛЬКО ДЛЯ УЧАСТНИКОВ ПРОЕКТА)
    """
    # Проверяем доступ к проекту
    has_access = await check_project_access(conn, task.project_id, current_user)
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this project")
    
    # Если указан assignee_id, проверяем что он либо участник проекта, либо в том же отделе
    if task.assignee_id:
        is_member = await conn.fetchrow(
            "SELECT id FROM project_members WHERE project_id = $1 AND user_id = $2",
            task.project_id, task.assignee_id
        )
        if not is_member:
            # Проверяем, в одном ли они отделе
            is_in_dept = await conn.fetchrow("""
                SELECT u.id FROM users u
                JOIN projects p ON u.department_id = p.department_id
                WHERE p.id = $1 AND u.id = $2 AND p.department_id IS NOT NULL
            """, task.project_id, task.assignee_id)
            
            if not is_in_dept:
                raise HTTPException(
                    status_code=400, 
                    detail="Исполнитель должен быть участником проекта или сотрудником того же отдела"
                )
    
    # Если assignee_id не указан, назначаем на текущего пользователя
    assignee_id = task.assignee_id or current_user["user_id"]
    
    query = """
    INSERT INTO tasks (project_id, title, description, status, priority, metadata, assigned_to)
    VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
    """
    
    # Map string priority to int
    p_map = {"low": 0, "medium": 1, "high": 2}
    db_priority = p_map.get(task.priority, 0) if isinstance(task.priority, str) else (task.priority or 0)

    try:
        task_id = await conn.fetchval(
            query, 
            task.project_id, 
            task.title, 
            task.description, 
            task.status, 
            db_priority, 
            json.dumps(task.metadata) if task.metadata else None,
            assignee_id
        )
        
        # Создаем запись в логе
        await conn.execute("""
            INSERT INTO task_logs (task_id, user_id, action, details)
            VALUES ($1, $2, 'created', $3)
        """, task_id, current_user["user_id"], json.dumps({"title": task.title}))
        
        return {"id": task_id, "message": "Task created successfully"}
    
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(status_code=400, detail="Project not found")

@app.get("/tasks/", response_model=List[dict])
async def get_tasks(
    project_id: Optional[int] = Query(None, description="Фильтр по ID проекта"),
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis),
    current_user: dict = Depends(any_authenticated)
):
    """
    ПОЛУЧЕНИЕ ЗАДАЧ (ТОЛЬКО ИЗ ПРОЕКТОВ, К КОТОРЫМ ЕСТЬ ДОСТУП)
    """
    if current_user["role"] in ["admin", "manager"]:
        # Админы и менеджеры видят все задачи
        if project_id:
            query = """
            SELECT t.id, t.project_id, t.title, t.description, t.status, t.priority, t.assigned_to, t.metadata, t.created_at, t.updated_at,
                   u.username as assigned_to_name, p.title as project_title
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.project_id = $1
            """
            rows = await conn.fetch(query, project_id)
        else:
            query = """
            SELECT t.id, t.project_id, t.title, t.description, t.status, t.priority, t.assigned_to, t.metadata, t.created_at, t.updated_at,
                   u.username as assigned_to_name, p.title as project_title
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN projects p ON t.project_id = p.id
            ORDER BY t.created_at DESC
            """
            rows = await conn.fetch(query)
    else:
        # Обычные пользователи видят только задачи из своих проектов
        if project_id:
            # Проверяем доступ к конкретному проекту
            has_access = await check_project_access(conn, project_id, current_user)
            if not has_access:
                raise HTTPException(status_code=403, detail="No access to this project")
            
            query = """
            SELECT t.id, t.project_id, t.title, t.description, t.status, t.priority, t.assigned_to, t.metadata, t.created_at, t.updated_at,
                   u.username as assigned_to_name, p.title as project_title
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.project_id = $1
            """
            rows = await conn.fetch(query, project_id)
        else:
            # Обычные пользователи (user) видят свои задачи + задачи своего отдела
            user_info = await conn.fetchrow("SELECT department_id FROM users WHERE id = $1", current_user["user_id"])
            query = """
            SELECT DISTINCT t.id, t.project_id, t.title, t.description, t.status, t.priority, t.assigned_to, t.metadata, t.created_at, t.updated_at,
                            u.username as assigned_to_name, p.title as project_title
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN project_members pm ON p.id = pm.project_id
            WHERE t.assigned_to = $1 OR (p.department_id = $2 AND $2 IS NOT NULL) OR pm.user_id = $1
            ORDER BY t.created_at DESC
            """
            rows = await conn.fetch(query, current_user["user_id"], user_info["department_id"] if user_info else None)
    
    # Преобразуем datetime в строки
    result = []
    for row in rows:
        row_dict = dict(row)
        if 'created_at' in row_dict and row_dict['created_at']:
            row_dict['created_at'] = row_dict['created_at'].isoformat()
        if 'updated_at' in row_dict and row_dict['updated_at']:
            row_dict['updated_at'] = row_dict['updated_at'].isoformat()
        result.append(row_dict)
    
    return result

@app.get("/tasks/{id}/logs")
async def get_task_logs(
    id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """ПОЛУЧЕНИЕ ИСТОРИИ ЗАДАЧИ STANDALONE"""
    rows = await conn.fetch("""
        SELECT tl.*, u.username
        FROM task_logs tl
        JOIN users u ON tl.user_id = u.id
        WHERE tl.task_id = $1
        ORDER BY tl.timestamp DESC
    """, id)
    
    log_result = []
    for r in rows:
        d = dict(r)
        if d['timestamp']: d['timestamp'] = d['timestamp'].isoformat()
        log_result.append(d)
    return log_result

# 🔍 ПОИСК
@app.get("/search")
async def search(
    q: str = Query(..., min_length=2),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """ПОИСК ПО ЗАДАЧАМ И ПРОЕКТАМ (TSVECTOR)"""
    # Поиск по задачам (с использованием GIN индекса и ILIKE как фоллбек)
    tasks = await conn.fetch("""
        SELECT t.*, u.username as assigned_to_name, p.title as project_title, 'task' as type
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.tsv @@ plainto_tsquery('russian', $1) 
           OR t.title ILIKE $2 
           OR t.description ILIKE $2
        LIMIT 20
    """, q, f"%{q}%")
    
    # Поиск по проектам
    projects = await conn.fetch("""
        SELECT id, title, 'project' as type, '' as parent_title
        FROM projects
        WHERE title ILIKE $1 OR description ILIKE $1
        LIMIT 5
    """, f"%{q}%")
    
    return {"tasks": [dict(r) for r in tasks], "projects": [dict(r) for r in projects]}

# 📈 АНАЛИТИКА И ОТЧЕТЫ
@app.get("/analytics/stats")
async def get_analytics(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """ДАННЫЕ ДЛЯ ГРАФИКОВ"""
    # 1. Распределение по статусам
    status_counts = await conn.fetch("""
        SELECT status, count(*) as count FROM tasks GROUP BY status
    """)
    
    # 2. Нагрузка по отделам
    dept_workload = await conn.fetch("""
        SELECT d.name, count(t.id) as task_count
        FROM departments d
        LEFT JOIN projects p ON d.id = p.department_id
        LEFT JOIN tasks t ON p.id = t.project_id
        GROUP BY d.name
    """)
    
    return {
        "statuses": {r["status"]: r["count"] for r in status_counts},
        "departments": {r["name"]: r["task_count"] for r in dept_workload}
    }
@app.get("/reports/tasks-stats/", response_model=List[dict])
async def tasks_stats(
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis),
    current_user: dict = Depends(any_worker)
):
    """
    СТАТИСТИКА ЗАДАЧ
    """
    cache_key = "reports:tasks_stats"
    
    cached_data = redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    query = "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"
    rows = await conn.fetch(query)
    
    result = [dict(row) for row in rows]
    redis.setex(cache_key, 1800, json.dumps(result))
    
    return result

# 🔍 ПОИСК
@app.get("/search/tasks/", response_model=List[dict])
async def search_tasks(
    q: str, 
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    query = """
    SELECT id, title, description, ts_headline('russian', description, plainto_tsquery('russian', $1)) as highlight
    FROM tasks 
    WHERE tsv @@ plainto_tsquery('russian', $1)
    """
    rows = await conn.fetch(query, q)
    return [dict(row) for row in rows]

# ЗАДАЧИ ПОЛЬЗОВАТЕЛЯ
@app.get("/my-tasks/", response_model=List[dict])
async def get_my_tasks(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """
    ПОЛУЧЕНИЕ ЗАДАЧ, НАЗНАЧЕННЫХ НА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
    """
    if status:
        query = """
        SELECT t.*, p.title as project_title 
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.assigned_to = $1 AND t.status = $2
        ORDER BY t.priority DESC, t.created_at DESC
        """
        rows = await conn.fetch(query, current_user["user_id"], status)
    else:
        query = """
        SELECT t.*, p.title as project_title 
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.assigned_to = $1
        ORDER BY t.priority DESC, t.created_at DESC
        """
        rows = await conn.fetch(query, current_user["user_id"])
    
    result = []
    for row in rows:
        row_dict = dict(row)
        if 'created_at' in row_dict and row_dict['created_at']:
            row_dict['created_at'] = row_dict['created_at'].isoformat()
        if 'updated_at' in row_dict and row_dict['updated_at']:
            row_dict['updated_at'] = row_dict['updated_at'].isoformat()
        result.append(row_dict)
    
    return result

# УДАЛЕНИЕ УЧАСТНИКА ИЗ ПРОЕКТА
@app.delete("/projects/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: int,
    user_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker)
):
    """
    УДАЛЕНИЕ УЧАСТНИКА ИЗ ПРОЕКТА
    """
    # Проверяем что текущий пользователь - владелец проекта
    project = await conn.fetchrow("SELECT owner_id FROM projects WHERE id = $1", project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Только владелец может удалять участников (кроме себя)
    if project["owner_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only project owner can remove members")
    
    # Нельзя удалить владельца
    if user_id == project["owner_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove project owner")
    
    # Удаляем участника
    result = await conn.execute(
        "DELETE FROM project_members WHERE project_id = $1 AND user_id = $2",
        project_id, user_id
    )
    
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Member not found in project")
    
    return {"message": "Member removed successfully"}

@app.get("/users/department")
async def get_department_users(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker)
):
    """ПОЛУЧЕНИЕ СПИСКА ПОЛЬЗОВАТЕЛЕЙ ИЗ ОТДЕЛА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ"""
    user_info = await conn.fetchrow("SELECT department_id FROM users WHERE id = $1", current_user["user_id"])
    if not user_info or user_info["department_id"] is None:
        # Если у пользователя нет отдела, возвращаем его самого
        return [{"id": current_user["user_id"], "username": current_user["username"]}]
    
    users = await conn.fetch("""
        SELECT id, username FROM users 
        WHERE department_id = $1 AND is_active = true
        ORDER BY username
    """, user_info["department_id"])
    return [dict(u) for u in users]

class StatusUpdate(BaseModel):
    status: str

@app.patch("/tasks/{task_id}/status")
async def update_task_status(
    task_id: int,
    status_data: StatusUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker)
):
    """ОБНОВЛЕНИЕ СТАТУСА ЗАДАЧИ С ЛОГИРОВАНИЕМ"""
    # Проверяем существование задачи и доступ к проекту
    task = await conn.fetchrow("SELECT project_id, status as old_status, title FROM tasks WHERE id = $1", task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    has_access = await check_project_access(conn, task["project_id"], current_user)
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this task's project")
    
    # Только исполнитель, менеджер отдела или админ может менять статус (для простоты пока любой с доступом к проекту)
    await conn.execute("""
        UPDATE tasks SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2
    """, status_data.status, task_id)
    
    # Создаем запись в логе
    action_map = {
        'pending': 'вернул в ожидание',
        'in_progress': 'взял в работу',
        'completed': 'завершил'
    }
    action_text = action_map.get(status_data.status, f"изменил статус на {status_data.status}")
    
    await conn.execute("""
        INSERT INTO task_logs (task_id, user_id, action, details)
        VALUES ($1, $2, $3, $4)
    """, task_id, current_user["user_id"], action_text, json.dumps({"old_status": task["old_status"], "new_status": status_data.status}))
    
    return {"message": "Status updated"}

# 🏥 HEALTH CHECKS
@app.get("/")
async def root():
    return {"message": "Business App API is running", "version": "1.0.0"}

@app.get("/health/")
async def health_check(
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis)
):
    try:
        db_result = await conn.fetchval("SELECT 1")
        redis_result = redis.ping()
        return {
            "status": "healthy", 
            "database": "connected",
            "redis": "connected" if redis_result else "disconnected"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# 🗄️ УПРАВЛЕНИЕ КЭШЕМ
@app.delete("/cache/clear/")
async def clear_cache(
    redis: redis_lib.Redis = Depends(get_redis), 
    current_user: dict = Depends(admin_only)
):
    """Очистка всего кэша"""
    redis.flushdb()
    return {"message": "Кэш полностью очищен"}

# 🔍 DEBUG ENDPOINT - List all tables
@app.get("/debug/tables")
async def list_tables(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_only)
):
    """Вывод всех таблиц в базе данных (только для админов)"""
    tables = await conn.fetch("""
        SELECT 
            table_name,
            (SELECT COUNT(*) FROM information_schema.columns 
             WHERE table_name = t.table_name AND table_schema = 'public') as column_count
        FROM information_schema.tables t
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    
    return {
        "total": len(tables),
        "tables": [{"name": t["table_name"], "columns": t["column_count"]} for t in tables]
    }

@app.delete("/cache/tasks/")
async def clear_tasks_cache(
    redis: redis_lib.Redis = Depends(get_redis), 
    current_user: dict = Depends(admin_or_manager)
):
    """Очистка кэша задач"""
    keys = redis.keys("tasks:*")
    if keys:
        redis.delete(*keys)
    return {"message": f"Кэш задач очищен, удалено ключей: {len(keys)}"}