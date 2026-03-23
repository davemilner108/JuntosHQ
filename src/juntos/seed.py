"""Default seed data: the original Philadelphia Junto (1727)."""

from flask import current_app

from juntos.models import Commitment, CommitmentStatus, Junto, Member, db

JUNTO_NAME = "Philadelphia Junto \u2014 1727"
JUNTO_DESCRIPTION = (
    "The original mutual-improvement society founded by Benjamin Franklin "
    "in Philadelphia, 1727. Twelve citizens met every Friday evening to "
    "discuss morals, politics, and natural philosophy \u2014 and to hold one "
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

# One commitment per member, keyed by name
COMMITMENTS = {
    "Benjamin Franklin":   "Write a new essay on the virtue of industry for the Junto's consideration",
    "Joseph Breintnall":   "Transcribe three deeds without error and deliver them to their owners",
    "Thomas Godfrey":      "Complete the lunar-distance calculations needed for the winter almanac",
    "Nicholas Scull":      "Survey and map the boundaries of the Penn's Creek land grant",
    "William Parsons":     "Repair the boots of two neighbours who cannot afford a cobbler",
    "William Maugridge":   "Craft a writing desk for the Junto's meeting room",
    "Hugh Meredith":       "Plant the north field with flax and record the method for the Junto",
    "Stephen Potts":       "Bind and deliver all outstanding almanac orders before the month's end",
    "George Webb":         "Set type and print fifty copies of the Junto's latest broadside",
    "Robert Grace":        "Purchase three new books for the Junto's lending library",
    "William Coleman":     "Reconcile the merchant's ledgers and present the quarterly accounts",
    "John Jones":          "Tailor new coats for two members in time for the next Friday meeting",
}


def run():
    """Insert the Philadelphia Junto if it doesn't already exist, then seed commitments."""
    existing = Junto.query.filter_by(name=JUNTO_NAME).first()
    if existing:
        print(f"Junto '{JUNTO_NAME}' already exists (id={existing.id}). Skipping junto creation.")
        _seed_commitments(existing)
    else:
        junto = Junto(name=JUNTO_NAME, description=JUNTO_DESCRIPTION)
        db.session.add(junto)
        db.session.flush()

        for name, role in MEMBERS:
            db.session.add(Member(name=name, role=role, junto_id=junto.id))

        db.session.flush()
        db.session.commit()
        print(f"Seeded '{JUNTO_NAME}' with {len(MEMBERS)} members (id={junto.id}).")
        _seed_commitments(junto)

    founders_coupon = current_app.config.get("HARD_CODED_COUPON", "")
    if founders_coupon:
        print(f"Founders coupon (use this to sign in): {founders_coupon}")


def _seed_commitments(junto: Junto) -> None:
    """Add one permanent (week 0) commitment per member if not already seeded."""
    added = 0
    for member in junto.members:
        already = Commitment.query.filter_by(member_id=member.id, cycle_week=0).first()
        if already:
            continue
        desc = COMMITMENTS.get(member.name)
        if not desc:
            continue
        db.session.add(
            Commitment(
                member_id=member.id,
                cycle_week=0,
                description=desc,
                status=CommitmentStatus.IN_PROGRESS,
            )
        )
        added += 1
    db.session.commit()
    if added:
        print(f"Seeded {added} commitment(s) as permanent defaults (week 0).")
    else:
        print("Permanent default commitments already present. Skipping.")
