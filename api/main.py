import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
import redis as redis_lib
import asyncpg
import json
from typing import Optional, List
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/bizapp")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:8080,http://web:8080").split(",")

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
)
from dependencies import (
    get_db, get_redis,
    get_current_user, admin_only, admin_or_manager, any_worker, any_authenticated,
    check_project_access,
)
from routers.ai import router as ai_router
from routers.comments import router as comments_router
from routers.notifications import router as notifications_router
from routers.analytics import router as analytics_router
from notify import push as notify_push


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    yield
    await app.state.pool.close()


app = FastAPI(
    title="Business App API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(comments_router)
app.include_router(notifications_router)
app.include_router(analytics_router)

# МОДЕЛИ ДЛЯ CRUD ОПЕРАЦИЙ
class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)

class TaskCreate(BaseModel):
    project_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: int = Field(1, ge=0, le=2)
    assigned_to: Optional[int] = None
    deadline: Optional[str] = None
    is_critical: bool = False

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
        # Сохраняем пользователя с ролью 'intern'
        user_id = await conn.fetchval("""
            INSERT INTO users (username, email, password, role, is_active, is_staff, is_superuser)
            VALUES ($1, $2, $3, 'intern', TRUE, FALSE, FALSE)
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
async def login(
    request: Request,
    user_data: UserLogin,
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login_attempts:{client_ip}"
    attempts = redis.get(rate_key)
    if attempts and int(attempts) >= 10:
        raise HTTPException(
            status_code=429,
            detail="Слишком много попыток входа. Попробуйте через 5 минут.",
        )

    user = await conn.fetchrow("""
        SELECT id, username, password as password_hash, role, is_active
        FROM users WHERE username = $1
    """, user_data.username)

    if not user or not verify_password(user_data.password, user["password_hash"]):
        pipe = redis.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, 300)
        pipe.execute()
        raise HTTPException(status_code=401, detail="Неверный username или password")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Ваш аккаунт деактивирован. Обратитесь к администратору.")

    redis.delete(rate_key)

    user_payload = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"]
    }
    return {
        "access_token": create_access_token(data=user_payload),
        "refresh_token": create_refresh_token(data=user_payload),
        "token_type": "bearer"
    }

@app.post("/auth/refresh", response_model=Token)
async def refresh_token_endpoint(
    token_data: TokenRefresh,
    conn: asyncpg.Connection = Depends(get_db)
):
    payload = verify_refresh_token(token_data.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный или просроченный refresh token")

    user_id = payload.get("user_id")
    username = payload.get("username")
    if not user_id or not username:
        raise HTTPException(status_code=401, detail="Невалидные данные в refresh token")

    user = await conn.fetchrow(
        "SELECT id, username, role, is_active FROM users WHERE id = $1",
        user_id,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Ваш аккаунт деактивирован")

    user_payload = {"user_id": user["id"], "username": user["username"], "role": user["role"]}
    return {
        "access_token": create_access_token(data=user_payload),
        "refresh_token": create_refresh_token(data=user_payload),
        "token_type": "bearer",
    }

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
    if profile.password is not None and profile.password.strip():
        from auth_utils import get_password_hash
        hashed = get_password_hash(profile.password)
        await conn.execute("UPDATE users SET password = $1 WHERE id = $2", hashed, current_user["user_id"])
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

    async with conn.transaction():
        project_id = await conn.fetchval(
            """INSERT INTO projects (title, description, owner_id, department_id)
               VALUES ($1, $2, $3, $4) RETURNING id""",
            project.title, project.description, current_user["user_id"], dept_id,
        )
        await conn.execute(
            "INSERT INTO project_members (project_id, user_id) VALUES ($1, $2)",
            project_id, current_user["user_id"],
        )

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
    # Только владелец проекта или администратор может управлять участниками
    project = await conn.fetchrow("SELECT owner_id, department_id FROM projects WHERE id = $1", id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    is_admin = current_user["role"] == "admin"
    is_owner = project["owner_id"] == current_user["user_id"]

    if not is_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Управлять участниками может только владелец проекта или администратор")

    target_user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    try:
        await conn.execute("""
            INSERT INTO project_members (project_id, user_id)
            VALUES ($1, $2) ON CONFLICT DO NOTHING
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
    result = []
    for r in rows:
        d = dict(r)
        if d.get("joined_at"):
            d["joined_at"] = d["joined_at"].isoformat()
        result.append(d)
    return result

@app.get("/projects/{project_id}", response_model=dict)
async def get_project(
    project_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """ПОЛУЧЕНИЕ ОДНОГО ПРОЕКТА ПО ID"""
    has_access = await check_project_access(conn, project_id, current_user)
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this project")

    row = await conn.fetchrow("""
        SELECT p.*, d.name as department_name, u.username as owner_name
        FROM projects p
        LEFT JOIN departments d ON p.department_id = d.id
        LEFT JOIN users u ON p.owner_id = u.id
        WHERE p.id = $1
    """, project_id)

    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    d = dict(row)
    if d.get('created_at'):
        d['created_at'] = d['created_at'].isoformat()
    return d

@app.get("/users/", response_model=List[dict])
async def get_users(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager)
):
    """СПИСОК ПОЛЬЗОВАТЕЛЕЙ: менеджеры и администраторы видят всех активных пользователей"""
    rows = await conn.fetch("""
        SELECT id, username, role, department_id FROM users
        WHERE is_active = true ORDER BY username
    """)
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
    elif current_user["role"] in ("user", "intern"):
        # Пользователи и стажёры видят проекты своего отдела + те, где они участники
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
    redis: redis_lib.Redis = Depends(get_redis),
    current_user: dict = Depends(admin_or_manager)
):
    """
    СОЗДАНИЕ ЗАДАЧИ (ТОЛЬКО ДЛЯ УЧАСТНИКОВ ПРОЕКТА)
    """
    # Проверяем доступ к проекту
    has_access = await check_project_access(conn, task.project_id, current_user)
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this project")
    
    # Если указан assigned_to, проверяем что он либо участник проекта, либо в том же отделе
    if task.assigned_to:
        is_member = await conn.fetchrow(
            "SELECT id FROM project_members WHERE project_id = $1 AND user_id = $2",
            task.project_id, task.assigned_to
        )
        if not is_member:
            is_in_dept = await conn.fetchrow("""
                SELECT u.id FROM users u
                JOIN projects p ON u.department_id = p.department_id
                WHERE p.id = $1 AND u.id = $2 AND p.department_id IS NOT NULL
            """, task.project_id, task.assigned_to)
            if not is_in_dept:
                raise HTTPException(
                    status_code=400,
                    detail="Исполнитель должен быть участником проекта или сотрудником того же отдела"
                )

    assignee_id = task.assigned_to

    query = """
    INSERT INTO tasks (project_id, title, description, status, priority, assigned_to, deadline, is_critical)
    VALUES ($1, $2, $3, 'pending', $4, $5, $6, $7) RETURNING id
    """

    p_map = {"low": 0, "medium": 1, "high": 2}
    db_priority = p_map.get(task.priority, 0) if isinstance(task.priority, str) else (task.priority or 0)

    from datetime import datetime as dt
    deadline_val = None
    if task.deadline:
        try:
            deadline_val = dt.fromisoformat(task.deadline)
        except (ValueError, TypeError):
            pass

    try:
        task_id = await conn.fetchval(
            query,
            task.project_id,
            task.title,
            task.description,
            db_priority,
            assignee_id,
            deadline_val,
            task.is_critical,
        )

        await conn.execute("""
            INSERT INTO task_logs (task_id, user_id, action, details)
            VALUES ($1, $2, 'created', $3)
        """, task_id, current_user["user_id"], json.dumps({"title": task.title}))

        if assignee_id and assignee_id != current_user["user_id"]:
            await notify_push(
                conn, assignee_id, "task_assigned",
                f"Вам назначена задача: «{task.title}»",
                task_id=task_id, project_id=task.project_id,
            )

        redis.delete("reports:tasks_stats")

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
            SELECT t.id, t.project_id, t.title, t.description, t.status, t.priority,
                   t.assigned_to, t.deadline, t.is_critical, t.ai_generated, t.ai_score,
                   t.created_at, t.updated_at,
                   u.username as assigned_to_name, p.title as project_title
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.project_id = $1
            ORDER BY t.priority DESC, t.created_at DESC
            """
            rows = await conn.fetch(query, project_id)
        else:
            query = """
            SELECT t.id, t.project_id, t.title, t.description, t.status, t.priority,
                   t.assigned_to, t.deadline, t.is_critical, t.ai_generated, t.ai_score,
                   t.created_at, t.updated_at,
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
            has_access = await check_project_access(conn, project_id, current_user)
            if not has_access:
                raise HTTPException(status_code=403, detail="No access to this project")

            query = """
            SELECT t.id, t.project_id, t.title, t.description, t.status, t.priority,
                   t.assigned_to, t.deadline, t.is_critical, t.ai_generated, t.ai_score,
                   t.created_at, t.updated_at,
                   u.username as assigned_to_name, p.title as project_title
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.project_id = $1
            ORDER BY t.priority DESC, t.created_at DESC
            """
            rows = await conn.fetch(query, project_id)
        else:
            user_info = await conn.fetchrow("SELECT department_id FROM users WHERE id = $1", current_user["user_id"])
            query = """
            SELECT DISTINCT t.id, t.project_id, t.title, t.description, t.status, t.priority,
                   t.assigned_to, t.deadline, t.is_critical, t.ai_generated, t.ai_score,
                   t.created_at, t.updated_at,
                   u.username as assigned_to_name, p.title as project_title
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN project_members pm ON p.id = pm.project_id
            WHERE t.assigned_to = $1 OR (p.department_id = $2 AND $2 IS NOT NULL) OR pm.user_id = $1
            ORDER BY t.created_at DESC
            """
            rows = await conn.fetch(query, current_user["user_id"], user_info["department_id"] if user_info else None)
    
    result = []
    for row in rows:
        row_dict = dict(row)
        for field in ('created_at', 'updated_at', 'deadline'):
            if row_dict.get(field):
                row_dict[field] = row_dict[field].isoformat()
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

    # 3. Критичные задачи (не завершённые)
    critical_count = await conn.fetchval("""
        SELECT count(*) FROM tasks WHERE is_critical = TRUE AND status NOT IN ('completed', 'cancelled')
    """)

    statuses = {r["status"]: r["count"] for r in status_counts}
    statuses["critical"] = critical_count or 0

    return {
        "statuses": statuses,
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
        for field in ('created_at', 'updated_at', 'deadline', 'completed_at'):
            if row_dict.get(field):
                row_dict[field] = row_dict[field].isoformat()
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

_VALID_TRANSITIONS = {
    "pending": {"in_progress", "cancelled"},
    "in_progress": {"completed", "pending", "cancelled"},
    "completed": set(),
    "cancelled": {"pending"},
}

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    priority: Optional[int] = None
    deadline: Optional[str] = None
    is_critical: Optional[bool] = None

@app.patch("/tasks/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager),
):
    """РЕДАКТИРОВАНИЕ ЗАДАЧИ (ТОЛЬКО МЕНЕДЖЕР/АДМИНИСТРАТОР)"""
    task = await conn.fetchrow("SELECT project_id FROM tasks WHERE id = $1", task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    has_access = await check_project_access(conn, task["project_id"], current_user)
    if not has_access:
        raise HTTPException(status_code=403, detail="Нет доступа к проекту")

    if body.assigned_to is not None:
        is_member = await conn.fetchrow(
            "SELECT id FROM project_members WHERE project_id = $1 AND user_id = $2",
            task["project_id"], body.assigned_to,
        )
        if not is_member:
            raise HTTPException(status_code=400, detail="Исполнитель должен быть участником проекта")

    fields = []
    values = []
    idx = 1
    if body.title is not None:
        fields.append(f"title = ${idx}"); values.append(body.title); idx += 1
    if body.description is not None:
        fields.append(f"description = ${idx}"); values.append(body.description); idx += 1
    if body.assigned_to is not None:
        fields.append(f"assigned_to = ${idx}"); values.append(body.assigned_to); idx += 1
    if body.priority is not None:
        fields.append(f"priority = ${idx}"); values.append(body.priority); idx += 1
    if body.deadline is not None:
        from datetime import datetime as dt
        try:
            deadline_val = dt.fromisoformat(body.deadline)
        except (ValueError, TypeError):
            deadline_val = None
        fields.append(f"deadline = ${idx}"); values.append(deadline_val); idx += 1
    if body.is_critical is not None:
        fields.append(f"is_critical = ${idx}"); values.append(body.is_critical); idx += 1

    if not fields:
        return {"message": "Nothing to update"}

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(task_id)
    await conn.execute(
        f"UPDATE tasks SET {', '.join(fields)} WHERE id = ${idx}",
        *values,
    )
    return {"message": "Task updated"}


class StatusUpdate(BaseModel):
    status: str

@app.patch("/tasks/{task_id}/status")
async def update_task_status(
    task_id: int,
    status_data: StatusUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis),
    current_user: dict = Depends(any_worker)
):
    """ОБНОВЛЕНИЕ СТАТУСА ЗАДАЧИ С ЛОГИРОВАНИЕМ"""
    task = await conn.fetchrow(
        "SELECT project_id, status as old_status, title, assigned_to FROM tasks WHERE id = $1", task_id
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    allowed = _VALID_TRANSITIONS.get(task["old_status"], set())
    if status_data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя перевести задачу из '{task['old_status']}' в '{status_data.status}'",
        )

    has_access = await check_project_access(conn, task["project_id"], current_user)
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this task's project")

    is_privileged = current_user["role"] in ("admin", "manager")
    is_assignee = task["assigned_to"] == current_user["user_id"]
    if not is_privileged and not is_assignee:
        raise HTTPException(status_code=403, detail="Изменять статус может только исполнитель задачи или менеджер")

    if status_data.status == 'completed':
        await conn.execute("""
            UPDATE tasks SET status = $1, updated_at = CURRENT_TIMESTAMP,
            completed_at = CURRENT_TIMESTAMP WHERE id = $2
        """, status_data.status, task_id)
    else:
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

    redis.delete("reports:tasks_stats")

    status_labels = {
        'in_progress': 'взята в работу',
        'completed': 'завершена',
        'cancelled': 'отменена',
        'pending': 'возвращена в ожидание',
    }
    label = status_labels.get(status_data.status, status_data.status)

    project = await conn.fetchrow("SELECT owner_id FROM projects WHERE id = $1", task["project_id"])
    owner_id = project["owner_id"] if project else None

    if task["assigned_to"] and task["assigned_to"] != current_user["user_id"]:
        await notify_push(
            conn, task["assigned_to"], "task_status",
            f"Статус задачи «{task['title']}» изменён: {label}",
            task_id=task_id, project_id=task["project_id"],
        )
    if owner_id and owner_id != current_user["user_id"] and owner_id != task["assigned_to"]:
        await notify_push(
            conn, owner_id, "task_status",
            f"Задача «{task['title']}» {label}",
            task_id=task_id, project_id=task["project_id"],
        )

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