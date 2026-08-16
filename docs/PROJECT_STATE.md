# 📊 PROJECT_STATE.md — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Дата создания:** 2026-08-15
**Последнее обновление:** 2026-08-16
**Статус:** ✅ Портфельный актив. Реализован, прошёл Deployment Validation, опубликован как публичный репозиторий с живым демо.

---

## 🎯 1. Project Summary

Telegram-бот для аудита встреч, звонков и уроков. Пользователь отправляет аудио или видео в Telegram; бот транскрибирует речь через AssemblyAI с разделением по спикерам (`speaker_labels`) и проводит структурированный аудит диалога по выбираемому сценарию через LLM (OpenAI / GigaChat). Результат возвращается в Telegram, а администратор управляет сценариями, провайдерами и наблюдает за обработками через веб-панель `/admin`.

**Ключевые параметры:**

| Параметр | Значение |
|----------|----------|
| UI | Telegram Bot (polling) |
| Web API | FastAPI + Uvicorn |
| STT | AssemblyAI (диаризация `speaker_labels`) |
| LLM | OpenAI / GigaChat (Chat Completions) + fallback |
| БД | PostgreSQL 16 |
| Контейнеризация | Docker Compose (`web` + `postgres`) |
| Админка | AIP Dark UI, cookie-based demo-RBAC |
| Runtime-config | `storage/config.json` (gitignored, seeded из `app/core/default_config.py`) |
| Промпты | `prompts/v1/*.md` + custom override `storage/prompts/*.md` с `title:` frontmatter |
| Observability | stdout-логи + execution sessions/steps + security audit log |

---

## 📊 2. Current Status

**Стадия:** ✅ Портфельный актив (публичное демо). Реализованы: Telegram-бот, AssemblyAI STT с диаризацией, мультипровайдерный LLM-аудит, веб-админка `/admin` с runtime-конфигом, execution tracing, security audit log, демо-RBAC, дневной лимит обработок, Deployment Validation пройдена, публичный репозиторий опубликован, живое демо развёрнуто.

### ✅ Завершённые задачи

- [x] Реализация Telegram-бота с приёмом аудио/видео и прогресс-сообщениями.
- [x] Интеграция AssemblyAI: upload, poll, `speaker_labels`.
- [x] Multi-provider LLM (`LLMProvider`): OpenAI + GigaChat, active → fallback.
- [x] Runtime-конфиг `storage/config.json` для активного провайдера, модели, промпта.
- [x] Prompt registry с базовыми промптами `prompts/v1/*.md` и custom override `storage/prompts/*.md`.
- [x] Human-readable названия промптов из frontmatter `title:`.
- [x] Веб-админка AIP Dark: dashboard, смена промпта, тест провайдера, список сессий, аудит лог.
- [x] Cookie-based demo-RBAC: `ADMIN_TOKEN` и `ADMIN_DEMO_TOKEN`, backend-guard на мутациях.
- [x] Execution tracing: `execution_sessions` + `execution_steps` (download, transcribe, audit, notify).
- [x] Security audit log: `admin_audit_log` (login, config_update, provider_test, rbac_denied).
- [x] Дневной лимит: 5 успешных обработок на пользователя, `ADMIN_USER_ID` освобождён.
- [x] Централизованная очистка markdown-обёртки `strip_markdown_fence` для Telegram и админки.
- [x] Реалистичный двухголосый B2B-диалог для E2E (`examples/sample-b2b-sales-call-retail.md`).
- [x] E2E-сценарии и скриншоты (14 штук), каталог `docs/MEDIA_INDEX.md`.
- [x] Deployment Validation в чистом окружении.
- [x] Публикация публичного репозитория и живого демо.

### 🟡 Возможное развитие (за границей v1.0)

- Добавление webhook-режима Telegram вместо polling для продакшн-нагрузок.
- Версионирование промптов и rollback изменений.
- Распознавание длительности видео/аудио и отдельная квота по длительности.
- Поддержка дополнительных LLM-провайдеров (YandexGPT, локальные модели).
- Автоматические pytest-тесты на детерминированное ядро.

