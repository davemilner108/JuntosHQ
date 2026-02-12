# Feature: Commitments Tracking

## What It Does

After discussing the weekly Franklin prompt, each member makes **one personal commitment** for the cycle (initially weekly). This turns intellectual conversation into actionable accountability — the "personal stake" that makes juntos more than casual meetups.

The MVP version is **owner-managed only**: the junto creator sets/edits commitments and statuses for all members. This keeps it simple, fits the Free tier, and creates natural upgrade pressure (self-reporting unlocks in Standard+).

Commitments drive retention: members return to check progress, owners see who's following through, and the group builds momentum toward real impact.

---

## How It Works in the App (MVP)

### One commitment per member per cycle

- Cycle = current week (tied to the weekly prompt via ISO week number).
- Description: Free-text (e.g., "Read chapter 3 of Autobiography and share one takeaway").
- Status: Not started / In progress / Done / Partial / Blocked.
- Visible on the junto show page, right below the weekly prompt card.

### Owner-only editing in MVP

- Only the owner sees the form to add/edit commitments and change statuses.
- Non-owners see a read-only summary (e.g., "David: In progress — 'Exercise 3x this week'").
- No history or archives yet — just the current week's commitments.

### Display example on junto show page

Below the prompt:

**This Week's Commitments**

- **David (Owner)**: "Finalize prompt rotation code" — Done  
- **Sarah**: "Research local volunteer opportunities" — In progress  
- **Mike**: "No commitment set yet"  

(Owner sees edit button/form; others see read-only cards.)

---

## Data Model

New table: `commitments`

```python
class CommitmentStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    PARTIAL = "partial"
    BLOCKED = "blocked"

class Commitment(db.Model):
    __tablename__ = "commitments"
    
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    cycle_week = Column(Integer, nullable=False)          # ISO week number
    description = Column(String(500), nullable=False)
    status = Column(Enum(CommitmentStatus), default=CommitmentStatus.NOT_STARTED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    member = relationship("Member", backref="commitments")