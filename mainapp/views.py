from django.db.models import Avg, Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductStatsSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD для категорий."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    """
    CRUD для продуктов. Используются разные сериализаторы:
    - list   → ProductListSerializer (краткий список)
    - retrieve → ProductDetailSerializer (детальный ответ с вложенной категорией)
    - create/update/partial_update → ProductSerializer (запись)
    """
    queryset = Product.objects.select_related("category")
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductSerializer

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Кастомный эндпоинт: GET /api/v1/products/stats/
        Возвращает агрегированную статистику (используется ProductStatsSerializer).
        """
        agg = Product.objects.aggregate(
            total_products=Count("id"),
            avg_price=Avg("price"),
        )
        total_categories = Category.objects.count()
        data = {
            "total_products": agg["total_products"] or 0,
            "total_categories": total_categories,
            "avg_price": agg["avg_price"] or 0,
        }
        serializer = ProductStatsSerializer(data)
        return Response(serializer.data)
