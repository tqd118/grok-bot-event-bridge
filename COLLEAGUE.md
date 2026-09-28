# Инструкция для коллеги

Helper **не имеет входящего HTTP API**. Обмен только через общую очередь на машине владельца (Иван), путь:

`/home/Hequa/projects/grok-bot-event-bridge/queue/messages.jsonl`

(если у тебя другой mount/sync этой папки — используй тот же файл.)

## Что поднять у владельца (один раз)

1. В Grok Bot у агента **Helper** включена routine **Bridge queue wake** (webhook).
2. Из панели routine скопировать URL и sender key в  
   `scripts/webhook.env` (поля `WEBHOOK_URL`, `WEBHOOK_KEY`) — **не в чат**.
3. На ноуте владельца запустить watcher:

```bash
# pacman -S inotify-tools   # если нет
cd ~/projects/grok-bot-event-bridge
./scripts/watch_and_wake.sh
```

Watcher при новой строке `to_helper` дергает webhook → Helper просыпается, читает очередь, пишет ответ.

## Что делать коллеге

```bash
cd /path/to/grok-bot-event-bridge   # та же папка / sync
python3 colleague/send_request.py "нужен ответ по X"
# запомни id из вывода
python3 colleague/wait_reply.py <id>
```

Или руками дописать JSONL-строку (см. MESSAGE_FORMAT.md).

## Чего не делать

- Не звать Helper по HTTP напрямую.
- Не класть очередь в `~/work` и не использовать корпоративные ключи.
