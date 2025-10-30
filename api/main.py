from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
import redis as redis_lib
import asyncpg
import json
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # ДОБАВЬ ЭТОТ ИМПОРТ

security = HTTPBearer()

# ИМПОРТЫ ДЛЯ JWT АУТЕНТИФИКАЦИИ
from models import (
    UserCreate, UserLogin, UserResponse, Token, TokenRefresh
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

# СОЗДАЕМ ПРИЛОЖЕНИЕ FASTAPI
app = FastAPI(
    title="Business App API", 
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Функция для подключения к БД
async def get_db():
    conn = await asyncpg.connect(
        user='user', 
        password='password', 
        database='bizapp', 
        host='db',
        port='5432'
    )
    try:
        yield conn
    finally:
        await conn.close()

# Функция для подключения к Redis
def get_redis():
    redis = redis_lib.Redis(
        host='redis',
        port=6379,
        db=0,
        decode_responses=True,
        encoding='utf-8'
    )
    try:
        yield redis
    finally:
        redis.close()

# МОДЕЛИ ДЛЯ CRUD ОПЕРАЦИЙ
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    owner_id: int

class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    status: str = 'pending'
    priority: int = 0
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
            INSERT INTO users (username, email, password_hash, role, is_active)
            VALUES ($1, $2, $3, 'guest', TRUE) 
            RETURNING id
        """, user_data.username, user_data.email, hashed_password)
        
        # Возвращаем данные пользователя
        new_user = await conn.fetchrow("""
            SELECT id, username, email, role, is_active, created_at
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
        SELECT id, username, password_hash, role, is_active 
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
        SELECT id, username, email, role, is_active, created_at
        FROM users WHERE id = $1
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

# 📊 CRUD ДЛЯ ПРОЕКТОВ
@app.post("/projects/", response_model=dict)
async def create_project(
    project: ProjectCreate, 
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker)
):
    """
    СОЗДАНИЕ ПРОЕКТА
    """
    query = """
    INSERT INTO projects (title, description, owner_id)
    VALUES ($1, $2, $3) RETURNING id
    """
    project_id = await conn.fetchval(query, project.title, project.description, project.owner_id)
    return {"id": project_id, "message": "Project created successfully"}

@app.get("/projects/", response_model=List[dict])
async def get_projects(
    owner_id: Optional[int] = None, 
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated)
):
    """
    ПОЛУЧЕНИЕ ПРОЕКТОВ
    """
    if owner_id:
        query = "SELECT * FROM projects WHERE owner_id = $1"
        rows = await conn.fetch(query, owner_id)
    else:
        query = "SELECT * FROM projects"
        rows = await conn.fetch(query)
    
    # Преобразуем datetime в строки
    result = []
    for row in rows:
        row_dict = dict(row)
        if 'created_at' in row_dict and row_dict['created_at']:
            row_dict['created_at'] = row_dict['created_at'].isoformat()
        result.append(row_dict)
    
    return result

# ✅ CRUD ДЛЯ ЗАДАЧ
@app.post("/tasks/", response_model=dict)
async def create_task(
    task: TaskCreate, 
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker)
):
    """
    СОЗДАНИЕ ЗАДАЧИ
    """
    query = """
    INSERT INTO tasks (project_id, title, description, status, priority, metadata, assigned_to)
    VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
    """
    try:
        task_id = await conn.fetchval(
            query, 
            task.project_id, 
            task.title, 
            task.description, 
            task.status, 
            task.priority, 
            json.dumps(task.metadata) if task.metadata else None,
            current_user["id"]  # Назначаем текущему пользователю
        )
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
    ПОЛУЧЕНИЕ ЗАДАЧ
    """
    # Формируем ключ для кэша
    if project_id:
        cache_key = f"tasks:project:{project_id}"
    else:
        cache_key = "tasks:all"
    
    # Пытаемся получить данные из кэша
    cached_data = redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Если в кэше нет, запрашиваем из БД
    if project_id:
        query = "SELECT * FROM tasks WHERE project_id = $1"
        rows = await conn.fetch(query, project_id)
    else:
        query = "SELECT * FROM tasks"
        rows = await conn.fetch(query)
    
    # Преобразуем datetime в строки
    result = []
    for row in rows:
        row_dict = dict(row)
        if 'created_at' in row_dict and row_dict['created_at']:
            row_dict['created_at'] = row_dict['created_at'].isoformat()
        if 'updated_at' in row_dict and row_dict['updated_at']:
            row_dict['updated_at'] = row_dict['updated_at'].isoformat()
        result.append(row_dict)
    
    # Сохраняем в кэш на 1 час
    redis.setex(cache_key, 3600, json.dumps(result))
    
    return result

@app.get("/tasks/{task_id}", response_model=dict)
async def get_task(
    task_id: int, 
    conn: asyncpg.Connection = Depends(get_db), 
    current_user: dict = Depends(any_authenticated)
):
    query = "SELECT * FROM tasks WHERE id = $1"
    row = await conn.fetchrow(query, task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = dict(row)
    if 'created_at' in result and result['created_at']:
        result['created_at'] = result['created_at'].isoformat()
    if 'updated_at' in result and result['updated_at']:
        result['updated_at'] = result['updated_at'].isoformat()
    
    return result

# 📈 АНАЛИТИКА И ОТЧЕТЫ
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