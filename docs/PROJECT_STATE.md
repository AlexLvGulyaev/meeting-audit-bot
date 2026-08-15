# 📊 PROJECT_STATE — Meeting Audit Bot

## Project Summary

Кейс `meeting-audit-bot` — AI-ассистент для аудита аудио- и видео-встреч. Бот принимает файл в Telegram, транскрибирует через AssemblyAI (с разделением по говорящим), проводит аудит диалога по файлу-критериям через LLM и сохраняет результаты в PostgreSQL. Проект развивается на основе урока PEcb10 модуля «Карьера в бизнесе, часть 2».

## Current Status

**Стадия:** разработка завершена, готовится Deployment Validation и публикация.  
Реализованы: FastAPI + Telegram polling, AssemblyAI diarization, multi-provider LLM (OpenAI + GigaChat) с fallback, prompt registry (base + custom), веб-админка с demo-RBAC, execution tracing, security audit log, PostgreSQL-хранилище, Docker Compose, README и DEPLOYMENT_GUIDE.

## Market Validation

- Урок PEcb10 входит в программу обучения промпт-инжинирингу; кейсы 8 и 9 (`ai-data-assistant`, `review-auto-responder`) уже упакованы в портфель.
- Паттерн «запись → транскрипция → AI-аудит» востребован в HR, sales-coaching, customer-success и образовании.
- Прямые заказы на аудит звонков/встреч уже есть в направлении лаборатории «Анализ звонков».

## Commercial Assessment

**Потенциал:** средний. MVP демонстрирует универсальный паттерн; коммерциализация требует интеграции с Zoom/Meet API, CRM и ролевой RBAC.  
**Риски:** зависимость от AssemblyAI (STT) и стоимость LLM-токенов на длинных транскриптах.  
**Целевая цена MVP:** $300–600 за развёртывание + ключи.

## Key Technology Areas

| Компетенция | Уровень | Примечание |
|-------------|---------|------------|
| FastAPI + Telegram polling | есть | использовались в `review-auto-responder` |
| PostgreSQL + psycopg2 | есть | использовался в исходнике |
| AssemblyAI API | нужно верифицировать | diarization, upload/poll |
| Multi-provider LLM (OpenAI/GigaChat) | есть | адаптеры из `review-auto-responder` |
| Runtime-конфиг `/admin` | есть | паттерн из `ai-data-assistant` |
| Cookie-based demo-RBAC | есть | паттерн из `review-auto-responder` |
| Execution tracing + audit-log | есть | паттерн из `review-auto-responder` / `ai-curator` |
| Docker Compose + Deployment Validation | есть | стандарт APL |

## Decision

Развивать кейс до портфельного актива:
- модульная архитектура;
- FastAPI + Telegram polling;
- `/admin` с cookie-based auth и demo-RBAC;
- `/admin/executions` и `/admin/audit`;
- multi-provider LLM (OpenAI + GigaChat) + fallback;
- prompt-as-file с реестром промптов (base + custom);
- файловое хранилище `storage/uploads/`, `storage/transcripts/`, `storage/audits/`;
- execution tracing и security audit-log в PostgreSQL;
- structured JSON output от LLM + fallback-парсер;
- Deployment Validation и публикация в GitHub.

## Next Steps

1. Разбить `bot.py` на модули (`app/main.py`, `app/services/...`, `app/core/...`, `app/routes/...`).
2. Добавить FastAPI-приложение с `/health`, `/admin`, `/admin/executions`, `/admin/audit`.
3. Вынести промпт в `prompts/v1/onboarding.md`.
4. Реализовать multi-provider LLM (OpenAI + GigaChat) + fallback + JSON output.
5. Добавить PromptRegistry (base + custom) и редактор в `/admin`.
6. Добавить execution tracing и security audit-log.
7. Сохранять исходные файлы, транскрипты и аудиты в `storage/`.
8. Добавить Telegram-квоты и demo-RBAC.
9. Подготовить промпты для ДЗ (`sales-call`, `online-lesson`, `client-chat`) и синтетические аудиофайлы.
10. Подготовить `DEPLOYMENT_GUIDE.md` и пройти Deployment Validation.
11. Опубликовать в `https://github.com/AlexLvGulyaev/meeting-audit-bot` и подготовить отчёт по ДЗ.

## Status History

| Дата | Статус | Что произошло |
|------|--------|---------------|
| 2026-08-15 | Идея → Проектирование | Создан кейс, скопирован legacy, написаны ARCHITECTURE, SPEC, IMPLEMENTATION_PLAN |
| 2026-08-15 | Проектирование → Разработка | Реализованы все модули приложения, admin UI, Docker Compose, README, DEPLOYMENT_GUIDE |
