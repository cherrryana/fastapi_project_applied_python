# Link shortener

Сокращение ссылок на FastAPI с PostgreSQL и Redis

## Старт

1. Настроить .env
  ```bash
  cp .env.example .env
  ```

2. Запустить через docker compose
  ```
  docker-compose up --build
  ```

Сервис будет доступен на `http://localhost:8000`
Swagger: `http://localhost:8000/docs`

---

## API

### Авторизация

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/auth/register` | Регистрация нового пользователя |
| POST | `/auth/login` | Логин (возвращает JWT-токен) |

### Ссылки

| Метод | URL | Авторизация | Описание |
|-------|-----|-------------|----------|
| POST | `/links/shorten` | Необязательна | Создать короткую ссылку |
| GET | `/links/{short_code}` | Нет | Редирект на оригинальный URL |
| PUT | `/links/{short_code}` | Обязательна | Обновить URL ссылки |
| DELETE | `/links/{short_code}` | Обязательна | Удалить ссылку |
| GET | `/links/{short_code}/stats` | Нет | Статистика по ссылке |
| GET | `/links/search?original_url=...` | Нет | Поиск по оригинальному URL |
| GET | `/links/expired` | Нет | Список истекших ссылок |

---

## Примеры запросов

### Регистрация

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "qwerty"}'
```

### Логин

```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=user&password=qwerty"
```

### Создать короткую ссылку

Анонимно
```bash
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'
```

С авторизацией + кастомный alias + срок жизни
```
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{"url": "https://example.com", "custom_alias": "mylink", "expires_at": "2026-12-31T23:59:00Z"}'
```

### Редирект

```bash
curl -L http://localhost:8000/links/mylink
```

### Статистика

```bash
curl http://localhost:8000/links/mylink/stats
```

### Поиск по URL

```bash
curl "http://localhost:8000/links/search?original_url=https://example.com"
```

### Обновить ссылку

```bash
curl -X PUT http://localhost:8000/links/mylink \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{"url": "https://new-example.com"}'
```

### Удалить ссылку

```bash
curl -X DELETE http://localhost:8000/links/mylink \
  -H "Authorization: Bearer eyJ..."
```

---

## БД

### Таблица users

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | Integer |  |
| username | String(50), unique | Имя пользователя |
| hashed_password | String(128) | Хеш пароля |
| created_at | DateTime | Дата регистрации |

### Таблица links

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | Integer | |
| short_code | String(20), unique, index | Короткий код ссылки |
| original_url | String(2048) | Оригинальный URL |
| user_id | Integer, nullable | Юзер |
| created_at | DateTime | Дата создания |
| expires_at | DateTime, nullable | Срок жизни ссылки |
| redirect_count | Integer | Количество переходов |
| last_used_at | DateTime, nullable | Дата последнего перехода |

