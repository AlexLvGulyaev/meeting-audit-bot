# 🏠 Meeting Audit Bot

Telegram-бот для аудита встреч, звонков и уроков: скачивает аудио/видео, транскрибирует речь через AssemblyAI с разделением по спикерам и анализирует диалог по выбираемому сценарию через OpenAI или GigaChat. Администратор управляет сценариями аудита, провайдерами LLM и наблюдает за обработками через веб-панель `/admin`.

> 🤖 **Живое демо — Telegram-бот:** @PEcb10_bot  
> 🖥️ **Операторская панель:** <https://meeting-audit-bot.alex-n8n.site/admin>  
> 📦 **Репозиторий:** <https://github.com/AlexLvGulyaev/meeting-audit-bot>

> 📌 **Атрибуция:** идея аудио-аудита встреч и исходная архитектура Telegram-бота взяты из публичного репозитория [`MrGAN12009/stt_analyse`](https://github.com/MrGAN12009/stt_analyse). Текущая версия переработана в единый самодостаточный сервис: единый процесс FastAPI + Telegram polling, мультипровайдерный LLM (OpenAI/GigaChat), runtime-конфигурация, веб-админка `/admin`, execution-трейсы и аудит.

---

## 🌐 Публичные точки входа

| Точка | URL | Назначение |
|-------|-----|-----------|
| **Telegram-бот** | @PEcb10_bot | Основная точка входа: отправить аудио/видео, получить аудит |
| **Операторская панель** | `…/admin` | Только для операторов: runtime-config, смена сценария аудита, observability |
| **Демо-вход в админку** | `…/admin/login/demo` | Read-only просмотр без токена в браузере |
| **Health** | `…/health` | `{"status":"ok"}` |

> 📌 Локально после `docker compose up -d --build`: админка — `http://localhost:8000/admin`, health — `http://localhost:8000/health`.

---

## 🎬 Демо-тур

Короткий визуальный обзор системы. Полный скриншот-тур — в [🎬 `docs/SYSTEM_DEMO.md`](docs/SYSTEM_DEMO.md).

**Telegram — `/start` и список сценариев:** пользователь видит доступные сценарии аудита и активный промпт.

![Telegram /start: приветствие и список сценариев](docs/screenshots/tg-start-scenarios.png)

**Telegram — аудит B2B-звонка:** отправлен аудиофайл, бот вернул транскрипт и оценку 87,5%.

![Telegram: аудит sales-call с оценкой 87,5%](docs/screenshots/tg-audio-sales-call-audit.png)

**Операторская панель `/admin`** — dashboard, выбор активного сценария аудита и список сессий:

![Админка: dashboard со статусами провайдеров и селектором промпта](docs/screenshots/admin-dashboard.png)

![Админка: список сессий обработки](docs/screenshots/admin-executions-list.png)

---

## 🎯 1. Что это

Руководители, HR, sales-менеджеры и тренеры получают записи встреч и звонков. Вместо ручного прослушивания и разбора:

- **Telegram-бот** принимает аудио/видео и возвращает структурированный аудит диалога.
- **AssemblyAI** с `speaker_labels` разделяет речь по спикерам и формирует читаемый транскрипт.
- **LLM** (OpenAI / GigaChat) проверяет диалог по выбранному сценарию: онбординг, холодный звонок, онлайн-урок, переписка с клиентом.
- **Веб-админка** позволяет сменить активный сценарий, провайдера и модель без рестарта.
- **Три контура observability** показывают, что происходило с каждым файлом.

Система не падает без активного провайдера: при сбое или отсутствии ключа срабатывает fallback-провайдер.

---

## 💡 2. Ключевые возможности

| Возможность | Описание |
|-------------|----------|
| 🤖 **Мультипровайдерность** | OpenAI / GigaChat (Сбер) через единую абстракцию Chat Completions; active/fallback LLM-цепочка |
| 🎛️ **Смена сценария без рестарта** | `/admin`: активный промпт (аудит-чеклист) меняется в runtime, следующий файл обрабатывается по новому сценарию |
| 📝 **Промпты — файлы** | Базовые промпты в `prompts/v1/`; custom override в `storage/prompts/` с human-readable `title:` frontmatter |
| 🔐 **Демо-RBAC админки** | Полный токен (`ADMIN_TOKEN`) + read-only демо-токен (`ADMIN_DEMO_TOKEN`); backend-guard на мутации |
| 🎙️ **Диаризация AssemblyAI** | `speaker_labels`: `Speaker A` / `Speaker B` в транскрипте |
| 📹 **Аудио и видео** | Поддерживает mp3, mp4, ogg, wav, m4a и другие форматы, которые распознаёт Telegram |
| 📈 **Execution tracing** | Каждая обработка = сессия со шагами `download`, `transcribe`, `audit`, `notify` и метриками |
| 📋 **Security audit log** | Фиксируются login, config_update, provider_test, rbac_denied |
| 🛡️ **Дневной лимит** | 5 успешных обработок в сутки на обычного пользователя; `ADMIN_USER_ID` освобождён |
| 🖥️ **AIP Dark админка** | Единый хидер, sidebar, dashboard, консоли «Сессии» и «Аудит» |
| 🚀 **Docker Compose** | `docker compose up --build -d` поднимает web + PostgreSQL |

---

## 🛠️ 3. Стек

| Компонент | Технология |
|-----------|------------|
| Web API + Telegram | Python 3.12, FastAPI, Uvicorn, `python-telegram-bot` (polling) |
| STT + диаризация | AssemblyAI |
| LLM | OpenAI SDK + GigaChat OAuth HTTP-адаптер |
| БД | PostgreSQL 16, `psycopg` |
| Контейнеризация | Docker, Docker Compose |

---

## 🚀 4. Быстрый старт

```bash
git clone https://github.com/AlexLvGulyaev/meeting-audit-bot.git
cd meeting-audit-bot
cp .env.example .env      # заполнить секреты
```

Откройте `.env` и укажите минимум:

```dotenv
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ASSEMBLYAI_API_KEY=your_assemblyai_api_key
OPENAI_API_KEY=your_openai_api_key
ADMIN_TOKEN=your_admin_token
ADMIN_DEMO_TOKEN=demo-admin-session
ADMIN_USER_ID=123456789
DATABASE_URL=postgresql://meeting_audit:meeting_audit@postgres:5432/meeting_audit
```

Запуск:

```bash
docker compose up -d --build
```

Админка: `http://localhost:8000/admin` · Health: `http://localhost:8000/health`

> ⚠️ Без LLM-ключа система не сможет сгенерировать аудит; fallback на GigaChat работает, если задан `GIGACHAT_AUTH_KEY`.

Полная инструкция, smoke-тест и проверка демо-RBAC — в [🚀 `docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md).

---

## 🧪 5. Проверка работы

1. Найдите бота в Telegram и отправьте `/start`.
2. Отправьте аудиофайл (mp3, ogg) или видео.
3. В течение 30–120 секунд получите транскрипт и аудит по активному сценарию.
4. Откройте `/admin` → «Сессии», чтобы увидеть цепочку шагов и метрики.

Подробно — [🚀 DEPLOYMENT_GUIDE.md §4](docs/DEPLOYMENT_GUIDE.md) и [🎬 E2E_SCENARIOS.md](docs/E2E_SCENARIOS.md).

---

## 📊 6. Observability

Три контура наблюдаемости: stdout-логи (`docker compose logs`), execution-трейсы каждой обработки (`/admin/executions`) и журнал admin/security-событий (`/admin/audit`).

- **stdout** — `LOG_LEVEL`, структурированные логи загрузки, транскрибации, аудита.
- **Сессии** — master-detail: список обработок + шаги `download`, `transcribe`, `audit`, `notify` с таймингами, провайдером, моделью, токенами.
- **Аудит** — login, config_update, provider_test, rbac_denied с IP и metadata.

Подробно — [🏗️ ARCHITECTURE.md §6](docs/ARCHITECTURE.md) и [🎛️ OPERATOR_GUIDE.md §7](docs/OPERATOR_GUIDE.md).

---

## 📚 7. Документация

### Для заказчиков и менеджеров

| Документ | Описание |
|----------|----------|
| [💼 `docs/BUSINESS_VALUE.md`](docs/BUSINESS_VALUE.md) | Бизнес-проблема, решение, эффект, выгода |
| [🎬 `docs/SYSTEM_DEMO.md`](docs/SYSTEM_DEMO.md) | Скриншоты, диалоги, бизнес-сценарии |
| [🎬 `docs/E2E_SCENARIOS.md`](docs/E2E_SCENARIOS.md) | Сквозные сценарии (Telegram + `/admin`) |

### Для пользователей и операторов

| Документ | Описание |
|----------|----------|
| [📖 `docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | Как пользоваться ботом: квота, форматы, пример аудита |
| [🎛️ `docs/OPERATOR_GUIDE.md`](docs/OPERATOR_GUIDE.md) | Управление `/admin`: смена сценария, провайдера, observability |

### Для инженеров и интеграторов

| Документ | Описание |
|----------|----------|
| [🏗️ `docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Архитектура, C4-схемы, модель данных, потоки данных |
| [📂 `docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) | Полное файловое дерево репозитория с комментариями |
| [📋 `docs/SPEC.md`](docs/SPEC.md) | Продуктовая спецификация (замороженный baseline) |
| [📋 `docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) | Технический план и критерии готовности |
| [🔌 `docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | Контракты HTTP API |
| [📝 `docs/PROMPT_ARCHITECTURE.md`](docs/PROMPT_ARCHITECTURE.md) | Архитектура промпта (файлы, frontmatter, override) |
| [🤖 `docs/EXTERNAL_PROVIDERS.md`](docs/EXTERNAL_PROVIDERS.md) | Параметры провайдеров AssemblyAI, OpenAI, GigaChat |
| [🛡️ `docs/SECURITY_NOTES.md`](docs/SECURITY_NOTES.md) | Безопасность, демо-RBAC, дневной лимит |
| [🧪 `docs/TESTING.md`](docs/TESTING.md) | Стратегия тестирования (4 уровня проверки) |
| [🚀 `docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) | Развёртывание с нуля (Source of Truth) |
| [✅ `docs/DEPLOYMENT_VALIDATION_REPORT.md`](docs/DEPLOYMENT_VALIDATION_REPORT.md) | Отчёт воспроизводимости в чистом окружении |
| [📊 `docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) | Паспорт состояния проекта и roadmap |

---

## 📂 8. Структура проекта

```
.
├── docker-compose.yml          # web + PostgreSQL
├── .env.example                # Переменные окружения
├── Dockerfile                  # Python 3.12 + FastAPI + Telegram polling
├── app/                        # Исходный код
│   ├── main.py                 # FastAPI lifespan + Telegram polling
│   ├── core/                   # Config, runtime config, logging
│   ├── routes/                 # /health, /admin, /admin/api/*
│   ├── services/               # Telegram bot, media, transcription, audit,
│   │                           # providers, prompt_loader, execution, storage
│   ├── templates/              # Jinja2-шаблоны админки
│   └── utils/                  # Общие утилиты (strip_markdown_fence)
├── prompts/v1/                 # Базовые промпты (onboarding, sales-call, ...)
├── examples/                   # Примеры данных (транскрипт B2B-звонка)
├── storage/                    # Uploads, transcripts, audits, custom prompts,
│                               # runtime config.json (gitignored)
├── docs/                       # Публичная документация и скриншоты
└── scripts/                    # Вспомогательные скрипты (screenshots)
```

Полное файловое дерево с комментарием — в [📂 `docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md).

---

## 🧭 9. Минимальный путь по коду

Чтобы понять систему, достаточно прочитать эти файлы по порядку:

1. [`app/main.py`](app/main.py) — единая точка входа FastAPI + lifespan (инициализация БД, runtime-config, запуск Telegram polling).
2. [`app/services/telegram_bot.py`](app/services/telegram_bot.py) — обработка входящих медиа, execution tracing, сохранение аудита.
3. [`app/services/media.py`](app/services/media.py) — скачивание файлов из Telegram и извлечение метаданных.
4. [`app/services/transcription.py`](app/services/transcription.py) — AssemblyAI upload/poll с `speaker_labels`.
5. [`app/services/audit.py`](app/services/audit.py) — LLM-анализ транскрипта, цепочка active → fallback.
6. [`app/routes/admin.py`](app/routes/admin.py) — веб-админка и JSON API.

> 📌 Продакшн-расширения (мультипровайдерность, runtime-config, execution-трейсы, аудит, демо-RBAC, дневной лимит) изолированы в модулях `app/services/` и `app/core/`. Полная карта — в [📂 `docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md), архитектура — в [🏗️ `docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## ✅ 10. Статус проекта

✅ **Портфельный актив.** Реализован, прошёл Deployment Validation, опубликован как публичный репозиторий с живым демо.

Текущая версия — **v1.0**: Telegram-бот с диаризацией, мультипровайдерный LLM-аудит, веб-админка AIP Dark, runtime-конфиг, три контура observability, демо-RBAC и дневной лимит.

Полная история статусов и roadmap — в [📊 `docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md).

---

MIT. Проект развит на основе исходного репозитория [`MrGAN12009/stt_analyse`](https://github.com/MrGAN12009/stt_analyse).
