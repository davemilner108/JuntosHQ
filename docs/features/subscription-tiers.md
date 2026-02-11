# Feature: Subscription Tiers

## Overview

JuntosHQ monetizes through a three-tier subscription model that gates capacity and features, plus an optional AI add-on. The tiers are designed around a natural growth curve: a user starts free with one junto, hits the limit as they get serious, and upgrades when the app has already proven its value.

The pricing targets individuals and small community leaders — not enterprises. The numbers are low enough that a single motivated person pays without needing budget approval.

| Tier | Price | Juntos | Meetings per Junto | Key Differentiators |
|---|---|---|---|---|
| **Free** | $0 | 1 | Unlimited (last 3 visible) | Try before you buy; single-group use |
| **Standard** | $4.99/mo | 5 | 25 per junto (full history) | Multi-group leaders, full meeting archive |
| **Unlimited** | $9.99/mo | Unlimited | Unlimited | Power users, organizations, everything unlocked |

**Add-on**: Ben Franklin AI Chatbot — $4.99/mo, available on any tier.

---

## Why Three Tiers

### Free gets people in the door

A free user can run a single junto with full member management, weekly discussion prompts, and basic meeting logging. This is enough to run one group for months before wanting more. The limit on visible meeting history (last 3) creates a natural pull toward paid — the data is there, they just can't see it.

### Standard captures the typical paying user

Most community-minded people run 2-3 groups (a book club, a professional mastermind, a neighborhood board). Five juntos covers this comfortably. The 25-meeting limit per junto means roughly 6 months of weekly meetings before hitting the cap — long enough to prove value, short enough to eventually upsell.

### Unlimited removes all friction

For power users, coaches, or organizations that run many groups. No limits, no thinking about limits. The jump from $4.99 to $9.99 is small enough that anyone annoyed by limits will just upgrade rather than manage around them.

---

## Revenue Model

### Assumptions (conservative)

| Metric | Value |
|---|---|
| Free users (Year 1) | 1,000 |
| Free → Standard conversion | 8% |
| Standard → Unlimited conversion | 15% of Standard |
| Chatbot add-on attach rate | 10% of all paid |
| Monthly churn (paid) | 5% |

### Monthly Recurring Revenue (steady state, Year 1)

| Tier | Users | MRR |
|---|---|---|
| Standard | 80 | $399.20 |
| Unlimited | 12 | $119.88 |
| Chatbot add-on | ~9 | $44.91 |
| **Total** | | **$563.99** |

These are deliberately conservative. The real leverage is in reducing churn — once meeting history and commitment data accumulate, switching cost is high.

---

## Feature Matrix

| Feature | Free | Standard | Unlimited |
|---|---|---|---|
| Create juntos | 1 | 5 | Unlimited |
| Members per junto | 12 | 12 | 12 |
| Log meetings | Yes | Yes | Yes |
| View meeting history | Last 3 | 25 per junto | Unlimited |
| Commitment tracking | Owner-managed | Self-reporting | Self-reporting |
| Weekly Franklin prompts | Yes | Yes | Yes |
| Custom discussion prompts | No | No | Yes |
| Export meetings (CSV/PDF) | No | Yes | Yes |
| Member invite links | No | Yes | Yes |
| Priority support | No | No | Yes |
| Ben Franklin Chatbot | Add-on ($4.99) | Add-on ($4.99) | Add-on ($4.99) |

---

## Limit Enforcement Strategy

### Soft vs. hard limits

- **Junto count**: Hard limit. The "New Junto" button is hidden or disabled when at capacity. If a user downgrades, existing juntos remain accessible (read-only) but no new ones can be created until they're under the limit or re-upgrade.
- **Meeting history visibility**: Soft limit. All meetings are stored in the database regardless of tier. The view layer filters what's shown. Upgrading instantly reveals full history — no data loss, instant gratification.
- **Meeting count per junto**: Hard limit on Standard tier. Once 25 meetings are logged for a single junto, logging is disabled for that junto with a prompt to upgrade.

