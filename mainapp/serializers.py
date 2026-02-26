from rest_framework import serializers
from .models import Category, Product


# --- Тип 1: ModelSerializer (стандартный CRUD) ---

class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категории: все поля модели «как есть»."""
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания/обновления продукта.
    При записи принимаем category_id (PK), при чтении можно отдавать id.
    """
    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price",
            "category", "created_at", "updated_at",
        ]


# --- Тип 2: Вложенный сериализатор (nested) ---

class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Для детального ответа: продукт с вложенным объектом категории,
    а не просто id. Удобно для GET /products/1/.
    """
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price",
            "category", "created_at", "updated_at",
        ]


# --- Тип 3: Разные сериализаторы для списка и для записи ---

class ProductListSerializer(serializers.ModelSerializer):
    """
    Для списка продуктов: минимум полей (без description, без дат),
    плюс название категории для удобства.
    """
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "price", "category", "category_name"]


# --- Тип 4: Обычный Serializer (не ModelSerializer) ---

class ProductStatsSerializer(serializers.Serializer):
    """
    Кастомный сериализатор для «агрегированных» данных:
    не привязан к одной модели, поля задаём вручную.
    Используется для эндпоинта вида /products/stats/.
    """
    total_products = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    avg_price = serializers.DecimalField(max_digits=10, decimal_places=2)
