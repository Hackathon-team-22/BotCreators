# Модель данных (упрощённо)

## Сообщение (ChatMessage)
- `message_id`: строка
- `timestamp`: datetime (может отсутствовать)
- `author`: RawUserRef или None (service)
- `mentions`: список RawUserRef
- `is_service_message`: bool
- `is_forwarded`: bool
- `forward_author`: RawUserRef или None
- `text`: строка

## Пользователь/канал (RawUserRef)
- `user_id`: int | None (в HTML может отсутствовать)
- `username`: str | None (с @, если есть)
- `display_name`: str (обязательное)
- `first_name` / `last_name`: опционально
- `is_deleted` / `is_bot` / `is_channel`: флаги

## Профиль аудитории (AudienceProfile)
- Идентификация: `user_id` → `username` → `display_name` (fallback)
- `profile_type`: participant | mentioned_only | channel | bot
- `username`, `display_name`, `first_name`, `last_name`
- `has_channel`: bool (true только если сам канал)
- `description`, `registered_at`: не заполняются из мобильного экспорта

## Отчёт (AudienceReport)
- Формат: plain_text | excel
- Метаданные: `exported_at`, `chat_name`, `participant_count`
- Plain text: список строк `Имя (@username)`
- Excel: листы participants / mentioned_only / channels
- Колонки: Дата экспорта, Username, Имя, Фамилия, Отображаемое имя, Описание, Дата регистрации, Наличие канала
