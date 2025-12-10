import unittest
from datetime import datetime, timezone

from audience_bot.domain.reporting import ExcelReportBuilder, ReportMetadata
from audience_bot.domain.extraction import AudienceProfile, ExtractionResult, ProfileId, ProfileType


class ExcelReportBuilderTests(unittest.TestCase):
    def test_builder_creates_expected_sheets(self):
        result = ExtractionResult()
        participant = AudienceProfile(
            profile_id=ProfileId(user_id=1, username="@alice", display_name="Алиса"),
            profile_type=ProfileType.PARTICIPANT,
            username="@alice",
            display_name="Алиса",
            first_name="Алиса",
            last_name="Тест",
            has_channel=False,
        )
        mentioned = AudienceProfile(
            profile_id=ProfileId(user_id=2, username="@bob", display_name="Боб"),
            profile_type=ProfileType.MENTIONED_ONLY,
            username="@bob",
            display_name="Боб",
            first_name="Боб",
            last_name="Тест",
        )
        channel = AudienceProfile(
            profile_id=ProfileId(user_id=3, username="@channel", display_name="Канал"),
            profile_type=ProfileType.CHANNEL,
            username="@channel",
            display_name="Канал",
            first_name="Канал",
            last_name="Тест",
            has_channel=True,
        )
        result.add_participant(participant)
        result.add_mentioned(mentioned)
        result.add_channel(channel)

        metadata = ReportMetadata(exported_at=datetime.now(timezone.utc), chat_name="Test", participant_count=1)
        builder = ExcelReportBuilder()
        report = builder.build(result, metadata)

        self.assertEqual(len(report.sheets), 3)
        self.assertEqual(report.sheets[0].name, "Участники")
        self.assertEqual(report.sheets[1].name, "Упомянутые")
        self.assertEqual(report.sheets[2].name, "Каналы")
        self.assertTrue(any(row["Username"] == "@alice" and row["Имя"] == "Алиса" for row in report.sheets[0].rows))
