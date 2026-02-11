# Feature: Commitments Tracking

## What It Does

At the end of every Franklin junto meeting, each member stated something they would do before the next meeting. At the next meeting, they reported back. This **public accountability loop** is what made the junto more than a talking club.

Commitments tracking digitizes that loop. Each member sets one commitment per meeting cycle. At the next meeting, they mark it done, partially done, or not done. The history accumulates and becomes a record of each person's follow-through.

This is the feature most likely to create **daily active use** — members will open the app between meetings to see their current commitment and mark it done when complete.

---

## User Experience

### On the junto show page

A "Commitments" section shows the current cycle's commitments from each member:

```
Current Commitments  (cycle: Feb 6 – Feb 13)
──────────────────────────────────────────────
Alice   Read two chapters of Poor Richard's Almanack   ✓ Done
Bob     Write one page of the new chapter              ● In progress
Carol   Contact three potential sponsors               ✗ Not done
David   (no commitment set)
```

Owners see everyone's status. Members see their own commitment with an editable status.

### Setting a commitment

After logging a meeting (or anytime between meetings), a member clicks "Set my commitment" and types a short statement — one sentence, plain text:

```
My commitment this week
───────────────────────
[                                          ]

[Save]
```

### Checking in

Members see a simple three-button check-in on their own commitment card:

```
Your commitment:  "Write one page of the new chapter"

[✓ Done]  [● In progress]  [✗ Not done]
```

Tapping a button saves immediately (no form submit). On mobile this feels like a quick daily check-in.

### History view

On each member's profile within the junto, a history of past commitments and outcomes:

```
Alice's commitment history
──────────────────────────
Feb 6    Read two chapters of Poor Richard's Almanack    ✓ Done
Jan 30   Finish expense report                           ✓ Done
Jan 23   Schedule dentist appointment                    ✗ Not done
Jan 16   Review meeting notes and send summary           ● Partial
```

---

## Data Model

```python
class Commitment(db.Model):
    __tablename__ = "commitment"

    id          = db.Column(db.Integer, primary_key=True)
    member_id   = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    junto_id    = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)
    text        = db.Column(db.Text, nullable=False)
    status      = db.Column(
        db.Enum("pending", "done", "partial", "not_done", name="commitment_status"),
        nullable=False,
        default="pending"
    )
    cycle_start = db.Column(db.Date, nullable=False)   # date of the meeting that opened this cycle
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
```

Add to `Member`:
```python
commitments = db.relationship(
    "Commitment", backref="member", lazy=True, order_by="Commitment.cycle_start.desc()"
)
```

Add to `Junto`:
```python
commitments = db.relationship(
    "Commitment", backref="junto", lazy=True, cascade="all, delete-orphan"
)
```

### Status values

| Value | Meaning |
|---|---|
| `pending` | Set but not yet checked in |
| `done` | Member completed it |
| `partial` | Partial progress, acknowledged |
| `not_done` | Member did not complete it |

Using a database `ENUM` keeps the values constrained. SQLite (used in tests) stores enums as strings — no compatibility issue.

---

## Routes

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/juntos/<jid>/commitments/` | member* | Set commitment for current cycle |
| POST | `/juntos/<jid>/commitments/<cid>/status` | member* | Update check-in status |
| GET | `/juntos/<jid>/members/<mid>/commitments` | — | Member's commitment history |

*"member" auth means: user must be logged in AND be the member record in this junto. This requires a `Member.user_id` FK (see below).

---

## Required Change: Member Ownership

Currently `Member` is just a name and role — there is no link between a `Member` row and a `User` account. For commitments to be self-reported, members need to claim their seat in the junto.

### Option A — Invite link (recommended for v1)

The owner shares a join link. Clicking it creates a `Member` record linked to the signed-in user's account. Simple, no email required.

### Option B — Owner assigns

The owner manually links a member to a user account by entering their email. More friction but gives the owner control over the roster.

### Schema addition for either option

```python
# Add to Member model
user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
```

`nullable=True` preserves backward compatibility — existing member rows without a linked account still work; they just can't self-report commitments.

---

## Freemium Consideration

- **Free tier**: owner can manually set status on behalf of any member; no self-reporting
- **Paid tier**: members claim their seat and self-report check-ins; full history

This positions the paid tier as enabling true peer accountability rather than just owner-managed record keeping.

---

## Future Extensions

- **Streak counter** — "Alice: 8 weeks in a row done" shown on the member list
- **Junto completion rate** — percentage of commitments marked done across all members, displayed as a junto health metric
- **Weekly email reminder** — "You have an open commitment: [text]. Mark it done →"
- **Commitment templates** — common categories (read, write, contact, finish) for faster entry
