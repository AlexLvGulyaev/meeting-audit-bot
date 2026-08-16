# 🏗️ ARCHITECTURE.md — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Дата:** 2026-08-16
**Статус:** Engineering Layer — архитектура и путь данных.

---

## 🎯 1. Архитектурные принципы

| Принцип | Суть |
|---------|------|
| **Telegram как основной UI** | Пользователь отправляет файл в привычный мессенджер; бот отвечает аудитом.
| **FastAPI + polling в одном процессе** | Веб-админка и Telegram-бот живут в одном контейнере, что упрощает деплой кейса.
| **Секреты отдельно от runtime** | API-ключи — `.env`; операторские параметры и промпты — `storage/config.json` и `storage/prompts/*.md` (shared volume). Ключи никогда не попадают в `/admin`/браузер/config.json.
| **Fallback-by-design** | active LLM → fallback LLM → статический fallback. Система сообщает об ошибке, но не падает.
| **Observability — три контура** | stdout-логи · execution-трейсы (БД) · журнал аудита (БД).
| **Файлы как SOT для промптов** | Базовые промпты в `prompts/v1/*.md`; custom override в `storage/prompts/*.md`. `title:` frontmatter — human-readable название.

---

## 🌐 2. Context Diagram (C4 Level 1)

```mermaid
flowchart TB
    subgraph "Внешние пользователи"
        User[Пользователь Telegram]
        Admin[Администратор / Демо-наблюдатель]
    end

    MAB["Meeting Audit Bot<br/>Telegram + FastAPI + STT + LLM"]

    subgraph "Внешние системы"
        TG[Telegram Bot API]
        STT[AssemblyAI]
        LLM[LLM-провайдер<br/>OpenAI / GigaChat]
    end

    User -->|"отправляет аудио/видео"| TG
    TG -->|" webhook / polling"| MAB
    MAB -->|"скачать файл"| TG
    MAB -->|"upload + poll transcript"| STT
    MAB -->|"Chat Completions — аудит"| LLM
    MAB -->|"отправить аудит"| TG
    Admin -->|"HTTP — /admin"| MAB
```

- **Пользователь Telegram** — отправляет файл и получает аудит.
- **Администратор** — входит в `/admin`, меняет сценарий/провайдера, смотрит сессии и аудит.
- **Telegram Bot API** — входящие и исходящие сообщения.
- **AssemblyAI** — STT + диаризация.
- **LLM** — OpenAI или GigaChat через единую абстракцию.

---

## 📦 3. Container Diagram (C4 Level 2)

```mermaid
flowchart TB
    subgraph Web["web — FastAPI + Telegram polling"]
        Routes["Routes<br/>/health, /admin/*, /admin/api/*"]
        AdminUI["Admin UI<br/>Jinja2 templates"]
        TelegramBot["TelegramBot<br/>handlers"]
    end

    subgraph Services["Services"]
        Media["MediaService<br/>download"]
        Transcription["TranscriptionService<br/>AssemblyAI"]
        Audit["AuditService<br/>LLM analyze"]
        Providers["Providers<br/>OpenAI / GigaChat"]
        PromptLoader["PromptLoader<br/>base + custom"]
        Execution["ExecutionService<br/>sessions/steps"]
        AuditLog["AuditLogService<br/>security log"]
    end

    DB[("PostgreSQL 16")]
    Storage[("storage/<br/>uploads · transcripts · audits · prompts · config.json")]
    TG["Telegram"]
    STT["AssemblyAI"]
    LLM["LLM-провайдер"]

    TelegramBot -->|"получил файл"| Media
    Media --> Storage
    TelegramBot --> Execution
    Execution --> DB
    TelegramBot --> Transcription
    Transcription -->|"upload/poll"| STT
    Transcription --> Storage
    TelegramBot --> Audit
    Audit -->|"load prompt"| PromptLoader
    PromptLoader --> Storage
    PromptLoader -->|"base prompts"| prompts["prompts/v1/"]
    Audit -->|"active/fallback"| Providers
    Providers -->|"OpenAI"| LLM
    Providers -->|"GigaChat"| LLM
    Audit --> TelegramBot
    TelegramBot -->|"ответ"| TG
    Routes --> AdminUI
    Routes --> Execution
    Routes --> AuditLog
    Routes --> Storage
    AuditLog --> DB
    Execution --> DB
```

- **`web`** — единый сервис FastAPI + `python-telegram-bot` polling.
- **Services** — модули с чёткими зонами ответственности.
- **PostgreSQL** — `video_audits`, `execution_sessions`, `execution_steps`, `admin_audit_log`.
- **storage volume** — файлы uploads/transcripts/audits, custom prompts, runtime config.

---

## 🗂️ 4. Модель данных

