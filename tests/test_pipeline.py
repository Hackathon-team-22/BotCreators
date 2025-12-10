import os
import unittest
from pathlib import Path

from audience_bot.application.usecases.dto import RawFileDTO
from audience_bot.cli import create_pipeline


class PipelineTests(unittest.TestCase):
    def test_full_pipeline_returns_text_for_small_export(self):
        path = Path("tests/data/sample.json")
        raw_file = RawFileDTO(path=str(path), filename=path.name, content=path.read_bytes())
        original_threshold = os.environ.get("REPORT_TEXT_THRESHOLD")
        os.environ["REPORT_TEXT_THRESHOLD"] = "1000"
        try:
            pipeline = create_pipeline()
        finally:
            if original_threshold is None:
                os.environ.pop("REPORT_TEXT_THRESHOLD", None)
            else:
                os.environ["REPORT_TEXT_THRESHOLD"] = original_threshold
        report = pipeline.execute([raw_file], chat_name="Demo chat", user_id="tester")

        self.assertEqual(report.format.value, "plain_text")
        self.assertIn("UserOne", report.text or "")
