# Overview

AudienceBot — консольное/Telegram-приложение, которое принимает экспорт истории чата и строит отчёт об аудитории. В основе лежит DDD-архитектура с явными слоями Parsing → Extraction → Reporting и адаптерами Telegram CLI.

## Основные возможности

- Приём одного или нескольких файлов экспорта мобильного Telegram-клиента (JSON/HTML/ZIP).
- Дедупликация участников/упоминаний, фильтрация удалённых аккаунтов и выделение каналов.
- Формирование текстового списка (если участников ≤ порога) или Excel-отчёта с тремя вкладками (участники, упомянутые, каналы).
- Telegram-бот с командами `/start`, `/help`, `/status`, `/process`, `/reset`, поддержка ручного выбора формата (`/process chat|file`).
- CLI и Docker-окружение для локального запуска или развёртывания.

## Технологический стек

- Python 3.10+, `dependency-injector`, `pydantic-settings`, `openpyxl`, `PyYAML`.
- DDD + Clean Architecture: доменные модели (`src/audience_bot/domain`), application use case’ы и инфраструктурные адаптеры.
- Конфигурация через `.env` и `config/logging.yml`, Dockerfile и docker-compose для развёртывания.

## Как запустить (коротко)

```bash
python -m pip install -e '.[dev]'
python -m audience_bot.cli tests/data/sample.json
```

Для Telegram-бота: создать `.env` с `TELEGRAM_BOT_TOKEN`, затем `python -m audience_bot.cli --poll-telegram` или `docker compose up`.

Дополнительные детали по ограничениям, форматам и логированию — в `docs/limits.md`, `docs/formats.md`, `docs/logging.md`.***
