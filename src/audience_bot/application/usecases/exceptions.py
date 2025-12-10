class PipelineError(Exception):
    """Ошибка пайплайна обработки файлов экспорта."""


class InvalidInputError(PipelineError):
    pass
