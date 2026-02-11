# Feature: Free Tier

## What It Is

The Free tier is the entry point for every JuntosHQ user. It provides enough functionality to run a single junto group with full member management, weekly Franklin discussion prompts, and basic meeting logging. The goal is to let someone experience the core value of the app — organizing and running a junto — without paying anything.

**Price**: $0 forever. No credit card required to sign up.

---

## What's Included

| Feature | Free Tier Limit |
|---|---|
| Juntos | 1 |
| Members per junto | 12 (same as all tiers) |
| Log meetings | Yes |
| Visible meeting history | Last 3 meetings |
| Commitment tracking | Owner-managed only |
| Weekly Franklin prompts | Yes |
| Custom discussion prompts | No |
| Export (CSV/PDF) | No |
| Member invite links | No |
| Ben Franklin Chatbot | Available as add-on ($4.99/mo) |

---

## Why These Limits

### 1 junto — enough to prove value, not enough to stay forever

A user running a single book club or mastermind group can do everything they need on Free. But the moment they want to start a second group — a neighborhood board, a work accountability circle — they need Standard. This is the most natural upgrade trigger because it happens when the user is *already enthusiastic about the app*.

### 3 visible meetings — the data accumulates but hides

All meetings are stored. The user logs meeting 4 and suddenly can't see meeting 1 anymore. The prompt to upgrade shows the count of hidden meetings: "You have 12 meetings in your history. Upgrade to see them all." This is the second strongest upgrade trigger because the value is already created — the user just needs to pay to access it.

### Owner-managed commitments — works but creates friction

On Free, only the junto owner can set and update commitment statuses for members. Members can't self-report. This means the owner has to manually check in with each member and update the app. It works for small groups where the owner is disciplined, but it's tedious. The paid tiers unlock self-reporting, which removes this friction and makes the commitment loop genuinely peer-driven.

### No invite links — manual member management only

Free tier members are added by the owner typing in names and roles. There's no way for a member to claim their own seat by clicking a link. This limits the collaborative feel and makes the upgrade to Standard appealing for groups that want true multi-user participation.

---

## User Experience

### Sign-up flow

1. User clicks "Sign up" → OAuth with Google or GitHub
2. Account is created with `subscription.tier = "free"` (or no Subscription row, which defaults to free)
3. User lands on the homepage with a prompt: "Create your first junto"
4. No paywall, no trial countdown, no "14 days remaining" banner

### Creating a junto

The "New Junto" button works normally for the first junto. After one junto exists, the button is replaced with:

```
┌─────────────────────────────────────────────┐
│  You've reached the Free tier limit (1/1).  │
│  Upgrade to Standard to create up to 5.     │
│                                             │
│  [See plans →]                              │
└─────────────────────────────────────────────┘
```

### Meeting history

The junto show page displays the most recent 3 meetings. If more exist, a banner appears below:

```
Meetings
────────────────────────────────────────
Feb 6, 2026 · 5 attended · View →
Jan 30, 2026 · 4 attended · View →
Jan 23, 2026 · 6 attended · View →

┌─────────────────────────────────────┐
│  9 older meetings in your history.  │
│  Upgrade to see them all.           │
│  [Upgrade →]                        │
└─────────────────────────────────────┘
```

### Commitment tracking

The commitments section shows current commitments but all status changes go through the owner:

```
Current Commitments  (cycle: Feb 6 – Feb 13)
──────────────────────────────────────────────
Alice   Read two chapters   [Set status ▾]  ← owner dropdown
Bob     Write one page      [Set status ▾]
Carol   (no commitment set)

ℹ  Upgrade to let members check in themselves.
```

---

## Enforcement Logic

### Junto creation gate

```python
@bp.route("/new")
@login_required
def new():
    if not can_create_junto(g.current_user):
        flash("You've reached your plan's junto limit. Upgrade to create more.")
        return redirect(url_for("main.pricing"))
    return render_template("juntos/new.html")
```

### Meeting history filter

```python
def get_visible_meetings(junto, user):
    limit = visible_meeting_limit(user)
    query = Meeting.query.filter_by(junto_id=junto.id).order_by(Meeting.held_on.desc())
    if limit is not None:
        return query.limit(limit).all(), query.count()
    return query.all(), query.count()
```

The template receives both the visible list and the total count, so it can display "N older meetings hidden."

---

## What Free Users Cannot Do

- Create more than 1 junto
- View meeting history beyond the 3 most recent
- Export meeting data
- Use member invite links (members are owner-added only)
- Allow members to self-report commitment status
- Add custom discussion prompts
- Use the Ben Franklin Chatbot (unless purchased as add-on)

---

## Conversion Triggers (Upgrade Prompts)

These are the moments where a Free user naturally encounters the limit:

1. **Second junto attempt** — "Upgrade to create more groups"
2. **4th meeting logged** — "Your oldest meeting is now hidden. Upgrade to see your full history."
3. **Member asks to self-report** — "Invite links and self-reporting require Standard or above."
4. **Weekly Franklin prompt** — subtle footer: "Want your group to discuss custom questions? Upgrade to Unlimited."

Each trigger links to `/pricing` with a `?source=` parameter for conversion tracking.

---

## Related Docs

- [Subscription Tiers](subscription-tiers.md) — full tier comparison and billing architecture
- [Standard Tier](standard-tier.md) — the next step up
- [Expanded Tier](expanded-tier.md) - more room to grow for leaders