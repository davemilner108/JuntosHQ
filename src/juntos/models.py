from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Junto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    members = db.relationship("Member", backref="junto", lazy=True)

    def __repr__(self):
        return f"<Junto {self.name}>"


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    junto_id = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)

    def __repr__(self):
        return f"<Member {self.name}>"
