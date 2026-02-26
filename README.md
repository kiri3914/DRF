### Цели урока

К концу урока студент должен уметь:

- **Понимать, что такое API и зачем нужен DRF**.
- **Объяснить связку Model → Serializer → ViewSet → Router → URL**.
- **Строить API с несколькими связанными моделями** (например, Category и Product).
- **Различать и применять 3–4 типа сериализаторов**: ModelSerializer, вложенный (nested), отдельный для списка, обычный Serializer для отчётов.
- **Использовать в одном ViewSet разные сериализаторы** (list / retrieve / create) и кастомные эндпоинты (`@action`).
- **Знать, где искать документацию и дополнительные материалы**.

---

## 1. Что такое API и зачем нужен DRF

**API (Application Programming Interface)** — это способ, с помощью которого одно приложение или сервис может общаться с другим. В веб-разработке чаще всего речь идёт о **HTTP API**: клиент (браузер, мобильное приложение, другой сервер) отправляет запросы (GET, POST, PUT, DELETE), сервер отвечает данными (обычно в формате JSON).

**Django** отлично подходит для HTML-сайтов, но «из коробки» ему не очень удобно отдавать данные в виде JSON и строить полноценное REST API.

**Django REST Framework (DRF)** — это надстройка над Django, которая:

- упрощает создание REST API;
- позволяет быстро описывать сериализацию данных;
- предоставляет готовые классы представлений (ViewSet, APIView и др.);
- включает в себя роутеры, обработку ошибок, пагинацию, авторизацию и много другого.

В вашем проекте DRF уже подключён в `INSTALLED_APPS`:

```python
"rest_framework",
"drf_yasg",
"mainapp",
```

---

## 2. Обзор структуры проекта `FirstAPI`

Основные части проекта:

- `mainapp/models.py` — две модели: **Category** и **Product** (связь ForeignKey).
- `mainapp/serializers.py` — **несколько сериализаторов**: для категорий, для продуктов (CRUD, список, детали, статистика).
- `mainapp/views.py` — **CategoryViewSet** и **ProductViewSet** (у продуктов — разные сериализаторы для list/retrieve/create и кастомный эндпоинт `stats`).
- `mainapp/urls.py` — роутер регистрирует оба ViewSet.
- `core/urls.py` — префикс `api/v1/` для всего API.

Конечные URL:

- `GET/POST /api/v1/categories/`, `GET/PUT/PATCH/DELETE /api/v1/categories/<id>/`
- `GET/POST /api/v1/products/`, `GET/PUT/PATCH/DELETE /api/v1/products/<id>/`
- `GET /api/v1/products/stats/` — статистика (количество продуктов, категорий, средняя цена).

---

## 3. Модели: источник данных и связь между ними

В проекте две связанные модели: **Category** (категория) и **Product** (товар). Товар принадлежит одной категории — связь «многие к одному» (ForeignKey).

Файл `mainapp/models.py`:

```python
class Category(models.Model):
    """Категория товаров (связана с Product через ForeignKey)."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
```

**Что важно понять:**

- **Category** — самостоятельная сущность; у неё есть `products` (обратная связь через `related_name`).
- **Product** хранит ссылку на категорию в поле `category` (в БД — `category_id`).
- При удалении категории продукты не удаляются: `on_delete=models.SET_NULL` обнуляет `category` у связанных продуктов.
- После изменения моделей нужно выполнить: `python manage.py makemigrations` и `python manage.py migrate`.

---

## 4. Взаимодействие с несколькими моделями в API

После добавления **Category** и связи **Product → Category** в проекте появляются два ресурса и связь между ними.

### Эндпоинты

| Метод | URL | Описание |
|--------|-----|----------|
| GET / POST | `/api/v1/categories/` | Список категорий / создание категории |
| GET / PUT / PATCH / DELETE | `/api/v1/categories/<id>/` | Одна категория |
| GET / POST | `/api/v1/products/` | Список продуктов / создание продукта |
| GET / PUT / PATCH / DELETE | `/api/v1/products/<id>/` | Один продукт (с деталями категории) |
| GET | `/api/v1/products/stats/` | Агрегированная статистика (кастомный эндпоинт) |

### Как связаны модели в запросах

- **Создание продукта с категорией** — в теле POST передаём `category` (id категории):

  ```json
  {
    "name": "Молоко",
    "description": "1 л",
    "price": "120.00",
    "category": 1
  }
  ```

