# Key Sequences

## Happy path: загрузка экспортов → Excel отчёт

```plantuml
@startuml
!theme plain
participant User
participant Telegram
participant Conversation
participant Pipeline as "RunFullPipelineUC"
participant Parser
participant Extractor
participant Reporter

User -> Telegram: /start + файлы
Telegram -> Conversation: Updates (документы)
Conversation -> Conversation: Save TempFileRef
User -> Telegram: /process
Telegram -> Conversation: Команда /process
Conversation -> Pipeline: execute(files, chat_name, user_id)
Pipeline -> Parser: parse(files)
Parser --> Pipeline: ParsedMessagesDTO
Pipeline -> Extractor: extract(messages)
Extractor --> Pipeline: ExtractionResultDTO
Pipeline -> Reporter: build(result, metadata)
Reporter --> Pipeline: ReportDTO (Excel)
Pipeline --> Conversation: ReportDTO
Conversation -> Telegram: sendDocument(chat, audience-report.xlsx)
Telegram -> User: Excel отчёт
@enduml
```

Этот сценарий покрывает основной поток: пользователь загружает экспорт, запускает обработку, и при большом числе участников получает Excel-файл. Вариант с plain-text отличается только шагом Reporter, который возвращает текстовый список.***
