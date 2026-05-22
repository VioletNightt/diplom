# School Event Registration

Веб-приложение для регистрации на учебно-организационные мероприятия:

- пробные экзамены;
- входное тестирование в 9/11 класс;
- очные встречи с учителями.

## Стек

- Python 3.12
- Django 6
- Django REST Framework
- SQLite для локальной разработки
- PostgreSQL можно подключить для боевого окружения
- Django admin как основной административный интерфейс

## Запуск

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Админ-панель: <http://127.0.0.1:8000/admin/>

Пользовательский интерфейс: <http://127.0.0.1:8000/>

Проверка сервера: <http://127.0.0.1:8000/health/>

Демо-пользователи после `seed_demo`:

- `admin@example.com` / `admin12345`
- `teacher@example.com` / `teacher12345`
- `parent@example.com` / `parent12345`

В админ-панели появился справочник `Кабинеты`: этаж, номер, количество мест, активность.
При создании слота встречи учителем кабинет обязателен.

## Основные API

- `POST /api/auth/register/` - открытая регистрация пользователя.
- `POST /api/auth/login/` - получение токена.
- `GET, PUT /api/auth/profile/` - профиль текущего пользователя.
- `GET /api/events/` - список мероприятий.
- `GET /api/slots/` - список слотов с фильтрами.
- `POST /api/registrations/` - запись на слот.
- `DELETE /api/registrations/{id}/` - отмена записи.
- `POST /api/registrations/{id}/attendance/` - отметка явки.
- `GET /api/my-registrations/` - записи текущего пользователя.
- `GET /api/teacher-slots/{teacher_id}/` - слоты учителя.
- `GET /api/registrations/by-slot/{slot_id}/` - участники слота.
- `GET /api/reports/?format=csv` - CSV-отчет.
- `GET /api/reports/?format=xlsx` - Excel-отчет.

Для API-запросов после входа используйте заголовок:

```http
Authorization: Token <token>
```
