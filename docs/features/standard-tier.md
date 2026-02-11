# Feature: Standard Tier ($4.99/month)

## What It Is

The Standard tier is the primary revenue tier for JuntosHQ. It targets the community-minded person who runs multiple groups — a book club and a mastermind, a church small group and a volunteer board. At $4.99/month, it's priced below the threshold where most individuals need to think twice.

**Price**: $4.99/month (future: $49.99/year — 2 months free)

---

## What's Included

| Feature | Standard Tier |
|---|---|
| Juntos | Up to 5 |
| Members per junto | 12 |
| Log meetings | Yes |
| Visible meeting history | 25 per junto |
| Commitment tracking | Self-reporting enabled |
| Weekly Franklin prompts | Yes |
| Custom discussion prompts | No |
| Member invite links | Yes |
| Export (CSV/PDF) | Yes |
| Priority support | No |
| Ben Franklin Chatbot | Available as add-on ($4.99/mo) |

---

## Why $4.99

### Low enough for impulse purchase

$4.99 is a coffee. If the app has already proven useful during the Free tier, there's almost no deliberation. The user doesn't need to justify it to a spouse, a boss, or their budget spreadsheet.

### High enough to signal value

Free apps feel disposable. $4.99 says "this is worth something" without feeling expensive. It also filters for users who are actually engaged — paying users churn less and provide better feedback.

### Competitive positioning

Most group management tools (Meetup, GroupMe, Band) are either free-with-ads or enterprise-priced. $4.99 with no ads and a unique Franklin-based methodology sits in unclaimed territory.

---

## Key Features Unlocked

### 1. Up to 5 Juntos

The junto creation limit increases from 1 to 5. The "New Junto" button works normally until 5 juntos exist. At 5:

```
┌─────────────────────────────────────────────┐
│  You've reached the Standard limit (5/5).   │
│  Upgrade to Unlimited for no limits.        │
│                                             │
│  [See plans →]                              │
└─────────────────────────────────────────────┘
```

Five juntos covers the vast majority of individual organizers. Only people running an organization or coaching practice need more.

### 2. 25 Meetings per Junto (Full Visible History)

Meeting history expands from 3 to 25 per junto. For a weekly meeting cadence, that's roughly 6 months of history. The user can scroll back, search, and reference past discussions.

When meeting 26 is logged, meeting 1 rolls off the visible list:

```
┌──────────────────────────────────────────────────┐
│  2 older meetings hidden.                        │
│  Upgrade to Unlimited for full history forever.  │
│  [Upgrade →]                                     │
└──────────────────────────────────────────────────┘
```

### 3. Self-Reporting Commitments

Members can claim their seat via invite link and self-report their commitment status. This transforms the commitment loop from owner-managed busywork into genuine peer accountability.

The workflow:
1. Owner sends an invite link (generated per-junto)
2. Member clicks link, signs in with OAuth, and is linked to their `Member` record
3. Member sees their own commitment card with status buttons
4. Check-in is instant — tap "Done" and it saves

This is the feature that creates daily active use. Members open the app between meetings to mark their commitment complete.

### 4. Member Invite Links

Each junto gets a unique invite URL. The owner shares it via text, email, or group chat. When a member visits the link:

1. If not signed in → redirect to OAuth → back to invite
2. If already a member → redirect to junto page
3. If junto has space → create link between `User` and `Member` → redirect to junto page
4. If junto is full (12 members) → show "This junto is full" message

```
Invite members to "Portland Book Club"
───────────────────────────────────────
Share this link:
https://juntoshq.com/juntos/7/invite/abc123def

[Copy link]  [Regenerate link]
```

The owner can regenerate the link to invalidate the old one.

### 5. Export to CSV/PDF

Standard users can export meeting history and commitment data:

- **Meetings CSV**: date, attendee count, attendee names, notes (truncated)
- **Meetings PDF**: formatted meeting log suitable for printing or archiving
- **Commitments CSV**: member, commitment text, status, cycle date

Export buttons appear on the junto show page:

```
[Export meetings ▾]
  → CSV
  → PDF
```

---

## Upgrade Path from Free

When a Free user hits a limit, the upgrade flow is:

1. User clicks "Upgrade" or "See plans" from any limit banner
2. Redirected to `/pricing` with the Standard tier highlighted
3. Clicks "Subscribe" → Stripe Checkout session
4. Completes payment → webhook updates `subscription.tier` to `"standard"`
5. Redirected back to the app → all Standard features immediately active
6. Hidden meeting history becomes visible instantly
7. "New Junto" button works again (up to 5)

### First-time upgrade experience

On the first page load after upgrading, show a brief confirmation:

```
┌─────────────────────────────────────────────────┐
│  Welcome to Standard!                           │
│                                                 │
│  You can now:                                   │
│  • Create up to 5 juntos                        │
│  • See your full meeting history (25 per grupo) │
│  • Invite members with a link                   │
│  • Export your data                             │
│                                                 │
│  [Got it →]                                     │
└─────────────────────────────────────────────────┘
```

---

## Upgrade Triggers to Unlimited

Standard users see Unlimited prompts when they:

1. **Hit 5 juntos** — "Need more groups? Unlimited has no cap."
2. **Hit 25 meetings on a junto** — "Your oldest meeting just rolled off. Unlimited keeps everything."
3. **Try to add custom prompts** — "Custom discussion questions are an Unlimited feature."

---

## Data Model

No separate model — the Standard tier is a value in the `Subscription.tier` enum. Tier-specific logic lives in helper functions (see [Subscription Tiers](subscription-tiers.md)).

### Invite link model

```python
class JuntoInvite(db.Model):
    __tablename__ = "junto_invite"

    id        = db.Column(db.Integer, primary_key=True)
    junto_id  = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)
    token     = db.Column(db.String(64), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
```

Generate tokens with `secrets.token_urlsafe(32)`. Regenerating a link sets the old one to `is_active=False` and creates a new row.

---

## Routes (Standard-specific)

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/juntos/<jid>/invite` | owner + Standard+ | Show/generate invite link |
| POST | `/juntos/<jid>/invite/regenerate` | owner + Standard+ | Create new invite token |
| GET | `/juntos/<jid>/join/<token>` | user | Accept invite and join junto |
| GET | `/juntos/<jid>/export/meetings.csv` | owner + Standard+ | Export meetings as CSV |
| GET | `/juntos/<jid>/export/meetings.pdf` | owner + Standard+ | Export meetings as PDF |
| GET | `/juntos/<jid>/export/commitments.csv` | owner + Standard+ | Export commitments as CSV |

"Standard+" means the user must be on Standard or Unlimited tier.

---

## Cancellation Behavior

When a Standard user cancels:

1. Access continues until `current_period_end`
2. After period ends, `subscription.status` changes to `"canceled"` (via Stripe webhook)
3. Account reverts to Free tier behavior:
   - All juntos remain but become read-only if more than 1 exists
   - Meeting history collapses to last 3 visible
   - Invite links stop working
   - Export buttons disappear
   - Commitments revert to owner-managed
4. All data is preserved — re-subscribing restores full access instantly

---

## Related Docs

- [Subscription Tiers](subscription-tiers.md) — full comparison and billing architecture
- [Free Tier](free-tier.md) — what users start with
- [Unlimited Tier](unlimited-tier.md) — the next step up
- [Commitments Tracking](commitments-tracking.md) — self-reporting details
