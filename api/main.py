from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
import redis as redis_lib
import asyncpg
import json
from typing import Optional, List

app = FastAPI(title="Business App API", version="1.0.0")

# Функция для подключения к БД
async def get_db():
    conn = await asyncpg.connect(
        user='user', 
        password='password', 
        database='bizapp', 
        host='localhost',  # Используем localhost т.к. запускаем снаружи Docker
        port='5433'        # Порт который мы настроили
    )
    try:
        yield conn
    finally:
        await conn.close()

# Функция для подключения к Redis (синхронная)
def get_redis():
    redis = redis_lib.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True,  # Автоматически декодирует в строки
        encoding='utf-8'
    )
    try:
        yield redis
    finally:
        redis.close()

# Разбор функции get_redis:

# aioredis.from_url() - создает подключение к Redis по URL

# encoding="utf-8" - кодировка для русских символов

# decode_responses=True - автоматически декодирует из bytes в строки

# yield redis - возвращает клиент Redis для использования

# finally - гарантирует закрытие соединения


# Модели Pydantic для валидации
class UserCreate(BaseModel):
    username: str
    email: str
    password_hash: str
    role: str = 'user'

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

# CRUD для пользователей
@app.post("/users/", response_model=dict)
async def create_user(user: UserCreate, conn: asyncpg.Connection = Depends(get_db)):
    query = """
    INSERT INTO users (username, email, password_hash, role)
    VALUES ($1, $2, $3, $4) RETURNING id
    """
    try:
        user_id = await conn.fetchval(query, user.username, user.email, user.password_hash, user.role)
        return {"id": user_id, "message": "User created successfully"}
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Username or email already exists")

@app.get("/users/", response_model=List[dict])
async def get_users(conn: asyncpg.Connection = Depends(get_db)):
    query = "SELECT id, username, email, role FROM users"
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]

# CRUD для проектов
@app.post("/projects/", response_model=dict)
async def create_project(project: ProjectCreate, conn: asyncpg.Connection = Depends(get_db)):
    query = """
    INSERT INTO projects (title, description, owner_id)
    VALUES ($1, $2, $3) RETURNING id
    """
    project_id = await conn.fetchval(query, project.title, project.description, project.owner_id)
    return {"id": project_id, "message": "Project created successfully"}

@app.get("/projects/", response_model=List[dict])
async def get_projects(owner_id: Optional[int] = None, conn: asyncpg.Connection = Depends(get_db)):
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

# CRUD для задач
@app.post("/tasks/", response_model=dict)
async def create_task(task: TaskCreate, conn: asyncpg.Connection = Depends(get_db)):
    query = """
    INSERT INTO tasks (project_id, title, description, status, priority, metadata)
    VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
    """
    try:
        task_id = await conn.fetchval(
            query, 
            task.project_id, 
            task.title, 
            task.description, 
            task.status, 
            task.priority, 
            json.dumps(task.metadata) if task.metadata else None
        )
        return {"id": task_id, "message": "Task created successfully"}
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(status_code=400, detail="Project not found")

@app.get("/tasks/", response_model=List[dict])
async def get_tasks(
    project_id: Optional[int] = Query(None, description="Фильтр по ID проекта"),
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis)
):
    # Формируем ключ для кэша
    if project_id:
        cache_key = f"tasks:project:{project_id}"
    else:
        cache_key = "tasks:all"
    
    # Пытаемся получить данные из кэша (синхронно)
    cached_data = redis.get(cache_key)
    if cached_data:
        print(f"✅ Данные получены из кэша: {cache_key}")
        return json.loads(cached_data)
    
    # Если в кэше нет, запрашиваем из БД
    print(f"🔍 Данные не найдены в кэше, запрашиваем из БД: {cache_key}")
    if project_id:
        query = "SELECT * FROM tasks WHERE project_id = $1"
        rows = await conn.fetch(query, project_id)
    else:
        query = "SELECT * FROM tasks"
        rows = await conn.fetch(query)
    
    # Преобразуем строки с datetime в JSON-совместимый формат
    result = []
    for row in rows:
        row_dict = dict(row)
        # Преобразуем datetime объекты в строки ISO format
        if 'created_at' in row_dict and row_dict['created_at']:
            row_dict['created_at'] = row_dict['created_at'].isoformat()
        if 'updated_at' in row_dict and row_dict['updated_at']:
            row_dict['updated_at'] = row_dict['updated_at'].isoformat()
        result.append(row_dict)
    
    # Сохраняем в кэш на 1 час (3600 секунд) - синхронно
    redis.setex(cache_key, 3600, json.dumps(result))
    print(f"💾 Данные сохранены в кэш: {cache_key}")
    
    return result

