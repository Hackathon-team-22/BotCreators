# Testing Strategy (summary)

Основные принципы:

- **Domain unit tests** — покрывают `ExtractionResult`, `ProfileId`, `AudienceExtractor`, сценарии дедупликации, фильтрации удалённых, работу с упоминаниями/каналами.
- **Application tests** — `ParseChatExportUC`, `ExtractAudienceUC`, `BuildAudienceReportUC`, `RunFullPipelineUC`, а также `ConversationService` (команды `/start`, `/help`, `/process`, лимиты).
- **Adapter/integration tests** — ParserAdapter (JSON/HTML/ZIP), ReportingAdapter/ExcelReportBuilder, ExcelRendererAdapter, проверка структуры отчёта (3 вкладки, фиксированные колонки).
- **Contract tests** — базовые проверки портов (`IParser`, `IExtractor`, `IReportBuilder`, `IExcelRenderer`), чтобы альтернативные реализации соответствовали интерфейсам.
- **Pipeline limit tests** — проверка `max_messages`, `max_total_bytes`, `max_processing_seconds` на уровне `RunFullPipelineUC`.
- **Conversation flow tests** — сценарии загрузки файлов → `/process chat|file`, сообщения об ошибках при превышении лимитов.
- **E2E (backlog)** — планируются полноформатные сценарии через Telegram API / docker-compose.

Все тесты запускаются через `python -m pytest` (реком. установка: `pip install -e '.[dev]'`).***
