from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class IngredientTypeOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class IngredientTypeIn(BaseModel):
    name: str


class IngredientIn(BaseModel):
    name: str
    amount: float
    unit: str
    note: str | None = None


class RecipeIn(BaseModel):
    name: str
    description: str
    time_minutes: int
    ingredients: list[IngredientIn]


class IngredientOut(BaseModel):
    name: str
    amount: float
    unit: str
    note: str | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, value):
        if isinstance(value, Decimal):
            return float(value)
        return value

    @classmethod
    def from_recipe_ingredient(cls, recipe_ingredient):
        return cls(
            name=recipe_ingredient.ingredient.name,
            amount=recipe_ingredient.amount,
            unit=recipe_ingredient.unit,
            note=recipe_ingredient.note,
        )


class RecipeListOut(BaseModel):
    id: int
    name: str
    views: int
    time_minutes: int

    model_config = ConfigDict(from_attributes=True)


class RecipeDetailOut(BaseModel):
    name: str
    time_minutes: int
    description: str
    ingredients: list[IngredientOut]

    @classmethod
    def from_recipe(cls, recipe):
        return cls(
            name=recipe.name,
            time_minutes=recipe.time_minutes,
            description=recipe.description,
            ingredients=[
                IngredientOut.from_recipe_ingredient(item)
                for item in recipe.recipe_ingredients
            ],
        )


class RecipeCreatedOut(RecipeDetailOut):
    id: int

    @classmethod
    def from_recipe(cls, recipe):
        detail = RecipeDetailOut.from_recipe(recipe)
        return cls(id=recipe.id, **detail.model_dump())
