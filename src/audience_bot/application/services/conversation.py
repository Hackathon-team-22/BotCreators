from __future__ import annotations

from dataclasses import dataclass
import io
import logging
import zipfile
from typing import List, Optional

from ..config import PipelineConfig
from ..usecases.dto import RawFileDTO
from ..usecases.exceptions import PipelineError
from ..usecases.files import TempFileRef
from ..usecases.pipeline import RunFullPipelineUC
from ..usecases.ports import ITempFileStorage
from .sessions import ISessionStore, SessionRecord, SessionState


logger = logging.getLogger(__name__)


START_TEXT = (
    "Этот бот принимает файлы истории Telegram-чата и собирает список участников.\n"
    "Отправьте файлы истории чата в формате JSON или HTML. После загрузки файлов используйте /process."
)
HELP_TEXT = (
    "Команды:\n"
    "/start – приветствие.\n"
    "/help или ? – справка по форматам и лимитам.\n"
    "/reset – очистить текущую сессию.\n"
    "/process [chat|file] – построить отчёт (текст или Excel); опционально указать формат доставки.\n\n"
    "Сессия: корзина ваших загрузок до вызова /process или /reset; хранится до {ttl_min} минут.\n"
    "Лимиты на одну сессию: до {max_files} файлов, каждый ≤ {max_mb} МБ. "
    "Формат отчёта: текст, если участников ≤ {plain_threshold}; иначе Excel."
    "\nФормат данных: JSON — предпочтителен (есть user_id, точная дедупликация). "
    "HTML — поддерживается, но беден данными (только отображаемые имена), возможны дубли. "
    "Рекомендуем присылать JSON и не смешивать форматы данных в одной сессии (не загружайте одновременно JSON и HTML одного и того же чата)."
)
RESET_TEXT = "Сессия очищена, можете загрузить новые файлы истории чата."
NO_FILES_TEXT = "Файлы истории чата не загружены. Отправьте данные, прежде чем вызывать /process."
PROCESSING_ERROR_TEXT = "Не удалось обработать файлы истории чата. Попробуй позже."
SESSION_LIMIT_TEXT = "Достигнут лимит файлов. Удали старые и попробуй снова."
SIZE_LIMIT_TEXT = "Файл превышает максимальный допустимый размер."
MIXED_FORMAT_TEXT = (
    "В одной сессии нельзя смешивать разные форматы данных (JSON и HTML). "
    "Заверши обработку /process или сбрось сессию /reset, затем загружай файлы одного формата данных."
)


@dataclass
class BotResponse:
    text: str
    file_bytes: Optional[bytes] = None
    filename: Optional[str] = None
    is_error: bool = False


