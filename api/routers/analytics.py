from datetime import date, timedelta
import asyncpg
from fastapi import APIRouter, Depends, Query
from dependencies import get_db, any_authenticated, admin_or_manager

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def overview(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated),
):
    uid = current_user["user_id"]
    role = current_user["role"]

    if role in ("admin", "manager"):
        total = await conn.fetchval("SELECT COUNT(*) FROM tasks")
        completed = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        in_progress = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'")
        overdue = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('completed','cancelled') AND deadline < NOW() AND deadline IS NOT NULL"
        )
        critical = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE is_critical = TRUE AND status NOT IN ('completed','cancelled')"
        )
        avg_score = await conn.fetchval(
            "SELECT ROUND(AVG(ai_score)::numeric, 1) FROM tasks WHERE ai_score IS NOT NULL"
        )
        projects_total = await conn.fetchval("SELECT COUNT(*) FROM projects")
        projects_active = await conn.fetchval(
            "SELECT COUNT(DISTINCT project_id) FROM tasks WHERE status = 'in_progress'"
        )
    else:
        total = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE assigned_to = $1", uid)
        completed = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE assigned_to = $1 AND status = 'completed'", uid
        )
        in_progress = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE assigned_to = $1 AND status = 'in_progress'", uid
        )
        overdue = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE assigned_to = $1 AND status NOT IN ('completed','cancelled') AND deadline < NOW() AND deadline IS NOT NULL",
            uid,
        )
        critical = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE assigned_to = $1 AND is_critical = TRUE AND status NOT IN ('completed','cancelled')",
            uid,
        )
        avg_score = await conn.fetchval(
            "SELECT ROUND(AVG(ai_score)::numeric, 1) FROM tasks WHERE assigned_to = $1 AND ai_score IS NOT NULL", uid
        )
        projects_total = await conn.fetchval(
            "SELECT COUNT(DISTINCT project_id) FROM tasks WHERE assigned_to = $1", uid
        )
        projects_active = await conn.fetchval(
            "SELECT COUNT(DISTINCT project_id) FROM tasks WHERE assigned_to = $1 AND status = 'in_progress'", uid
        )

    completion_rate = round((completed / total * 100), 1) if total else 0
    overdue_rate = round((overdue / total * 100), 1) if total else 0

    return {
        "total_tasks": int(total or 0),
        "completed": int(completed or 0),
        "in_progress": int(in_progress or 0),
        "overdue": int(overdue or 0),
        "critical": int(critical or 0),
        "avg_score": float(avg_score or 0),
        "completion_rate": completion_rate,
        "overdue_rate": overdue_rate,
        "projects_total": int(projects_total or 0),
        "projects_active": int(projects_active or 0),
    }


@router.get("/workload")
async def workload(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(admin_or_manager),
):
    rows = await conn.fetch(
        """
        SELECT
            u.username,
            COUNT(t.id) FILTER (WHERE t.status = 'pending')     AS pending,
            COUNT(t.id) FILTER (WHERE t.status = 'in_progress') AS in_progress,
            COUNT(t.id) FILTER (WHERE t.status = 'completed')   AS completed,
            COUNT(t.id) FILTER (WHERE t.status NOT IN ('completed','cancelled') AND t.deadline < NOW() AND t.deadline IS NOT NULL) AS overdue,
            ROUND(AVG(t.ai_score) FILTER (WHERE t.ai_score IS NOT NULL)::numeric, 1) AS avg_score
        FROM users u
        LEFT JOIN tasks t ON t.assigned_to = u.id
        WHERE u.is_active = TRUE AND u.role NOT IN ('admin')
        GROUP BY u.id, u.username
        HAVING COUNT(t.id) > 0
        ORDER BY (COUNT(t.id) FILTER (WHERE t.status = 'in_progress')) DESC
        LIMIT 15
        """
    )
    return [
        {
            "username": r["username"],
            "pending": int(r["pending"] or 0),
            "in_progress": int(r["in_progress"] or 0),
            "completed": int(r["completed"] or 0),
            "overdue": int(r["overdue"] or 0),
            "avg_score": float(r["avg_score"] or 0),
        }
        for r in rows
    ]


@router.get("/completion-trend")
async def completion_trend(
    weeks: int = Query(default=8, ge=2, le=24),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated),
):
    uid = current_user["user_id"]
    role = current_user["role"]

    rows = await conn.fetch(
        """
        SELECT
            DATE_TRUNC('week', COALESCE(completed_at, updated_at))::date AS week_start,
            COUNT(*) AS completed_count
        FROM tasks
        WHERE status = 'completed'
          AND COALESCE(completed_at, updated_at) >= NOW() - ($1 || ' weeks')::interval
          AND ($2 OR assigned_to = $3)
        GROUP BY 1
        ORDER BY 1
        """,
        str(weeks),
        role in ("admin", "manager"),
        uid,
    )

    today = date.today()
    start = today - timedelta(weeks=weeks)
    start = start - timedelta(days=start.weekday())

    week_map = {r["week_start"]: int(r["completed_count"]) for r in rows}
    result = []
    cur = start
    while cur <= today:
        result.append({"week": cur.isoformat(), "completed": week_map.get(cur, 0)})
        cur += timedelta(weeks=1)

    return result


@router.get("/priority-stats")
async def priority_stats(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated),
):
    uid = current_user["user_id"]
    role = current_user["role"]

    rows = await conn.fetch(
        """
        SELECT priority, status, COUNT(*) AS cnt
        FROM tasks
        WHERE ($1 OR assigned_to = $2)
        GROUP BY priority, status
        """,
        role in ("admin", "manager"),
        uid,
    )

    result = {0: {}, 1: {}, 2: {}}
    for r in rows:
        p = r["priority"]
        if p in result:
            result[p][r["status"]] = int(r["cnt"])

    labels = {0: "Низкий", 1: "Средний", 2: "Высокий"}
    return [
        {
            "priority": labels[p],
            "pending": result[p].get("pending", 0),
            "in_progress": result[p].get("in_progress", 0),
            "completed": result[p].get("completed", 0),
            "cancelled": result[p].get("cancelled", 0),
        }
        for p in (0, 1, 2)
    ]


@router.get("/burndown/{project_id}")
async def burndown(
    project_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: dict = Depends(any_authenticated),
):
    project = await conn.fetchrow("SELECT id, title, created_at FROM projects WHERE id = $1", project_id)
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Проект не найден")

    total_tasks = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE project_id = $1", project_id)

    rows = await conn.fetch(
        """
        SELECT
            DATE_TRUNC('day', COALESCE(completed_at, updated_at))::date AS day,
            COUNT(*) AS done_count
        FROM tasks
        WHERE project_id = $1 AND status = 'completed'
        GROUP BY 1
        ORDER BY 1
        """,
        project_id,
    )

    start = project["created_at"].date()
    today = date.today()

    done_by_day = {}
    cumulative = 0
    for r in rows:
        cumulative += int(r["done_count"])
        done_by_day[r["day"]] = cumulative

    result = []
    cur = start
    cumulative = 0
    while cur <= today:
        if cur in done_by_day:
            cumulative = done_by_day[cur]
        remaining = int(total_tasks) - cumulative
        result.append({"date": cur.isoformat(), "remaining": max(remaining, 0), "completed": cumulative})
        cur += timedelta(days=1)

    return {"project_title": project["title"], "total": int(total_tasks), "points": result}
