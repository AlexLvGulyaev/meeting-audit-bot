# 📂 PROJECT_STRUCTURE.md — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Дата:** 2026-08-16
**Статус:** Engineering Layer — карта репозитория для инженеров и интеграторов.

Полное файловое дерево публичного репозитория с комментарием на каждый файл.
Краткая сводка для README — в [🏠 `README.md` §8](../README.md#-8-структура-проекта).

---

## 📁 Дерево репозитория

```text
meeting-audit-bot/
├── README.md                            # Точка входа в проект
├── .env.example                         # Шаблон переменных окружения (заполнить → .env)
├── .gitignore
├── Dockerfile                           # python:3.12-slim, uvicorn
├── docker-compose.yml                   # Postgres + web (FastAPI + Telegram polling)
├── requirements.txt                     # Python-зависимости
├── docs/                                # Публичная документация
│   ├── API_CONTRACT.md                  # Контракты HTTP API
│   ├── ARCHITECTURE.md                  # Архитектура, C4-схемы, модель данных, потоки
│   ├── BUSINESS_VALUE.md                # Бизнес-ценность, эффект, выгода
│   ├── DEPLOYMENT_GUIDE.md              # Развёртывание с нуля (Source of Truth)
│   ├── DEPLOYMENT_VALIDATION_REPORT.md  # Отчёт воспроизводимости
│   ├── E2E_SCENARIOS.md                 # Сквозные сценарии (Telegram + /admin)
│   ├── IMPLEMENTATION_PLAN.md           # Технический план и критерии готовности
│   ├── MEDIA_INDEX.md                   # Каталог медиаматериалов
│   ├── OPERATOR_GUIDE.md                # Руководство оператора /admin
│   ├── PROJECT_STATE.md                 # Паспорт состояния проекта
│   ├── PROJECT_STRUCTURE.md             # Этот документ
│   ├── PROMPT_ARCHITECTURE.md           # Архитектура промптов и registry
│   ├── SECURITY_NOTES.md                # Безопасность, RBAC, лимиты
│   ├── SPEC.md                          # Продуктовая спецификация
│   ├── SYSTEM_DEMO.md                   # Скриншот-тур и демо-сценарии
│   ├── TESTING.md                       # Стратегия тестирования
│   ├── USER_GUIDE.md                    # Руководство пользователя Telegram-бота
│   └── screenshots/                     # Иллюстрации системы
├── app/                                 # Приложение FastAPI + Telegram-бот
│   ├── main.py                          # Lifespan: storage paths, seed config, init tables, Telegram polling
│   ├── core/
│   │   ├── config.py                    # Pydantic-dataclass Settings (env vars, пути)
│   │   ├── default_config.py            # DEFAULT_CONFIG для runtime
│   │   ├── logging_config.py            # dictConfig для stdout-логов
│   │   └── runtime_config.py            # RuntimeConfig: load/save config.json с deep merge + migration
│   ├── routes/
│   │   ├── admin.py                     # /admin: демо-RBAC, dashboard, config save, test provider, audit
│   │   └── health.py                    # /health и /health/db
│   ├── services/
│   │   ├── audit.py                     # LLM-аудит транскрипта, fallback-цепочка
│   │   ├── audit_log.py                 # Запись security audit log
│   │   ├── execution.py                 # ExecutionService: сессии и шаги
│   │   ├── media.py                     # Извлечение metadata из Telegram media + скачивание файла
│   │   ├── prompt_loader.py             # Registry промптов: base + custom override, title frontmatter
│   │   ├── storage.py                   # PostgreSQL: video_audits, execution_sessions, execution_steps, admin_audit_log
│   │   ├── telegram_bot.py              # Handlers /start, /help, media, daily limit, chunking
│   │   ├── transcription.py             # AssemblyAI STT с speaker_labels
│   │   └── providers/
│   │       ├── base.py                  # Абстракция LLMProvider
│   │       ├── factory.py               # get_provider: openai / gigachat
│   │       ├── openai_provider.py       # OpenAI Chat Completions
│   │       ├── gigachat_provider.py     # GigaChat async-обёртка
│   │       └── gigachat_adapter.py      # GigaChat OAuth + HTTP
│   ├── templates/
│   │   ├── admin_base.html              # Базовый шаблон AIP Dark
│   │   ├── admin/
│   │   │   ├── admin.html               # Dashboard /admin
│   │   │   ├── audit.html               # Security audit log
│   │   │   ├── executions.html          # Список execution-сессий
│   │   │   └── login.html               # Страница входа
│   │   └── ...
│   └── utils/
│       └── text.py                      # strip_markdown_fence и текстовые утилиты
├── prompts/
│   └── v1/                              # Базовые (вшитые) промпты
│       ├── client-chat.md               # Аудит клиентского чата
│       ├── onboarding.md                # Аудит онбординг-встречи
│       ├── online-lesson.md             # Аудит онлайн-урока
│       └── sales-call.md                # Аудит звонка/продажи
├── examples/
│   └── sample-b2b-sales-call-retail.md  # Пример транскрипта для отладки промпта
└── scripts/
    └── take_screenshots.py              # Скрипт автоматического создания скриншотов админки
```

> ℹ️ `__init__.py` опущены для краткости. Секреты (`TELEGRAM_BOT_TOKEN`,
> `ASSEMBLYAI_API_KEY`, `OPENAI_API_KEY`, `GIGACHAT_AUTH_KEY`, `ADMIN_TOKEN`,
> `ADMIN_DEMO_TOKEN`) — только в `.env` (в `.gitignore`), в репозитории их нет.
> `storage/config.json` и `storage/prompts/*.md` живут в Docker volume
> `meeting_audit_storage` (не в дереве репозитория) — см.
> [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта.
- [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md) — архитектура, C4-схемы, модель данных.
- [📋 `docs/IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — технический план и состав компонентов.
- [🔌 `docs/API_CONTRACT.md`](API_CONTRACT.md) — контракты HTTP API.
