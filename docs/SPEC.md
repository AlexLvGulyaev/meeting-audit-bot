# 📋 SPEC — Meeting Audit Bot

## 1. Цель проекта

Создать AI-ассистента для аудита аудио- и видео-встреч. Пользователь отправляет запись в Telegram; бот транскрибирует речь через AssemblyAI (с разделением по говорящим) и проводит аудит диалога по заданным критериям через LLM.

## 2. Функциональные требования

### 2.1. Приём файлов
- Telegram-бот принимает видео и аудио файлы.
- Поддерживаемые форматы: mp3, mp4, ogg, wav, m4a и другие, распознаваемые Telegram.
- Бот скачивает файл в `storage/uploads/`.

### 2.2. Транскрибация
- Используется AssemblyAI API.
- Транскрипт сохраняется в `storage/transcripts/{file_unique_id}.md` с разделением по спикерам (`Speaker A`, `Speaker B`).
- Длинные файлы обрабатываются в фоновом режиме с прогресс-сообщениями.

### 2.3. Аудит диалога
- Активный промпт выбирается через runtime-конфиг `/admin`.
- Промпт содержит блоки: `<role>`, `<task_objective>`, `<internal_criteria>`, `<audit_process>`, `<core_instructions>`, `<constraints_and_negations>`.
- LLM провайдер выбирается через `/admin`: OpenAI, GigaChat.
- Поддерживается fallback-провайдер и статический fallback при недоступности LLM.

### 2.4. Сохранение результатов
- Исходный файл — `storage/uploads/`.
- Транскрипт — `storage/transcripts/`.
- Аудит — `storage/audits/`.
- Метаданные обработки — `video_audits` в PostgreSQL.

### 2.5. Execution tracing
- Каждая обработка файла = `execution_session`.
- Шаги: `download`, `transcribe`, `audit`, `notify`.
- Каждый шаг фиксирует статус, тайминг и метаданные (provider, model, latency, tokens, fallback_reason).

### 2.6. Security audit
- Таблица `audit_logs` фиксирует: вход/выход в `/admin`, смену runtime-config, создание/редактирование промптов, RBAC-отказ, превышение Telegram-квоты.
- Поля: actor, user_role, ip_address, action, resource_type, resource_id, JSONB details.

### 2.7. Web-админка
- `/admin` — HTTP Basic Auth. Главный экран: конфиг LLM + реестр промптов + статус системы.
- `/admin/login/demo` — одно-кликовый демо-вход (read-only).
- `/admin/executions` — консоль «Логи»: список обработок с детализацией шагов, транскрипта и аудита.
- `/admin/audit` — консоль «Аудит»: security/админ события.

### 2.8. Ограничения и безопасность
- Квота 5 успешных обработок в сутки на обычного пользователя.
- `ADMIN_USER_ID` не учитывается в квоте.
- Секреты только в `.env`.

### 2.9. Observability
- `/health` — проверка БД и LLM.
- stdout-логи.
- `execution_sessions`/`execution_steps` + `audit_logs`.

## 3. Нефункциональные требования

- Python 3.12.
- FastAPI + Telegram polling.
- Docker Compose: `web` + `db`.
- PostgreSQL 16.
- Deployment Validation в чистом окружении.

## 4. Границы проекта

- AssemblyAI не заменяется на альтернативный STT.
- Telegram polling — основной UI; webhook не реализуется в v1.
- Версионирование промптов не реализуется в v1.

## 5. Критерии приёмки

- Бот успешно обрабатывает mp3 3–5 минут.
- Результат аудита получается в Telegram.
- `/admin` позволяет сменить провайдер/промпт без рестарта.
- `/admin/executions` показывает шаги, транскрипт и аудит.
- `/health` возвращает `{"status":"ok"}`.
- Deployment Validation проходит в чистом окружении.
