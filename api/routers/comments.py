import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dependencies import get_db, any_worker
from notify import push as notify_push

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["Comments"])


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.get("", response_model=list)
async def list_comments(
    task_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker),
):
    task = await conn.fetchrow("SELECT id FROM tasks WHERE id = $1", task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    rows = await conn.fetch(
        """
        SELECT c.id, c.task_id, c.text, c.created_at,
               u.id as user_id, u.username
        FROM task_comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.task_id = $1
        ORDER BY c.created_at ASC
        """,
        task_id,
    )

    return [
        {
            "id": r["id"],
            "task_id": r["task_id"],
            "text": r["text"],
            "created_at": r["created_at"].isoformat(),
            "user_id": r["user_id"],
            "username": r["username"],
        }
        for r in rows
    ]


@router.post("", response_model=dict, status_code=201)
async def add_comment(
    task_id: int,
    body: CommentCreate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker),
):
    task = await conn.fetchrow("SELECT id FROM tasks WHERE id = $1", task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    row = await conn.fetchrow(
        """
        INSERT INTO task_comments (task_id, user_id, text)
        VALUES ($1, $2, $3)
        RETURNING id, task_id, text, created_at
        """,
        task_id,
        current_user["user_id"],
        body.text,
    )

    task_full = await conn.fetchrow(
        "SELECT title, assigned_to, project_id FROM tasks WHERE id = $1", task_id
    )
    if task_full:
        recipients = set()
        if task_full["assigned_to"] and task_full["assigned_to"] != current_user["user_id"]:
            recipients.add(task_full["assigned_to"])
        project = await conn.fetchrow("SELECT owner_id FROM projects WHERE id = $1", task_full["project_id"])
        if project and project["owner_id"] != current_user["user_id"]:
            recipients.add(project["owner_id"])
        for uid in recipients:
            await notify_push(
                conn, uid, "comment",
                f"{current_user['username']} прокомментировал задачу «{task_full['title']}»",
                task_id=task_id, project_id=task_full["project_id"],
            )

    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "text": row["text"],
        "created_at": row["created_at"].isoformat(),
        "user_id": current_user["user_id"],
        "username": current_user["username"],
    }


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    task_id: int,
    comment_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker),
):
    comment = await conn.fetchrow(
        "SELECT id, user_id FROM task_comments WHERE id = $1 AND task_id = $2",
        comment_id,
        task_id,
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")

    if comment["user_id"] != current_user["user_id"] and current_user["role"] not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Нельзя удалить чужой комментарий")

    await conn.execute("DELETE FROM task_comments WHERE id = $1", comment_id)
