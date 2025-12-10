import unittest
from datetime import datetime, timezone

from audience_bot.domain.extraction import AudienceExtractor
from audience_bot.domain.messages import ChatMessage, RawUserRef


class AudienceExtractorTests(unittest.TestCase):
    def test_filters_deleted_and_dedups(self):
        extractor = AudienceExtractor()
        author = RawUserRef(display_name="Алиса", user_id=1, username="@alice", first_name="Алиса", last_name=None)
        mention = RawUserRef(display_name="Боб", user_id=2, username="@bob", first_name="Боб", last_name=None)
        deleted = RawUserRef(
            display_name="ghost", user_id=None, username="@ghost", first_name=None, last_name=None, is_deleted=True
        )
        message = ChatMessage(
            message_id="123",
            timestamp=datetime.now(timezone.utc),
            author=author,
            mentions=[mention, deleted],
            text="Приветствуем!",
        )
        result = extractor.extract([message])

        self.assertEqual(result.participant_count(), 1)
        self.assertEqual(result.mentioned_count(), 1)
        self.assertNotIn(
            "ghost", [profile.username for profile in result.mentioned_only.values()]
        )

    def test_forwards_from_channels_go_to_channels(self):
        extractor = AudienceExtractor()
        author = RawUserRef(display_name="User", user_id=10, username="@user", first_name="User", last_name=None)
        fwd_channel = RawUserRef(display_name="Channel X", user_id=None, username=None, first_name=None, last_name=None, is_channel=True)
        message = ChatMessage(
            message_id="fwd1",
            timestamp=datetime.now(timezone.utc),
            author=author,
            mentions=[],
            text="forwarded",
            is_forwarded=True,
            forward_author=fwd_channel,
        )
        result = extractor.extract([message])

        self.assertEqual(result.participant_count(), 1)
        self.assertEqual(result.channel_count(), 1)

    def test_forward_from_user_goes_to_mentioned(self):
        extractor = AudienceExtractor()
        author = RawUserRef(display_name="User", user_id=10, username="@user", first_name="User", last_name=None)
        fwd_user = RawUserRef(display_name="Forwarded", user_id=20, username="@forwarded", first_name=None, last_name=None)
        message = ChatMessage(
            message_id="fwd2",
            timestamp=datetime.now(timezone.utc),
            author=author,
            mentions=[],
            text="forwarded user",
            is_forwarded=True,
            forward_author=fwd_user,
        )
        result = extractor.extract([message])

        self.assertEqual(result.participant_count(), 1)
        self.assertEqual(result.mentioned_count(), 1)

    def test_dedup_uses_user_id_priority(self):
        extractor = AudienceExtractor()
        msg1 = ChatMessage(
            message_id="m1",
            timestamp=datetime.now(timezone.utc),
            author=RawUserRef(display_name="User Alpha", user_id=42, username="@alpha", first_name="User", last_name=None),
            text="hello",
        )
        msg2 = ChatMessage(
            message_id="m2",
            timestamp=datetime.now(timezone.utc),
            author=RawUserRef(display_name="User Beta", user_id=42, username="@beta", first_name="User", last_name=None),
            text="world",
        )
        result = extractor.extract([msg1, msg2])

        self.assertEqual(result.participant_count(), 1)
        only_profile = next(iter(result.participants.values()))
        self.assertEqual(only_profile.profile_id.user_id, 42)

    def test_dedup_fallback_username_when_no_user_id(self):
        extractor = AudienceExtractor()
        msg1 = ChatMessage(
            message_id="m1",
            timestamp=datetime.now(timezone.utc),
            author=RawUserRef(display_name="User", user_id=None, username="@SameName", first_name=None, last_name=None),
            text="hi",
        )
        msg2 = ChatMessage(
            message_id="m2",
            timestamp=datetime.now(timezone.utc),
            author=RawUserRef(display_name="Another Name", user_id=None, username="@samenAme", first_name=None, last_name=None),
            text="again",
        )
        result = extractor.extract([msg1, msg2])

        self.assertEqual(result.participant_count(), 1)

    def test_dedup_fallback_display_name_when_no_identifiers(self):
        extractor = AudienceExtractor()
        msg1 = ChatMessage(
            message_id="m1",
            timestamp=datetime.now(timezone.utc),
            author=RawUserRef(display_name="Display Only", user_id=None, username=None, first_name=None, last_name=None),
            text="hi",
        )
        msg2 = ChatMessage(
            message_id="m2",
            timestamp=datetime.now(timezone.utc),
            author=RawUserRef(display_name="Display Only", user_id=None, username=None, first_name=None, last_name=None),
            text="again",
        )
        result = extractor.extract([msg1, msg2])

        self.assertEqual(result.participant_count(), 1)
