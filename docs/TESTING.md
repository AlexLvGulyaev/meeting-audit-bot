# 🧪 TESTING.md — Meeting Audit Bot

**Проект:** meeting-audit-bot
**Версия:** 1.0
**Дата:** 2026-08-16
**Статус:** Active — Deployment Validation пройдена, ручные E2E-сценарии, программные smoke-проверки конвейера.

> 📌 **Важно.** У проекта нет pytest-набора unit/integration-тестов. Проверка ведётся
> на четырёх уровнях: воспроизведение с нуля (L1), ручные сквозные сценарии (L2),
> программные smoke-проверки детерминированного ядра (L3), верификация провайдеров
> реальными LLM-вызовами (L4). Почему так — см. §7.

---

## 🎯 1. Назначение

Зафиксировать, как и на каких уровнях проверяется работоспособность проекта.
Цель — воспроизводимая уверенность, что конвейер «получить файл → транскрибировать →
провести LLM-аудит → вернуть в Telegram» работает, мультипровайдерность и демо-RBAC
функционируют, а развёртывание воспроизводимо с нуля по документации.

---

## 🧩 2. Уровни проверки

| Уровень | Что проверяет | Внешние вызовы | Где описан | Стоимость |
|---------|---------------|---------------|------------|-----------|
| **L1 — Deployment Validation** | Воспроизведение с нуля в чистом окружении по `DEPLOYMENT_GUIDE` | Telegram + AssemblyAI + LLM | `DEPLOYMENT_VALIDATION_REPORT.md` | Средняя (развернуть + прогнать) |
| **L2 — E2E-сценарии (ручные)** | Сквозные потоки в Telegram и браузере | Telegram + AssemblyAI + LLM | `E2E_SCENARIOS.md` (14 сценариев) | Низкая (браузер + Telegram) |
| **L3 — Smoke-проверки (программно)** | Детерминированное ядро: health, RBAC, demo read-only, JSON API, fallback-ответ — без LLM/STT | Нет | §4 ниже | ~0 |
| **L4 — Верификация провайдеров** | Реальные LLM-вызовы: смена провайдера, тест, аудит через выбранный LLM | LLM (active+fallback) | `EXTERNAL_PROVIDERS.md`, §4 | По токенам |

### 🧪 2.1. L1 — Deployment Validation

Воспроизведение полностью работоспособного экземпляра с нуля исключительно по
`DEPLOYMENT_GUIDE.md` в чистом окружении (новый VPS/VM/чистый хост; не рабочее
окружение разработчика). Критерий готовности к публикации. Каждый шаг — PASS/FAIL
в `DEPLOYMENT_VALIDATION_REPORT.md`. Текущая валидация: 26 шагов, все PASS.

### 🎬 2.2. L2 — E2E-сценарии (ручные)

14 сквозных сценариев в Telegram и браузере по [🎬 `E2E_SCENARIOS.md`](E2E_SCENARIOS.md):
Telegram (`/start`, `/help`, отправка аудио, получение аудита), операторская панель
(вход, dashboard, смена промпта, список сессий, детализация, аудит-лог, demo read-only,
тест провайдера).

### ⚙️ 2.3. L3 — Smoke-проверки (программно, без LLM/STT)

Детерминированное ядро проверяется curl-командами без расхода токенов:
health-эндпоинты, demo-RBAC (403 на мутациях), JSON API, статический fallback.
Команды — §4.

### 🔌 2.4. L4 — Верификация провайдеров

Реальные LLM-вызовы по провайдерам (OpenAI/GigaChat): смена активного провайдера
в `/admin` → аудит через выбранный → кнопка «Проверить» (1-токенный real-вызов,
latency). Гейтится секретами в `.env`. Метрики пишутся в execution-трейс
(`provider/model/tokens`).

---

## 🛠️ 3. Требования к окружению

