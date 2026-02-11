"""Seed the database with the original Philadelphia Junto (1727)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from juntos import create_app
from juntos.models import Junto, Member, db

JUNTO_NAME = "Philadelphia Junto — 1727"
JUNTO_DESCRIPTION = (
    "The original mutual-improvement society founded by Benjamin Franklin "
    "in Philadelphia, 1727. Twelve citizens met every Friday evening to "
    "discuss morals, politics, and natural philosophy — and to hold one "
    "another accountable for personal growth and civic action."
)

MEMBERS = [
    ("Benjamin Franklin", "Printer & Postmaster"),
    ("Joseph Breintnall", "Copier of Deeds"),
    ("Thomas Godfrey", "Glazier & Mathematician"),
    ("Nicholas Scull", "Surveyor"),
    ("William Parsons", "Shoemaker & Astrologer"),
    ("William Maugridge", "Joiner & Cabinetmaker"),
    ("Hugh Meredith", "Farmer & Printer"),
    ("Stephen Potts", "Bookbinder"),
    ("George Webb", "Printer"),
    ("Robert Grace", "Gentleman of Means"),
    ("William Coleman", "Merchant's Clerk"),
    ("John Jones", "Tailor"),
]


def seed():
    app = create_app()
    with app.app_context():
        existing = Junto.query.filter_by(name=JUNTO_NAME).first()
        if existing:
            print(f"Junto '{JUNTO_NAME}' already exists (id={existing.id}). Skipping.")
            return

        junto = Junto(name=JUNTO_NAME, description=JUNTO_DESCRIPTION)
        db.session.add(junto)
        db.session.flush()

        for name, role in MEMBERS:
            db.session.add(Member(name=name, role=role, junto_id=junto.id))

        db.session.commit()
        print(f"Seeded '{JUNTO_NAME}' with {len(MEMBERS)} members (id={junto.id}).")


if __name__ == "__main__":
    seed()
