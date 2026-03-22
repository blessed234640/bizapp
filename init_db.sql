-- ДЕПАРТАМЕНТЫ
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- ПОЛЬЗОВАТЕЛИ
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'guest' CHECK (role IN ('admin', 'manager', 'user', 'guest')),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    is_active BOOLEAN DEFAULT true,
    is_staff BOOLEAN DEFAULT false,
    is_superuser BOOLEAN DEFAULT false,
    last_login TIMESTAMP,
    date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    avatar_url TEXT
);

-- ПРОЕКТЫ
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE
);

-- УЧАСТНИКИ ПРОЕКТОВ
CREATE TABLE IF NOT EXISTS project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- ЗАДАЧИ
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority INTEGER DEFAULT 0,
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tsv tsvector -- Для полнотекстового поиска
);

-- ЛОГИ ЗАДАЧ
CREATE TABLE IF NOT EXISTS task_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ЗАЯВКИ НА ПОВЫШЕНИЕ РОЛИ
CREATE TABLE IF NOT EXISTS role_upgrade_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    requested_role VARCHAR(20) NOT NULL,
    current_user_role VARCHAR(20) NOT NULL,
    status VARCHAR(10) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- Индекс для полнотекстового поиска
CREATE INDEX IF NOT EXISTS tasks_tsv_idx ON tasks USING GIN(tsv);

-- Функция для обновления tsv
CREATE OR REPLACE FUNCTION tasks_trigger() RETURNS trigger AS $$
begin
  new.tsv :=
    setweight(to_tsvector('russian', coalesce(new.title,'')), 'A') ||
    setweight(to_tsvector('russian', coalesce(new.description,'')), 'B');
  return new;
end
$$ LANGUAGE plpgsql;

-- Триггер для обновления tsv
DROP TRIGGER IF EXISTS tsvectorupdate ON tasks;
CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
ON tasks FOR EACH ROW EXECUTE FUNCTION tasks_trigger();