```mermaid
erDiagram
    video_audits {
        bigint id PK
        timestamptz created_at
        bigint chat_id
        bigint user_id
        text username
        text file_id
        text file_unique_id
        text filename
        text transcript
        text analysis
        text status
        text error_message
        text provider
        text prompt_id
        text mime_type
        bigint file_size
        int duration
        text storage_filename
    }
    execution_sessions {
        uuid session_id PK
        timestamptz created_at
        timestamptz updated_at
        bigint chat_id
        bigint user_id
        text username
        text file_id
        text filename
        text storage_filename
        text status
        bigint video_audit_id FK
    }
    execution_steps {
        uuid step_id PK
        uuid session_id FK
        text name
        text status
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }
    admin_audit_log {
        bigint id PK
        timestamptz created_at
        text actor
        text user_id
        text user_name
        text user_role
        text ip_address
        text action
        text resource_type
        text resource_id
        jsonb details
    }

    execution_sessions }o--o| video_audits : "video_audit_id"
    execution_steps }o--|| execution_sessions : "session_id CASCADE"
```

**Ключевые факты модели:**

- `video_audits` — результат обработки: транскрипт, аудит, метаданные файла, провайдер, промпт.
- `execution_sessions` + `execution_steps` — контур execution-tracing. Шаги: `download`, `transcribe`, `audit`, `notify`.
- `admin_audit_log` — контур аудита: кто/что/когда/откуда. Секреты и полные промпты не пишутся.

---

## 🔀 5. Путь данных

### 5.1. Общая схема

```mermaid
flowchart TD
    U([Пользователь Telegram]) -->|"аудио/видео"| TG[Telegram]
    TG -->|"polling"| Bot[TelegramBot]
    Bot -->|"download_media"| Media[MediaService]
    Media -->|"upload"| Uploads[storage/uploads]
    Bot -->|"start session"| Exec[ExecutionService]
    Exec --> DB[(PostgreSQL)]
    Bot -->|"transcribe"| Trans[TranscriptionService]
    Trans -->|"upload/poll"| STT[AssemblyAI]
    Trans -->|"transcript"| StorageT[storage/transcripts]
    Bot -->|"analyze"| Audit[AuditService]
    Audit -->|"load prompt"| PL[PromptLoader]
    PL --> prompts["prompts/v1/*.md<br/>storage/prompts/*.md"]
    Audit -->|"active/fallback"| Prov[Providers]
    Prov -->|"Chat Completions"| LLM[LLM]
    Audit -->|"audit"| StorageA[storage/audits]
    Bot -->|"ответ"| TG
    Admin([Администратор]) -->|"/admin"| Routes[FastAPI Routes]
    Routes -->|"config"| RC[storage/config.json]
    Routes -->|"executions/audit"| DB
```

### 5.2. Последовательность обработки одного файла

```mermaid
sequenceDiagram
    autonumber
    participant U as Пользователь
    participant TG as Telegram
    participant Bot as TelegramBot
    participant Media as MediaService
    participant Exec as ExecutionService
    participant DB as PostgreSQL
    participant STT as AssemblyAI
    participant Audit as AuditService
    participant Prov as LLM Provider

    U->>TG: отправить аудио/видео
    TG->>Bot: Update с файлом
    Bot->>Exec: start_session()
    Exec->>DB: INSERT execution_sessions
    Bot->>Media: download_media()
    Media->>TG: getFile → download
    Media-->>Bot: upload_path
    Bot->>Exec: finish_step(download, ok)
    Bot->>STT: upload + create + poll
    STT-->>Bot: transcript with utterances
    Bot->>Exec: finish_step(transcribe, ok)
    Bot->>Audit: analyze(transcript)
    Audit->>DB: SELECT? no — load prompt from files
    Audit->>Prov: chat_completion(system, user, model)
    Prov-->>Audit: analysis + usage
    Audit-->>Bot: analysis, provider, model
    Bot->>Exec: finish_step(audit, ok)
    Bot->>DB: INSERT video_audits
    Bot->>Exec: finish_step(notify, ok)
    Bot->>Exec: finish_session(success)
    Bot->>TG: send_message(analysis)
    TG-->>U: аудит в чате
```

### 5.3. Runtime-config flow

```mermaid
flowchart LR
    Admin[Администратор /admin] -->|POST| Routes[FastAPI /admin/config]
    Routes -->|write| Config["storage/config.json"]
    Bot[TelegramBot / AuditService] -->|read| Config
    Config -->|active_provider<br/>fallback_provider<br/>prompt_id<br/>model/temperature/max_tokens| Bot
```

- `/admin` пишет `storage/config.json` атомарно (`json.dumps` + `write_text`).
- `AuditService` читает config при каждом вызове; миграция stale keys через `RuntimeConfig._migrate_config`.
- Смена применяется к следующей обработке без рестарта.

