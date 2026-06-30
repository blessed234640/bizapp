from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_rename_guest_to_intern'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Новые поля в tasks
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS deadline TIMESTAMP;",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_generated BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_score INTEGER CHECK (ai_score BETWEEN 1 AND 10);",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_feedback TEXT;",

                # Таблица AI-отчётов
                """
                CREATE TABLE IF NOT EXISTS ai_reports (
                    id SERIAL PRIMARY KEY,
                    manager_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
                    content JSONB NOT NULL,
                    report_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (manager_id, project_id, report_date)
                );
                """,

                # Таблица накопительной статистики сотрудников
                """
                CREATE TABLE IF NOT EXISTS employee_stats (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    total_completed INTEGER DEFAULT 0,
                    completed_on_time INTEGER DEFAULT 0,
                    completed_overdue INTEGER DEFAULT 0,
                    avg_score DECIMAL(4, 2) DEFAULT 0.00,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
            ],
            reverse_sql=[
                "DROP TABLE IF EXISTS employee_stats;",
                "DROP TABLE IF EXISTS ai_reports;",
                "ALTER TABLE tasks DROP COLUMN IF EXISTS ai_feedback;",
                "ALTER TABLE tasks DROP COLUMN IF EXISTS ai_score;",
                "ALTER TABLE tasks DROP COLUMN IF EXISTS completed_at;",
                "ALTER TABLE tasks DROP COLUMN IF EXISTS ai_generated;",
                "ALTER TABLE tasks DROP COLUMN IF EXISTS is_critical;",
                "ALTER TABLE tasks DROP COLUMN IF EXISTS deadline;",
            ],
        ),
    ]
