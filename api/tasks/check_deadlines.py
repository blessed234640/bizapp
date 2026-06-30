import asyncio
import json
import logging
import os
from datetime import datetime

import asyncpg

from celery_app import celery

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/bizapp")


async def _run(conn: asyncpg.Connection) -> dict:
    now = datetime.utcnow()

    newly_critical = await conn.fetch(
        """
        SELECT id, title, assigned_to, project_id, deadline
        FROM tasks
        WHERE deadline < $1
          AND status NOT IN ('completed', 'cancelled')
          AND is_critical = FALSE
        """,
        now,
    )

    if not newly_critical:
        return {"marked_critical": 0}

    task_ids = [r["id"] for r in newly_critical]

    async with conn.transaction():
        await conn.execute(
            "UPDATE tasks SET is_critical = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = ANY($1::int[])",
            task_ids,
        )

        logs = [
            (
                task["id"],
                json.dumps({
                    "reason": "deadline_exceeded",
                    "deadline": task["deadline"].isoformat() if task["deadline"] else None,
                }),
            )
            for task in newly_critical
        ]

        await conn.executemany(
            """
            INSERT INTO task_logs (task_id, user_id, action, details)
            VALUES ($1, NULL, 'marked_critical', $2)
            """,
            logs,
        )

    logger.info("Помечено критичными: %d задач", len(task_ids))
    return {"marked_critical": len(task_ids), "task_ids": task_ids}


@celery.task(name="tasks.check_deadlines.check_overdue_tasks", bind=True, max_retries=3)
def check_overdue_tasks(self):
    async def _main():
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            return await _run(conn)
        finally:
            await conn.close()

    try:
        result = asyncio.run(_main())
        logger.info("check_overdue_tasks завершена: %s", result)
        return result
    except Exception as exc:
        logger.error("check_overdue_tasks ошибка: %s", exc)
        raise self.retry(exc=exc, countdown=60)
