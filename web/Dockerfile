FROM python:3.10-slim

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Запускаем миграции и сервер
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8080"]