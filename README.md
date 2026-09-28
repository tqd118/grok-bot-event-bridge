# Event-driven мост между двумя Grok-ботами (личный)

Рабочий прототип обмена сообщениями **без входящего API у Helper** и **без периодического поллинга Helper**. Коллега пишет в общую очередь на машине владельца; локальный триггер (inotify / mtime) будит Helper через **webhook routine**; Helper читает очередь, отвечает, пишет ответ в тот же файл; коллега забирает ответ.

> **Аккаунт:** только личный (`~/projects`, GitHub `tqd118`). Не использовать `~/work` и корпоративные ключи/репозитории.

---

## Архитектура

```
Коллега (бот / скрипт)          Ноут владельца                    Helper (Grok Bot)
─────────────────────          ────────────────                  ─────────────────
send_request.py  ──append──►  queue/messages.jsonl
                                    │
                              watch_and_wake.sh
                              (inotify / mtime)
                                    │
                              POST webhook  ──────────────────►  routine «Bridge queue wake»
                                                                    │
                                                              читает JSONL
                                                              пишет ответ  ──append──► messages.jsonl
Коллега wait_reply.py  ◄─────────────────────────────────────────────────────────────┘
```

Почему так:

- У Helper **нет** публичного входящего HTTP API «позови меня с вопросом».
- Пробуждение идёт через **webhook** сохранённой routine (аналог send_task).
- Очередь — обычный **JSONL-файл** на диске владельца (можно заменить на локальный Redis позже тем же контрактом).
- Триггер **не** крутит «есть ли что у Helper?»; он реагирует на появление строки в файле и один раз будит агента.

Дополнительно в репо остались ранние демо (HTTP webhook-relay и Redis pub/sub между двумя локальными клиентами) — см. раздел «Опциональные демо». Основной путь для реальных Grok-ботов — **JSONL + webhook**.

---

## Что есть в репозитории

| Путь | Назначение |
|------|------------|
| `queue/messages.jsonl` | Общая очередь (создаётся при первом send) |
| `MESSAGE_FORMAT.md` | Контракт строк JSONL |
| `COLLEAGUE.md` | Краткая инструкция коллеге |
| `colleague/send_request.py` | Коллега: положить вопрос |
| `colleague/wait_reply.py` | Коллега: дождаться ответа по `id` |
| `scripts/watch_and_wake.sh` | Триггер: файл изменился → POST webhook |
| `scripts/webhook.env` | URL и key webhook (**локально**, не в git) |
| `scripts/process_pending.py` | Логика обработки одного pending (Helper / ручной тест) |
| `bots/*`, `bus/*`, `run_demo*.sh` | Опциональные локальные демо без Grok |

---

## Формат сообщений

Каждая строка файла — один JSON. Только **append**. Запрос обработан, если для того же `id` уже есть `direction=to_colleague`.

**Запрос коллеги → Helper:**

```json
{"v":1,"id":"<uuid>","ts":"2026-09-28T17:50:24+03:00","direction":"to_helper","status":"pending","from":"colleague","payload":{"question":"нужен ответ по X"}}
```

**Ответ Helper → коллега:**

```json
{"v":1,"id":"<same-uuid>","ts":"...","direction":"to_colleague","status":"done","from":"helper","payload":{"answer":"..."}}
```

Подробности: `MESSAGE_FORMAT.md`.

---

## Как поднять у владельца (Иван / Helper)

### 1. Клон (личный GitHub)

```bash
cd ~/projects
git clone git@github.com-personal:tqd118/grok-bot-event-bridge.git
cd grok-bot-event-bridge
```

(Host `github.com-personal` → личный SSH-ключ; не `github.com-work`.)

### 2. Routine webhook у Helper

В Grok Bot у агента **Helper** должна быть включена routine **Bridge queue wake** (триггер webhook).

Из панели routine скопируй в локальный файл (файл в `.gitignore`):

```bash
cp scripts/webhook.env.example scripts/webhook.env
# вставь WEBHOOK_URL и WEBHOOK_KEY из панели:
#   Webhook URL / Webhook key / Authorization header
```

Ссылки в UI Helper: Webhook URL / Webhook key у routine `bridge-queue-wake`.

**Не вставляй key в чат и не коммить `webhook.env`.**

### 3. Триггер на машине

```bash
# рекомендуется
sudo pacman -S inotify-tools   # Arch; иначе скрипт использует проверку mtime раз в 2с

cd ~/projects/grok-bot-event-bridge
./scripts/watch_and_wake.sh
```

Оставь этот процесс работать, пока ждёшь сообщения от коллеги.

### 4. Проверка без webhook (опционально)

```bash
python3 colleague/send_request.py "тест"
python3 scripts/process_pending.py --answer "ручной ответ"
python3 colleague/wait_reply.py <id>
```

---

## Как коллеге настроить своего бота-подписчика

1. Получить доступ к **тому же** `queue/messages.jsonl` (общая папка, sync, SSH mount, git ignored queue на shared disk — как договоритесь). Не нужен API Helper.
2. Установить Python 3.
3. Слать вопросы:

```bash
python3 colleague/send_request.py "нужен ответ по X"
# выведет id=...
python3 colleague/wait_reply.py <id>
```

4. В своём боте: при необходимости ответа Helper — **append** строку `to_helper` в JSONL; подписаться на появление строк `to_colleague` с тем же `id` (inotify по файлу или ожидание mtime, как в `wait_reply.py`). Не поллить Helper по сети.

См. также `COLLEAGUE.md`.

---

## Как работает триггер

1. Коллега делает `append` в `messages.jsonl`.
2. `watch_and_wake.sh` видит изменение (`inotifywait` или fallback по размеру файла).
3. Если в добавленном куске есть `"direction":"to_helper"`, скрипт делает `curl POST` на webhook routine Helper с `Authorization: Bearer <key>`.
4. Helper просыпается по routine, читает очередь на ноуте владельца, пишет `to_colleague`.
5. Коллега читает ответ из файла.

Никакого таймера вида «сходить к Helper, есть ли работа» на стороне Helper API нет.

---

## Команды запуска (шпаргалка)

```bash
# владелец — watcher
./scripts/watch_and_wake.sh

# коллега — запрос / ответ
python3 colleague/send_request.py "нужен ответ по X"
python3 colleague/wait_reply.py <uuid>

# владелец — ручная обработка одного pending
python3 scripts/process_pending.py --answer "..."
```

---

## Опциональные демо (локальные клиенты, не Grok API)

- HTTP-шина: `./run_demo.sh` (`bus/relay.py`, `bots/bot_a.py`, `bots/bot_b.py`)
- Redis pub/sub: поднять локальный Redis, затем `./run_demo_redis.sh`

Это иллюстрация pub/sub; прод-схема с Helper — JSONL + webhook выше.

---

## Безопасность

- `scripts/webhook.env` — секреты, только локально.
- Очередь может содержать текст вопросов/ответов — не коммитьте содержимое `queue/` с продакшен-данными.
- Личный GitHub / личные пути только.
