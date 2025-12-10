# Использование CLI

```bash
python -m audience_bot.cli tests/data/sample.json
```

Параметры:
- `paths` — пути к файлам экспорта (JSON/HTML/ZIP).
- `--chat-name` — название чата в отчёте.
- `--simulate-telegram` — демонстрация диалога с командами Telegram.
- `--poll-telegram` — запустить long polling (требует `TELEGRAM_BOT_TOKEN` в .env).
- `--env-file` — путь к файлу окружения (по умолчанию `.env`).

Результат:
- Если отчёт текстовый — выводится в stdout.
- Если Excel — сохраняется в `audience-report.xlsx`.
