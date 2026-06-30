import asyncio
import logging
import os

import asyncpg

from celery_app import celery
from routers.ai import _build_and_save_report

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/bizapp")


async def _run() -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        projects = await conn.fetch(
            "SELECT id, owner_id FROM projects ORDER BY id"
        )

        generated = 0
        errors = 0

        for project in projects:
            try:
                await _build_and_save_report(
                    conn=conn,
                    project_id=project["id"],
                    manager_id=project["owner_id"],
                )
                generated += 1
            except Exception as e:
                logger.error(
                    "Ошибка отчёта для проекта %d: %s", project["id"], e
                )
                errors += 1

        return {"generated": generated, "errors": errors}
    finally:
        await conn.close()


@celery.task(name="tasks.daily_report.generate_all_reports", bind=True, max_retries=2)
def generate_all_reports(self):
    try:
        result = asyncio.run(_run())
        logger.info("generate_all_reports завершена: %s", result)
        return result
    except Exception as exc:
        logger.error("generate_all_reports ошибка: %s", exc)
        raise self.retry(exc=exc, countdown=120)
