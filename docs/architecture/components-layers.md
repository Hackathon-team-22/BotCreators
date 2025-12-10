# Components & Layers

Разложение системы по слоям (Application / Domain / Infrastructure) и ключевым компонентам.

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml
LAYOUT_WITH_LEGEND()

System_Boundary(AppBot, "AudienceBot") {
  Container(convo, "Conversation Service", "Telegram команды, управление сессиями", "Application")
  Container(pipelineUC, "RunFullPipelineUC", "Orchestration (Parse → Extract → Report)", "Application")
  Container(parserDTO, "DTO Layer", "RawFileDTO, ParsedMessagesDTO, ReportDTO", "Application")

  Container_Boundary(domainLayer, "Domain Layer") {
    Container(parsingDomain, "Chat Export Parsing Domain", "ChatMessage, RawUserRef", "Domain")
    Container(extractionDomain, "Audience Extraction Domain", "ExtractionResult, Policies", "Domain")
    Container(reportingDomain, "Audience Reporting Domain", "AudienceReport, ReportPolicy", "Domain")
  }

  Container_Boundary(infraLayer, "Infrastructure Layer") {
    Container(parserAdapter, "ParserAdapter", "JSON/HTML/ZIP → DTO", "Infrastructure")
    Container(extractorAdapter, "ExtractionAdapter", "DTO → Domain", "Infrastructure")
    Container(reportingAdapter, "ReportingAdapter + ExcelRenderer", "Text/Excel output", "Infrastructure")
    Container(telegramAdapter, "BotController + Telegram API Adapter", "Long polling/webhook", "Infrastructure")
    Container(tempStorage, "TempFileStorage", "Временные файлы", "Infrastructure")
    Container(sessionStore, "SessionStore", "Состояние пользователя", "Infrastructure")
  }
}

Rel(convo, pipelineUC, "/process, /status")
Rel(pipelineUC, parsingDomain, "Использует")
Rel(pipelineUC, extractionDomain, "Использует")
Rel(pipelineUC, reportingDomain, "Использует")
Rel(parsingDomain, parserAdapter, "Парсит файлы экспорта")
Rel(extractionDomain, extractorAdapter, "DTO → Domain")
Rel(reportingDomain, reportingAdapter, "Генерирует отчёт")
Rel(convo, telegramAdapter, "Отправка/приём Telegram сообщений")
Rel(convo, tempStorage, "Сохраняет TempFileRef")
Rel(convo, sessionStore, "Сессии пользователя")
@enduml
```

Application layer инициирует доменные use case’ы, домен содержит чистые бизнес-правила, а инфраструктура реализует конкретные адаптеры (парсинг, Excel, Telegram, временное хранилище). Конфигурация (`PipelineConfig`, `.env`, `config/logging.yml`) прокидывается через application layer.***
