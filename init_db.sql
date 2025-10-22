CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user'
);

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE task_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_metadata ON tasks USING GIN(metadata);

-- Триггер для логирования
CREATE OR REPLACE FUNCTION log_task_changes() RETURNS TRIGGER AS $$  
BEGIN
    INSERT INTO task_logs (task_id, action) VALUES (NEW.id, 'update');
    RETURN NEW;
END;
  $$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_task_update
AFTER UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION log_task_changes();

-- Полнотекстовый поиск (добавим вектор)
ALTER TABLE tasks ADD COLUMN tsv TSVECTOR;
UPDATE tasks SET tsv = to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(description, ''));
CREATE INDEX idx_tasks_tsv ON tasks USING GIN(tsv);

CREATE OR REPLACE FUNCTION update_tsv() RETURNS TRIGGER AS $$  
BEGIN
    NEW.tsv = to_tsvector('russian', coalesce(NEW.title, '') || ' ' || coalesce(NEW.description, ''));
    RETURN NEW;
END;
  $$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_tasks_tsv
BEFORE INSERT OR UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION update_tsv();