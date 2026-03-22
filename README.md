# Link shortener

Сервис для сокращения ссылок на FastAPI + PostgreSQL + Redis


## Как запустить

### Локально через docker

```bash
git clone https://github.com/cherrryana/fastapi_project_applied_python.git
cd fastapi_project_applied_python

cp .env.example .env

docker-compose up --build
```

После этого:
- Сервис: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

---

## Тесты

### Запуск тестов

```bash
pip install -r requirements.txt

# запуск всех тестов
pytest tests/ -v

# запуск с покрытием
coverage run --source=app -m pytest tests/ -v
coverage report -m
coverage html
```

### Структура тестов

```
tests/
├── conftest.py      # тестовая БД (SQLite), мок Redis, HTTP-клиент
├── test_unit.py     # юнит-тесты
└── test_api.py      # функциональные тесты: все эндпоинты API
```

Покрытие: 91%

### Нагрузочное тестирование

```bash
docker compose up --build

locust -f locustfile.py --host http://localhost:8000
```

Откроется веб-интерфейс на `http://localhost:8089`, где можно задать кол-во пользователей и наблюдать за метриками

---

## API

### Авторизация

| Метод | URL | Что делает |
|-------|-----|------------|
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Логин, возвращает токен |

### Ссылки

| Метод | URL | Нужен токен? | Что делает |
|-------|-----|:------------:|------------|
| POST | `/links/shorten` | Нет* | Создать короткую ссылку |
| GET | `/links/{short_code}` | Нет | Переход по ссылке |
| PUT | `/links/{short_code}` | Да | Обновить URL |
| DELETE | `/links/{short_code}` | Да | Удалить ссылку |
| GET | `/links/{short_code}/stats` | Нет | Статистика |
| GET | `/links/search?original_url=...` | Нет | Поиск по URL |

\* Без токена ссылка создаётся анонимно, ее потом нельзя будет удалить/изменить

---

## Примеры

### Регистрация и логин

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "yana", "password": "qwerty123"}'

curl -X POST http://localhost:8000/auth/login \
  -d "username=yana&password=qwerty123"
```

### Создать ссылку

```bash
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/very/long/path/to/something"}'

curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <твой_токен>" \
  -d '{"url": "https://example.com", "custom_alias": "mylink"}'
```

### Перейти по ссылке

```bash
curl -L http://localhost:8000/links/mylink
```

### Посмотреть статистику

```bash
curl http://localhost:8000/links/mylink/stats
```

---

## БД

Две таблицы: `users` и `links`

**users**: id, username, hashed_password, created_at

**links**: id, short_code, original_url, user_id, created_at, expires_at, redirect_count, last_used_at

Если user_id = NULL - ссылка анонимная. `redirect_count` увеличивается при каждом переходе, `last_used_at` обновляется. Ссылки, не использованные больше 90 дней, удаляются.
