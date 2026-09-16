# 📸 MEDIA_INDEX — Meeting Audit Bot

## 🎯 1. Назначение

Каталог скриншотов E2E-сценариев и иллюстраций Meeting Audit Bot. Все изображения используются в публичной документации и верифицированы перед публикацией.

---

## 📂 2. Каталог изображений

| # | Файл | Сценарий | Статус |
|---|------|----------|--------|
| 1 | `docs/screenshots/tg-start-scenarios.png` | Telegram `/start`: приветствие, список доступных сценариев с human-readable названиями, отметка активного промпта ✅ | ✅ Готов |
| 2 | `docs/screenshots/tg-audio-sales-call-audit.png` | Telegram: отправка аудио и получение аудита sales-call (87,5%) | ✅ Готов |
| 3 | `docs/screenshots/tg-help.png` | Telegram `/help`: расширенная инструкция и список сценариев | ✅ Готов |
| 4 | `docs/screenshots/admin-login.png` | Админка `/admin/login`: страница авторизации по токену | ✅ Готов |
| 5 | `docs/screenshots/admin-dashboard.png` | Админка `/admin`: dashboard со статусами провайдеров и селектором активного промпта | ✅ Готов |
| 6 | `docs/screenshots/admin-change-prompt.png` | Админка `/admin`: открытый селектор промптов, выбран новый активный промпт | ✅ Готов |
| 7 | `docs/screenshots/admin-executions-list.png` | Админка `/admin/executions`: общий список сессий с глобальной нумерацией | ✅ Готов |
| 8 | `docs/screenshots/admin-execution-detail.png` | Админка `/admin/executions`: детализация одной сессии с аудио-плеером и сводкой | ✅ Готов |
| 9 | `docs/screenshots/admin-execution-transcript-full.png` | Админка `/admin/executions`: полный текст транскрипта (развёрнутая панель/модальное окно) | ✅ Готов |
| 10 | `docs/screenshots/admin-execution-audit-full.png` | Админка `/admin/executions`: полный текст аудита (развёрнутая панель/модальное окно) | ✅ Готов |
| 11 | `docs/screenshots/admin-audit-log.png` | Админка `/admin/audit`: security audit log с пользователем, IP, действием | ✅ Готов |
| 12 | `docs/screenshots/admin-audit-detail.png` | Админка `/admin/audit`: детализация выбранного аудит-события | ✅ Готов |
| 13 | `docs/screenshots/admin-demo-readonly.png` | Админка demo-режим: read-only формы и disabled кнопки | ✅ Готов |
| 14 | `docs/screenshots/admin-provider-test.png` | Админка `/admin`: тест провайдера с toast-уведомлением | ✅ Готов |

> **Опционально:** `docs/screenshots/tg-daily-limit.png` — Telegram сообщение о дневном лимите обработок. Не включено в обязательный E2E, так как требует 6 отправок с неадминского аккаунта.

| 15 | `docs/screenshots/mab_portfolio_light.png` | Витрина кейса — светлая тема | README.md (hero, LIGHT) |
| 16 | `docs/screenshots/mab_portfolio_dark.png` | Витрина кейса — тёмная тема | ARCHITECTURE.md (hero, DARK) |

---

## 📚 3. Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта.
- [🎬 `docs/E2E_SCENARIOS.md`](E2E_SCENARIOS.md) — сквозные сценарии и чек-лист скриншотов.
- [🎬 `docs/SYSTEM_DEMO.md`](SYSTEM_DEMO.md) — нарратив демо и скриншоты.
- [🚀 `docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание и проверка.

---

**Статус:** as-built
**Последнее обновление:** 2026-09-16
**История изменений:** [📝 CHANGE_LOG.md](CHANGE_LOG.md#-1-история-изменений-документации)
