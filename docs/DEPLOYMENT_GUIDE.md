# 🚀 DEPLOYMENT_GUIDE.md — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Дата:** 2026-08-16
**Статус:** Source of Truth воспроизводимости развёртывания.

> 📌 **SOT-дисциплина:** этот документ — единственный источник истины процесса развёртывания. Критерий качества — **успешное развёртывание по инструкции**, а не качество текста. Если после полного выполнения система не работоспособна — документ не актуален. Валидация — запуском в чистом окружении (см. [✅ DEPLOYMENT_VALIDATION_REPORT.md](DEPLOYMENT_VALIDATION_REPORT.md)).

---

## 🧰 1. Требования к окружению

| Требование | Версия / параметр | Проверка |
|------------|-------------------|----------|
| Docker Engine | 24+ | `docker --version` |
| Docker Compose | v2 (plugin) | `docker compose version` |
| PostgreSQL | 16 (образ `postgres:16-alpine` в compose) | поднимается `docker compose up` — отдельная установка не требуется |
| ОС | Linux / macOS / Windows+WSL2 | — |
| RAM | ≥ 1 ГБ свободной | — |
| Порты | `8000` внутри контейнера `web` | публикуется через reverse proxy |
| Сеть | `n8n_default` (external) для интеграции с Traefik/Nginx | `docker network ls` |