| Переменная | Назначение | Когда нужна |
|------------|-----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API | L1, L2 |
| `ASSEMBLYAI_API_KEY` | Транскрибация | L1, L2, L4 (аудит) |
| `OPENAI_API_KEY` / `GIGACHAT_AUTH_KEY` | LLM-провайдеры | L1, L2 (аудит), L4 |
| `ADMIN_TOKEN` / `ADMIN_DEMO_TOKEN` | Доступ к `/admin` | L1–L4 |
| `ADMIN_USER_ID` | Exempt от лимита | L2 (опционально) |
| `DATABASE_URL` | PostgreSQL | Всегда |

> ⚠️ L3 можно прогонять без `ASSEMBLYAI_API_KEY` и LLM-ключей: health, RBAC и
> JSON API работают независимо. Транскрибация и LLM-аудит потребуют ключей.

---

## ▶️ 4. Команды проверки

```bash
# 0. Развёртывание
cp .env.example .env            # заполнить секреты
docker compose up -d --build
docker compose ps                # postgres + web — Up (healthy)

# 1. Health (L3)
curl -s http://localhost:8000/health                              # {"status":"ok",...}
curl -s http://localhost:8000/health/db                           # {"status":"ok","database":"ok"}

# 2. Admin login (L3) — получаем cookie
curl -s -c /tmp/a.txt -X POST http://localhost:8000/admin/login \
  -d "token=YOUR_ADMIN_TOKEN" -o /dev/null -w "%{http_code}\n"   # 303

# 3. Admin JSON API (L3)
curl -s -b /tmp/a.txt http://localhost:8000/admin/api/config | python3 -m json.tool

# 4. Demo-RBAC: мутация под demo-cookie → 403 (L3)
curl -s -c /tmp/d.txt -X POST http://localhost:8000/admin/login/demo \
  -o /dev/null -w "%{http_code}\n"                                 # 303
curl -s -b /tmp/d.txt -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:8000/admin/save \
  -d "active_provider=openai&fallback_provider=gigachat&openai_model=gpt-4.1-mini&openai_temperature=0.1&openai_max_tokens=2048&gigachat_model=GigaChat&gigachat_temperature=0.1&gigachat_max_tokens=2048&prompt_id=sales-call&prompt_content="   # 403

# 5. Execution list (L3)
curl -s -b /tmp/a.txt http://localhost:8000/admin/api/executions/any-uuid  # 404 если нет записей

# 6. Audit log (L3)
curl -s -b /tmp/a.txt http://localhost:8000/admin/api/audit/1  # 404 если лог пуст
```

---

## 🎯 5. Ручной E2E-сценарий sales-call

1. Разверните проект, убедитесь, что бот отвечает на `/start`.
2. В `/admin` выберите активный промпт `sales-call` и сохраните.
3. Отправьте тестовый аудиофайл в Telegram.
4. Дождитесь аудита с оценкой. Ожидаемый результат для стабильного примера:
   **87,5%** (7 ✅, 1 ⚠️ по критерию «Следующий шаг»).
5. Проверьте в `/admin/executions`, что сессия со статусом `success` и 4 шагами.

---

## 🧹 6. Что не тестируется автоматически

- Реальная работа AssemblyAI STT (требует аудио и API-ключа).
- Реальная генерация LLM-аудита (L4 — ручная верификация).
- Telegram polling в условиях rate limit от Telegram.
- Производительность под нагрузкой (single-container).

---

## 📝 7. Почему нет pytest-набора

Проект задуман как демо/портфельный актив с минимальной кодовой базой. Основная
сложность не в алгоритмах, а в интеграции внешних сервисов (Telegram, AssemblyAI,
OpenAI/GigaChat) и в observability. Поэтому проверка сфокусирована на:

- воспроизводимости развёртывания (L1);
- сквозных бизнес-сценариях (L2);
- детерминированном ядре, которое можно проверить curl (L3);
- реальных вызовах провайдеров (L4).

---

## 📚 Связанные документы

- [✅ `DEPLOYMENT_VALIDATION_REPORT.md`](DEPLOYMENT_VALIDATION_REPORT.md) — отчёт L1.
- [🎬 `E2E_SCENARIOS.md`](E2E_SCENARIOS.md) — ручные сценарии L2.
- [🔌 `EXTERNAL_PROVIDERS.md`](EXTERNAL_PROVIDERS.md) — параметры провайдеров L4.
