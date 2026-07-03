import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database import Base, get_db
from main import app
from models import IngredientType, Recipe, RecipeIngredient  # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

SAMPLE_INGREDIENTS = [
    {"name": "свёкла", "amount": 2, "unit": "шт"},
    {"name": "капуста", "amount": 300, "unit": "г"},
    {"name": "картофель", "amount": 3, "unit": "шт"},
]


@pytest.fixture
def client():
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    test_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def init_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_db())

    async def override_get_db():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.clear()
    asyncio.run(test_engine.dispose())


def create_recipe(client, name, description, ingredients, time_minutes, views=0):
    response = client.post(
        "/api/recipes",
        json={
            "name": name,
            "description": description,
            "ingredients": ingredients,
            "time_minutes": time_minutes,
        },
    )
    assert response.status_code == 200
    data = response.json()
    if views:
        for _ in range(views):
            client.get(f"/api/recipes/{data['id']}")
    return data


def test_get_recipes_empty(client):
    response = client.get("/api/recipes")

    assert response.status_code == 200
    assert response.json() == []


def test_create_recipe(client):
    response = client.post(
        "/api/recipes",
        json={
            "name": "Борщ",
            "description": "Классический борщ",
            "ingredients": SAMPLE_INGREDIENTS,
            "time_minutes": 90,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Борщ"
    assert data["description"] == "Классический борщ"
    assert data["time_minutes"] == 90
    assert len(data["ingredients"]) == 3
    assert data["ingredients"][0]["name"] == "свёкла"
    assert data["ingredients"][0]["amount"] == 2.0
    assert data["ingredients"][0]["unit"] == "шт"
    assert "views" not in data
    assert "id" in data


def test_get_recipes_returns_short_representation(client):
    create_recipe(
        client,
        name="Борщ",
        description="Классический борщ",
        ingredients=SAMPLE_INGREDIENTS,
        time_minutes=90,
        views=3,
    )

    response = client.get("/api/recipes")

    assert response.status_code == 200
    recipe = response.json()[0]
    assert set(recipe.keys()) == {"id", "name", "views", "time_minutes"}
    assert recipe == {
        "id": recipe["id"],
        "name": "Борщ",
        "views": 3,
        "time_minutes": 90,
    }


def test_get_recipes_sorted_by_popularity(client):
    create_recipe(
        client,
        "Плов",
        "Описание",
        [
            {"name": "рис", "amount": 400, "unit": "г"},
            {"name": "мясо", "amount": 500, "unit": "г"},
        ],
        120,
        views=5,
    )
    create_recipe(
        client,
        "Борщ",
        "Описание",
        [{"name": "свёкла", "amount": 2, "unit": "шт"}],
        90,
        views=2,
    )
    create_recipe(
        client,
        "Салат",
        "Описание",
        [{"name": "огурец", "amount": 1, "unit": "шт"}],
        15,
        views=5,
    )

    response = client.get("/api/recipes")

    assert response.status_code == 200
    recipes = response.json()
    assert [recipe["name"] for recipe in recipes] == ["Салат", "Плов", "Борщ"]


def test_get_recipe_by_id(client):
    created = create_recipe(
        client,
        name="Омлет",
        description="На завтрак",
        ingredients=[
            {"name": "яйца", "amount": 3, "unit": "шт"},
            {"name": "молоко", "amount": 100, "unit": "мл"},
        ],
        time_minutes=10,
    )

    response = client.get(f"/api/recipes/{created['id']}")

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "name",
        "time_minutes",
        "ingredients",
        "description",
    }
    assert response.json()["ingredients"] == [
        {"name": "яйца", "amount": 3.0, "unit": "шт", "note": None},
        {"name": "молоко", "amount": 100.0, "unit": "мл", "note": None},
    ]


def test_get_recipe_increments_views(client):
    created = create_recipe(
        client,
        name="Блины",
        description="Тонкие блины",
        ingredients=[
            {"name": "мука", "amount": 200, "unit": "г"},
            {"name": "молоко", "amount": 500, "unit": "мл"},
        ],
        time_minutes=25,
    )

    client.get(f"/api/recipes/{created['id']}")
    client.get(f"/api/recipes/{created['id']}")

    list_response = client.get("/api/recipes")
    recipe = next(item for item in list_response.json() if item["name"] == "Блины")

    assert recipe["views"] == 2


def test_get_recipe_not_found(client):
    response = client.get("/api/recipes/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Рецепт не найден"


def test_create_recipe_validation_error(client):
    response = client.post(
        "/api/recipes",
        json={
            "name": "Без ингредиентов",
            "description": "Описание",
            "time_minutes": 30,
        },
    )

    assert response.status_code == 422


def test_main_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Кулинарная книга" in response.text
