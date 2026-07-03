from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from constants import DEFAULT_INGREDIENTS, DEFAULT_UNITS
from database import Base, async_session_maker, engine, get_db
from models import IngredientType, Recipe, RecipeIngredient
from schemas import (
    IngredientTypeIn,
    IngredientTypeOut,
    RecipeCreatedOut,
    RecipeDetailOut,
    RecipeIn,
    RecipeListOut,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

RECIPE_WITH_INGREDIENTS = selectinload(Recipe.recipe_ingredients).selectinload(
    RecipeIngredient.ingredient
)


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


async def seed_ingredients():
    async with async_session_maker() as db:
        result = await db.execute(select(IngredientType))
        existing = {item.name for item in result.scalars().all()}
        for name in DEFAULT_INGREDIENTS:
            if name not in existing:
                db.add(IngredientType(name=name))
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_ingredients()
    yield
    await engine.dispose()


app = FastAPI(
    default_response_class=UTF8JSONResponse,
    lifespan=lifespan,
)


async def get_or_create_ingredient(db: AsyncSession, name: str) -> IngredientType:
    result = await db.execute(select(IngredientType).where(IngredientType.name == name))
    ingredient = result.scalar_one_or_none()
    if ingredient is None:
        ingredient = IngredientType(name=name)
        db.add(ingredient)
        await db.flush()
    return ingredient


async def get_recipe_with_ingredients(
    db: AsyncSession, recipe_id: int
) -> Recipe | None:
    result = await db.execute(
        select(Recipe).options(RECIPE_WITH_INGREDIENTS).where(Recipe.id == recipe_id)
    )
    return result.scalar_one_or_none()


@app.get("/api/ingredients", response_model=list[IngredientTypeOut])
async def get_ingredients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IngredientType).order_by(IngredientType.name))
    return result.scalars().all()


@app.get("/api/units", response_model=list[str])
async def get_units():
    return DEFAULT_UNITS


@app.post("/api/ingredients", response_model=IngredientTypeOut)
async def create_ingredient(
    ingredient_in: IngredientTypeIn, db: AsyncSession = Depends(get_db)
):
    name = ingredient_in.name.strip()
    if not name:
        raise HTTPException(
            status_code=400, detail="Название ингредиента не может быть пустым"
        )

    result = await db.execute(select(IngredientType).where(IngredientType.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    ingredient = IngredientType(name=name)
    db.add(ingredient)
    await db.commit()
    await db.refresh(ingredient)
    return ingredient


@app.get("/api/recipes", response_model=list[RecipeListOut])
async def get_recipes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Recipe).order_by(Recipe.views.desc(), Recipe.time_minutes.asc())
    )
    return result.scalars().all()


@app.get("/api/recipes/{recipe_id}", response_model=RecipeDetailOut)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    recipe = await get_recipe_with_ingredients(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Рецепт не найден")
    recipe.increase_views()
    await db.commit()
    recipe = await get_recipe_with_ingredients(db, recipe_id)
    return RecipeDetailOut.from_recipe(recipe)


@app.post("/api/recipes", response_model=RecipeCreatedOut)
async def create_recipe(recipe_in: RecipeIn, db: AsyncSession = Depends(get_db)):
    recipe = Recipe(
        name=recipe_in.name,
        description=recipe_in.description,
        time_minutes=recipe_in.time_minutes,
        views=0,
    )
    db.add(recipe)
    await db.flush()

    for item in recipe_in.ingredients:
        ingredient_type = await get_or_create_ingredient(db, item.name)
        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient_type.id,
                amount=item.amount,
                unit=item.unit,
                note=item.note,
            )
        )

    await db.commit()
    created_recipe = await get_recipe_with_ingredients(db, int(recipe.id))
    assert created_recipe is not None
    return RecipeCreatedOut.from_recipe(created_recipe)


@app.get("/")
async def main():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