---

## 🛒 3. Market Validation

- Проект создан как портфельный кейс лаборатории AI Automation Portfolio Lab — демонстрация паттерна «STT + LLM-аудит + Telegram UI + web-админка».
- Паттерн универсален: аудит sales-звонков, онбординг-встреч, онлайн-уроков, переписки с клиентами.
- Реалистичная область — собственные записи встреч и звонков компании, не нарушающие правил обработки данных третьих лиц.

---

## 💰 4. Commercial Assessment

**Потенциал:**

- Готовый шаблон «аудит разговора по чек-листу» — переиспользуемая заготовка для HR, sales, обучения.
- Единый конвейер STT → LLM → UI → observability снижает трудозатраты на ручной разбор.
- Multi-provider и fallback снижают риск зависимости от одного LLM.

**Риски:**

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|--------|-----------|
| Качество аудита зависит от промпта/модели | Средняя | Среднее | Промпты в файлах, fallback, runtime-переключение модели |
| Стоимость STT + LLM на больших объёмах | Средняя | Среднее | Дневной лимит, выбор модели, кэширование |
| Диаризация AssemblyAI путает спикеров | Низкая | Среднее | Явные маркеры спикеров в промпте; fallback на текст без деления |
| Публичный Telegram-бот = абуз лимитов | Высокое для демо | Среднее | ✅ Дневной лимит 5/сутки; exempt `ADMIN_USER_ID` |
| GigaChat TLS (`ssl.CERT_NONE` dev) | Низкое | Низкое | `GIGACHAT_CA_BUNDLE` на production |

---

## 🔧 5. Key Technology Areas

| Область | Компетенция | Статус |
|---------|-------------|--------|
| FastAPI + Telegram polling | Единый процесс FastAPI + `python-telegram-bot` polling | ✅ |
| AssemblyAI STT | Upload/poll, `speaker_labels`, русский язык | ✅ |
| Multi-provider LLM | OpenAI + GigaChat, active/fallback | ✅ |
| Runtime-config | `storage/config.json`, hot-reload на чтении | ✅ |
| Prompt registry | `title:` frontmatter, base + custom override | ✅ |
| PostgreSQL | `video_audits`, `execution_sessions/steps`, `admin_audit_log` | ✅ |
| Demo-RBAC | Cookie-based admin/demo, backend guard | ✅ |
| Observability | stdout + execution tracing + audit log | ✅ |
| AIP Dark UI | Jinja2, sidebar, dashboard | ✅ |
| Docker Compose | `web` + `postgres` с healthcheck | ✅ |

---

## ✅ 6. Decision

**Принято:** продолжить как публичный портфолио-кейс — доработать учебный проект урока PEcb10 до самодостоятельного публичного репозитория с инженерной документацией и Deployment Validation.

**Реализованные решения:**

- Сохранён учебный сценарий аудита онбординга; добавлены дополнительные сценарии (`sales-call`, `online-lesson`, `client-chat`).
- Вынесена prompt registry с `title:` frontmatter и custom override.
- Реализован runtime-конфиг (`storage/config.json`) для смены провайдера/модели/промпта без рестарта.
- Multi-provider LLM: OpenAI + GigaChat через единую абстракцию `LLMProvider`.
- Execution tracing и security audit log в PostgreSQL.
- Demo-RBAC в админке: полный и read-only доступ.
- Дневной лимит обработок в Telegram.
- AIP Dark UI для `/admin`.
- Docker Compose + DEPLOYMENT_GUIDE + Deployment Validation.

---

## 🚀 7. Next Steps

### Завершённые этапы

