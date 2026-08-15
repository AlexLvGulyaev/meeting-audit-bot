# 🏗️ Архитектура Meeting Audit Bot

> Первая версия архитектуры кейса `meeting-audit-bot` на основе урока PEcb10.

---

## 1. Что строим

Telegram-бот, который принимает аудио/видео встречи, транскрибирует их через AssemblyAI (с разделением по говорящим) и проводит аудит транскрипта по заданным критериям через LLM. Результат сохраняется в PostgreSQL.

Помимо Telegram-интерфейса добавляем веб-админку `/admin` для runtime-конфигурации провайдера, модели и промпта.

---

## 2. Компоненты

| Компонент | Роль | Технология |
|-----------|------|------------|
| **Web API** | `/health`, `/admin` | FastAPI |
| **Telegram Bot** | Приём файлов, ответы пользователю | `python-telegram-bot`, polling |
| **Media Service** | Скачивание файлов из Telegram | `python-telegram-bot` + `tempfile` |
| **Transcription Service** | Upload в AssemblyAI, polling транскрипта | `requests` |
| **Audit Service** | LLM-анализ транскрипта по промпту | OpenAI SDK + GigaChat-адаптер |
| **Storage Service** | Сохранение сессий обработки | PostgreSQL + `psycopg2` |
| **Prompt Loader** | Загрузка активного промпта из файла | `pathlib` |
| **Runtime Config** | Active provider, model, temperature, prompt_id | `storage/config.json` |

---

## 3. Поток данных

```
Telegram mp3/video
    → MediaService скачивает файл
    → TranscriptionService → AssemblyAI → transcript
    → AuditService
        → PromptLoader загружает активный prompt.md
        → RuntimeConfig читает provider/model/temperature
        → LLM-вызов
    → результат сохраняется в PostgreSQL
    → ответ отправляется в Telegram частями
```

Оператор через `/admin` изменяет `storage/config.json`. Следующий аудит читает новые параметры без перезапуска бота.

---

## 4. Модель данных

Таблица `video_audits`:

| Поле | Тип | Назначение |
|------|-----|------------|
| `id` | BIGSERIAL PK | Идентификатор записи |
| `created_at` | TIMESTAMPTZ | Время создания |
| `chat_id` | BIGINT | Telegram chat_id |
| `user_id` | BIGINT | Telegram user_id |
| `username` | TEXT | Telegram username |
| `file_id` | TEXT | Telegram file_id |
| `file_unique_id` | TEXT | Уникальный id файла |
| `filename` | TEXT | Имя файла |
| `transcript` | TEXT | Транскрипт |
| `analysis` | TEXT | Результат аудита |
| `status` | TEXT | `success` / `failed` |
| `error_message` | TEXT | Текст ошибки |

---

## 5. Runtime-конфиг

Файл `storage/config.json` управляет поведением AuditService:

```json
{
  "active_provider": "openai",
  "fallback_provider": "gigachat",
  "openai_model": "gpt-4.1-mini",
  "temperature": 0.1,
  "prompt_id": "onboarding",
  "providers": {
    "openai": { "api_key_env": "OPENAI_API_KEY" },
    "gigachat": { "auth_key_env": "GIGACHAT_AUTH_KEY" }
  }
}
```

`/admin` позволяет оператору менять `active_provider`, `openai_model`, `temperature`, `prompt_id`.

---

## 6. Промпты

Промпты хранятся в `prompts/v1/` как файлы Markdown. По умолчанию поставляется:

- `prompts/v1/onboarding.md` — исходные 11 критериев аудита онбординга из урока.
- `prompts/v1/sales-call.md` — адаптированный промпт для аудита холодного звонка (ДЗ).

Активный промпт выбирается через `prompt_id` в runtime-конфиге.

---

## 7. Допущения и ограничения первой версии

- AssemblyAI остаётся единственным STT-провайдером (diarization).
- Telegram polling — основной интерфейс; webhook не реализуется в v1.
- Docker Compose: один сервис `web` (FastAPI + Telegram polling) + `db` (Postgres 16).
- Видео файлы транскрибируются как аудио: AssemblyAI принимает видео-файл напрямую.

---

## 8. Следующие шаги

1. Разбить `bot.py` на модули по компонентам.
2. Добавить FastAPI-приложение с `/health` и `/admin`.
3. Реализовать RuntimeConfig и PromptLoader.
4. Реализовать multi-provider LLM (OpenAI + GigaChat + fallback).
5. Добавить `prompts/v1/sales-call.md` для ДЗ.
6. Подготовить `.env.example`, `docker-compose.yml`, `Dockerfile`.
7. Написать DEPLOYMENT_GUIDE и провести Deployment Validation.