### Downgrade behavior

When a user downgrades from a higher tier:
1. All data is preserved — nothing is deleted.
2. If they have more juntos than the new tier allows, all juntos become read-only. The user must archive juntos to get back under the limit before creating new ones.
3. Meeting history beyond the tier's visible limit is hidden but not deleted.
4. Commitments revert to owner-managed mode (no self-reporting).

This "data hostage" approach is standard in SaaS and is fair because nothing is destroyed — the user just needs to pay to see it all again.

---

## Payment Infrastructure

### Recommended: Stripe

- Stripe Checkout for initial subscription
- Stripe Customer Portal for self-service plan changes, cancellations, payment method updates
- Stripe Webhooks for real-time subscription state sync

### Data model additions

```python
class Subscription(db.Model):
    __tablename__ = "subscription"

    id                    = db.Column(db.Integer, primary_key=True)
    user_id               = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    tier                  = db.Column(db.Enum("free", "standard", "unlimited", name="subscription_tier"),
                                     nullable=False, default="free")
    stripe_customer_id    = db.Column(db.String(255), nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    chatbot_addon         = db.Column(db.Boolean, nullable=False, default=False)
    current_period_end    = db.Column(db.DateTime, nullable=True)
    status                = db.Column(db.String(50), nullable=False, default="active")  # active, past_due, canceled
    created_at            = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at            = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                      onupdate=lambda: datetime.now(timezone.utc))
```

Add to `User`:
```python
subscription = db.relationship("Subscription", backref="user", uselist=False, lazy=True)
```

### Helper for tier checks

```python
def user_tier(user) -> str:
    if user.subscription is None:
        return "free"
    if user.subscription.status != "active":
        return "free"
    return user.subscription.tier

def can_create_junto(user) -> bool:
    tier = user_tier(user)
    limits = {"free": 1, "standard": 5, "unlimited": float("inf")}
    return len(user.juntos) < limits[tier]

def visible_meeting_limit(user) -> int | None:
    tier = user_tier(user)
    limits = {"free": 3, "standard": 25, "unlimited": None}
    return limits[tier]

def has_chatbot_access(user) -> bool:
    if user.subscription is None:
        return False
    return user.subscription.chatbot_addon and user.subscription.status == "active"
```

---

## Routes

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/pricing` | — | Public pricing page |
| GET | `/account/subscription` | user | Current plan details |
| POST | `/account/subscription/checkout` | user | Create Stripe Checkout session |
| POST | `/account/subscription/portal` | user | Redirect to Stripe Customer Portal |
| POST | `/webhooks/stripe` | — | Stripe webhook endpoint (signature verified) |

---

## Pricing Page Design

The pricing page is the primary conversion point. It should:

1. Show all three tiers side-by-side (single column on mobile)
2. Highlight Standard as the "most popular" (even before it is — social proof priming)
3. Show the chatbot add-on as a separate card below the tiers
4. Include a FAQ section addressing: "What happens to my data if I cancel?", "Can I change plans?", "Is there a free trial?"
5. Use annual pricing option later (e.g., $49.99/year for Standard = 2 months free)

---

## Implementation Priority

1. **Subscription model + tier helpers** — get the data layer right first
2. **Stripe integration** — Checkout + webhooks for Standard and Unlimited
3. **Limit enforcement in views** — junto creation gate, meeting history filter
4. **Pricing page** — public-facing conversion page
5. **Account subscription management** — via Stripe Customer Portal
6. **Chatbot add-on billing** — separate line item on the Stripe subscription
7. **Downgrade handling** — graceful read-only behavior

---

## Related Docs

- [Free Tier](free-tier.md)
- [Standard Tier](standard-tier.md)
- [Unlimited Tier](unlimited-tier.md)
- [Ben Franklin Chatbot](ben-franklin-chatbot.md)
