# Кулинарная книга

## Запуск

```bash
pip install fastapi uvicorn sqlalchemy aiosqlite greenlet httpx pytest
uvicorn main:app --reload
```

Приложение: [http://127.0.0.1:8000](http://127.0.0.1:8000)  
Документация API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API


| Метод | URL                 | Описание                                   |
| ----- | ------------------- | ------------------------------------------ |
| GET   | `/api/recipes`      | Список рецептов (сортировка по просмотрам) |
| GET   | `/api/recipes/{id}` | Детали рецепта (+1 к просмотрам)           |
| POST  | `/api/recipes`      | Создание рецепта                           |


## Структура

- `main.py` — эндпоинты
- `database.py` — подключение к БД
- `models.py` — ORM-модели
- `schemas.py` — Pydantic-схемы
- `static/` — фронтенд
- `test_main.py` — тесты

## Тесты

```bash
pytest test_main.py -v
```

