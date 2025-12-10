import types
from typing import Protocol

import pytest


class ParserContract(Protocol):
    def parse(self, files): ...


class ExtractorContract(Protocol):
    def extract(self, parsed): ...


class ReportBuilderContract(Protocol):
    def build(self, extraction, metadata): ...


class ExcelRendererContract(Protocol):
    def render(self, report): ...


@pytest.fixture
def parser_contract_factory():
    def factory():
        return types.SimpleNamespace(parse=lambda files: files)  # pragma: no cover - placeholder

    return factory
