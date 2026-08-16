# 🔌 API_CONTRACT.md — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Дата:** 2026-08-16
**Статус:** Engineering Layer — контракты HTTP API бота и операторской панели.

Базовый URL сайта: `http://localhost:8000` (после `docker compose up` с публикацией порта) или `https://your-domain` (production).

---

## 🔌 1. Публичные эндпоинты

### 🔌 1.1. `GET /health`

Health-эндпоинт для Deployment Verification/Validation.

**Ответ:** `200 OK`
```json
{
  "status": "ok",
  "service": "meeting-audit-bot",
  "timestamp": "2026-08-16T12:34:56.789+00:00"
}
```

### 🔌 1.2. `GET /health/db`

Health-эндпоинт базы данных.

**Ответ:** `200 OK`
```json
{
  "status": "ok",
  "database": "ok"
}
```

**Если БД недоступна:** `503 Service Unavailable`
```json
{
  "status": "degraded",
  "database": "unreachable"
}
```

---

## 🔐 2. Аутентификация операторской панели

Все маршруты `/admin/*` требуют cookie `meeting_audit_admin`. Cookie устанавливается при входе по `ADMIN_TOKEN` (полный доступ) или `ADMIN_DEMO_TOKEN` (только чтение). Cookie действует 1 час.

| Роль | Cookie содержит | Возможности |
|------|-----------------|-------------|
| `admin` | `ADMIN_TOKEN` | Чтение + мутации |
| `demo-admin` | `ADMIN_DEMO_TOKEN` | Только чтение; мутации → `403` |

---

## 🔌 3. Эндпоинты входа/выхода

### 🔌 3.1. `GET /admin/login`

HTML-форма входа. Без авторизации.

### 🔌 3.2. `POST /admin/login`

Вход по полному или демо-токену.

**Тело:** `application/x-www-form-urlencoded`
```
token=<ADMIN_TOKEN или ADMIN_DEMO_TOKEN>
```

**Успех:** `303 See Other` → `/admin`, cookie установлен.

**Неверный токен:** `401 Unauthorized`, рендерится login-форма с ошибкой.

**Событие аудита:** `admin.login_success` или `admin.login_failed`.

### 🔌 3.3. `POST /admin/login/demo`

Одно-кликовой демо-вход. Сервер сам ставит cookie с `ADMIN_DEMO_TOKEN` — токен не попадает в браузер.

**Успех:** `303 See Other` → `/admin`.

**Демо-вход отключён (`ADMIN_DEMO_TOKEN` не задан):** `403 Forbidden`.

### 🔌 3.4. `POST /admin/logout`

Выход. Требует валидную cookie.

**Успех:** `303 See Other` → `/admin/login`, cookie удалён.

---

## 🎛️ 4. Операторская панель `/admin`

### 🎛️ 4.1. `GET /admin`

Dashboard: статусы провайдеров, Telegram, БД; метрики; селектор активного промпта; форма конфигурации.

**Авторизация:** любая валидная cookie (admin или demo).

**Query-параметры (flash-сообщения):**
- `?saved=1` — конфигурация сохранена.
- `?test=ok&prov=openai&msg=...` — результат теста провайдера.
- `?test=err&prov=openai&msg=...` — ошибка теста провайдера.

### 🎛️ 4.2. `POST /admin/save`

Сохранение runtime-конфигурации и custom-промпта.

**Авторизация:** только `admin` (demo → `403`).

**Тело:** `application/x-www-form-urlencoded`

| Параметр | Тип | Описание |
|----------|-----|----------|
| `active_provider` | `openai` \| `gigachat` | Активный LLM-провайдер |
| `fallback_provider` | `openai` \| `gigachat` | Fallback LLM-провайдер |
| `openai_base_url` | string | Base URL для OpenAI-compatible API (пусто = default) |
| `openai_model` | string | Например `gpt-4.1-mini` |
| `openai_temperature` | float | 0,0–2,0 |
| `openai_max_tokens` | int | Максимум токенов |
| `gigachat_model` | string | Например `GigaChat` |
| `gigachat_temperature` | float | 0,0–2,0 |
| `gigachat_max_tokens` | int | Максимум токенов |
| `prompt_id` | string | ID активного сценария аудита |
| `prompt_content` | string | Тело промпта (сохраняется как custom override, если отличается от base) |