- **Список продуктов** — в ответе у каждого продукта есть поле `category` (id) и при необходимости `category_name` (если используется сериализатор списка).
- **Детальный продукт** — в ответе `category` может быть вложенным объектом `{ "id": 1, "name": "Молочные", "slug": "milk" }`, а не только id.

Связь «несколько моделей» проявляется в том, что один запрос может возвращать данные из двух таблиц (Product + Category), а при создании/обновлении продукта мы передаём ссылку на категорию по id.

---

## 5. Четыре типа сериализаторов и когда их использовать

В DRF сериализаторы бывают разными. В проекте специально используются **4 варианта**, чтобы показать типичные ситуации.

---

### Тип 1: ModelSerializer — стандартный CRUD

**Назначение:** отображение и запись полей одной модели «как есть», без сложной логики.

**Примеры в проекте:** `CategorySerializer`, `ProductSerializer`.

```python
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price",
            "category", "created_at", "updated_at",
        ]
```

**Когда использовать:** обычный CRUD по одной модели; поля совпадают с моделью; при записи принимаем внешний ключ как число (id категории).

**Особенности:** DRF сам подставляет типы полей, валидацию и логику `create()` / `update()`.

---

### Тип 2: Вложенный сериализатор (nested)

**Назначение:** в ответе показывать не только id связанной модели, а целый объект (например, категорию с именем и slug).

**Пример в проекте:** `ProductDetailSerializer` — при GET одного продукта возвращаем продукт с вложенным объектом `category`.

```python
class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)  # вложенный объект

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price",
            "category", "created_at", "updated_at",
        ]
```

**Пример ответа API:**

```json
{
  "id": 1,
  "name": "Молоко",
  "description": "1 л",
  "price": "120.00",
  "category": {
    "id": 1,
    "name": "Молочные",
    "slug": "milk"
  },
  "created_at": "2025-02-25T10:00:00Z",
  "updated_at": "2025-02-25T10:00:00Z"
}
```

**Когда использовать:** детальный просмотр (retrieve), когда клиенту нужна полная информация о связанной сущности без отдельного запроса. Для записи (create/update) обычно используют другой сериализатор, где `category` — просто PrimaryKeyRelatedField (id).

---

### Тип 3: Разные сериализаторы для списка и для записи

**Назначение:** для списка (list) отдавать меньше полей и/или добавить вычисляемые (например, название категории); для создания и обновления — полный набор полей.

**Пример в проекте:** `ProductListSerializer` — только id, name, price, category, плюс `category_name` (read-only).

```python
class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "price", "category", "category_name"]
```

**Когда использовать:** список должен быть «лёгким» (меньше данных, быстрее ответ); в списке нужно показывать имя категории без вложенного объекта. Выбор сериализатора в ViewSet делается через `get_serializer_class()` в зависимости от `self.action` (list / retrieve / create / update).

---

### Тип 4: Обычный Serializer (не ModelSerializer)

**Назначение:** ответ или запрос, который **не совпадает 1:1 с одной моделью** — агрегаты, отчёты, комбинированные данные.

**Пример в проекте:** `ProductStatsSerializer` для эндпоинта `GET /api/v1/products/stats/`.

```python
class ProductStatsSerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    avg_price = serializers.DecimalField(max_digits=10, decimal_places=2)
```

Во ViewSet данные собираются вручную и передаются в сериализатор:

```python
@action(detail=False, methods=["get"])
def stats(self, request):
    agg = Product.objects.aggregate(
        total_products=Count("id"),
        avg_price=Avg("price"),
    )
    data = {
        "total_products": agg["total_products"] or 0,
        "total_categories": Category.objects.count(),
        "avg_price": agg["avg_price"] or 0,
    }
    serializer = ProductStatsSerializer(data)
    return Response(serializer.data)
```

**Когда использовать:** кастомные отчёты, дашборды, ответы из нескольких моделей или агрегатов. У такого сериализатора нет `Meta.model` и нет автоматического `create()`/`update()`.

---

### Сводка: какой сериализатор когда

