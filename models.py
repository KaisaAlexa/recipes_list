from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from database import Base


class IngredientType(Base):
    __tablename__ = "ingredient_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredient_types.id"), nullable=False)

    amount = Column(Numeric, nullable=False)
    unit = Column(String, nullable=False)
    note = Column(String, nullable=True)

    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("IngredientType", back_populates="recipe_ingredients")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    time_minutes = Column(Integer, nullable=False)
    views = Column(Integer, nullable=False, default=0)

    recipe_ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )

    def increase_views(self):
        self.views += 1
