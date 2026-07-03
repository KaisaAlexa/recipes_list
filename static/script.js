const listView = document.getElementById("list-view");
const detailView = document.getElementById("detail-view");
const formView = document.getElementById("form-view");
const recipesTableWrap = document.getElementById("recipes-table-wrap");
const recipesBody = document.getElementById("recipes-body");
const listLoading = document.getElementById("list-loading");
const listError = document.getElementById("list-error");
const detailLoading = document.getElementById("detail-loading");
const detailError = document.getElementById("detail-error");
const recipeCard = document.getElementById("recipe-card");
const recipeForm = document.getElementById("recipe-form");
const formError = document.getElementById("form-error");
const ingredientsFields = document.getElementById("ingredients-fields");
const ingredientRowTemplate = document.getElementById("ingredient-row-template");

const NEW_OPTION_VALUE = "__new__";

let availableIngredients = [];
let availableUnits = [];

function formatApiError(detail) {
    if (!detail) {
        return "Не удалось сохранить рецепт";
    }
    if (typeof detail === "string") {
        return detail;
    }
    if (Array.isArray(detail)) {
        return detail.map((item) => item.msg || JSON.stringify(item)).join(", ");
    }
    return "Не удалось сохранить рецепт";
}

function showListView() {
    listView.classList.remove("hidden");
    detailView.classList.add("hidden");
    formView.classList.add("hidden");
    location.hash = "";
}

function showDetailView(recipeId) {
    listView.classList.add("hidden");
    detailView.classList.remove("hidden");
    formView.classList.add("hidden");
    location.hash = `recipe/${recipeId}`;
    loadRecipe(recipeId);
}

async function loadFormOptions() {
    const [ingredientsResponse, unitsResponse] = await Promise.all([
        fetch("/api/ingredients"),
        fetch("/api/units"),
    ]);

    if (!ingredientsResponse.ok || !unitsResponse.ok) {
        throw new Error("Не удалось загрузить справочники");
    }

    availableIngredients = await ingredientsResponse.json();
    availableUnits = await unitsResponse.json();
}

function fillSelect(select, options, placeholder) {
    select.innerHTML = "";

    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = placeholder;
    emptyOption.disabled = true;
    emptyOption.selected = true;
    select.appendChild(emptyOption);

    options.forEach((option) => {
        const item = document.createElement("option");
        if (typeof option === "string") {
            item.value = option;
            item.textContent = option;
        } else {
            item.value = option.name;
            item.textContent = option.name;
        }
        select.appendChild(item);
    });

    const newOption = document.createElement("option");
    newOption.value = NEW_OPTION_VALUE;
    newOption.textContent = "+ Добавить свой вариант";
    select.appendChild(newOption);
}

function setupCustomSelect(select, customInput) {
    select.addEventListener("change", () => {
        const isCustom = select.value === NEW_OPTION_VALUE;
        customInput.classList.toggle("hidden", !isCustom);
        customInput.required = isCustom;
        if (!isCustom) {
            customInput.value = "";
        }
    });
}

function addIngredientToCatalog(name) {
    const trimmed = name.trim();
    if (!trimmed) {
        return;
    }
    if (!availableIngredients.some((item) => item.name === trimmed)) {
        availableIngredients.push({ id: null, name: trimmed });
        availableIngredients.sort((a, b) => a.name.localeCompare(b.name, "ru"));
    }
}

function refreshIngredientSelects() {
    ingredientsFields.querySelectorAll(".ingredient-select").forEach((select) => {
        const currentValue = select.value === NEW_OPTION_VALUE
            ? select.parentElement.querySelector(".ingredient-name-custom").value.trim()
            : select.value;
        fillSelect(select, availableIngredients, "Выберите ингредиент");
        if (currentValue && availableIngredients.some((item) => item.name === currentValue)) {
            select.value = currentValue;
        }
    });
}

function addIngredientRow() {
    const row = ingredientRowTemplate.content.cloneNode(true).querySelector(".ingredient-row");
    const ingredientSelect = row.querySelector(".ingredient-select");
    const ingredientCustom = row.querySelector(".ingredient-name-custom");
    const unitSelect = row.querySelector(".ingredient-unit-select");
    const unitCustom = row.querySelector(".ingredient-unit-custom");

    fillSelect(ingredientSelect, availableIngredients, "Выберите ингредиент");
    fillSelect(unitSelect, availableUnits, "Выберите единицу");
    setupCustomSelect(ingredientSelect, ingredientCustom);
    setupCustomSelect(unitSelect, unitCustom);

    ingredientCustom.addEventListener("blur", () => {
        const name = ingredientCustom.value.trim();
        if (name) {
            addIngredientToCatalog(name);
            refreshIngredientSelects();
            ingredientSelect.value = name;
            ingredientCustom.classList.add("hidden");
            ingredientCustom.required = false;
        }
    });

    row.querySelector(".remove-ingredient-btn").addEventListener("click", () => {
        if (ingredientsFields.children.length > 1) {
            row.remove();
        }
    });

    ingredientsFields.appendChild(row);
}

