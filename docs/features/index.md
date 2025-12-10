# Feature Catalog

| Фича | Короткое описание | Основные ссылки |
|------|-------------------|-----------------|
| Импорт экспортов чата | Приём JSON/HTML/ZIP файлов мобильного Telegram-клиента, валидация лимитов (`MAX_FILES`, `MAX_FILE_SIZE`, `MAX_TOTAL_BYTES`). | Requirements (`docs/requirements/requirements.md`), `src/audience_bot/infrastructure/parsers.py`. |
| Audience Extraction | Нормализация сообщений, дедупликация участников по `ProfileId`, выделение упомянутых пользователей и каналов. | `src/audience_bot/domain/extraction/core.py`. |
| Reporting | Выбор формата отчёта (plain text ≤ порога, Excel иначе), генерация Excel с 3 вкладками и фиксированными колонками. | `src/audience_bot/domain/reporting`. |
| Telegram Conversation | Команды `/start`, `/help`, `/status`, `/process`, `/reset`, загрузка файлов и ручной выбор формата (`/process chat|file`). | `src/audience_bot/application/services/conversation.py`, README. |
| CLI / Docker запуск | Выполнение пайплайна через CLI (`python -m audience_bot.cli`) и контейнеризацию (`Dockerfile`, `docker-compose.yml`). | README, `Dockerfile`, `docs/usage`. |

При появлении новых значимых фич добавляйте краткий summary и ссылку на соответствующий дизайн/реализацию.***
