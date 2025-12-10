# Architecture Overview

## Слои

1. **Domain** (`src/audience_bot/domain`): чистые модели и политики.
   - *Chat Export Parsing* — нормализует сообщения (`ChatMessage`, `RawUserRef`).
   - *Audience Extraction* — агрегат `ExtractionResult`, дедупликация и классификация профилей.
   - *Audience Reporting* — модели отчёта, политика выбора формата.
2. **Application** (`src/audience_bot/application`): use case’ы, orchestrating pipeline и Conversation Service.
   - `ParseChatExportUC`, `ExtractAudienceUC`, `BuildAudienceReportUC`, `RunFullPipelineUC`.
   - `ConversationService` управляет сессиями и командами Telegram.
3. **Infrastructure** (`src/audience_bot/infrastructure`): адаптеры Telegram API, парсер экспортов, Excel renderer, временное хранилище файлов.

## Bounded Contexts

| Контекст | Роль |
|----------|------|
| Telegram Bot Interaction | Принимает команды/файлы, управляет пользовательскими сессиями, вызывает pipeline. |
| Chat Export Parsing | Разбирает JSON/HTML/ZIP экспорта и выдаёт нормализованные сообщения. |
| Audience Extraction | Формирует уникальный набор участников, упомянутых пользователей и каналов. |
| Audience Reporting | Генерирует текст или Excel отчёт и определяет, что отправить пользователю. |

## Потоки

```
Telegram Update → ConversationService → ParseChatExport → ExtractAudience → BuildAudienceReport → Telegram Response
```

- Перед запуском пайплайна проверяются лимиты: количество файлов, общий размер, количество сообщений, время обработки.
- Результат (`ReportDTO`) передаётся обратно ConversationService, который либо отправляет текст, либо Excel-файл пользователю.

## Основные артефакты

- **Конфигурация**: `src/audience_bot/application/config/settings.py`, `.env`, `config/logging.yml`.
- **Развёртывание**: `Dockerfile`, `docker-compose.yml`, CLI (`python -m audience_bot.cli`).

## Диаграммы (PlantUML / C4)

В архитектурных диаграммах используем PlantUML с библиотекой C4. Шаблон:

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml
LAYOUT_WITH_LEGEND()

Person(user, "NetOps/User", "Загружает Excel, инициирует/аппрувит импорт")
System_Ext(ext, "External APIs", "Внешние источники данных")
System_Boundary(App, "AudienceBot") {
  System(TBI, "Telegram Bot Interaction", "Команды, загрузка файлов, сессии")
  System(CEP, "Chat Export Parsing", "JSON/HTML/ZIP → ChatMessage")
  System(AE, "Audience Extraction", "Дедуп участников/упоминаний/каналов")
  System(AR, "Audience Reporting", "Текст/Excel отчёты")
}

Rel(user, TBI, "Команды /process, загрузка файлов")
Rel(TBI, CEP, "Customer/Supplier", "Published Language: ChatMessage")
Rel(CEP, AE, "Нормализованные сообщения")
Rel(AE, AR, "ExtractionResult")
Rel(AR, TBI, "ReportDTO (text/excel)")
@enduml
```

Используйте его как основу при добавлении новых C4-диаграмм (context-map, layers, feature-context, последовательности).***
