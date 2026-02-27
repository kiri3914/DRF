# Авторизация в Django REST Framework

## Содержание
1. [Токен авторизация (Token Auth)](#1-токен-авторизация)
2. [JWT токены](#2-jwt-токены)
3. [Сравнение подходов](#3-сравнение-подходов)

---

## 1. Токен авторизация

### Как это работает

```
Клиент → логин/пароль → Сервер → выдаёт токен
Клиент → токен в заголовке → Сервер → проверяет токен → даёт доступ
```

Токен — это просто случайная строка, которая хранится в базе данных и привязана к пользователю.

---

### Установка

```bash
pip install djangorestframework
```

### Настройка `settings.py`

```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework.authtoken',  # добавляем приложение для токенов
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Создаём таблицу токенов

```bash
python manage.py migrate
```

---

### Получение токена — `urls.py`

```python
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('api/login/', obtain_auth_token),  # встроенный endpoint для логина
]
```

---

### Как клиент получает токен

**Запрос:**
```http
POST /api/login/
Content-Type: application/json

{
    "username": "john",
    "password": "secret123"
}
```

**Ответ:**
```json
{
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

### Как клиент использует токен

```http
GET /api/profile/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

---

### Защита вьюх

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    return Response({'username': request.user.username})
```

Или через класс:

```python
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'username': request.user.username})
```

---

### Создание токена вручную (например, при регистрации)

```python
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

user = User.objects.create_user(username='john', password='secret123')
token = Token.objects.create(user=user)
print(token.key)  # → 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

---

### Плюсы и минусы Token Auth

| ✅ Плюсы | ❌ Минусы |
|----------|----------|
| Просто реализовать | Токен хранится в БД (нагрузка на БД) |
| Легко отозвать токен | Токен не истекает автоматически |
| Встроен в DRF | Не масштабируется на несколько серверов |

---

## 2. JWT токены

### Как это работает

JWT (JSON Web Token) — это токен, который **не хранится в базе данных**. Вся информация о пользователе зашита внутри самого токена.

```
Клиент → логин/пароль → Сервер → выдаёт access + refresh токены
Клиент → access токен → Сервер → проверяет подпись → даёт доступ (БД не нужна)
```

**JWT токен состоит из 3 частей:**
```
xxxxx.yyyyy.zzzzz
  │      │      └── Подпись (Signature) — проверяет подлинность
  │      └───────── Данные (Payload) — user_id, срок действия
  └──────────────── Заголовок (Header) — тип токена, алгоритм
```

---

### Установка

```bash
pip install djangorestframework-simplejwt
```

### Настройка `settings.py`

```python
INSTALLED_APPS = [
    ...
    'rest_framework',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Настройка срока действия токенов (опционально)

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),   # access живёт 15 минут
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),      # refresh живёт 7 дней
}
```

---

### Подключение URL-ов — `urls.py`

```python
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   # логин → выдаёт access + refresh
    TokenRefreshView,      # refresh → выдаёт новый access
)

urlpatterns = [
    path('api/login/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]
```

---

### Как клиент получает токены

**Запрос:**
```http
POST /api/login/
Content-Type: application/json

{
    "username": "john",
    "password": "secret123"
}
```

**Ответ:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

- **access** — используется для запросов, живёт недолго (15 мин)
- **refresh** — используется чтобы получить новый access, живёт дольше (7 дней)

---

### Как клиент использует access токен

```http
GET /api/profile/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

> ⚠️ Отличие от Token Auth: здесь пишем `Bearer`, а не `Token`

---

### Обновление access токена

Когда access токен истёк, клиент отправляет refresh токен:

**Запрос:**
```http
POST /api/token/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Ответ:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...новый..."
}
```

---

### Защита вьюх — точно такая же, как и с Token Auth

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    return Response({'username': request.user.username})
```

---

### Добавить данные пользователя в токен (кастомный payload)

По умолчанию в токене только `user_id`. Можно добавить, например, `username` или `email`:

```python
# serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MyTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username  # добавляем username в токен
        token['email'] = user.email
        return token
```

```python
# views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import MyTokenSerializer

class MyTokenView(TokenObtainPairView):
    serializer_class = MyTokenSerializer
```

```python
# urls.py
urlpatterns = [
    path('api/login/', MyTokenView.as_view()),
    ...
]
```

---

### Плюсы и минусы JWT

| ✅ Плюсы | ❌ Минусы |
|----------|----------|
| Не нужна БД для проверки | Нельзя легко отозвать токен |
| Работает на нескольких серверах | Токен больше по размеру |
| Срок действия встроен в токен | Нужно хранить refresh токен безопасно |

---

## 3. Сравнение подходов

| | Token Auth | JWT |
|---|---|---|
| Хранение в БД | Да | Нет |
| Автоматическое истечение | Нет | Да |
| Отзыв токена | Просто (удалить из БД) | Сложнее |
| Несколько серверов | Проблематично | Легко |
| Сложность настройки | Низкая | Средняя |

**Когда использовать Token Auth:**
- Маленький проект
- Нужна простота
- Нужно легко отзывать токены

**Когда использовать JWT:**
- Несколько серверов / микросервисы
- Нужно автоматическое истечение токена
- Нужно хранить данные внутри токена

---

## Быстрая шпаргалка

```bash
# Token Auth
pip install djangorestframework
python manage.py migrate

# JWT
pip install djangorestframework-simplejwt
```

| Действие | Token Auth | JWT |
|---|---|---|
| Заголовок запроса | `Authorization: Token <токен>` | `Authorization: Bearer <токен>` |
| Endpoint логина | `obtain_auth_token` | `TokenObtainPairView` |
| Обновление | — | `TokenRefreshView` |