async function showFormView() {
    listView.classList.add("hidden");
    detailView.classList.add("hidden");
    formView.classList.remove("hidden");
    formError.classList.add("hidden");
    recipeForm.reset();
    ingredientsFields.innerHTML = "";

    try {
        await loadFormOptions();
        addIngredientRow();
        location.hash = "add";
    } catch (error) {
        formError.textContent = error.message;
        formError.classList.remove("hidden");
    }
}

function getSelectValue(select, customInput) {
    if (select.value === NEW_OPTION_VALUE) {
        return customInput.value.trim();
    }
    return select.value.trim();
}

function collectIngredients() {
    return Array.from(ingredientsFields.querySelectorAll(".ingredient-row"))
        .map((row) => {
            const name = getSelectValue(
                row.querySelector(".ingredient-select"),
                row.querySelector(".ingredient-name-custom"),
            );
            const unit = getSelectValue(
                row.querySelector(".ingredient-unit-select"),
                row.querySelector(".ingredient-unit-custom"),
            );
            const amount = Number(row.querySelector(".ingredient-amount").value);
            const note = row.querySelector(".ingredient-note").value.trim();

            return {
                name,
                amount,
                unit,
                note: note || null,
            };
        })
        .filter((item) => item.name && item.amount && item.unit);
}

function formatIngredientNote(note) {
    return note || "—";
}

async function loadRecipes() {
    listLoading.classList.remove("hidden");
    listError.classList.add("hidden");
    recipesTableWrap.classList.add("hidden");
    recipesBody.innerHTML = "";

    try {
        const response = await fetch("/api/recipes");
        if (!response.ok) {
            throw new Error("Не удалось загрузить список рецептов");
        }

        const recipes = await response.json();
        recipesBody.innerHTML = recipes.map((recipe) => `
            <tr>
                <td>
                    <a class="recipe-link" href="#" data-id="${recipe.id}">${recipe.name}</a>
                </td>
                <td>${recipe.views}</td>
                <td>${recipe.time_minutes}</td>
            </tr>
        `).join("");

        recipesBody.querySelectorAll(".recipe-link").forEach((link) => {
            link.addEventListener("click", (event) => {
                event.preventDefault();
                showDetailView(link.dataset.id);
            });
        });

        recipesTableWrap.classList.remove("hidden");
    } catch (error) {
        listError.textContent = error.message;
        listError.classList.remove("hidden");
    } finally {
        listLoading.classList.add("hidden");
    }
}

async function loadRecipe(recipeId) {
    detailLoading.classList.remove("hidden");
    detailError.classList.add("hidden");
    recipeCard.classList.add("hidden");

    try {
        const response = await fetch(`/api/recipes/${recipeId}`);
        if (!response.ok) {
            throw new Error("Рецепт не найден");
        }

        const recipe = await response.json();
        document.getElementById("recipe-name").textContent = recipe.name;
        document.getElementById("recipe-time").textContent =
            `Время приготовления: ${recipe.time_minutes} мин`;

        document.getElementById("recipe-ingredients").innerHTML = recipe.ingredients
            .map((item) => `
                <tr>
                    <td>${item.name}</td>
                    <td>${item.amount}</td>
                    <td>${item.unit}</td>
                    <td>${formatIngredientNote(item.note)}</td>
                </tr>
            `)
            .join("");

        document.getElementById("recipe-description").textContent = recipe.description;
        recipeCard.classList.remove("hidden");
    } catch (error) {
        detailError.textContent = error.message;
        detailError.classList.remove("hidden");
    } finally {
        detailLoading.classList.add("hidden");
    }
}

async function createRecipe(event) {
    event.preventDefault();
    formError.classList.add("hidden");

    const name = document.getElementById("recipe-name-input").value.trim();
    const description = document.getElementById("recipe-description-input").value.trim();
    const ingredients = collectIngredients();
    const timeMinutes = Number(document.getElementById("recipe-time-input").value);

    if (!name || !description || !ingredients.length || !timeMinutes) {
        formError.textContent = "Заполните все обязательные поля и добавьте хотя бы один ингредиент";
        formError.classList.remove("hidden");
        return;
    }

    try {
        const response = await fetch("/api/recipes", {
            method: "POST",
            headers: {
                "Content-Type": "application/json; charset=utf-8",
            },
            body: JSON.stringify({
                name,
                description,
                ingredients,
                time_minutes: timeMinutes,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(formatApiError(errorData?.detail));
        }

        showListView();
        await loadRecipes();
    } catch (error) {
        formError.textContent = error.message;
        formError.classList.remove("hidden");
    }
}

document.getElementById("add-recipe-btn").addEventListener("click", showFormView);
document.getElementById("add-ingredient-btn").addEventListener("click", addIngredientRow);
document.getElementById("back-btn").addEventListener("click", () => {
    showListView();
    loadRecipes();
});
document.getElementById("form-back-btn").addEventListener("click", showListView);
recipeForm.addEventListener("submit", createRecipe);

function handleRoute() {
    const recipeMatch = location.hash.match(/^#recipe\/(\d+)$/);
    if (recipeMatch) {
        showDetailView(recipeMatch[1]);
        return;
    }

    if (location.hash === "#add") {
        showFormView();
        return;
    }

    showListView();
    loadRecipes();
}

window.addEventListener("hashchange", handleRoute);
handleRoute();
