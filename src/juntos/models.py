import enum
import secrets
from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utcnow():
    return datetime.now(UTC)


class SubscriptionTier(enum.Enum):
    FREE = "free"
    STANDARD = "standard"
    EXPANDED = "expanded"


class JuntoTier(enum.Enum):
    FREE = "free"
    SUBSCRIPTION = "subscription"
    EXPANDED = "expanded"


# Junto-creation limits per subscription tier
JUNTO_LIMITS: dict[SubscriptionTier, int] = {
    SubscriptionTier.FREE: 1,
    SubscriptionTier.STANDARD: 3,
    SubscriptionTier.EXPANDED: 5,
}


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_id = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.String(2048), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    user_timezone = db.Column(db.String(50), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(255), nullable=True)
    last_active_at = db.Column(db.DateTime, nullable=True)
    notification_prefs = db.Column(db.JSON, nullable=True)
    chatbot_msgs_used = db.Column(db.Integer, nullable=False, default=0)
    chatbot_addon = db.Column(db.Boolean, nullable=False, default=False)
    subscription_tier = db.Column(
        db.Enum(SubscriptionTier, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubscriptionTier.FREE,
    )
    stripe_customer_id = db.Column(db.String(255), nullable=True, unique=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)

    juntos = db.relationship("Junto", backref="owner", lazy=True)

    __table_args__ = (
        db.UniqueConstraint("provider", "provider_id", name="uq_user_provider"),
    )

    @property
    def junto_limit(self) -> int:
        return JUNTO_LIMITS.get(self.subscription_tier, 1)

    def __repr__(self):
        return f"<User {self.provider}:{self.provider_id}>"


class Junto(db.Model):
    __tablename__ = "junto"

    MAX_MEMBERS = 12

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    meeting_url = db.Column(db.String(2048), nullable=True)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    tier = db.Column(
        db.Enum(JuntoTier), nullable=False, default=JuntoTier.FREE
    )
    members = db.relationship(
        "Member", backref="junto", lazy=True, cascade="all, delete-orphan"
    )
    meetings = db.relationship(
        "Meeting",
        backref="junto",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Meeting.held_on.desc()",
    )
    invites = db.relationship(
        "MemberInvite",
        backref="junto",
        lazy=True,
        cascade="all, delete-orphan",
    )

    _TIER_MEETING_LIMITS = {
        JuntoTier.FREE: 1,
        JuntoTier.SUBSCRIPTION: 3,
        JuntoTier.EXPANDED: 5,
    }

    _TIER_COMMITMENT_LIMITS = {
        JuntoTier.FREE: 2,
        JuntoTier.SUBSCRIPTION: 3,
        JuntoTier.EXPANDED: 5,
    }

    @property
    def meeting_limit(self):
        return self._TIER_MEETING_LIMITS.get(self.tier, 1)

    @property
    def commitment_limit(self):
        return self._TIER_COMMITMENT_LIMITS.get(self.tier, 2)

    @property
    def is_full(self):
        return len(self.members) >= self.MAX_MEMBERS

    def __repr__(self):
        return f"<Junto {self.name}>"


class MemberStatus(enum.Enum):
    INVITED = "invited"
    ACTIVE = "active"
    INACTIVE = "inactive"


class Member(db.Model):
    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    junto_id = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    occupation = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    joined_at = db.Column(db.DateTime, nullable=True, default=_utcnow)
    status = db.Column(
        db.Enum(MemberStatus), nullable=False, default=MemberStatus.ACTIVE
    )
    avatar_url = db.Column(db.String(2048), nullable=True)

    user = db.relationship("User", backref="memberships", lazy=True)
    attendances = db.relationship(
        "MeetingAttendance", backref="member", lazy=True, cascade="all, delete"
    )

    def __repr__(self):
        return f"<Member {self.name}>"


class CommitmentStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class Commitment(db.Model):
    __tablename__ = "commitment"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    cycle_week = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(CommitmentStatus),
        nullable=False,
        default=CommitmentStatus.NOT_STARTED,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    member = db.relationship(
        "Member",
        backref=db.backref("commitments", cascade="all, delete-orphan"),
    )

    def __repr__(self):
        return f"<Commitment member={self.member_id} week={self.cycle_week}>"


class Meeting(db.Model):
    __tablename__ = "meeting"

    id = db.Column(db.Integer, primary_key=True)
    junto_id = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)
    held_on = db.Column(db.Date, nullable=False)
    url = db.Column(db.String(2048))
    location = db.Column(db.String(255))
    agenda = db.Column(db.Text)
    instructions = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    attendances = db.relationship(
        "MeetingAttendance",
        backref="meeting",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Meeting {self.held_on} junto={self.junto_id}>"


class MeetingAttendance(db.Model):
    __tablename__ = "meeting_attendance"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meeting.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)


class MemberInvite(db.Model):
    __tablename__ = "member_invite"

    id = db.Column(db.Integer, primary_key=True)
    junto_id = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    token = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(48),
    )
    email = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)

    member = db.relationship(
        "Member",
        backref=db.backref("invites", cascade="all, delete"),
        lazy=True,
    )

    def __repr__(self):
        return f"<MemberInvite junto={self.junto_id} member={self.member_id}>"


class ChatSession(db.Model):
    __tablename__ = "chat_session"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    junto_id = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    messages = db.relationship(
        "ChatMessage",
        backref="session",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )
    user = db.relationship("User", backref="chat_sessions", lazy=True)

    def __repr__(self):
        return f"<ChatSession user={self.user_id}>"


class ChatMessage(db.Model):
    __tablename__ = "chat_message"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("chat_session.id"), nullable=False
    )
    role = db.Column(db.String(10), nullable=False)  # "user" | "assistant"
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    def __repr__(self):
        return f"<ChatMessage session={self.session_id} role={self.role}>"
