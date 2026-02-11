# Feature: Unlimited Tier ($9.99/month)

## What It Is

The Unlimited tier removes all capacity limits and unlocks every feature in JuntosHQ. It targets power users: coaches who run multiple accountability groups, community organizers managing a network of juntos, or anyone who simply doesn't want to think about limits.

**Price**: $9.99/month (future: $99.99/year — 2 months free)

---

## What's Included

| Feature | Unlimited Tier |
|---|---|
| Juntos | Unlimited |
| Members per junto | 12 |
| Log meetings | Yes |
| Visible meeting history | Unlimited (full archive) |
| Commitment tracking | Self-reporting enabled |
| Weekly Franklin prompts | Yes |
| Custom discussion prompts | Yes |
| Member invite links | Yes |
| Export (CSV/PDF) | Yes |
| Priority support | Yes |
| Ben Franklin Chatbot | Available as add-on ($4.99/mo) |

---

## Why $9.99

### Double the Standard price, but not painful

The jump from $4.99 to $9.99 is small enough that a Standard user who hits limits will upgrade without serious deliberation. The total cost is still under $10/month — less than most streaming services.

### Captures the highest-value users

Users who run 6+ juntos or need full meeting archives are the most engaged. They're also the least likely to churn. Charging them $9.99 instead of $4.99 captures more revenue from users who would happily pay more.

### Leaves room for future enterprise pricing

If JuntosHQ eventually adds team/org accounts, those can be priced at $29.99+ per month. The Unlimited tier at $9.99 stays positioned as the individual power-user plan, not the enterprise plan.

---

## Key Features Unlocked (Beyond Standard)

### 1. Unlimited Juntos

No cap. Create as many juntos as needed. The "New Junto" button always works.

Use cases:
- A leadership coach running 10 mastermind groups
- A church with 8 small groups, each with its own junto
- A community organizer with neighborhood, civic, and professional groups
- Someone who just doesn't want to count

### 2. Unlimited Meeting History

Every meeting ever logged is visible. No rolling window, no hidden history. The full archive is searchable and exportable.

This matters most for long-running groups. A junto that's been meeting weekly for 2 years has 100+ meetings. On Standard (25 limit), 75% of their history would be hidden. On Unlimited, it's all there.

### 3. Custom Discussion Prompts

Unlimited users can add their own discussion questions to the weekly rotation, supplementing Franklin's 24 with group-specific prompts.

```
Discussion Prompts for "Portland Book Club"
────────────────────────────────────────────
Week rotation: Franklin's 24 + 3 custom

Custom prompts:
1. "What passage from this month's book challenged your assumptions?"
2. "How has your reading habit changed since joining the group?"
3. "What book should we read next, and why?"

[+ Add custom prompt]  [Edit rotation order]
```

#### How custom prompts work

- Franklin's 24 questions remain in the rotation — they can't be removed
- Custom prompts are interleaved: weeks 1-24 are Franklin's, weeks 25+ are custom, then the cycle repeats
- Alternatively, the owner can set a custom order or pin a specific prompt for any week
- Custom prompts are per-junto, not per-user

#### Data model

```python
class CustomPrompt(db.Model):
    __tablename__ = "custom_prompt"

    id        = db.Column(db.Integer, primary_key=True)
    junto_id  = db.Column(db.Integer, db.ForeignKey("junto.id"), nullable=False)
    text      = db.Column(db.Text, nullable=False)
    position  = db.Column(db.Integer, nullable=False)  # order in the custom rotation
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
```

### 4. Priority Support

Unlimited users get a "Contact Support" link in their account page that goes to a dedicated email or form. Response commitment: within 24 hours on business days.

This is a low-cost differentiator. At the scale of early users, all support is effectively priority support. But naming it as a tier benefit makes Unlimited feel premium.

---

## Who This Tier Is For

### Profile 1: The Multi-Group Leader

Runs 6-10 groups across different contexts (work, personal, community). Needs all of them in one place with full history. Would pay more if asked.

### Profile 2: The Coach or Facilitator

Runs accountability groups professionally. Meeting history and commitment data are client deliverables. Export and archive features are essential. May eventually need team/org features.

### Profile 3: The "Just Remove the Limits" Person

Runs 2-3 groups but hates seeing limit banners. Would rather pay $10/month than think about whether they're approaching a cap. This person is surprisingly common and very low-churn.

---

## Upgrade Path from Standard

The upgrade triggers are:

1. **6th junto attempt** — "You've hit the Standard limit. Upgrade to Unlimited for no limits."
2. **26th meeting on a junto** — "Your oldest meeting just rolled off. Unlimited keeps everything."
3. **Custom prompt attempt** — "Custom discussion prompts are an Unlimited feature."
4. **Account page** — persistent "Upgrade to Unlimited" option with feature comparison

### Upgrade flow

1. User clicks "Upgrade" → `/pricing` with Unlimited highlighted
2. Stripe updates the existing subscription (proration handled automatically)
3. Webhook updates `subscription.tier` to `"unlimited"`
4. All limits removed immediately

Stripe handles proration natively: the user is charged the difference for the remainder of the current billing period, then the new rate kicks in on the next cycle.

---

## Routes (Unlimited-specific)

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/juntos/<jid>/prompts` | owner + Unlimited | Manage custom prompts |
| POST | `/juntos/<jid>/prompts` | owner + Unlimited | Add custom prompt |
| POST | `/juntos/<jid>/prompts/<pid>/edit` | owner + Unlimited | Edit custom prompt |
| POST | `/juntos/<jid>/prompts/<pid>/delete` | owner + Unlimited | Remove custom prompt |
| GET | `/account/support` | Unlimited | Priority support form |

---

## Downgrade Behavior

When an Unlimited user downgrades to Standard:

1. Juntos beyond the Standard limit (5) become read-only. User must archive extras to create new ones.
2. Meeting history beyond 25 per junto is hidden (not deleted).
3. Custom prompts are preserved in the database but stop appearing in the rotation. The junto reverts to Franklin's 24 only.
4. Priority support link disappears.
5. All data is preserved. Re-upgrading restores everything.

When downgrading to Free:

- Same as above, plus Standard features (invite links, export, self-reporting) are also reverted.
- Only 1 junto is accessible; the rest are read-only.

---

## Future Considerations

- **Annual pricing**: $99.99/year (save ~$20) to reduce churn and improve cash flow
- **Team/org accounts**: Multiple Unlimited users under one billing entity — this is a separate tier above Unlimited, not a replacement
- **API access**: Unlimited users could get API access to their data for integrations — a future differentiator
- **White-label**: For coaches who want their own branding on the junto experience — premium add-on above Unlimited

---

## Related Docs

- [Subscription Tiers](subscription-tiers.md) — full comparison and billing architecture
- [Standard Tier](standard-tier.md) — what most users will pay for
- [Free Tier](free-tier.md) — the entry point
- [Discussion Prompts](discussion-prompts.md) — Franklin's 24 questions and custom prompts
