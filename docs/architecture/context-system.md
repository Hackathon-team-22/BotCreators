# System Context

AudienceBot взаимодействует с пользователем через Telegram Bot API и предоставляет CLI/Docker-варианты для локального запуска.

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml
LAYOUT_WITH_LEGEND()

Person(user, "Telegram User", "Загружает экспорт и получает отчёт")
Person(cliUser, "CLI User / DevOps", "Запускает локально/в Docker")
System_Ext(telegram, "Telegram Bot API", "Updates, команды, файлы")
System_Ext(storage, "Local/Docker Environment", "Файловая система, .env, logging.yml")

System_Boundary(AppBot, "AudienceBot") {
  System(AudienceBotSystem, "AudienceBot Core", "Parsing → Extraction → Reporting")
}

Rel(user, telegram, "Команды, загрузка файлов")
Rel(telegram, AudienceBotSystem, "Updates / documents")
Rel(AudienceBotSystem, telegram, "Ответы (текст/Excel)")
Rel(cliUser, AudienceBotSystem, "CLI: python -m audience_bot.cli")
Rel(cliUser, storage, "конфигурация, логи")
Rel(AudienceBotSystem, storage, "чтение .env, config/logging.yml")
@enduml
```

Система работает как Telegram-бот (long polling/webhook) и/или CLI. Для развёртывания используется Docker, где внутренняя конфигурация доступна приложению через файловую систему/переменные окружения.***
