from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import asyncpg
import json
from datetime import datetime
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
    created_at: datetime
    updated_at: datetime

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
    return [dict(row) for row in rows]

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
async def get_tasks(project_id: Optional[int] = None, conn: asyncpg.Connection = Depends(get_db)):
    if project_id:
        query = "SELECT * FROM tasks WHERE project_id = $1"
        rows = await conn.fetch(query, project_id)
    else:
        query = "SELECT * FROM tasks"
        rows = await conn.fetch(query)
    return [dict(row) for row in rows]

@app.get("/tasks/{task_id}", response_model=dict)
async def get_task(task_id: int, conn: asyncpg.Connection = Depends(get_db)):
    query = "SELECT * FROM tasks WHERE id = $1"
    row = await conn.fetchrow(query, task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(row)

# Аналитика и отчеты
@app.get("/reports/tasks-stats/", response_model=List[dict])
async def tasks_stats(conn: asyncpg.Connection = Depends(get_db)):
    query = "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]

@app.get("/reports/project-stats/", response_model=List[dict])
async def project_stats(conn: asyncpg.Connection = Depends(get_db)):
    query = """
    SELECT p.title, COUNT(t.id) as task_count, 
           COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_count
    FROM projects p
    LEFT JOIN tasks t ON p.id = t.project_id
    GROUP BY p.id, p.title
    """
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]

# Полнотекстовый поиск задач
@app.get("/search/tasks/", response_model=List[dict])
async def search_tasks(q: str, conn: asyncpg.Connection = Depends(get_db)):
    query = """
    SELECT id, title, description, ts_headline('russian', description, plainto_tsquery('russian', $1)) as highlight
    FROM tasks 
    WHERE tsv @@ plainto_tsquery('russian', $1)
    """
    rows = await conn.fetch(query, q)
    return [dict(row) for row in rows]

# Health check
@app.get("/")
async def root():
    return {"message": "Business App API is running", "version": "1.0.0"}

@app.get("/health/")
async def health_check(conn: asyncpg.Connection = Depends(get_db)):
    try:
        # Проверяем подключение к БД
        result = await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}