# Базовый образ с Python 3.12
FROM python:3.12-slim-bookworm

# Установка ffmpeg и системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY .. .

# Запуск бота
CMD ["python", "./main.py"]