1. ~~Реализовать Telegram-бот + AssemblyAI STT + LLM-аудит~~.
2. ~~Добавить `/admin` dashboard, config, executions, audit~~.
3. ~~Реализовать multi-provider и runtime-config~~.
4. ~~Добавить demo-RBAC и дневной лимит~~.
5. ~~Подготовить E2E-сценарии и скриншоты~~.
6. ~~Пройти Deployment Validation~~.
7. ~~Опубликовать репозиторий и живое демо~~.
8. ~~Подготовить полный пакет APL-документации~~.
9. ~~Подготовить файлы ДЗ PEcb10~~.

### Возможное развитие (v1.1+)

- Webhook-режим Telegram.
- Версионирование промптов.
- Автоматические unit/smoke-тесты.
- Поддержка дополнительных LLM-провайдеров.

---

## 🔗 8. Dependencies

| Зависимость | Описание | Влияние |
|-------------|----------|---------|
| Telegram Bot API | Основной UI | Блокирует входящие файлы |
| AssemblyAI | STT + диаризация | Блокирует транскрибацию |
| LLM-провайдер | Аудит диалога | Fallback на другой провайдер |
| PostgreSQL | Хранение сессий, аудитов, audit log | Блокирует web и tracing |
| VPS / Docker Host | Публичный деплой | Блокирует живое демо |

---

## 📜 9. Status History

| Дата | Статус | Примечание |
|------|--------|----------|
| 2026-08-15 | Старт кейса | Проектирование архитектуры на основе урока PEcb10 |
| 2026-08-15 | Реализация MVP | Telegram-бот, AssemblyAI, OpenAI аудит, PostgreSQL |
| 2026-08-15 | Админка | FastAPI `/admin`, dashboard, executions, audit |
| 2026-08-15 | Multi-provider | OpenAI + GigaChat, runtime-config, prompt registry |
| 2026-08-15 | Observability | Execution tracing + security audit log |
| 2026-08-15 | Deployment Validation | Публичный деплой и E2E-сценарии |
| 2026-08-16 | UI/UX доработки | AIP Dark, human-readable сценарии, markdown-очистка, demo-RBAC, лимит |
| 2026-08-16 | E2E и скриншоты | 14 сценариев, реалистичный B2B-аудио, MEDIA_INDEX |
| 2026-08-16 | Документация APL | README, PROJECT_STATE, SPEC, ARCHITECTURE, DEPLOYMENT_GUIDE и др. |
| 2026-08-16 | PEcb10 ДЗ | pecb10-homework.md + cover-letter |

---

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта.
- [💼 `docs/BUSINESS_VALUE.md`](BUSINESS_VALUE.md) — бизнес-ценность и экономика.
- [🎬 `docs/SYSTEM_DEMO.md`](SYSTEM_DEMO.md) — скриншот-тур и демо-сценарии.
- [🎬 `docs/E2E_SCENARIOS.md`](E2E_SCENARIOS.md) — сквозные сценарии проверки.
- [📖 `docs/USER_GUIDE.md`](USER_GUIDE.md) — руководство пользователя Telegram-бота.
- [🎛️ `docs/OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) — управление `/admin`.
- [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md) — архитектура и путь данных.
- [📂 `docs/PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) — файловое дерево репозитория.
- [📋 `docs/SPEC.md`](SPEC.md) — функциональная спецификация.
- [📋 `docs/IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — технический план.
- [🔌 `docs/API_CONTRACT.md`](API_CONTRACT.md) — контракты HTTP API.
- [📝 `docs/PROMPT_ARCHITECTURE.md`](PROMPT_ARCHITECTURE.md) — архитектура промптов.
- [🤖 `docs/EXTERNAL_PROVIDERS.md`](EXTERNAL_PROVIDERS.md) — параметры внешних провайдеров.
- [🛡️ `docs/SECURITY_NOTES.md`](SECURITY_NOTES.md) — безопасность и RBAC.
- [🧪 `docs/TESTING.md`](TESTING.md) — стратегия тестирования.
- [🚀 `docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание с нуля.
- [✅ `docs/DEPLOYMENT_VALIDATION_REPORT.md`](DEPLOYMENT_VALIDATION_REPORT.md) — отчёт воспроизводимости.
