# Feature: Discussion Prompts (Franklin's 24 Questions)

## What It Does

Benjamin Franklin wrote 24 questions for his junto members to consider and discuss. They covered moral philosophy, civic improvement, personal conduct, and useful knowledge. These questions were not trivia — they were designed to generate genuine debate among people with different views.

JuntosHQ can surface one of these questions each week as a **rotating discussion prompt**, giving groups a ready-made conversation starter that is simultaneously historically grounded and genuinely useful. No other modern app does this. It is a free differentiator that reinforces the Franklin identity of the app.

---

## Franklin's 24 Original Questions

These are in the public domain, drawn from Franklin's autobiography and historical records of the junto's rules:

1. Have you met with any thing in the author you last read, remarkable, or suitable to be communicated to the junto? Particularly in history, morality, poetry, physics, travels, mechanic arts, or other parts of knowledge?
2. What new story have you lately heard agreeable for telling in conversation?
3. Hath any citizen in your knowledge failed in his business lately, and what have you heard of the cause?
4. Have you lately heard of any citizen's thriving well, and by what means?
5. Have you lately heard of any hardship imposed on an innocent person? How may it be prevented or redressed?
6. Do you know of any deserving young beginner lately set up, whom it lies in the power of the junto in any way to encourage?
7. Have you lately observed any defect in the laws of your country, of which it would be proper to move the legislature for an amendment? Or do you know of any beneficial law that is wanting?
8. Is there any point of the town's management, which you know to be badly conducted, and which it might be proper to mention for some better methods?
9. Have you lately observed any encroachment on the just liberties of the people?
10. Have you any weighty affair on hand, in which you think the advice of the junto may be of service to you?
11. What benefits have you lately received from any man not present?
12. Is there any man whose friendship you want, and which the junto, or any of them, can procure for you?
13. Do you know of any deserving young gentleman in want of some financial support, who might merit assistance from the junto?
14. Have you lately heard any member's character attacked, and how have you defended it?
15. Hath any man injured you, from whom it is in the power of the junto to procure redress?
16. In what manner can the junto or any of them assist you in any of your honourable designs?
17. Have you any information to give of persons abroad or at home, which may be useful to any of the junto?
18. Is there any private or public affair, in which you think the junto's secrecy or assistance would be beneficial?
19. Do you see any opening for a lucrative trade or means of making money, of which the junto might take advantage?
20. Do you know any fellow-citizen who has lately done a worthy action, deserving praise and imitation?
21. Is there any point of natural philosophy, which you think it would be well to have discussed by men of learning?
22. Do you know of any fellow-citizen who has lately committed a mean action, deserving censure?
23. Hath any person or persons lately done anything to impede the public progress of knowledge, and how may it be counteracted?
24. Is there any step in our own personal conduct which we should correct or improve, that we may profit from the observations of our junto brethren?

---

## How It Works in the App

### Weekly rotation

A **deterministic weekly question** is derived from the current week number:

```python
FRANKLIN_QUESTIONS = [...]  # list of 24 strings

def current_question() -> dict:
    week_number = datetime.now(timezone.utc).isocalendar()[1]
    index = (week_number - 1) % len(FRANKLIN_QUESTIONS)
    return {
        "number": index + 1,
        "text": FRANKLIN_QUESTIONS[index],
        "week": week_number,
    }
```

This is stateless — no database entry needed. Every junto sees the same question this week, which creates a shared cultural moment across all groups on the platform.

### Displayed on the junto show page

Below the junto name and above the member list, a styled card shows the current question:

```
┌─────────────────────────────────────────────────────┐
│  This week's Franklin question  (Q7 of 24)          │
│                                                     │
│  "Have you lately observed any defect in the        │
│   laws of your country, of which it would be        │
│   proper to move the legislature for an             │
│   amendment? Or do you know of any beneficial       │
│   law that is wanting?"                             │
│                                                     │
│  — Benjamin Franklin, Junto Rules, 1727             │
└─────────────────────────────────────────────────────┘
```

A small "?" icon links to the About page section on the junto's history for users who want context.

### Optional: per-junto question override

The owner can pin a different question from the 24 for a given week, or skip the prompt entirely. This is a secondary feature — build the rotation first.

---

## Data Model

No new tables required for the basic rotation. The question is computed in Python from the current date.

If per-junto overrides are added later:

```python
class JuntoPromptOverride(db.Model):
    __tablename__ = "junto_prompt_override"

    id           = db.Column(db.Integer, primary_key=True)
    junto_id     = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)
    week_number  = db.Column(db.Integer, nullable=False)
    year         = db.Column(db.Integer, nullable=False)
    question_idx = db.Column(db.Integer)   # None = suppress prompt this week
```

Ship the MVP (read-only rotation) without this table.

---

## Implementation

### 1. Add the question list to a constants file

Create `src/juntos/franklin.py`:

```python
QUESTIONS = [
    "Have you met with any thing in the author you last read, remarkable, ...",
    # ... all 24
]

def weekly_question() -> dict | None:
    from datetime import datetime, timezone
    week = datetime.now(timezone.utc).isocalendar()[1]
    idx = (week - 1) % len(QUESTIONS)
    return {"number": idx + 1, "text": QUESTIONS[idx]}
```

### 2. Inject into the junto show template

In `routes/juntos.py`, in the `show` view:

```python
from juntos.franklin import weekly_question

@bp.route("/<int:id>")
def show(id):
    junto = db.get_or_404(Junto, id)
    return render_template(
        "juntos/show.html",
        junto=junto,
        prompt=weekly_question(),
    )
```

### 3. Render in `juntos/show.html`

```html
{% if prompt %}
<div class="franklin-prompt">
  <p class="prompt-label">This week's Franklin question <span>(Q{{ prompt.number }} of 24)</span></p>
  <blockquote>{{ prompt.text }}</blockquote>
  <cite>— Benjamin Franklin, Junto Rules, 1727</cite>
</div>
{% endif %}
```

---

## Why This Matters for Retention

A group that builds a habit around "what does the Franklin question say this week?" has a reason to open the app before every meeting. It also signals to new users — before they even create a group — that JuntosHQ has a point of view, not just features.

The 24-question cycle is 24 weeks, meaning groups on the platform will complete one full rotation roughly every 6 months. This creates a natural renewal conversation: "We've been through all 24 — and we're still meeting."

---

## Future Extensions

- **Question archive** — show past questions with links to log from those weeks' meetings
- **Discussion thread per question** — async text replies from members, visible on the meeting log
- **Custom question sets** — paid tier allows juntos to add their own questions to the rotation
- **Franklin vault** — curated quotes, aphorisms, and almanac entries surfaced alongside the weekly question
