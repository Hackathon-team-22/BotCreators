# Bounded Context Map

Обзор bounded context-ов AudienceBot и их отношений.

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml
LAYOUT_WITH_LEGEND()

System_Boundary(App, "AudienceBot") {
  System(TBI, "Telegram Bot Interaction (Generic)", "UX, команды, сессии")
  System(CEP, "Chat Export Parsing (Supporting)", "Нормализация JSON/HTML/ZIP")
  System(AE, "Audience Extraction (Core)", "Дедуп участников, упоминаний, каналов")
  System(AR, "Audience Reporting (Supporting)", "Текстовый/Excel отчёт")
}

Rel(TBI, CEP, "Customer/Supplier", "Published Language: ChatMessage")
Rel(CEP, AE, "Передаёт нормализованные сообщения")
Rel(AE, AR, "Передаёт ExtractionResult")
Rel(TBI, AE, "Customer/Supplier (через Application)")
Rel(TBI, AR, "Customer/Supplier (через Application)")
@enduml
```

- **Telegram Bot Interaction (Generic)** — точка контакта с пользователем, управляет сессиями и запускает pipeline.
- **Chat Export Parsing (Supporting)** — преобразует экспорт Telegram в унифицированные сообщения.
- **Audience Extraction (Core)** — бизнес-ценность (список участников/упоминаний/каналов).
- **Audience Reporting (Supporting)** — формирует итоговый отчёт в необходимом формате.***
