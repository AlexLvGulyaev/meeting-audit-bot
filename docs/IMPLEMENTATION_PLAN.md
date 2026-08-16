# 📋 IMPLEMENTATION_PLAN — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Версия:** 1.0
**Дата:** 2026-08-16
**Статус:** ✅ Выполнен

---

## 1. Архитектура

- **FastAPI** — `/health`, `/admin`, `/admin/executions`, `/admin/audit`, JSON API.
- **Telegram polling** — основной UI, работает в том же процессе с FastAPI.
- **Модульные сервисы:**
  - `app/services/media.py` — скачивание файлов из Telegram.
  - `app/services/transcription.py` — AssemblyAI upload/poll + `speaker_labels`.
  - `app/services/audit.py` — LLM-анализ транскрипта.
  - `app/services/providers/factory.py` — multi-provider: OpenAI, GigaChat.
  - `app/services/storage.py` — PostgreSQL + файловые пути.
  - `app/services/prompt_loader.py` — реестр промптов (base + custom override).
  - `app/services/execution.py` — execution sessions/steps.
  - `app/services/telegram_bot.py` — Telegram handlers.
  - `app/services/audit_log.py` — security audit log.
- **Конфигурация:** `app/core/config.py` (env), `app/core/default_config.py` (defaults), `app/core/runtime_config.py` (`storage/config.json`).

---

## 2. План реализации

| Этап | Задача | Статус |
|------|--------|--------|
| 1 | Разбить `bot.py` на модули `app/services/` | ✅ |
| 2 | FastAPI + `/health` + `/admin` + `/admin/executions` + `/admin/audit` | ✅ |
| 3 | Runtime-конфиг + PromptRegistry | ✅ |
| 4 | Multi-provider LLM + fallback | ✅ |
| 5 | Execution tracing + audit-log + demo-RBAC + Telegram-лимиты | ✅ |
| 6 | Сохранение файлов: `storage/uploads/`, `storage/transcripts/`, `storage/audits/` | ✅ |
| 7 | Промпты для ДЗ: `sales-call.md`, `online-lesson.md`, `client-chat.md` | ✅ |
| 8 | Docker Compose + DEPLOYMENT_GUIDE | ✅ |
| 9 | Deployment Validation | ✅ |
| 10 | Документация APL | ✅ |
| 11 | Публикация в GitHub + отчёт по ДЗ | ✅ |

---

## 3. Модель данных

### `video_audits`

| Поле | Тип |
|------|-----|
| id | BIGSERIAL PK |
| created_at | TIMESTAMPTZ |
| chat_id | BIGINT |
| user_id | BIGINT NULL |
| username | TEXT NULL |
| file_id | TEXT |
| file_unique_id | TEXT |
| filename | TEXT |
| transcript | TEXT |
| analysis | TEXT |
| status | TEXT |
| error_message | TEXT NULL |
| provider | TEXT NULL |
| prompt_id | TEXT NULL |
| mime_type | TEXT NULL |
| file_size | BIGINT NULL |
| duration | INT NULL |
| storage_filename | TEXT NULL |

### `execution_sessions`

| Поле | Тип |
|------|-----|
| session_id | UUID PK |
| created_at | TIMESTAMPTZ |
| updated_at | TIMESTAMPTZ |
| chat_id | BIGINT NULL |
| user_id | BIGINT NULL |
| username | TEXT NULL |
| file_id | TEXT NULL |
| filename | TEXT NULL |
| storage_filename | TEXT NULL |
| status | TEXT |
| video_audit_id | BIGINT NULL |

### `execution_steps`

| Поле | Тип |
|------|-----|
| step_id | UUID PK |
| session_id | UUID FK |
| name | TEXT |
| status | TEXT |
| metadata | JSONB |
| created_at | TIMESTAMPTZ |
| updated_at | TIMESTAMPTZ |

### `admin_audit_log`

| Поле | Тип |
|------|-----|
| id | BIGSERIAL PK |
| created_at | TIMESTAMPTZ |
| actor | TEXT |
| user_id | TEXT NULL |
| user_name | TEXT NULL |
| user_role | TEXT NULL |
| ip_address | TEXT NULL |
| action | TEXT |
| resource_type | TEXT |
| resource_id | TEXT NULL |
| details | JSONB |

---

## 4. Интеграции

| Система | Тип интеграции | Назначение |
|---------|----------------|------------|
| Telegram Bot API | Long polling | Приём файлов, отправка аудита |
| AssemblyAI | HTTP API | STT + `speaker_labels` |
| OpenAI | HTTP API (SDK) | Chat Completions для аудита |
| GigaChat | HTTP API (custom adapter) | Chat Completions для аудита |
| PostgreSQL | Прямое подключение | Хранение метаданных, сессий, аудита |

---

## 5. Критерии готовности

- [x] `docker compose up --build -d` поднимает сервисы.
- [x] `/health` возвращает `{"status":"ok"}`.
- [x] `/health/db` возвращает `{"database":"ok"}`.
- [x] Telegram-бот отвечает на `/start`.
- [x] Отправка mp3/ogg приводит к транскрипту и аудиту.
- [x] `/admin` доступна по токену и demo-токену.
- [x] `/admin/executions` показывает обработки с деталями.
- [x] `/admin/audit` показывает security/админ события.
- [x] Смена промпта в `/admin` применяется без рестарта.
- [x] E2E sales-call даёт 87,5%.
- [x] Deployment Validation пройдена.
