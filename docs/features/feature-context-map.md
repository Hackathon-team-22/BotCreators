# Feature ↔ Context Map

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml
LAYOUT_WITH_LEGEND()

System_Boundary(Features, "Features") {
  System(ImportExport, "Импорт экспортов", "Приём файлов и лимиты")
  System(ExtractionF, "Audience Extraction", "Классификация участников/упоминаний/каналов")
  System(ReportingF, "Reporting", "Выбор формата, Excel/текст вывод")
  System(ConversationF, "Telegram Conversation", "Команды /start,/help,/process,/reset")
}

System_Boundary(Contexts, "Bounded Contexts") {
  System(TBI, "Telegram Bot Interaction", "UX/сессии")
  System(CEP, "Chat Export Parsing", "JSON/HTML/ZIP → ChatMessage")
  System(AE, "Audience Extraction Context", "Core-поддомен")
  System(AR, "Audience Reporting", "Excel/Text отчёт")
}

Rel(ImportExport, CEP, "Реализуется в")
Rel(ExtractionF, AE, "Реализуется в")
Rel(ReportingF, AR, "Реализуется в")
Rel(ConversationF, TBI, "Основной контекст")
Rel(ConversationF, AE, "Взаимодействие через Application Layer")
Rel(ConversationF, AR, "Отдача результатов пользователю")
@enduml
```

Ключевые фичи показывают, в каких bounded-context’ах они реализуются. Например, импорт экспортов опирается на контекст Parsing, а Telegram Conversation связывает Interaction BC с Extraction/Reporting через application layer.***
