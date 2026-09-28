# Формат сообщений (JSONL)

Файл очереди (личный ноут):
`/home/Hequa/projects/grok-bot-event-bridge/queue/messages.jsonl`

Каждая строка — один JSON-объект. Только append, не редактировать старые строки.

## Запрос коллеги → Helper

```json
{"v":1,"id":"<uuid>","ts":"2026-09-28T14:00:00+03:00","direction":"to_helper","status":"pending","from":"colleague","payload":{"question":"нужен ответ по X"}}
```

## Ответ Helper → коллега

```json
{"v":1,"id":"<same-uuid>","ts":"...","direction":"to_colleague","status":"done","from":"helper","payload":{"answer":"..."}}
```

Правило: запрос `id` считается обработанным, если в файле уже есть строка с тем же `id` и `direction=to_colleague`.
