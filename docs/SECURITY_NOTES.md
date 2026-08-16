# 🛡️ SECURITY_NOTES.md — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Дата:** 2026-08-16
**Статус:** Engineering Layer — безопасность, доступ, демо-RBAC, лимиты.

---

## 🔐 1. Секреты

| Секрет | Где | Назначение |
|--------|-----|-----------|
| `TELEGRAM_BOT_TOKEN` | `.env` | Telegram Bot API |
| `ASSEMBLYAI_API_KEY` | `.env` | AssemblyAI STT |
| `OPENAI_API_KEY` | `.env` | Провайдер OpenAI |
| `GIGACHAT_AUTH_KEY` | `.env` | GigaChat OAuth-обмен |
| `ADMIN_TOKEN` | `.env` | Полный доступ к `/admin` |
| `ADMIN_DEMO_TOKEN` | `.env` | Read-only доступ к `/admin` |
| `DATABASE_URL` | `.env` | PostgreSQL connection string |

> ⚠️ **Все секреты — только в `.env`.** `.env` в `.gitignore`; в репозитории — `.env.example` с placeholder'ами. API-ключи **никогда** не попадают в файлы shared volume (`storage/config.json`, `storage/prompts/*.md`) и не передаются через `/admin`. Runtime-конфиг хранит только публичные несекретные параметры: имена провайдеров, модели, temperature, max_tokens, active prompt id.

---

## 🛡️ 2. Демо-RBAC для `/admin`

Реализован как демо-RBAC на два токена (admin/demo), role-based guard на backend.

### 🛡️ 2.1. Два токена, две роли

| Токен | Роль cookie | `is_demo` | Возможности |
|-------|-------------|-----------|-------------|
| `ADMIN_TOKEN` | `admin` | `false` | Чтение + мутация runtime-config |
| `ADMIN_DEMO_TOKEN` | `demo-admin` | `true` | Только чтение; мутация → `403` |

Токен передаётся через cookie `meeting_audit_admin` (httponly, secure, samesite=lax, TTL 1 час).

### 🛡️ 2.2. Две зависимости-гарда

| Зависимость | Допуск | Применение |
|-------------|--------|-----------|
| `admin_auth` | любой валидный токен (admin и demo) | `GET /admin/*` — чтение |
| `require_admin_full` | только `admin` (demo → `403`) | `POST /admin/save`, `POST /admin/test-provider` — мутация |

> 📌 **Backend — единственный реальный guard.** В demo-режиме UI дополнительно отключает
> кнопку сохранения и показывает бейдж «Демо-режим» — это удобство оператора, а не защита.
> Прямой `POST /admin/save` с demo-cookie (curl/инструмент) отклоняется на backend.

### 🛡️ 2.3. Почему не HTTP Basic

Cookie-based auth решает три проблемы HTTP Basic:
1. Браузер не кеширует credentials — можно явно выйти через `/admin/logout`.
2. Раздельный lifecycle у demo-cookie (TTL 1 ч) и admin-cookie.
3. Роль фиксируется в security audit log.

---

## 📊 3. Дневной лимит обработок в Telegram

| Параметр | Значение | Защита от |
|----------|----------|-----------|
| `MAX_UPLOADS_PER_DAY` | `5` | массовой обработки записей одним пользователем |
| Счётчик | `video_audits` за `CURRENT_DATE` со статусом `success` | обхода через перезапуск бота |
| Exempt | `ADMIN_USER_ID` | блокировки администратора, который тестирует систему |

Проверка выполняется в `app/services/telegram_bot.py:handle_media` до начала скачивания файла.

---

## 📁 4. Защита файлов `/admin/uploads/{filename}`

Маршрут раздаёт загруженные медиафайлы только авторизованным пользователям `/admin`.

**Path traversal guard:**
- `filename` разрешается относительно `storage/uploads_dir` через `Path.resolve()`.
- Если резolvированный путь выходит за пределы uploads — `400 Bad Request`.

**Авторизация:**
- Требуется валидная cookie `meeting_audit_admin` (admin или demo).

---

## 🧹 5. Рекомендации для production

1. **Задайте реальные токены.** Значения `your_*` в `.env.example` — заглушки. Перед любым
   публичным запуском замените `ADMIN_TOKEN` и `ADMIN_DEMO_TOKEN` на криптографически
   случайные строки.
2. **Используйте HTTPS.** Cookie `meeting_audit_admin` имеет флаг `secure=True`;
   без HTTPS cookie не будет передаваться, и админка не заработает в современных браузерах.
3. **Ограничьте доступ к порту 8000.** Контейнер `web` не публикует порт на хост в production;
   доступ только через reverse proxy в той же Docker-сети.
4. **Настройте CA-bundle для GigaChat.** Для production укажите `GIGACHAT_CA_BUNDLE` в `.env`
   вместо пустого значения (которое отключает проверку сертификата).
5. **Мониторьте лимиты.** Дневной лимит защищает публичное демо, но при масштабировании
   рассмотрите индивидуальные квоты и rate-limiting на уровне Telegram.

---

## 📚 Связанные документы

- [🔌 `API_CONTRACT.md`](API_CONTRACT.md) — коды ошибок и контракты.
- [🎛️ `OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) — как пользоваться RBAC.
- [🚀 `DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание.