class ConversationService:
    def __init__(
        self,
        session_store: ISessionStore,
        pipeline: RunFullPipelineUC,
        temp_storage: ITempFileStorage,
        config: PipelineConfig,
    ):
        self._sessions = session_store
        self._pipeline = pipeline
        self._storage = temp_storage
        self._config = config

    def start(self, user_id: str) -> BotResponse:
        self._sessions.clear(user_id)
        return BotResponse(text=START_TEXT)

    def help(self, user_id: str) -> BotResponse:
        text = HELP_TEXT.format(
            max_files=self._config.max_files,
            max_mb=int(self._config.max_file_size / (1024 * 1024)),
            ttl_min=int(self._config.session_ttl_seconds / 60),
            plain_threshold=self._config.report_text_threshold,
        )
        return BotResponse(text=text)

    def reset(self, user_id: str) -> BotResponse:
        self._sessions.clear(user_id)
        return BotResponse(text=RESET_TEXT)

    def status(self, user_id: str) -> BotResponse:
        record = self._sessions.get(user_id)
        message = (
            f"Загружено {len(record.files)} файлов. /process → запуск обработки."
            if record.files
            else "Файлы не загружены."
        )
        return BotResponse(text=message)

    def upload_file(self, user_id: str, raw_file: RawFileDTO) -> BotResponse:
        record = self._sessions.get(user_id)
        if len(record.files) >= self._config.max_files:
            logger.info("upload_rejected_limit", extra={"user_id": user_id, "reason": "max_files"})
            return BotResponse(text=SESSION_LIMIT_TEXT, is_error=True)
        if len(raw_file.content) > self._config.max_file_size:
            logger.info(
                "upload_rejected_limit",
                extra={"user_id": user_id, "reason": "file_size", "size": len(raw_file.content)},
            )
            return BotResponse(text=SIZE_LIMIT_TEXT, is_error=True)
        # Проверяем, что в одной сессии не смешиваются форматы данных (JSON vs HTML).
        detected_format = self._detect_export_format(raw_file.content)
        if detected_format is None:
            logger.info(
                "upload_rejected_format",
                extra={"user_id": user_id, "reason": "unknown_format", "file_name": raw_file.filename},
            )
            return BotResponse(
                text="Формат файла не похож на файл истории Telegram-чата (JSON/HTML). Проверьте данные и попробуйте снова.",
                is_error=True,
            )
        if record.export_format and record.export_format != detected_format:
            logger.info(
                "upload_rejected_format_mixed",
                extra={
                    "user_id": user_id,
                    "expected_format": record.export_format,
                    "got_format": detected_format,
                    "file_name": raw_file.filename,
                },
            )
            return BotResponse(text=MIXED_FORMAT_TEXT, is_error=True)

        temp_ref = self._storage.save(raw_file.filename, raw_file.content, raw_file.mime_type)
        record.add_file(temp_ref)
        record.export_format = record.export_format or detected_format
        record.state = SessionState.COLLECTING
        self._sessions.save(record)
        logger.info(
            "upload_accepted",
            extra={"user_id": user_id, "file_name": raw_file.filename, "size": len(raw_file.content)},
        )
        return BotResponse(text=f"Файл '{raw_file.filename}' загружен ({len(record.files)}).")

    def process(self, user_id: str, chat_name: Optional[str], target: str = "auto") -> BotResponse:
        record = self._sessions.get(user_id)
        if not record.files:
            return BotResponse(text=NO_FILES_TEXT, is_error=True)
        raw_files = self._build_raw_files(record.files)
        try:
            report = self._pipeline.execute(raw_files, chat_name=chat_name, user_id=user_id)
        except PipelineError as exc:
            logger.warning(
                "process_failed",
                extra={"user_id": user_id, "chat_name": chat_name, "error": str(exc)},
            )
            return BotResponse(text=str(exc) or PROCESSING_ERROR_TEXT, is_error=True)
        finally:
            self._cleanup_session(record)

        if target == "chat" and report.format.value == "excel":
            note = "Слишком много участников для текста. Отправляем файл."
            return BotResponse(
                text=note,
                file_bytes=report.excel_bytes,
                filename="audience-report.xlsx",
            )

        if report.format.value == "plain_text":
            if target == "file":
                return BotResponse(
                    text="Отчёт небольшой, отправляем текст в чат (Excel не требуется).",
                    file_bytes=None,
                    is_error=False,
                )
            return BotResponse(text=report.text or "Отчёт пуст.", is_error=False)
        return BotResponse(
            text="Отчёт готов. Смотри вложение.",
            file_bytes=report.excel_bytes,
            filename="audience-report.xlsx",
        )

    def _build_raw_files(self, refs: List[TempFileRef]) -> List[RawFileDTO]:
        files: List[RawFileDTO] = []
        for ref in refs:
            content = self._storage.read(ref)
            files.append(RawFileDTO(path=str(ref.path), filename=ref.filename, content=content))
        return files

    def _cleanup_session(self, record: SessionRecord) -> None:
        for ref in record.files:
            self._storage.delete(ref)
        record.clear()
        record.state = SessionState.EMPTY
        self._sessions.save(record)

    @staticmethod
    def _detect_export_format(content: bytes) -> Optional[str]:
        """Грубое определение формата данных по содержимому файла.

        Используется только для UX-ограничения: не смешивать HTML и JSON в одной сессии.
        Возвращает один из логических классов формата:
        - \"structured\" — JSON или ZIP с экспортом внутри;
        - \"html\" — HTML-экспорт;
        - None — не похоже на поддерживаемый экспорт.
        """
        if not content:
            return None
        # ZIP-проверка должна идти первой, иначе бинарный поток может не декодироваться.
        if zipfile.is_zipfile(io.BytesIO(content)):
            return "structured"
        # Остальные варианты считаем текстовыми.
        try:
            text = content.decode("utf-8", errors="ignore").lstrip()
        except Exception:
            return None
        if text.startswith("{"):
            return "structured"
        if text.startswith("<"):
            return "html"
        return None