> ℹ️ Для standalone-развёртывания без существующего reverse proxy см. [🧩 6. Альтернативные сценарии развёртывания](#🧩-6-альтернативные-сценарии-развёртывания).

---

## 🔧 2. Переменные окружения

### 🔧 2.1. Получение проекта

```bash
git clone https://github.com/AlexLvGulyaev/meeting-audit-bot.git
cd meeting-audit-bot
```

### 🔧 2.2. Файл `.env`

```bash
cp .env.example .env
```

Откройте `.env` и заполните **обязательные** переменные:

| Переменная | Обязательна? | Назначение |
|------------|--------------|-----------|
| `TELEGRAM_BOT_TOKEN` | да | Токен бота от @BotFather |
| `ASSEMBLYAI_API_KEY` | да | Ключ AssemblyAI для транскрибации |
| `OPENAI_API_KEY` | один из провайдеров | OpenAI / OpenAI-compatible API |
| `GIGACHAT_AUTH_KEY` | один из провайдеров | Authorization key GigaChat (OAuth-обмен) |
| `GIGACHAT_BASE_URL` | нет | Базовый URL GigaChat API (по умолчанию `https://gigachat.devices.sberbank.ru/api/v1`) |
| `GIGACHAT_TOKEN_URL` | нет | URL OAuth-обмена GigaChat (по умолчанию `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`) |
| `GIGACHAT_SCOPE` | нет | OAuth-scope GigaChat (по умолчанию `GIGACHAT_API_PERS`) |
| `GIGACHAT_CA_BUNDLE` | нет | Путь к CA-bundle Минцифры; пусто — проверка сертификата отключена (dev/demo); на production укажите путь |
| `DATABASE_URL` | да | PostgreSQL connection string. Внутри compose: `postgresql://meeting_audit:meeting_audit@postgres:5432/meeting_audit` |
| `POSTGRES_USER` | нет | Пользователь БД (по умолчанию `meeting_audit`) |
| `POSTGRES_PASSWORD` | нет | Пароль БД (по умолчанию `meeting_audit`) |
| `POSTGRES_DB` | нет | Имя БД (по умолчанию `meeting_audit`) |
| `ADMIN_TOKEN` | да | Полный доступ к `/admin` |
| `ADMIN_DEMO_TOKEN` | да | Read-only демо-доступ к `/admin` |
| `ADMIN_USER_ID` | нет | Telegram user id, exempt от дневного лимита загрузок |
| `LOG_LEVEL` | нет | Уровень логирования (`DEBUG`/`INFO`/`WARNING`, по умолчанию `INFO`) |
| `APP_HOST` | нет | Хост uvicorn (по умолчанию `0.0.0.0`) |
| `APP_PORT` | нет | Порт uvicorn внутри контейнера (по умолчанию `8000`) |

> ⚠️ **Минимум для запуска:** `TELEGRAM_BOT_TOKEN`, `ASSEMBLYAI_API_KEY`, `DATABASE_URL`, `ADMIN_TOKEN`, `ADMIN_DEMO_TOKEN`. Без LLM-ключей аудит уйдёт в статический fallback — бот ответит, но без нейросети.

> ⚠️ **Не коммитьте `.env`.** Он в `.gitignore`. В репозитории — только `.env.example` с placeholder'ами `your_*`.

---

## ▶️ 3. Запуск

### ▶️ 3.1. Подготовка сети

`docker-compose.yml` использует внешнюю сеть `n8n_default` для интеграции с Traefik/Nginx. Убедитесь, что сеть существует, или создайте её:

```bash
docker network create n8n_default
```

Если у вас уже есть сеть с другим именем — отредактируйте `docker-compose.yml` или используйте override-файл (см. [🧩 6.1](#🧩-61-локальный-запуск-без-traefik)).

### ▶️ 3.2. Сборка и старт

```bash
docker compose up -d --build
```

Поднимаются два сервиса: `postgres` и `web`. `web` ждёт готовности БД (`condition: service_healthy`). Внутри одного контейнера `web` работают одновременно FastAPI (uvicorn) и Telegram polling (`python-telegram-bot`).

### ▶️ 3.3. Проверка состояния сервисов

```bash
docker compose ps
```

Ожидаемый результат: оба сервиса `Up (healthy)`.

```bash
docker compose logs -f web
```

В логах должны появиться:
- `Storage directories ready`
- `Runtime config loaded/seeded`
- `Database tables initialized`
- `Telegram polling started`
- `Application startup complete`

---

## 🌐 4. Настройка доступа извне

### 🌐 4.1. Production: reverse proxy + HTTPS

Контейнер `web` не публикует порт `8000` на хост напрямую — он ожидает reverse proxy в той же сети `n8n_default`. Пример настройки Traefik:

```yaml
http:
  routers:
    meeting-audit-bot:
      rule: "Host(`meeting-audit-bot.alex-n8n.site`)"
      service: meeting-audit-bot
      tls:
        certresolver: letsencrypt
  services:
    meeting-audit-bot:
      loadBalancer:
        servers:
          - url: "http://meeting-audit-bot-web:8000"
```

> 📌 Адрес и resolver зависят от вашей инфраструктуры. Валидация проходила на домене `meeting-audit-bot.alex-n8n.site` с Traefik + Let's Encrypt.

### 🌐 4.2. Проверка health

```bash
curl https://your-domain/health
# → {"status":"ok","service":"meeting-audit-bot","timestamp":"..."}

curl https://your-domain/health/db
# → {"status":"ok","database":"ok"}
```

---

## 🤖 5. Проверка Telegram-бота

1. Найдите бота в Telegram по имени, заданному в @BotFather.
2. Отправьте `/start` — бот пришлёт приветствие и список сценариев аудита.
3. Отправьте видео или mp3-файл.
4. Дождитесь сообщения «Анализ готов. Отправляю результат…» и финального аудита.

> 📌 Для теста без расхода токенов можно использовать короткий голосовой файл длительностью < 1 минуты.

---

## 🧩 6. Альтернативные сценарии развёртывания

### 🧩 6.1. Локальный запуск без Traefik

Если нет готового reverse proxy, опубликуйте порт `8000` на хосте. Создайте `docker-compose.override.yml`:

```yaml
services:
  web:
    ports:
      - "8000:8000"
    networks:
      - default

  postgres:
    networks:
      - default

networks:
  default:
    driver: bridge
  n8n_default:
    external: false
```

Затем:

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

> ⚠️ Этот сценарий подходит для локальной разработки и тестов. Для публичного демо используйте HTTPS + reverse proxy.

### 🧩 6.2. Запуск без LLM-ключей (fallback-режим)

Если не задать `OPENAI_API_KEY` и `GIGACHAT_AUTH_KEY`, бот продолжит работать, но аудит будет возвращать статический fallback-ответ с объяснением ошибки. Это полезно для проверки конвейера без расхода токенов.

---

## 🔄 7. Обновление

```bash
git pull
docker compose up --build -d
```

Runtime-конфиг (`storage/config.json`) и custom-промпты (`storage/prompts/`) живут в Docker volume `meeting_audit_storage`, поэтому пересборка образа их не затрёт.

---

## 🧹 8. Очистка

```bash
# Остановить сервисы, сохранив данные
docker compose down

# Удалить всё, включая volumes с PostgreSQL и загруженными файлами
docker compose down -v
```

> ⚠️ Внимание: `-v` удалит volumes `postgres_data` и `meeting_audit_storage` — все аудиты, транскрипты, загруженные файлы и runtime-конфиг будут безвозвратно потеряны.

---

## 📚 Связанные документы

- [✅ `DEPLOYMENT_VALIDATION_REPORT.md`](DEPLOYMENT_VALIDATION_REPORT.md) — отчёт о воспроизводимости.
- [🛡️ `SECURITY_NOTES.md`](SECURITY_NOTES.md) — секреты, RBAC, лимиты.
- [🧪 `TESTING.md`](TESTING.md) — как проверить работоспособность.
- [🎬 `E2E_SCENARIOS.md`](E2E_SCENARIOS.md) — сквозные сценарии.
