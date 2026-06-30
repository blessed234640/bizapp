import os
import asyncpg
import redis as redis_lib
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth_utils import verify_access_token

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/bizapp")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

security = HTTPBearer()


async def get_db(request: Request):
    async with request.app.state.pool.acquire() as conn:
        yield conn


def get_redis():
    r = redis_lib.from_url(REDIS_URL, decode_responses=True, encoding="utf-8")
    try:
        yield r
    finally:
        r.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn: asyncpg.Connection = Depends(get_db),
) -> dict:
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный токен")

    user = await conn.fetchrow(
        "SELECT is_active FROM users WHERE id = $1", payload.get("user_id")
    )
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт деактивирован"
        )

    return payload


async def admin_only(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права администратора")
    return current_user


async def admin_or_manager(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") not in ("admin", "manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права менеджера или администратора")
    return current_user


async def any_worker(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") not in ("admin", "manager", "user", "intern"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права работника")
    return current_user


async def any_authenticated(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user


async def check_project_access(conn: asyncpg.Connection, project_id: int, user: dict) -> bool:
    if user["role"] == "admin":
        return True

    user_info = await conn.fetchrow("SELECT department_id FROM users WHERE id = $1", user["user_id"])
    project = await conn.fetchrow("SELECT department_id, owner_id FROM projects WHERE id = $1", project_id)

    if not project:
        return False

    if project["owner_id"] == user["user_id"]:
        return True

    if user["role"] == "manager":
        if (
            user_info
            and project["department_id"] is not None
            and project["department_id"] == user_info["department_id"]
        ):
            return True

    if (
        user_info
        and project["department_id"] is not None
        and project["department_id"] == user_info["department_id"]
    ):
        return True

    member = await conn.fetchrow(
        "SELECT id FROM project_members WHERE project_id = $1 AND user_id = $2",
        project_id,
        user["user_id"],
    )
    return member is not None
