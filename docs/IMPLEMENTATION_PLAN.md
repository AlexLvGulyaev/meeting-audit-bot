# 📋 IMPLEMENTATION_PLAN — Meeting Audit Bot

## 1. Архитектура

- **FastAPI** — `/health`, `/admin`, `/admin/executions`, `/admin/audit`.
- **Telegram polling** — основной UI.
- **Модульные сервисы**:
  - `app/services/media.py` — скачивание файлов из Telegram в `storage/uploads/`.
  - `app/services/transcription.py` — AssemblyAI upload + poll + speaker labels.
  - `app/services/audit.py` — LLM-анализ + fallback.
  - `app/services/storage.py` — PostgreSQL + файловые пути.
  - `app/services/prompt_loader.py` — реестр промптов (base + custom).
  - `app/services/execution.py` — execution sessions / steps.
  - `app/services/telegram_bot.py` — Telegram handlers.
- **Провайдеры LLM**: OpenAI, GigaChat, factory.
- **Конфигурация**: `app/core/config.py`, `default_config.py`, `runtime_config.py`.

## 2. План реализации

| Этап | Задача |
|------|--------|
| 1 | Разбить `bot.py` на модули |
| 2 | FastAPI + `/health` + `/admin` + `/admin/executions` + `/admin/audit` |
| 3 | Runtime-конфиг + PromptRegistry |
| 4 | Multi-provider LLM + fallback |
| 5 | Execution tracing + audit-log + demo-RBAC + Telegram-лимиты |
| 6 | Сохранение файлов: `storage/uploads/`, `storage/transcripts/`, `storage/audits/` |
| 7 | Промпты для ДЗ: `sales-call.md`, `online-lesson.md`, `client-chat.md` |
| 8 | Docker Compose + DEPLOYMENT_GUIDE |
| 9 | Deployment Validation |
| 10 | Документация APL |
| 11 | Публикация в GitHub + отчёт по ДЗ |

## 3. Модель данных

`video_audits`:

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
| upload_path | TEXT |
| transcript_path | TEXT |
| audit_path | TEXT |
| status | TEXT |
| error_message | TEXT NULL |
| provider | TEXT NULL |
| prompt_id | TEXT NULL |

`execution_sessions`:

| Поле | Тип |
|------|-----|
| id | BIGSERIAL PK |
| audit_id | BIGINT FK |
| status | TEXT |
| provider_key | TEXT |
| model_name | TEXT |
| duration_ms | INT |
| started_at | TIMESTAMPTZ |
| finished_at | TIMESTAMPTZ NULL |
| execution_metadata | JSONB |

`execution_steps`:

| Поле | Тип |
|------|-----|
| id | BIGSERIAL PK |
| execution_session_id | BIGINT FK |
| stage_name | TEXT |
| step_order | INT |
| status | TEXT |
| started_at | TIMESTAMPTZ |
| finished_at | TIMESTAMPTZ NULL |
| duration_ms | INT |
| step_metadata | JSONB |

`audit_logs`:

| Поле | Тип |
|------|-----|
| id | BIGSERIAL PK |
| created_at | TIMESTAMPTZ |
| user_id | TEXT |
| user_name | TEXT |
| user_role | TEXT |
| action | TEXT |
| resource_type | TEXT |
| resource_id | TEXT |
| ip_address | TEXT |
| details | JSONB |

## 4. Интеграции

- Telegram Bot API — polling.
- AssemblyAI API — upload + transcript poll + speaker_labels.
- OpenAI API — chat completions.
- GigaChat API — chat completions через адаптер.

## 5. Критерии готовности

- [ ] `docker compose up --build -d` поднимает сервисы.
- [ ] `/health` возвращает `{"status":"ok"}`.
- [ ] Telegram-бот отвечает на `/start`.
- [ ] Отправка mp3 приводит к транскрипту и аудиту.
- [ ] `/admin` доступна по токену и demo-токену.
- [ ] `/admin/executions` показывает обработки с деталями.
- [ ] `/admin/audit` показывает security/админ события.
- [ ] Смена промпта в `/admin` применяется без рестарта.
- [ ] Deployment Validation 12/12 PASS.
