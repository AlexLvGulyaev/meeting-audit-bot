# Meeting Audit Bot

Telegram-бот для аудита встреч и звонков: скачивает видео/аудио, транскрибирует через AssemblyAI с разделением по спикерам и анализирует диалог по выбираемому промпту через OpenAI или GigaChat.

## Возможности

- Приём видео и аудио (mp3/mp4) в Telegram.
- Транскрибация с диаризацией (`speaker_labels`) через AssemblyAI.
- Мультипровайдерный LLM-анализ: OpenAI-совместимые API + GigaChat (Sber).
- Веб-админка с демо-режимом:
  - Dashboard, Execution tracing, Audit log.
  - Runtime-конфиг: активный провайдер, модель, fallback, активный промпт.
  - Редактирование кастомных промптов с приоритетом над базовыми.
- Три уровня observability: stdout-логи, execution sessions/steps, security audit log.
- Ограничение для демо-пользователей: 5 успешных обработок в сутки; админ Telegram user id освобождён от лимита.

## Стек

- Python 3.12, FastAPI, Uvicorn
- python-telegram-bot (polling)
- AssemblyAI (STT + diarization)
- OpenAI SDK + GigaChat OAuth HTTP-адаптер
- PostgreSQL 16
- Docker, Docker Compose

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните секреты.
2. Запустите:

```bash
docker compose up --build -d
```

3. Откройте админку: `https://your-domain/admin` → **Войти в демо-режиме**.
4. Напишите боту в Telegram и отправьте видео/аудио.

## Архитектура

- `app/main.py` — единая точка входа FastAPI + lifespan (инициализация БД, runtime-config, Telegram polling).
- `app/services/telegram_bot.py` — обработка входящих медиа, execution tracing, сохранение аудита.
- `app/services/transcription.py` — AssemblyAI upload/poll с `speaker_labels`.
- `app/services/audit.py` — LLM-анализ с primary/fallback/static fallback.
- `app/routes/admin.py` — веб-админка и JSON API.
- `app/services/storage.py` — PostgreSQL: аудиты, execution sessions/steps, admin audit log.
- `prompts/v1/` — базовые промпты; `storage/prompts/` — кастомные overrides.
- `storage/config.json` — runtime config (gitignored, seeded из `app/core/default_config.py`).

## Документация

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — целевая архитектура.
- [docs/SPEC.md](docs/SPEC.md) — функциональная спецификация.
- [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) — план реализации.
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) — воспроизводимое развёртывание.
- [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) — паспорт состояния проекта.

## Лицензия

MIT. Исходный образовательный проект `stt_analyse` — Anton Khapinsky, Career in Business, Part 2.
