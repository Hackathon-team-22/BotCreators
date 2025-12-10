from __future__ import annotations

import argparse
import logging
import logging.config
import pathlib
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - fallback for environments without PyYAML
    yaml = None

from .application.container import AppContainer
from .application.usecases.dto import RawFileDTO
from .application.usecases.pipeline import RunFullPipelineUC
from .infrastructure.telegram import (
    BotController,
    ConsoleTelegramAPIAdapter,
    TelegramAPIAdapter,
    TelegramPollingService,
    TelegramWebhookAdapter,
)

logger = logging.getLogger(__name__)


def _build_container(env_file: str) -> AppContainer:
    container = AppContainer()
    container.config.env_file.from_value(env_file)
    return container


def main() -> None:
    # logging setup
    if yaml:
        try:
            with open("config/logging.yml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logging.config.dictConfig(config)
        except Exception:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s %(levelname)s %(name)s %(message)s",
                stream=sys.stdout,
            )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
        )

    parser = argparse.ArgumentParser(description="Запустить аудиторию Telegram-чата по экспорту.")
    parser.add_argument("paths", nargs="*", type=pathlib.Path, help="Файлы экспорта (JSON/HTML/ZIP).")
    parser.add_argument("--chat-name", default=None, help="Название чата для отчёта.")
    parser.add_argument("--simulate-telegram", action="store_true", help="Сымитировать серию Telegram-команд.")
    parser.add_argument("--poll-telegram", action="store_true", help="Запустить long polling Telegram API.")
    parser.add_argument("--env-file", default=".env", help="Файл переменных окружения.")
    args = parser.parse_args()

    container = _build_container(args.env_file)

    if args.poll_telegram:
        settings = container.settings()
        if not settings.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не указан, long polling не будет запущен.")
            sys.exit(1)
        run_polling(container)
        return

    if args.simulate_telegram:
        controller, webhook = create_telegram_stack(container)
        simulate_telegram_flow(webhook, args.paths)
        return

    if not args.paths:
        parser.error("Укажи хотя бы один файл экспорта.")

    files = [load_raw_file(path) for path in args.paths]
    pipeline = container.pipeline()
    report = pipeline.execute(files, chat_name=args.chat_name, user_id="cli")

    if report.format.value == "plain_text":
        print("Результат:")
        print(report.text or "Нет текста.")
    else:
        output = pathlib.Path("audience-report.xlsx")
        with open(output, "wb") as stream:
            stream.write(report.excel_bytes or b"")
        print(f"Excel отчёт записан → {output}")


def run_polling(container: AppContainer) -> None:
    telegram_config = container.telegram_config()
    conversation = container.conversation_service()
    api_adapter = TelegramAPIAdapter(telegram_config)
    controller = BotController(conversation, api_adapter)
    webhook = TelegramWebhookAdapter(controller)
    poller = TelegramPollingService(webhook, telegram_config)
    try:
        poller.run()
    except KeyboardInterrupt:
        logger.info("Polling остановлен.")


def create_telegram_stack(container: AppContainer) -> tuple[BotController, TelegramWebhookAdapter]:
    conversation = container.conversation_service()
    try:
        api_adapter = TelegramAPIAdapter(container.telegram_config())
    except ValueError:
        api_adapter = ConsoleTelegramAPIAdapter()
    controller = BotController(conversation, api_adapter)
    return controller, TelegramWebhookAdapter(controller)


def simulate_telegram_flow(webhook: TelegramWebhookAdapter, paths: list[pathlib.Path]) -> None:
    user_id = "demo-user"
    chat_id = "demo-chat"
    webhook.handle_request(
        {
            "message": {
                "chat": {"id": chat_id},
                "from": {"id": user_id},
                "text": "/start",
            }
        }
    )
    for path in paths:
        webhook.handle_request(
            {
                "message": {
                    "chat": {"id": chat_id},
                    "from": {"id": user_id},
                    "document": {
                        "file_id": path.name,
                        "file_name": path.name,
                        "mime_type": path.suffix,
                        "content": path.read_bytes(),
                    },
                }
            }
        )
    webhook.handle_request(
        {
            "message": {
                "chat": {"id": chat_id},
                "from": {"id": user_id},
                "text": "/process",
            }
        }
    )


def load_raw_file(path: pathlib.Path) -> RawFileDTO:
    content = path.read_bytes()
    suffix = path.suffix.lower()
    return RawFileDTO(path=str(path), filename=path.name, content=content, mime_type=suffix)


def create_pipeline(env_file: str = ".env") -> RunFullPipelineUC:
    container = _build_container(env_file)
    return container.pipeline()


if __name__ == "__main__":
    main()
