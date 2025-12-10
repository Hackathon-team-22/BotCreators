from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional

from ..messages import ChatMessage, ProfileContext, ProfileId, RawUserRef


class ProfileType(str, Enum):
    PARTICIPANT = "participant"
    MENTIONED_ONLY = "mentioned_only"
    CHANNEL = "channel"
    BOT = "bot"


@dataclass(frozen=True)
class AudienceProfile:
    profile_id: ProfileId
    profile_type: ProfileType
    username: Optional[str]
    display_name: Optional[str]
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    has_channel: bool = False
    description: Optional[str] = None
    registered_at: Optional[str] = None


class DeduplicationPolicy:
    def is_same(self, a: AudienceProfile, b: AudienceProfile) -> bool:
        return a.profile_id == b.profile_id


class ClassificationPolicy:
    def classify_author(self, raw: RawUserRef) -> ProfileType:
        if raw.is_channel:
            return ProfileType.CHANNEL
        if raw.is_bot:
            return ProfileType.BOT
        return ProfileType.PARTICIPANT

    def classify_mention(self, raw: RawUserRef) -> ProfileType:
        if raw.is_channel:
            return ProfileType.CHANNEL
        if raw.is_bot:
            return ProfileType.BOT
        return ProfileType.MENTIONED_ONLY


@dataclass
class ExtractionResult:
    participants: Dict[ProfileId, AudienceProfile] = field(default_factory=dict)
    mentioned_only: Dict[ProfileId, AudienceProfile] = field(default_factory=dict)
    channels: Dict[ProfileId, AudienceProfile] = field(default_factory=dict)

    def add_participant(self, profile: AudienceProfile) -> None:
        self._add(profile, self.participants, [self.mentioned_only])

    def add_mentioned(self, profile: AudienceProfile) -> None:
        if profile.profile_id in self.participants:
            return
        self._add(profile, self.mentioned_only, [])

    def add_channel(self, profile: AudienceProfile) -> None:
        self._add(profile, self.channels, [self.participants, self.mentioned_only])

    def _add(
        self,
        profile: AudienceProfile,
        target: Dict[ProfileId, AudienceProfile],
        to_clean: Iterable[Dict[ProfileId, AudienceProfile]],
    ) -> None:
        for collection in to_clean:
            collection.pop(profile.profile_id, None)
        target[profile.profile_id] = profile

    def merge(self, other: "ExtractionResult") -> None:
        for profile in other.participants.values():
            self.add_participant(profile)
        for profile in other.mentioned_only.values():
            self.add_mentioned(profile)
        for profile in other.channels.values():
            self.add_channel(profile)

    def finalize(self) -> None:
        """Поддерживаем инвариант единственности и приоритетов."""
        self.mentioned_only = {
            pid: profile
            for pid, profile in self.mentioned_only.items()
            if pid not in self.participants
        }
        self.channels = {
            pid: profile
            for pid, profile in self.channels.items()
            if pid not in self.participants
        }

    def participant_count(self) -> int:
        return len(self.participants)

    def mentioned_count(self) -> int:
        return len(self.mentioned_only)

    def channel_count(self) -> int:
        return len(self.channels)


class AudienceExtractionError(Exception):
    pass


class AudienceExtractor:
    def __init__(
        self,
        classification_policy: Optional[ClassificationPolicy] = None,
        deduplication_policy: Optional[DeduplicationPolicy] = None,
    ):
        self._classification_policy = classification_policy or ClassificationPolicy()
        self._deduplication_policy = deduplication_policy or DeduplicationPolicy()

    def extract(self, messages: List[ChatMessage]) -> ExtractionResult:
        if not messages:
            raise AudienceExtractionError("Нет сообщений для анализа.")
        result = ExtractionResult()
        for msg in messages:
            if msg.is_service_message:
                continue
            contexts = []
            if msg.author:
                contexts.append(ProfileContext(raw=msg.author, source="author", message_id=msg.message_id))
            for mention in msg.mentions:
                contexts.append(ProfileContext(raw=mention, source="mention", message_id=msg.message_id))
            if msg.forward_author and msg.forward_author.is_channel:
                contexts.append(ProfileContext(raw=msg.forward_author, source="forward", message_id=msg.message_id))
            elif msg.forward_author:
                contexts.append(ProfileContext(raw=msg.forward_author, source="forward_user", message_id=msg.message_id))
            for context in contexts:
                if context.raw.is_deleted:
                    continue
                profile_id = ProfileId.from_raw(context.raw)
                if profile_id is None:
                    continue
                profile = AudienceProfile(
                    profile_id=profile_id,
                    profile_type=self._classify(context),
                    username=context.raw.username,
                    display_name=context.raw.display_name,
                    first_name=context.raw.first_name,
                    last_name=context.raw.last_name,
                    has_channel=context.raw.is_channel,
                )
                self._apply_profile(profile, result)
        result.finalize()
        return result

    def _classify(self, context: ProfileContext) -> ProfileType:
        if context.source in {"mention", "forward_user"}:
            return self._classification_policy.classify_mention(context.raw)
        return self._classification_policy.classify_author(context.raw)

    def _apply_profile(self, profile: AudienceProfile, result: ExtractionResult) -> None:
        if profile.profile_type == ProfileType.CHANNEL:
            result.add_channel(profile)
        elif profile.profile_type == ProfileType.MENTIONED_ONLY:
            result.add_mentioned(profile)
        else:
            result.add_participant(profile)
