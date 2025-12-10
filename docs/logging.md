# Логирование

- Конфигурация по умолчанию: `config/logging.yml` (dictConfig), вывод в stdout, формат `%(asctime)s %(levelname)s %(name)s %(message)s`.
- Если PyYAML недоступен, используется fallback `basicConfig` с тем же форматом на stdout.
- Уровень можно задать через `LOG_LEVEL` (INFO/DEBUG/ERROR) при использовании fallback.
- Логи ключевых событий: загрузка файлов (лимиты/успех), парсинг/объёмы, выбор формата отчёта, ошибки пайплайна.
