# Feature: Meeting Log

## What It Does

A **meeting log** records each time a junto convenes: the date, who attended, and notes from the discussion. It gives the group a shared memory — new members can catch up on history, and returning members remember what was decided last time instead of rehashing it.

This is the feature that creates **switching cost**. Once a junto has six months of meeting history in the app, no one is going to move to a spreadsheet.

---

## User Experience

### On the junto show page

A new "Meetings" section below the member list shows recent meetings in reverse chronological order:

```
Meetings
────────────────────────────────────────
Feb 6, 2026 · 5 attended · View →
Jan 30, 2026 · 4 attended · View →
Jan 23, 2026 · 6 attended · View →

+ Log a meeting
```

Only the owner sees "Log a meeting". All junto members (and eventually, anyone with the link) can read the history.

### Log a meeting form

```
Date          [Feb 11, 2026     ]
Who attended  [✓] Alice  [✓] Bob  [✓] Carol  [ ] David
Notes         [                              ]
              [  free-form text, markdown ok ]

[Save meeting]  [Cancel]
```

The date defaults to today. Attendees are checkboxes generated from `junto.members`. Notes is a freeform textarea.

### Meeting detail page

```
Feb 6, 2026
Attended: Alice, Bob, Carol, David, Elena (5 of 6)

Notes
─────
Discussed Q4 goals. Alice presented her writing progress.
Bob raised the question of switching meeting day to Thursday.
Group agreed to try Thursday for February.

[Edit]  [Delete]
```

Edit and Delete are owner-only.

---

## Data Model

A new `Meeting` model with a `MeetingAttendance` join table:

```python
class Meeting(db.Model):
    __tablename__ = "meeting"

    id          = db.Column(db.Integer, primary_key=True)
    junto_id    = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)
    held_on     = db.Column(db.Date, nullable=False)
    notes       = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    attendances = db.relationship(
        "MeetingAttendance", backref="meeting", lazy=True, cascade="all, delete-orphan"
    )


class MeetingAttendance(db.Model):
    __tablename__ = "meeting_attendance"

    id         = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meeting.id"), nullable=False)
    member_id  = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
```

Add to the `Junto` model:

```python
meetings = db.relationship(
    "Meeting", backref="junto", lazy=True,
    cascade="all, delete-orphan",
    order_by="Meeting.held_on.desc()"
)
```

Add to the `Member` model:

```python
attendances = db.relationship("MeetingAttendance", backref="member", lazy=True)
```

---

## Routes

New blueprint or added to the existing `juntos` blueprint under a `meetings` sub-resource:

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/juntos/<jid>/meetings/new` | owner | Log meeting form |
| POST | `/juntos/<jid>/meetings/` | owner | Save meeting |
| GET | `/juntos/<jid>/meetings/<mid>` | — | View meeting detail |
| GET | `/juntos/<jid>/meetings/<mid>/edit` | owner | Edit form |
| POST | `/juntos/<jid>/meetings/<mid>/edit` | owner | Update meeting |
| POST | `/juntos/<jid>/meetings/<mid>/delete` | owner | Delete meeting |

---

## Migration

```bash
uv run alembic revision --autogenerate -m "add_meeting_and_attendance_tables"
uv run alembic upgrade head
```

The generated migration should create `meeting` and `meeting_attendance` tables. Review it before applying — autogenerate will not add the `order_by` or any data-migration logic.

---

## Freemium Consideration

- **Free tier**: view the last 1 meetings
- **Subscription tier**: view last 3 meetings, export to PDF/CSV
- **Expanded tier**: view last 5 meetings, export to PDF/CSV

This makes history the natural reason to upgrade. A group that's been meeting for a month hits the limit organically.

---

## Future Extensions

- **Attendance rate per member** — shown on the member list ("Alice: 11/12 meetings")
- **Search notes** — full-text search across meeting notes for a junto
- **Meeting templates** — pre-fill the notes field with an agenda based on Franklin's questions (connects directly to the Discussion Prompts feature)
- **Recurring meeting scheduler** — set a day of the week, get a reminder