**Успех:** `303 See Other` → `/admin?prompt_id={prompt_id}&saved=1`.

**Событие аудита:** `admin.config_update`.

### 🎛️ 4.3. `POST /admin/test-provider`

Real-тест выбранного LLM-провайдера.

**Авторизация:** только `admin`.

**Тело:** `application/x-www-form-urlencoded`
```
provider_id=openai
```

**Успех:** `303 See Other` → `/admin?test=ok&prov=openai&msg=готов`.

**Ошибка:** `303 See Other` → `/admin?test=err&prov=openai&msg=...`.

**Событие аудита:** `admin.provider_test`.

---

## 📊 5. JSON API операторской панели

Все маршруты требуют валидной cookie (admin или demo) — чтение доступно обеим ролям.

### 📊 5.1. `GET /admin/api/config`

Текущий runtime-конфиг `config.json`.

**Ответ:** `200 OK`
```json
{
  "active_provider": "openai",
  "fallback_provider": "gigachat",
  "openai_model": "gpt-4.1-mini",
  "gigachat_model": "GigaChat",
  "prompt_id": "sales-call",
  "providers": {
    "openai": { "base_url": null, "temperature": 0.1, "max_tokens": 2048 },
    "gigachat": { "temperature": 0.1, "max_tokens": 2048 }
  }
}
```

### 📊 5.2. `GET /admin/api/providers/{provider_id}/test`

JSON-версия теста провайдера.

**Ответ:** `200 OK`
```json
{
  "provider_id": "openai",
  "ok": true,
  "error": null
}
```

### 📊 5.3. `GET /admin/api/executions/{session_id}`

Детальная информация о сессии обработки со всеми шагами.

**Ответ:** `200 OK` — объект ExecutionSession.

**Если не найдено:** `404 Not Found`.

### 📊 5.4. `GET /admin/api/audit/{record_id}`

Детали одной записи security audit log.

**Ответ:** `200 OK` — объект AuditLogRecord.

**Если не найдено:** `404 Not Found`.

---

## 📁 6. HTML-страницы операторской панели

### 📁 6.1. `GET /admin/executions`

Список execution-сессий (HTML). Поддерживает query-параметры:
- `offset` — пагинация.
- `status` — фильтр по статусу (`success`, `failed`, `running`).
- `period` — фильтр по периоду.
- `q` — поисковая строка.
- `selected` — ID выбранной сессии.

### 📁 6.2. `GET /admin/audit`

Security audit log (HTML). Поддерживает query-параметры:
- `offset` — пагинация.
- `period` — фильтр по периоду.
- `action` — фильтр по действию.
- `resource_type` — фильтр по типу ресурса.
- `user_id` — фильтр по пользователю.
- `selected` — ID выбранной записи.

### 📁 6.3. `GET /admin/uploads/{filename}`

Выдача загруженного медиафайла. Защищён от path traversal.

**Авторизация:** любая валидная cookie.

**Ответ:** `200 OK` — файл с корректным `Content-Type`.

**Если файл не найден:** `404 Not Found`.

**При попытке выхода за пределы uploads:** `400 Bad Request`.

---

## 🚫 7. Коды ошибок

| Код | Условие |
|-----|---------|
| `303 See Other` | Нет cookie / невалидная cookie — редирект на `/admin/login` |
| `400 Bad Request` | Некорректный `filename` в `/admin/uploads/{filename}` |
| `401 Unauthorized` | Неверный токен на `/admin/login` |
| `403 Forbidden` | Demo-сессия пытается выполнить мутацию или demo-вход отключён |
| `404 Not Found` | Сессия или аудит-запись не найдены |
| `503 Service Unavailable` | БД недоступна на `/health/db` |

---

## 📚 Связанные документы

- [🏗️ `ARCHITECTURE.md`](ARCHITECTURE.md) — архитектура, runtime-config.
- [🛡️ `SECURITY_NOTES.md`](SECURITY_NOTES.md) — аутентификация и RBAC.
- [🎛️ `OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) — как пользоваться панелью.
- [🧪 `TESTING.md`](TESTING.md) — примеры curl-команд.