| Ситуация | Тип сериализатора | Пример в проекте |
|----------|-------------------|-------------------|
| Обычный CRUD по одной модели | ModelSerializer | CategorySerializer, ProductSerializer |
| В ответе — вложенный объект связи | ModelSerializer + вложенный сериализатор (nested) | ProductDetailSerializer |
| Список с другим набором полей / доп. полями | Отдельный ModelSerializer для list | ProductListSerializer |
| Данные не из одной модели (агрегаты, отчёты) | Serializer (без Model) | ProductStatsSerializer |

---

#### Доп. материалы: Сериализаторы в DRF

- **Документация:** [Serializers — Django REST framework](https://www.django-rest-framework.org/api-guide/serializers/)
- **Вопросы для самопроверки:**
  - В чём разница между `Serializer` и `ModelSerializer`?
  - Как сделать поле только для чтения (read_only)?
  - Как при записи принимать только id категории, а при чтении отдавать вложенный объект?
- **Практика:** добавьте поле `stock` в модель Product, обновите миграции и нужные сериализаторы; убедитесь, что в списке и в деталях поле ведёт себя так, как задумано.

---

## 6. ViewSet: логика работы с запросами и выбор сериализатора

В проекте два ViewSet: для категорий и для продуктов. У продуктов один ViewSet обрабатывает и список, и детали, и создание/обновление, но **использует разные сериализаторы** в зависимости от действия.

Файл `mainapp/views.py` (сокращённо):

```python
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category")

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductSerializer

    @action(detail=False, methods=["get"])
    def stats(self, request):
        # ... агрегация и ProductStatsSerializer
        return Response(serializer.data)
```

**Что важно:**

- **Один ViewSet — несколько сериализаторов:** через `get_serializer_class()` по `self.action` выбираем, какой сериализатор отдать для list, retrieve, create, update.
- **Кастомное действие:** декоратор `@action(detail=False)` добавляет эндпоинт `GET /api/v1/products/stats/`, не привязанный к одному объекту.
- **select_related("category")** уменьшает число запросов к БД при выводе списка и деталей продуктов.

---

#### Доп. материалы: Что такое ViewSet

- **Документация по ViewSet**:  
  [Viewsets — Django REST framework](https://www.django-rest-framework.org/api-guide/viewsets/)
- **Что почитать/обсудить:**
  - Разница между `ViewSet`, `ModelViewSet`, `ReadOnlyModelViewSet`.
  - Когда лучше использовать `APIView` вместо ViewSet.
- **Практика:**
  - Сделайте API только для чтения, заменив `ModelViewSet` на `ReadOnlyModelViewSet` и посмотрите, как изменится набор доступных методов.

---

## 7. Роутеры и URL: как формируются эндпоинты

Файл `mainapp/urls.py`:

```python
from rest_framework import routers
from .views import CategoryViewSet, ProductViewSet

router = routers.DefaultRouter()
router.register(r"categories", CategoryViewSet)
router.register(r"products", ProductViewSet)

urlpatterns = router.urls
```

**Что делает роутер:**

- Регистрирует оба ViewSet: категории и продукты.
- Для каждого ViewSet создаёт маршруты:
  - `/categories/`, `/categories/<id>/`;
  - `/products/`, `/products/<id>/`;
- Кастомное действие `@action(detail=False)` даёт дополнительный маршрут: `/products/stats/`.

Файл `core/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("mainapp.urls")),
]
```

Итоговые пути:

- `/api/v1/categories/`, `/api/v1/categories/<id>/`
- `/api/v1/products/`, `/api/v1/products/<id>/`, `/api/v1/products/stats/`

---

#### Доп. материалы: Роутеры в DRF

- **Документация по роутерам**:  
  [Routers — Django REST framework](https://www.django-rest-framework.org/api-guide/routers/)
- **Практика:**
  - Измените префикс `products` на `items` и проверьте, какие URL теперь доступны.
  - Добавьте второй ViewSet (например, `CategoryViewSet`) и зарегистрируйте его в том же роутере.

---

## 8. Как протестировать API

### Через браузер DRF

Если сервер запущен командой:

```bash
python manage.py runserver
```

то можно зайти в браузере на:

- `http://localhost:8000/api/v1/products/`

DRF обычно предоставляет удобный **web-browsable API**, где можно:

- смотреть список объектов;
- отправлять POST/PUT/PATCH/DELETE-запросы через форму.

### Через Postman / HTTP-клиенты

Примеры запросов:

- **Получить список продуктов**

  - Метод: `GET`
  - URL: `http://localhost:8000/api/v1/products/`

- **Создать продукт (с категорией)**

  - Метод: `POST`
  - URL: `http://localhost:8000/api/v1/products/`
  - Тело (JSON):

    ```json
    {
      "name": "Тестовый продукт",
      "description": "Описание продукта",
      "price": "99.99",
      "category": 1
    }
    ```
    (Сначала создайте категорию через `POST /api/v1/categories/` с полями `name` и `slug`.)

- **Статистика**

  - Метод: `GET`
  - URL: `http://localhost:8000/api/v1/products/stats/`
  - В ответе: `total_products`, `total_categories`, `avg_price`.

---

## 9. Документация и Swagger (drf_yasg)

В `INSTALLED_APPS` у вас подключён `drf_yasg` — это библиотека, которая генерирует Swagger / OpenAPI документацию.

**Рекомендуется для студентов:**

- Добавить в `core/urls.py` схему Swagger и Redoc.
- Показать, что документация генерируется автоматически из ViewSet’ов и сериализаторов.

Пример (который можно добавить в урок как доп. шаг):

```python
from django.urls import path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="FirstAPI",
        default_version='v1',
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("mainapp.urls")),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
```

---

## 10. Итоговая картина (mindmap связей)

Для закрепления полезно проговорить цепочку:

- **Модели (Category, Product)** — что хранится в БД; связь через ForeignKey.
- **Сериализаторы** — какой формат данных в каком случае: ModelSerializer (CRUD), вложенный (детали), отдельный для списка, обычный Serializer для отчётов.
- **ViewSet** — один класс на ресурс; через `get_serializer_class()` подбираем сериализатор под действие (list / retrieve / create / update); кастомные эндпоинты через `@action`.
- **Роутер** — регистрирует ViewSet’ы и формирует URL; кастомные действия попадают в маршруты автоматически.
- **`path('api/v1/', include('mainapp.urls'))`** — общий префикс API.

---

## 11. Дополнительные материалы по DRF

### Официальная документация

- Главная страница:  
  [Django REST framework — Home](https://www.django-rest-framework.org/)
- Tutorial (очень рекомендуется студентам):  
  [Tutorial — Django REST framework](https://www.django-rest-framework.org/tutorial/quickstart/)

### Темы для дальнейшего изучения

- Аутентификация и права доступа (Authentication & Permissions).
- Пагинация (Pagination).
- Фильтрация и поиск (Filtering, Ordering, Search).
- GenericAPIView и mixins.
- Тестирование API (APIClient в Django, pytest + DRF).

---

## 12. Предложенные учебные задания

1. **Миграции и новое поле**
   - Выполнить `makemigrations` и `migrate` после добавления Category и связи в Product.
   - Добавить поле `stock` (IntegerField) в Product, обновить миграции и сериализаторы.

2. **Сериализаторы**
   - Сделать эндпоинт категории с вложенным списком продуктов (nested) только для чтения.
   - Добавить второй кастомный Serializer для отчёта (например, «топ-3 категории по количеству товаров»).

3. **Ограничить доступ к API**
   - Подключить TokenAuthentication или SessionAuthentication.
   - Настроить `DEFAULT_PERMISSION_CLASSES` (например, только для авторизованных).

4. **Swagger/Redoc**
   - Подключить схему в `core/urls.py`, открыть `/swagger/` и `/redoc/`, проверить описание эндпоинтов и моделей.

---

## 13. Краткое резюме для студента

- DRF — инструмент для быстрого создания REST API на Django.
- В проекте **две модели** (Category, Product) и связь между ними; API даёт CRUD по обеим и показывает, как передавать связь (category id при создании продукта) и как отдавать вложенные данные (категория внутри продукта).
- **Четыре типа сериализаторов** в одном проекте:
  1. **ModelSerializer** — обычный CRUD (Category, Product при записи).
  2. **Вложенный (nested)** — детальный ответ с объектом категории (ProductDetailSerializer).
  3. **Отдельный для списка** — меньше полей + доп. поле `category_name` (ProductListSerializer).
  4. **Обычный Serializer** — данные не из одной модели (ProductStatsSerializer для stats).
- Один ViewSet может использовать разные сериализаторы через `get_serializer_class()`; кастомные эндпоинты — через `@action`.
- Дальше: авторизация, пагинация, фильтры, тесты.
