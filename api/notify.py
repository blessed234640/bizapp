import asyncpg


async def push(
    conn: asyncpg.Connection,
    user_id: int,
    type: str,
    text: str,
    task_id: int = None,
    project_id: int = None,
):
    if not user_id:
        return
    await conn.execute(
        """
        INSERT INTO notifications (user_id, type, text, task_id, project_id)
        VALUES ($1, $2, $3, $4, $5)
        """,
        user_id,
        type,
        text,
        task_id,
        project_id,
    )
