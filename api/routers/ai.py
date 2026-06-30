import json
import logging
from datetime import datetime, date, timedelta, timezone

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from dependencies import (
    get_db,
    admin_or_manager,
    any_worker,
    check_project_access,
)
from models import AIGenerateRequest, AIGenerateResponse, AIGeneratedTask
from ai_service import generate_tasks, evaluate_task_completion, generate_daily_report, QuotaExceededError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


# ---------------------------------------------------------------------------
# 1. Генерация задач — возвращает предпросмотр, ничего не сохраняет
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/plan", response_model=AIGenerateResponse)
async def ai_generate_plan(
    project_id: int,
    body: AIGenerateRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager),
):
    """
    Менеджер описывает что нужно сделать — ИИ разбивает на задачи с дедлайнами.
    Возвращает предпросмотр. Для сохранения используй /ai/projects/{id}/plan/apply.
    """
    project = await conn.fetchrow(
        "SELECT id, title, description, owner_id FROM projects WHERE id = $1",
        project_id,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    if project["owner_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только владелец проекта может запустить AI-планирование")

    existing_tasks = await conn.fetch(
        "SELECT title FROM tasks WHERE project_id = $1 AND status != 'cancelled'",
        project_id,
    )

    try:
        tasks = await generate_tasks(
            project_title=project["title"],
            project_description=project["description"],
            manager_description=body.description,
            existing_tasks=[dict(t) for t in existing_tasks],
        )
    except QuotaExceededError as e:
        logger.error("Gemini quota exceeded: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Ошибка генерации задач Gemini: %s", e)
        raise HTTPException(status_code=502, detail="Ошибка AI-сервиса. Попробуйте позже.")

    return AIGenerateResponse(
        tasks=[AIGeneratedTask(**t) for t in tasks]
    )


# ---------------------------------------------------------------------------
# 2. Применение плана — сохраняет задачи после назначения исполнителей
# ---------------------------------------------------------------------------

class TaskAssignment(AIGeneratedTask):
    assigned_to: Optional[int] = None


class ApplyPlanRequest(AIGenerateRequest):
    tasks: list[TaskAssignment]
    description: str = ""


@router.post("/projects/{project_id}/plan/apply", response_model=dict)
async def ai_apply_plan(
    project_id: int,
    body: ApplyPlanRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager),
):
    """
    Сохраняет AI-сгенерированные задачи. Менеджер передаёт список задач
    с опциональным assigned_to для каждой.
    """
    project = await conn.fetchrow("SELECT owner_id FROM projects WHERE id = $1", project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    if project["owner_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только владелец проекта может применить AI-план")

    created_ids = []
    now = datetime.utcnow()

    async with conn.transaction():
        for task in body.tasks:
            deadline = now + timedelta(days=task.deadline_days)

            task_id = await conn.fetchval(
                """
                INSERT INTO tasks
                    (project_id, title, description, status, priority, assigned_to,
                     deadline, ai_generated, created_at, updated_at)
                VALUES ($1, $2, $3, 'pending', $4, $5, $6, TRUE,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                project_id,
                task.title,
                task.description,
                task.priority,
                task.assigned_to,
                deadline,
            )

            await conn.execute(
                """
                INSERT INTO task_logs (task_id, user_id, action, details)
                VALUES ($1, $2, 'ai_created', $3)
                """,
                task_id,
                current_user["user_id"],
                json.dumps({"source": "gemini", "deadline_days": task.deadline_days}),
            )

            created_ids.append(task_id)

    return {"created": len(created_ids), "task_ids": created_ids}


# ---------------------------------------------------------------------------
# 3. Завершение задачи с AI-оценкой
# ---------------------------------------------------------------------------

class CompleteTaskRequest(BaseModel):
    description: str = ""


@router.post("/tasks/{task_id}/complete", response_model=dict)
async def complete_task_with_ai(
    task_id: int,
    body: CompleteTaskRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_worker),
):
    """
    Сотрудник завершает задачу и описывает что сделал.
    ИИ оценивает качество и скорость, обновляет накопительную статистику.
    """
    task = await conn.fetchrow(
        """
        SELECT t.id, t.title, t.description, t.status, t.deadline,
               t.assigned_to, t.project_id, t.ai_generated
        FROM tasks t
        WHERE t.id = $1
        """,
        task_id,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if task["status"] == "completed":
        raise HTTPException(status_code=400, detail="Задача уже завершена")
    if task["status"] not in ("in_progress", "pending"):
        raise HTTPException(status_code=400, detail="Нельзя завершить задачу в текущем статусе")

    if (
        task["assigned_to"] != current_user["user_id"]
        and current_user["role"] not in ("admin", "manager")
    ):
        raise HTTPException(status_code=403, detail="Завершить задачу может только исполнитель или менеджер")

    stats_row = await conn.fetchrow(
        "SELECT * FROM employee_stats WHERE user_id = $1",
        task["assigned_to"] or current_user["user_id"],
    )
    employee_stats = dict(stats_row) if stats_row else None

    completed_at = datetime.utcnow()

    def _deadline_naive(dt):
        if dt is None:
            return None
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    deadline_naive = _deadline_naive(task["deadline"])
    is_overdue = bool(deadline_naive and completed_at > deadline_naive)

    skip_ai = not body.description.strip()
    evaluation = None

    if not skip_ai:
        try:
            completed_at_aware = completed_at.replace(tzinfo=timezone.utc)
            deadline_for_ai = task["deadline"]
            if deadline_for_ai and deadline_for_ai.tzinfo is None:
                deadline_for_ai = deadline_for_ai.replace(tzinfo=timezone.utc)
            evaluation = await evaluate_task_completion(
                task_title=task["title"],
                task_description=task["description"],
                completion_note=body.description,
                deadline=deadline_for_ai,
                completed_at=completed_at_aware,
                employee_stats=employee_stats,
            )
        except Exception as e:
            logger.warning("AI оценка недоступна, авто-оценка: %s", str(e)[:80])

    if evaluation is None:
        if deadline_naive:
            delta_seconds = (deadline_naive - completed_at).total_seconds()
            if delta_seconds > 0:
                auto_score, time_note = 8, "завершена досрочно"
            elif delta_seconds > -86400:
                auto_score, time_note = 7, "завершена вовремя"
            elif delta_seconds > -3 * 86400:
                auto_score, time_note = 5, "небольшая просрочка"
            else:
                auto_score, time_note = 3, "значительная просрочка"
        else:
            auto_score, time_note = 6, "дедлайн не был установлен"

        note_bonus = min(2, len(body.description.split()) // 5) if body.description.strip() else 0
        evaluation = {
            "score": min(10, auto_score + note_bonus),
            "feedback": f"Авто-оценка по соблюдению сроков ({time_note}). Для детальной оценки добавьте описание выполненной работы.",
        }

    async with conn.transaction():
        await conn.execute(
            """
            UPDATE tasks
            SET status = 'completed',
                completed_at = $1,
                ai_score = $2,
                ai_feedback = $3,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $4
            """,
            completed_at,
            evaluation["score"],
            evaluation["feedback"],
            task_id,
        )

        await conn.execute(
            """
            INSERT INTO task_logs (task_id, user_id, action, details)
            VALUES ($1, $2, 'completed', $3)
            """,
            task_id,
            current_user["user_id"],
            json.dumps({
                "note": body.description,
                "ai_score": evaluation["score"],
                "is_overdue": is_overdue,
            }),
        )

        worker_id = task["assigned_to"] or current_user["user_id"]
        await _update_employee_stats(conn, worker_id, evaluation["score"], is_overdue)

    return {
        "message": "Задача завершена",
        "ai_score": evaluation["score"],
        "ai_feedback": evaluation["feedback"],
    }


async def _update_employee_stats(
    conn: asyncpg.Connection,
    user_id: int,
    score: int,
    is_overdue: bool,
) -> None:
    existing = await conn.fetchrow(
        "SELECT * FROM employee_stats WHERE user_id = $1", user_id
    )

    if existing:
        total = existing["total_completed"] + 1
        on_time = existing["completed_on_time"] + (0 if is_overdue else 1)
        overdue = existing["completed_overdue"] + (1 if is_overdue else 0)
        new_avg = round(
            (existing["avg_score"] * existing["total_completed"] + score) / total, 2
        )
        await conn.execute(
            """
            UPDATE employee_stats
            SET total_completed = $1,
                completed_on_time = $2,
                completed_overdue = $3,
                avg_score = $4,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $5
            """,
            total, on_time, overdue, new_avg, user_id,
        )
    else:
        await conn.execute(
            """
            INSERT INTO employee_stats
                (user_id, total_completed, completed_on_time, completed_overdue, avg_score)
            VALUES ($1, 1, $2, $3, $4)
            """,
            user_id,
            0 if is_overdue else 1,
            1 if is_overdue else 0,
            float(score),
        )


# ---------------------------------------------------------------------------
# 4. Ручной запуск генерации ежевечернего отчёта
# ---------------------------------------------------------------------------

@router.post("/reports/generate/{project_id}", response_model=dict)
async def generate_report_for_project(
    project_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager),
):
    """
    Вручную генерирует отчёт за сегодня для конкретного проекта.
    Celery-задача вызывает тот же метод автоматически каждый вечер.
    """
    project = await conn.fetchrow(
        "SELECT id, title, owner_id FROM projects WHERE id = $1", project_id
    )
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    if project["owner_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только владелец проекта может запросить отчёт")

    report = await _build_and_save_report(conn, project_id, current_user["user_id"])
    return report


@router.get("/reports/{project_id}", response_model=list)
async def get_project_reports(
    project_id: int,
    limit: int = 7,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager),
):
    """Возвращает последние N ежевечерних отчётов по проекту."""
    has_access = await check_project_access(conn, project_id, current_user)
    if not has_access:
        raise HTTPException(status_code=403, detail="Нет доступа к проекту")

    rows = await conn.fetch(
        """
        SELECT r.id, r.project_id, p.title as project_title,
               r.report_date, r.content, r.created_at
        FROM ai_reports r
        JOIN projects p ON r.project_id = p.id
        WHERE r.project_id = $1
        ORDER BY r.report_date DESC
        LIMIT $2
        """,
        project_id, limit,
    )

    result = []
    for r in rows:
        d = dict(r)
        d["report_date"] = d["report_date"].isoformat()
        d["created_at"] = d["created_at"].isoformat()
        if isinstance(d.get("content"), str):
            d["content"] = json.loads(d["content"])
        result.append(d)
    return result


@router.get("/reports", response_model=list)
async def get_my_reports(
    limit: int = 14,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager),
):
    """Возвращает все последние отчёты по проектам текущего менеджера."""
    rows = await conn.fetch(
        """
        SELECT r.id, r.project_id, p.title as project_title,
               r.report_date, r.content, r.created_at
        FROM ai_reports r
        JOIN projects p ON r.project_id = p.id
        WHERE r.manager_id = $1
        ORDER BY r.report_date DESC, r.created_at DESC
        LIMIT $2
        """,
        current_user["user_id"], limit,
    )

    result = []
    for r in rows:
        d = dict(r)
        d["report_date"] = d["report_date"].isoformat()
        d["created_at"] = d["created_at"].isoformat()
        if isinstance(d.get("content"), str):
            d["content"] = json.loads(d["content"])
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# 5. Статистика сотрудников (для дашборда менеджера)
# ---------------------------------------------------------------------------

@router.get("/stats/employees", response_model=list)
async def get_employees_stats(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager),
):
    """Накопительный профиль всех сотрудников отдела менеджера."""
    user_info = await conn.fetchrow(
        "SELECT department_id FROM users WHERE id = $1", current_user["user_id"]
    )

    if current_user["role"] == "admin" or not user_info or not user_info["department_id"]:
        rows = await conn.fetch(
            """
            SELECT u.id, u.username, u.role,
                   COALESCE(es.total_completed, 0) as total_completed,
                   COALESCE(es.completed_on_time, 0) as completed_on_time,
                   COALESCE(es.completed_overdue, 0) as completed_overdue,
                   COALESCE(es.avg_score, 0) as avg_score
            FROM users u
            LEFT JOIN employee_stats es ON u.id = es.user_id
            WHERE u.is_active = TRUE
            ORDER BY es.avg_score DESC NULLS LAST
            """
        )
    else:
        rows = await conn.fetch(
            """
            SELECT u.id, u.username, u.role,
                   COALESCE(es.total_completed, 0) as total_completed,
                   COALESCE(es.completed_on_time, 0) as completed_on_time,
                   COALESCE(es.completed_overdue, 0) as completed_overdue,
                   COALESCE(es.avg_score, 0) as avg_score
            FROM users u
            LEFT JOIN employee_stats es ON u.id = es.user_id
            WHERE u.department_id = $1 AND u.is_active = TRUE
            ORDER BY es.avg_score DESC NULLS LAST
            """,
            user_info["department_id"],
        )

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Внутренняя функция — используется роутером и Celery
# ---------------------------------------------------------------------------

async def _build_and_save_report(
    conn: asyncpg.Connection,
    project_id: int,
    manager_id: int,
) -> dict:
    today = date.today()

    project = await conn.fetchrow("SELECT title FROM projects WHERE id = $1", project_id)

    manager = await conn.fetchrow("SELECT username FROM users WHERE id = $1", manager_id)

    completed = await conn.fetch(
        """
        SELECT t.title, u.username as assigned_username, t.ai_score
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.project_id = $1
          AND t.status = 'completed'
        ORDER BY COALESCE(t.completed_at, t.updated_at) DESC
        LIMIT 20
        """,
        project_id,
    )

    overdue = await conn.fetch(
        """
        SELECT t.title, u.username as assigned_username,
               t.deadline::text as deadline
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.project_id = $1
          AND t.status NOT IN ('completed', 'cancelled')
          AND t.deadline IS NOT NULL
          AND t.deadline < NOW()
        ORDER BY t.deadline ASC
        """,
        project_id,
    )

    in_progress = await conn.fetch(
        """
        SELECT t.title, u.username as assigned_username,
               t.deadline::text as deadline
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.project_id = $1
          AND t.status = 'in_progress'
        ORDER BY t.priority DESC, t.deadline ASC NULLS LAST
        """,
        project_id,
    )

    pending = await conn.fetch(
        """
        SELECT t.title, u.username as assigned_username,
               t.deadline::text as deadline
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.project_id = $1
          AND t.status = 'pending'
        ORDER BY t.priority DESC, t.deadline ASC NULLS LAST
        LIMIT 10
        """,
        project_id,
    )

    try:
        content = await generate_daily_report(
            manager_username=manager["username"],
            project_title=project["title"],
            report_date=today.strftime("%d.%m.%Y"),
            completed_tasks=[dict(r) for r in completed],
            overdue_tasks=[dict(r) for r in overdue],
            in_progress_tasks=[dict(r) for r in in_progress],
            pending_tasks=[dict(r) for r in pending],
        )
    except Exception as e:
        logger.error("Ошибка генерации отчёта Gemini: %s", e)
        overdue_risk = [f"Задача «{dict(r)['title']}» просрочена" for r in overdue]

        total_tasks = len(completed) + len(in_progress) + len(pending) + len(overdue)
        if total_tasks == 0:
            summary = "В проекте пока нет задач. Создайте задачи, чтобы видеть прогресс."
        else:
            summary = (
                f"За последние 7 дней завершено {len(completed)} задач. "
                f"В работе: {len(in_progress)}, в ожидании: {len(pending)}"
                + (f", просрочено: {len(overdue)}" if overdue else "") + "."
            )

        highlights = []
        if completed:
            highlights.append(f"✓ Завершено {len(completed)} задач за последние 7 дней")
        if in_progress:
            highlights.append(f"↻ {len(in_progress)} задач активно выполняются")
        if not highlights and total_tasks > 0:
            highlights.append(f"Проект содержит {total_tasks} задач, готовых к работе")

        if overdue:
            recommendation = f"Срочно закройте {len(overdue)} просроченных задач: {', '.join(dict(r)['title'] for r in overdue[:2])}."
        elif in_progress:
            recommendation = f"Продолжайте работу над {len(in_progress)} активными задачами."
        elif pending:
            recommendation = f"Начните выполнение {len(pending)} задач в очереди."
        else:
            recommendation = "Создайте новые задачи для продолжения проекта."

        content = {
            "summary": summary,
            "completed_count": len(completed),
            "overdue_count": len(overdue),
            "in_progress_count": len(in_progress),
            "highlights": highlights,
            "risks": overdue_risk[:3],
            "recommendation": recommendation,
        }

    await conn.execute(
        """
        INSERT INTO ai_reports (manager_id, project_id, content, report_date)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (manager_id, project_id, report_date)
        DO UPDATE SET content = EXCLUDED.content, created_at = CURRENT_TIMESTAMP
        """,
        manager_id,
        project_id,
        json.dumps(content),
        today,
    )

    return {"report_date": today.isoformat(), "project_id": project_id, **content}
