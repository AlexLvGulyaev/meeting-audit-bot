# 🤖 EXTERNAL_PROVIDERS.md — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Дата:** 2026-08-16
**Статус:** исследовательская справка. Source of Truth — официальные доки провайдеров + код адаптеров (правило: внешняя интеграция — официальная документация, не память модели).

---

## 📋 Краткая сводка

| Провайдер | base_url | Модель (по умолчанию) | Auth | Назначение |
|-----------|----------|----------------------|------|------------|
| **AssemblyAI** | `https://api.assemblyai.com/v2` | `universal-3-5-pro` (speech model) | `ASSEMBLYAI_API_KEY` в header `authorization` | STT + диаризация |
| **OpenAI** | `https://api.openai.com/v1` (редактируется) | `gpt-4.1-mini` | `OPENAI_API_KEY` Bearer | LLM-аудит |
| **GigaChat** (Сбер) | `https://gigachat.devices.sberbank.ru/api/v1` | `GigaChat` | OAuth-обмен `GIGACHAT_AUTH_KEY` → access token | LLM-аудит fallback |

---

## 🎙️ 1. AssemblyAI — STT + диаризация

- **Upload:** `POST /upload` — загрузка аудиофайла, возвращает `upload_url`.
- **Transcript:** `POST /transcript` — создание задачи транскрибации.
- **Poll:** `GET /transcript/{id}` — ожидание статуса `completed` или `error`.
- **Параметры:**
  - `audio_url`: URL из шага upload.
  - `speech_models`: `["universal-3-5-pro"]` (актуальный параметр, заменивший deprecated `speech_model`).
  - `speaker_labels: true` — включить диаризацию.
- **Результат:** `utterances[]` с полями `speaker` и `text`. Если диаризация не сработала — fallback на общий `text`.
- **Реализация:** `app/services/transcription.py`.

> ⚠️ **Доработка:** старый параметр `speech_model` был исключён провайдером. Используется
> `speech_models: ["universal-3-5-pro"]`.

---

## 🟢 2. OpenAI — LLM-аудит (OpenAI-compatible)

- **base_url:** `https://api.openai.com/v1` (редактируется в `/admin`, поле `openai_base_url`). Любой OpenAI-compatible endpoint указывается через `base_url`.
- **Модель:** `gpt-4.1-mini` (редактируется в `/admin`, поле `openai_model`).
- **Temperature:** `0.1` по умолчанию (редактируется в `/admin`).
- **Max tokens:** `2048` по умолчанию (редактируется в `/admin`).
- **Auth:** `OPENAI_API_KEY` из `.env` → Bearer напрямую в `AsyncOpenAI(api_key=…, base_url=…)`.
- **Реализация:** `app/services/providers/openai_provider.py` — `OpenAIProvider`.

---

## 🤖 3. GigaChat (Сбер) — LLM fallback

- **base_url:** `https://gigachat.devices.sberbank.ru/api/v1` (read-only из `.env`). Фиксированный эндпоинт Сбера с OAuth-обменом и сертификатом Минцифры — смена требует правки `.env` и рестарта.
- **Модель:** `GigaChat` (редактируется в `/admin`, поле `gigachat_model`).
- **Temperature / Max tokens:** редактируются в `/admin`.
- **Auth:** authorization key **нельзя** использовать как статический `api_key`. Нужен обмен:
  - `POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth`
  - `Authorization: Basic <auth_key>`
  - `scope: GIGACHAT_API_PERS`
  - access token (~30 мин) — как `Bearer` в `/chat/completions`.
- **Refresh скрыт:** адаптер `gigachat_adapter.py` запрашивает свежий token **перед каждым запросом** (`_get_access_token`), ручного обновления оператором не требуется.
- **TLS:** сертификат Минцифры РФ. `GIGACHAT_CA_BUNDLE` — проверка; пусто — `ssl.CERT_NONE` (dev/демо); для prod — Russian Trusted Root CA bundle.
- **Реализация:** `gigachat_adapter.py` (urllib) + `gigachat_provider.py` (async-обёртка через `asyncio.to_thread`).
- **Секрет:** `GIGACHAT_AUTH_KEY` в `.env`.

### 🧪 Статус верификации

- **OpenAI** — end-to-end верифицирован реальным API key: `/chat/completions` → корректный аудит транскрипта.
- **GigaChat** — адаптер реализован, но live-валидация на as-built инстансе выполнялась через OpenAI. Для включения GigaChat задайте `GIGACHAT_AUTH_KEY` и выберите его в `/admin`.
- **«Проверить»** — real-тест провайдера доступен в `/admin` для обоих провайдеров.

---

## 🔌 4. Fallback-цепочка LLM

Цепочка fallback в `AuditService.analyze`:

1. **Активный LLM** (`active_provider`) — пытается сгенерировать аудит.
2. **Fallback LLM** (`fallback_provider`, если отличается от активного) — если активный упал.
3. **Статический fallback** — шаблонный ответ с объяснением, что LLM недоступен, и рекомендацией проверить ключи.

Execution-трейс фиксирует фактического провайдера-победителя в шаге `audit` (`provider`, `model`).

---

## 🔧 5. Источники

- [AssemblyAI API Reference — Transcript](https://www.assemblyai.com/docs/api-reference/transcripts)
- [OpenAI API Reference — Chat Completions](https://platform.openai.com/docs/api-reference/chat)
- [Sber Developers — GigaChat API](https://developers.sber.ru/docs/ru/gigachat/introduction)

---

## 📚 Связанные документы

- [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md) — архитектура, мультипровайдерность, runtime-config.
- [🔌 `docs/API_CONTRACT.md`](API_CONTRACT.md) — `/admin` поля.
- [🛡️ `docs/SECURITY_NOTES.md`](SECURITY_NOTES.md) — секреты провайдеров в `.env`.