---

## 🤖 6. Мультипровайдерность и runtime-config

### 6.1. Унификация

Все провайдеры унифицированы на Chat Completions.

| Провайдер | Реализация | Ключ |
|-----------|-----------|------|
| OpenAI | `OpenAIProvider` (openai SDK) | `OPENAI_API_KEY` |
| GigaChat | `GigaChatProvider` → `GigaChatAdapter` (urllib, OAuth per-request) | `GIGACHAT_AUTH_KEY` |

Цепочка fallback: **active LLM → fallback LLM → статический fallback**.

### 6.2. Разделение секретов и runtime-параметров

| Где | Что | Кто меняет |
|-----|-----|-----------|
| `.env` | API-ключи, токены, `ADMIN_USER_ID` | Инженер (рестарт) |
| `storage/config.json` | `active_provider`, `fallback_provider`, `openai_model`, `gigachat_model`, `temperature`, `max_tokens`, `prompt_id` | Оператор через `/admin` |
| `storage/prompts/*.md` | Custom override промптов | Оператор через `/admin` |
| `prompts/v1/*.md` | Базовые промпты | Вшиты в образ, read-only |

### 6.3. Prompt registry

- Базовые промпты лежат в `prompts/v1/`.
- Custom override лежит в `storage/prompts/` и перекрывает базовый по `id`.
- `PromptLoader._read_title()` читает первую строку `title:` из markdown frontmatter.
- Human-readable название используется в Telegram и админке.

---

## 📝 7. Промпты

- **Файлы-SOT:** `prompts/v1/{id}.md` — вшитые defaults; `storage/prompts/{id}.md` — custom override.
- **Bootstrap:** базовые промпты поставляются в образе; custom-папка создаётся при первом сохранении.
- **Frontmatter `title:`** — источник human-readable названия сценария.
- **Валидация:** `PromptLoader.validate_prompt()` проверяет наличие обязательных блоков (`Роль`, `Задача`, ...).
- **Atomic write:** `/admin` перезаписывает custom-файл через `write_text`.

Подробно — [📝 `PROMPT_ARCHITECTURE.md`](PROMPT_ARCHITECTURE.md).

---

## 📊 8. Наблюдаемость

**Три независимых контура observability:**

```mermaid
flowchart LR
    subgraph "Контур 1 — stdout"
        Stdout["docker compose logs<br/>LOG_LEVEL"]
    end
    subgraph "Контур 2 — execution tracing"
        Trace["/admin/executions<br/>трасса каждого файла"]
    end
    subgraph "Контур 3 — audit"
        Audit["/admin/audit<br/>admin/security-события"]
    end
    Web["web service"] --> Stdout
    Web -->|"insert session/step"| Trace
    Web -->|"AuditLogService.log"| Audit
```

### 8.1. stdout-логирование

- `LOG_LEVEL` через `logging_config.dictConfig`.
- Формат: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`.

### 8.2. Execution tracing

- Каждая обработка = `execution_session` со шагами `download`, `transcribe`, `audit`, `notify`.
- Шаги несут `metadata` (JSONB): размер файла, длина транскрипта, provider, model, токены.
- Просмотр: `/admin/executions` (read-only, demo допущен).

### 8.3. Audit

- `admin_audit_log`: `admin.login_success`, `admin.config_update`, `admin.provider_test`, `admin.rbac_denied`, `telegram.quota_exceeded`.
- Просмотр: `/admin/audit` (read-only, demo допущен).

---

## 🛡️ 9. Безопасность и доступ

- **Секреты** — только `.env`, в репозитории только `.env.example` с placeholder'ами.
- **Demo-RBAC** — `ADMIN_TOKEN` (admin) и `ADMIN_DEMO_TOKEN` (read-only demo). Backend guard на мутациях.
- **Дневной лимит** — 5 успешных обработок на пользователя, `ADMIN_USER_ID` exempt.
- **Cookie** — `meeting_audit_admin`, `httponly`, `secure`, `samesite=lax`.
- **IP** — извлекается по цепочке `X-Forwarded-For` → `X-Real-IP` → `client.host`.

Подробно — [🛡️ `SECURITY_NOTES.md`](SECURITY_NOTES.md).

---

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта.
- [📋 `docs/SPEC.md`](SPEC.md) — функциональная спецификация.
- [📝 `docs/PROMPT_ARCHITECTURE.md`](PROMPT_ARCHITECTURE.md) — архитектура промптов.
- [🔌 `docs/API_CONTRACT.md`](API_CONTRACT.md) — HTTP API.
- [🛡️ `docs/SECURITY_NOTES.md`](SECURITY_NOTES.md) — безопасность.
- [🚀 `docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание.
