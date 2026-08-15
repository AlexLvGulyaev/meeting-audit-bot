# DEPLOYMENT_GUIDE — Meeting Audit Bot

## Цель

Воспроизводимое получение полностью работоспособного экземпляра Meeting Audit Bot.

## Требования

- Linux сервер с Docker 24+ и Docker Compose v2.
- Домен и Traefik/Nginx для HTTPS (reverse proxy).
- Аккаунты и ключи:
  - Telegram Bot Token (от @BotFather).
  - AssemblyAI API Key.
  - OpenAI API Key (или OpenAI-совместимый).
  - GigaChat Authorization Key (опционально, для fallback).

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

```dotenv
TELEGRAM_BOT_TOKEN=...
ASSEMBLYAI_API_KEY=...
OPENAI_API_KEY=...
GIGACHAT_AUTH_KEY=...
GIGACHAT_BASE_URL=https://gigachat.devices.sberbank.ru/api/v1
GIGACHAT_TOKEN_URL=https://ngw.devices.sberbank.ru:9443/api/v2/oauth
GIGACHAT_SCOPE=GIGACHAT_API_PERS
DATABASE_URL=postgresql://meeting_audit:meeting_audit@db:5432/meeting_audit
ADMIN_TOKEN=...
ADMIN_DEMO_TOKEN=demo-admin-session
ADMIN_USER_ID=123456789
LOG_LEVEL=INFO
```

## Запуск

```bash
docker compose up --build -d
```

## Проверка

1. Health endpoint:

```bash
curl https://your-domain/health
```

2. Админка:

```bash
open https://your-domain/admin
# Войти в демо-режиме
```

3. Telegram:

- Найдите бота по имени.
- Отправьте видео или mp3.
- Дождитесь транскрипта и аудита.

## Обновление

```bash
git pull
docker compose up --build -d
```

## Очистка

```bash
docker compose down -v
```

> Внимание: `-v` удалит volumes с PostgreSQL-данными и загруженными файлами.
