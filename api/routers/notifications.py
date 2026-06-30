import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db, any_authenticated

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list)
async def list_notifications(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated),
):
    rows = await conn.fetch(
        """
        SELECT id, type, text, is_read, created_at, task_id, project_id
        FROM notifications
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 50
        """,
        current_user["user_id"],
    )
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "text": r["text"],
            "is_read": r["is_read"],
            "created_at": r["created_at"].isoformat(),
            "task_id": r["task_id"],
            "project_id": r["project_id"],
        }
        for r in rows
    ]


@router.get("/unread-count", response_model=dict)
async def unread_count(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated),
):
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM notifications WHERE user_id = $1 AND is_read = FALSE",
        current_user["user_id"],
    )
    return {"count": count}


@router.post("/read-all", response_model=dict)
async def mark_all_read(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated),
):
    await conn.execute(
        "UPDATE notifications SET is_read = TRUE WHERE user_id = $1",
        current_user["user_id"],
    )
    return {"ok": True}


@router.post("/{notification_id}/read", response_model=dict)
async def mark_read(
    notification_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated),
):
    n = await conn.fetchrow(
        "SELECT id, user_id FROM notifications WHERE id = $1", notification_id
    )
    if not n:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    if n["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await conn.execute(
        "UPDATE notifications SET is_read = TRUE WHERE id = $1", notification_id
    )
    return {"ok": True}
