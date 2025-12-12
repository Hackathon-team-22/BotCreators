# Telegram History Bot

Прототип Telegram-бота *AudienceBot* для извлечения аудитории по экспортам истории чата.

## Что реализовано

* Чистая доменная модель (Parsing / Extraction / Reporting) и связанный Application Layer (`RunFullPipeline`).
* Инфраструктура: парсер JSON/HTML, текст/Excel-репорт, `TempFileStorage` и `InMemorySessionStore`.
* Telegram-ориентированные адаптеры: `ConversationService`, `BotController`, `TelegramAPIAdapter`,
  `ConsoleTelegramAPIAdapter`, `TelegramWebhookAdapter` и long polling (`TelegramPollingService`).
* CLI с опциями `--simulate-telegram`, `--chat-name`, Dockerfile и тестами (`pytest` + `unittest`), плюс
  `dependency-injector` и `pydantic-settings`.

## Быстрый старт

```bash
python -m pip install --upgrade pip
pip install -e .
```

## CLI

```bash
python -m audience_bot.cli tests/data/sample.json
```

* Для симуляции диалога Telegram используйте `--simulate-telegram`.
* `--chat-name` формирует название чата в отчёте.

## Docker

```bash
docker build -t audience-bot .
```

Запуск long polling (требует `.env` с `TELEGRAM_BOT_TOKEN`):

```bash
docker compose up
```

Dockerfile использует Python 3.12, устанавливает зависимости из `pyproject.toml` и запускает CLI (
`python -m audience_bot.cli`). `.dockerignore` исключает `.venв`, `__pycache__` и `build`.
`docker compose up` поднимает long polling и требует `.env` (см. секцию выше) с `TELEGRAM_BOT_TOKEN`. Если токен не
установлен, контейнер падает с тем же `ValueError`.

## Long polling и .env

Скрипт читает переменные окружения из `.env` (приведи `TELEGRAM_BOT_TOKEN`). Пример:

```bash
cat <<'EOF' > .env
TELEGRAM_BOT_TOKEN=123456:ABCdefGhIjKlmNoPQrStUvWxYz
TELEGRAM_POLL_INTERVAL=2.0
EOF
```

Запустить long polling:

```bash
python -m audience_bot.cli --poll-telegram
```

Переменные окружения:

- `TELEGRAM_BOT_TOKEN` — токен бота (обязателен для long polling).
- `REPORT_TEXT_THRESHOLD` — порог участников: если `≤` порога — выдача текстом, иначе Excel (по умолчанию 50).
- `REPORT_FORCE_EXCEL` — `true`/`false`: если true, всегда отдаём Excel (игнорируем порог), по умолчанию false.
- `MAX_FILES` — максимум файлов в одной сессии (по умолчанию 10).
- `MAX_FILE_SIZE` — максимум размера файла в байтах (по умолчанию 5 МБ).
- `MAX_MESSAGES` — максимум сообщений в экспорте (по умолчанию 200000); при превышении обработка прекращается.
- `MAX_TOTAL_BYTES` — суммарный объём загруженных файлов в байтах (по умолчанию 50 МБ).
- `MAX_PROCESSING_SECONDS` — лимит времени обработки пайплайна (по умолчанию 15 c).
- `LOG_LEVEL` — уровень логов (INFO/DEBUG/ERROR), при использовании базовой конфигурации.

### Форматы данных

- JSON — предпочтителен: содержит `user_id`/`username`, обеспечивает более точную дедупликацию.
- HTML — поддерживается, но беднее данными (обычно только отображаемые имена), возможны дубли при идентификации.

## Тесты

```bash
source .venv/bin/activate
PYTHONPATH=src python -m pytest
```

## Отчёты и интерпретация полей

- Excel-отчёт содержит три вкладки: участники, упомянутые, каналы, с фиксированными колонками
  (дата экспорта, username, отображаемое имя, имя, фамилия, описание, дата регистрации, наличие канала).
- Колонка «Наличие канала» заполняется значением «да» только для тех профилей, которые в экспорте явно представлены как каналы.
  Для остальных строк поле остаётся пустым: мобильный экспорт не даёт достоверной информации о наличии/отсутствии канала в их профиле,
  поэтому мы не утверждаем «нет», если данных просто нет.

## Логи

По умолчанию используется `config/logging.yml` (dictConfig, вывод в stdout). Если PyYAML недоступен, включается
резервная конфигурация `basicConfig` с форматированием `%(asctime)s %(levelname)s %(name)s %(message)s` и выводом в
stdout. Уровень можно переопределить через `LOG_LEVEL`.
  