@app.get("/tasks/{task_id}", response_model=dict)
async def get_task(task_id: int, conn: asyncpg.Connection = Depends(get_db)):
    query = "SELECT * FROM tasks WHERE id = $1"
    row = await conn.fetchrow(query, task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Преобразуем datetime в строки
    result = dict(row)
    if 'created_at' in result and result['created_at']:
        result['created_at'] = result['created_at'].isoformat()
    if 'updated_at' in result and result['updated_at']:
        result['updated_at'] = result['updated_at'].isoformat()
    
    return result

# Аналитика и отчеты
@app.get("/reports/tasks-stats/", response_model=List[dict], operation_id="get_tasks_stats")
async def tasks_stats(
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis)
):
    cache_key = "reports:tasks_stats"
    
    # Проверяем кэш (синхронно)
    cached_data = redis.get(cache_key)
    if cached_data:
        print("✅ Статистика получена из кэша")
        return json.loads(cached_data)
    
    # Запрос к БД
    query = "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"
    rows = await conn.fetch(query)
    
    # Преобразуем строки
    result = []
    for row in rows:
        row_dict = dict(row)
        result.append(row_dict)
    
    # Сохраняем в кэш на 30 минут (1800 секунд) - синхронно
    redis.setex(cache_key, 1800, json.dumps(result))
    print("💾 Статистика сохранена в кэш")
    
    return result

@app.get("/reports/project-stats/", response_model=List[dict], operation_id="get_project_stats")
async def project_stats(
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis)
):
    cache_key = "reports:project_stats"
    
    # Проверяем кэш
    cached_data = redis.get(cache_key)
    if cached_data:
        print("✅ Статистика проектов получена из кэша")
        return json.loads(cached_data)
    
    # Запрос к БД
    query = """
    SELECT p.title, COUNT(t.id) as task_count, 
           COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_count
    FROM projects p
    LEFT JOIN tasks t ON p.id = t.project_id
    GROUP BY p.id, p.title
    """
    rows = await conn.fetch(query)
    
    # Преобразуем строки
    result = []
    for row in rows:
        row_dict = dict(row)
        result.append(row_dict)
    
    # Сохраняем в кэш на 30 минут
    redis.setex(cache_key, 1800, json.dumps(result))
    print("💾 Статистика проектов сохранена в кэш")
    
    return result

# Полнотекстовый поиск задач
@app.get("/search/tasks/", response_model=List[dict])
async def search_tasks(q: str, conn: asyncpg.Connection = Depends(get_db)):
    query = """
    SELECT id, title, description, ts_headline('russian', description, plainto_tsquery('russian', $1)) as highlight
    FROM tasks 
    WHERE tsv @@ plainto_tsquery('russian', $1)
    """
    rows = await conn.fetch(query, q)
    
    # Преобразуем datetime в строки
    result = []
    for row in rows:
        row_dict = dict(row)
        result.append(row_dict)
    
    return result

# Health check
@app.get("/")
async def root():
    return {"message": "Business App API is running", "version": "1.0.0"}

@app.get("/health/")
async def health_check(
    conn: asyncpg.Connection = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis)
):
    try:
        # Проверяем подключение к БД
        db_result = await conn.fetchval("SELECT 1")
        # Проверяем подключение к Redis
        redis_result = redis.ping()
        return {
            "status": "healthy", 
            "database": "connected",
            "redis": "connected" if redis_result else "disconnected"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    
# Эндпоинты для управления кэшем
@app.delete("/cache/clear/")
async def clear_cache(redis: redis_lib.Redis = Depends(get_redis)):
    """Очистка всего кэша"""
    redis.flushdb()
    return {"message": "Кэш полностью очищен"}

@app.delete("/cache/tasks/")
async def clear_tasks_cache(redis: redis_lib.Redis = Depends(get_redis)):
    """Очистка кэша задач"""
    keys = redis.keys("tasks:*")
    if keys:
        redis.delete(*keys)
    return {"message": f"Кэш задач очищен, удалено ключей: {len(keys)}"}

@app.get("/cache/keys/")
async def get_cache_keys(redis: redis_lib.Redis = Depends(get_redis)):
    """Просмотр всех ключей в кэше"""
    keys = redis.keys("*")
    return {"keys": keys}