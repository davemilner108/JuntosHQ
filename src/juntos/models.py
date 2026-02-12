import enum
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class JuntoTier(enum.Enum):
    FREE = "free"
    SUBSCRIPTION = "subscription"
    EXPANDED = "expanded"


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_id = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.String(2048), nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    juntos = db.relationship("Junto", backref="owner", lazy=True)

    __table_args__ = (
        db.UniqueConstraint("provider", "provider_id", name="uq_user_provider"),
    )

    def __repr__(self):
        return f"<User {self.provider}:{self.provider_id}>"


class Junto(db.Model):
    __tablename__ = "junto"

    MAX_MEMBERS = 12

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
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

    _TIER_MEETING_LIMITS = {
        JuntoTier.FREE: 1,
        JuntoTier.SUBSCRIPTION: 3,
        JuntoTier.EXPANDED: 5,
    }

    @property
    def meeting_limit(self):
        return self._TIER_MEETING_LIMITS.get(self.tier, 1)

    @property
    def is_full(self):
        return len(self.members) >= self.MAX_MEMBERS

    def __repr__(self):
        return f"<Junto {self.name}>"


class Member(db.Model):
    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    junto_id = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)

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
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    member = db.relationship(
        "Member",
        backref=db.backref("commitments", cascade="all, delete-orphan"),
    )

    __table_args__ = (
        db.UniqueConstraint("member_id", "cycle_week", name="uq_commitment_member_week"),
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
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

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
