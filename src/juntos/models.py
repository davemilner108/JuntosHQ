from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    members = db.relationship(
        "Member", backref="junto", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Junto {self.name}>"


class Member(db.Model):
    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    junto_id = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)

    def __repr__(self):
        return f"<Member {self.name}>"
