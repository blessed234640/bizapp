import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

_GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
_TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
_CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
_MODEL = "GigaChat"

_access_token: Optional[str] = None
_token_expires_at: float = 0


class QuotaExceededError(Exception):
    pass


def _get_token() -> str:
    global _access_token, _token_expires_at

    if _access_token and time.time() < _token_expires_at - 60:
        return _access_token

    r = requests.post(
        _TOKEN_URL,
        headers={
            "Authorization": f"Basic {_gigachat_auth_key()}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"scope": "GIGACHAT_API_PERS"},
        verify=False,
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    _access_token = data["access_token"]
    _token_expires_at = data.get("expires_at", (time.time() + 1800) * 1000) / 1000
    logger.info("GigaChat: получен новый access token")
    return _access_token


def _gigachat_auth_key() -> str:
    key = os.getenv("GIGACHAT_AUTH_KEY")
    if not key:
        raise RuntimeError("GIGACHAT_AUTH_KEY environment variable is required")
    return key


def _call_model_sync(prompt: str) -> str:
    token = _get_token()

    def _post(tok: str):
        return requests.post(
            _CHAT_URL,
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={
                "model": _MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            verify=False,
            timeout=30,
        )

    r = _post(token)

    if r.status_code == 401:
        global _access_token
        _access_token = None
        r = _post(_get_token())

    if r.status_code == 429:
        raise QuotaExceededError("Исчерпан лимит запросов GigaChat. Попробуйте позже.")

    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


async def _call_model(prompt: str) -> str:
    return await asyncio.to_thread(_call_model_sync, prompt)


def _parse_json(text: str) -> dict | list:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
    return json.loads(cleaned.strip())


async def generate_tasks(
    project_title: str,
    project_description: str,
    manager_description: str,
    existing_tasks: list[dict],
    project_deadline: Optional[datetime] = None,
) -> list[dict]:
    existing_summary = (
        "\n".join(f"- {t['title']}" for t in existing_tasks)
        if existing_tasks
        else "задач пока нет"
    )

    deadline_hint = (
        f"Дедлайн всего проекта: {project_deadline.strftime('%d.%m.%Y')}."
        if project_deadline
        else "Дедлайн проекта не задан, распределяй сроки разумно."
    )

    prompt = f"""
Ты — опытный менеджер проектов. Твоя задача — разбить работу на конкретные задачи.

Проект: {project_title}
Описание проекта: {project_description or 'не указано'}
{deadline_hint}

Что нужно сделать (слова менеджера):
{manager_description}

Уже существующие задачи (не дублируй их):
{existing_summary}

Верни ТОЛЬКО валидный JSON-массив без пояснений. Каждый элемент:
{{
  "title": "Название задачи (кратко, до 80 символов)",
  "description": "Подробное описание что именно нужно сделать",
  "priority": <число 0, 1 или 2, где 0=низкий, 1=средний, 2=высокий>,
  "deadline_days": <через сколько дней от сегодня должна быть выполнена>
}}

Требования:
- Минимум 3, максимум 10 задач
- Задачи должны быть конкретными и выполнимыми
- Дедлайны должны быть реалистичными и идти в логическом порядке
- Не включай задачи которые уже есть в списке выше
"""

    text = await _call_model(prompt)
    tasks = _parse_json(text)

    if not isinstance(tasks, list):
        raise ValueError("GigaChat вернул не массив задач")

    return tasks


async def evaluate_task_completion(
    task_title: str,
    task_description: str,
    completion_note: str,
    deadline: Optional[datetime],
    completed_at: datetime,
    employee_stats: Optional[dict] = None,
) -> dict:
    time_info = "Дедлайн не был установлен."
    if deadline:
        from datetime import timezone
        deadline_naive = deadline.replace(tzinfo=None) if deadline.tzinfo else deadline
        completed_naive = completed_at.replace(tzinfo=None) if completed_at.tzinfo else completed_at
        delta = completed_naive - deadline_naive
        if delta.total_seconds() > 0:
            time_info = f"Задача сдана с опозданием на {delta.days + 1} дн."
        else:
            time_info = f"Задача сдана досрочно, за {abs(delta.days)} дн. до дедлайна."

    history_hint = ""
    if employee_stats:
        history_hint = f"""
История сотрудника:
- Всего завершено задач: {employee_stats.get('total_completed', 0)}
- Сдано вовремя: {employee_stats.get('completed_on_time', 0)}
- Просрочено: {employee_stats.get('completed_overdue', 0)}
- Средняя оценка: {employee_stats.get('avg_score', 0)}/10
"""

    prompt = f"""
Ты — аналитик качества работы. Оцени выполнение задачи сотрудником.

Задача: {task_title}
Что нужно было сделать: {task_description or 'описание не указано'}
{time_info}
{history_hint}
Что написал сотрудник о выполнении:
"{completion_note}"

Оцени по двум критериям:
1. Соблюдение сроков (40% оценки)
2. Качество отчёта о выполнении — насколько подробно и понятно описана работа (60% оценки)

Верни ТОЛЬКО валидный JSON без пояснений:
{{
  "score": <целое число от 1 до 10>,
  "feedback": "Краткий комментарий на русском языке (1-2 предложения) — что хорошо и что можно улучшить"
}}
"""

    text = await _call_model(prompt)
    result = _parse_json(text)

    if not isinstance(result, dict) or "score" not in result:
        raise ValueError("GigaChat вернул неверный формат оценки")

    result["score"] = max(1, min(10, int(result["score"])))
    return result


async def generate_daily_report(
    manager_username: str,
    project_title: str,
    report_date: str,
    completed_tasks: list[dict],
    overdue_tasks: list[dict],
    in_progress_tasks: list[dict],
    pending_tasks: list[dict] = None,
) -> dict:
    def fmt_tasks(tasks: list[dict]) -> str:
        if not tasks:
            return "нет"
        lines = []
        for t in tasks:
            user = t.get("assigned_username") or "не назначен"
            score = f", оценка {t['ai_score']}/10" if t.get("ai_score") else ""
            deadline = f", дедлайн {t['deadline']}" if t.get("deadline") else ""
            lines.append(f"  - {t['title']} ({user}{score}{deadline})")
        return "\n".join(lines)

    pending_tasks = pending_tasks or []

    completed_titles = ", ".join(t["title"] for t in completed_tasks) or "нет"
    overdue_titles = ", ".join(t["title"] for t in overdue_tasks) or "нет"
    in_progress_titles = ", ".join(
        f"{t['title']} (исполнитель: {t.get('assigned_username') or 'не назначен'}, дедлайн: {t.get('deadline') or 'не задан'})"
        for t in in_progress_tasks
    ) or "нет"

    prompt = f"""
Ты — бизнес-аналитик. Составь детальный управленческий отчёт по проекту на основе КОНКРЕТНЫХ данных ниже.

Менеджер: {manager_username}
Проект: {project_title}
Дата отчёта: {report_date}

ЗАВЕРШЕНО за 7 дней ({len(completed_tasks)} шт.): {completed_titles}
ПРОСРОЧЕНО ({len(overdue_tasks)} шт.): {overdue_titles}
В РАБОТЕ ({len(in_progress_tasks)} шт.): {in_progress_titles}
В ОЧЕРЕДИ ({len(pending_tasks)} шт.): {fmt_tasks(pending_tasks)}

Правила:
- В summary упомяни конкретные задачи по названию, не пиши общими словами
- В highlights укажи что конкретно идёт хорошо (конкретные задачи или исполнители)
- В risks укажи конкретные риски: просроченные задачи, задачи без исполнителя, близкие дедлайны
- recommendation должна быть конкретной: назови задачу или исполнителя

Верни ТОЛЬКО валидный JSON без пояснений:
{{
  "summary": "2-3 предложения с упоминанием конкретных задач",
  "completed_count": {len(completed_tasks)},
  "overdue_count": {len(overdue_tasks)},
  "in_progress_count": {len(in_progress_tasks)},
  "highlights": ["конкретный позитивный момент 1", "конкретный позитивный момент 2"],
  "risks": ["конкретный риск 1"],
  "recommendation": "Конкретная рекомендация с названием задачи или исполнителя"
}}
"""

    text = await _call_model(prompt)
    result = _parse_json(text)

    result.setdefault("completed_count", len(completed_tasks))
    result.setdefault("overdue_count", len(overdue_tasks))
    result.setdefault("in_progress_count", len(in_progress_tasks))

    return result
