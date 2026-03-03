# JuntosHQ — Alpha Release Status

*Last updated: 2026-03-03*

This document summarises what is built and working, what is partially done, and what must still be completed before releasing to a small alpha group.

---

## What Is Built and Working

### Infrastructure & Authentication

| Item | Status |
|---|---|
| Flask application factory (`create_app`) | ✅ Done |
| OAuth sign-in via Google and GitHub | ✅ Done |
| Signed session cookie; 7-day lifetime | ✅ Done |
| SQLAlchemy ORM (PostgreSQL in prod, SQLite for tests) | ✅ Done |
| Alembic migrations (6 migrations applied) | ✅ Done |
| Automated test suite (8 test files, ~31 tests) | ✅ Done |
| Mobile-responsive CSS (600 px breakpoint, nav wrap, stacked forms) | ✅ Done |
| Viewport meta tag in `base.html` | ✅ Done |

### Core Group Features

| Item | Status |
|---|---|
| Junto CRUD (create, view, edit, delete) | ✅ Done |
| Member CRUD (add, edit, delete; max 12 per junto) | ✅ Done |
| Meeting log (create/edit/delete, attendance checkboxes, Markdown notes) | ✅ Done |
| Owner-managed commitments with per-tier slot limits | ✅ Done |
| Franklin's 24 rotating weekly questions (stateless, ISO week) | ✅ Done |
| Weekly prompt displayed on junto show page | ✅ Done |

### Invite System

| Item | Status |
|---|---|
| Owner generates a per-member invite token | ✅ Done |
| Invite email via Flask-Mail (optional; graceful fallback) | ✅ Done |
| Member accepts invite via link → `user_id` linked to `Member` row | ✅ Done |

### Ben's Counsel AI Chatbot

| Item | Status |
|---|---|
| Anthropic Claude integration (`claude-sonnet-4-6`) | ✅ Done |
| RAG pipeline: Voyage AI embeddings + pgvector search against Franklin corpus | ✅ Done |
| System prompt grounded in Franklin's writings (`scripts/ben_system_prompt.txt`) | ✅ Done |
| Optional junto context injected into prompt | ✅ Done |
| 5-message free trial per user; `chatbot_addon` flag for paid access | ✅ Done |
| Chat session + message persistence (`ChatSession` / `ChatMessage` models) | ✅ Done |
| Chat UI (show page, junto-scoped chat page) | ✅ Done |

### Pages & Navigation

| Item | Status |
|---|---|
| Homepage with junto list | ✅ Done |
| Junto show page (members, meetings, prompt, commitments, Ben's Counsel card) | ✅ Done |
| Pricing page (tier cards + Ben's Counsel feature block) | ✅ Done |
| About page | ✅ Done |

---

## What Is Partially Done

### Subscription Tiers & Limit Enforcement

The **data model** records per-junto tier values (`JuntoTier.FREE / SUBSCRIPTION / EXPANDED`) and derives meeting-visibility and commitment-slot limits from them. However, the tier is stored on the **`Junto` row**, not on the **`User`** account. This means:

- There is no `User.subscription_tier` or `User.subscription_status` field.
- The junto-creation gate is **absent** — any signed-in user can create unlimited juntos.
- The feature docs describe enforcement at the user level (e.g., "you've reached your plan's junto limit"). That logic has no backing data.

Meeting-visibility limits (free = 1, standard = 3, expanded = 5) *are* applied on the show page and in the meetings blueprint, but they rely on `junto.tier` which defaults to `FREE` for every new junto. The numbers in the code also diverge from the feature docs (docs say free = last 3 meetings; code enforces 1).

### Pricing Page — Dead Links

Four links on the pricing page (`/pricing`) point to routes that do not exist:

| Link | Problem |
|---|---|
| `Get Started Free → /signup` | No `/signup` route; sign-in is via OAuth at `/auth/login` |
| `Add to any plan → /account/subscription/checkout?addon=chatbot` | No `account` blueprint |
| `Subscribe to Standard → /account/subscription/checkout?plan=standard` | Same — 404 |
| `Subscribe to Expanded → /account/subscription/checkout?plan=expanded` | Same — 404 |

### Stripe / Billing

Stripe payment integration is implemented in the `billing` blueprint (`src/juntos/routes/billing.py`). The feature covers:

| Component | Description |
|---|---|
| **Subscription checkout** | `GET /account/subscription/checkout?plan=<standard\|expanded>` — creates a Stripe Checkout Session for plan upgrades. |
| **Chatbot add-on checkout** | `GET /account/addon/chatbot/checkout` — creates a Stripe Checkout Session for the $4.99/month Ben's Counsel add-on; sets `User.chatbot_addon = True` on success. |
| **Success landings** | `GET /account/subscription/success` and `GET /account/addon/chatbot/success` — post-payment confirmation pages. |
| **Customer Portal** | `GET /account/subscription/portal` — redirects the user to the Stripe Billing Portal so they can update their card, view invoices, or cancel. |
| **Webhook** | `POST /stripe/webhook` — handles `checkout.session.completed` (upgrades tier or enables chatbot addon), `customer.subscription.deleted` (downgrades to FREE or disables chatbot addon), and `customer.subscription.updated` (syncs tier from active price ID). Verifies the Stripe-Signature header when `STRIPE_WEBHOOK_SECRET` is set. |
| **User model** | `User.stripe_customer_id` and `User.stripe_subscription_id` columns added (migration `e2f3a4b5c6d7`). `User.chatbot_addon` already existed. |
| **Pricing page** | All four CTA buttons now link to live checkout or login endpoints. |

**Required environment variables before enabling billing:**

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STANDARD=price_...   # Monthly Standard price ID from Stripe dashboard
STRIPE_PRICE_EXPANDED=price_...   # Monthly Expanded price ID from Stripe dashboard
STRIPE_PRICE_CHATBOT=price_...    # Monthly Ben's Counsel add-on price ID
```

If `STRIPE_SECRET_KEY` is absent the checkout routes fall back to a "coming soon" flash message — safe for the free-only alpha.

---

## Remaining Tasks Before Alpha Release

### Must-Fix (Blockers)

1. **Fix pricing page links**
   - Change `Get Started Free` to point to `/auth/login`.
   - Change the three `Subscribe` / `Add to any plan` links to a "coming soon" placeholder (e.g., redirect to `/pricing` with a flash message, or render a waiting-list form).

2. **Add junto-creation limit**
   - Add a free-tier cap (1 junto) in `juntos.new` and `juntos.create`.
   - A user with no subscription should be blocked from creating a second junto, with a clear message linking to `/pricing`.
   - This can be based on `len(g.current_user.juntos)` until a proper `User.subscription_tier` field is introduced.

3. **Add `User.subscription_tier` field**
   - Add a `subscription_tier` column to `User` (enum: `free` / `standard` / `expanded`; default `free`).
   - Wire junto-creation and meeting-visibility limits to this user field instead of the per-junto tier.
   - Generate and apply an Alembic migration.

4. ~~**Align meeting visibility limits**~~ ✅ Resolved — canonical limits are **Free = 1, Standard = 3, Expanded = 5** (per-junto tier). Pricing page and `Junto._TIER_MEETING_LIMITS` are consistent.

### Should-Do Before Alpha (Not Hard Blockers)

5. **Upgrade banners / conversion prompts**
   - When a free user tries to create a second junto: show the "You've reached the Free tier limit" card (see `free-tier.md`).
   - When a user is on free tier and meeting history is truncated: show "N older meetings hidden. Upgrade to see them all."

6. **Export (CSV/PDF)**
   - Standard-tier feature. Not implemented. The Standard tier description on the pricing page lists it as included.
   - Minimum viable: add placeholder buttons that explain the feature is coming, rather than routing to a 404.

7. **Self-reporting commitments**
   - Standard-tier feature. Currently only the owner can edit commitments for any member.
   - Minimum viable: display a notice on the junto page explaining that self-reporting is a Standard feature.

8. **Custom discussion prompts**
   - Expanded-tier feature. Not implemented.

9. **`/auth/login` redirects to correct page after accept-invite**
   - Verify the invite-accept flow works end-to-end when the user is not yet signed in (redirect chain: invite link → OAuth → back to accept URL).

10. **Production deployment checklist**
    - PostgreSQL connection string with pgvector extension enabled.
    - `SECRET_KEY` set to a long random value (not the default `dev-secret`).
    - OAuth credentials (Google + GitHub) configured for the production domain.
    - `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` set for the chatbot to work.
    - `MAIL_SERVER` configured if invite emails are desired.
    - Run `alembic upgrade head` before starting the server.
    - Franklin corpus seeded into pgvector (`scripts/seed_franklin.py`).

### Nice-to-Have (Post-Alpha)

- Junto-creation limit banners on the homepage (disabled "Create Junto" button with upgrade prompt).
- Meeting-count cap enforcement (currently history is soft-limited by visibility; the Standard/Expanded hard cap on total meetings per junto is not enforced at write time).
- Annual pricing (`$49.99/yr`, `$99.99/yr`) — not implemented.
- Billing cancel / resume flow.
- Ben's Counsel chatbot add-on billing integration.
- Franklin's 13 Virtues tracker.
- Export to PDF (requires a PDF library not yet in dependencies).
- Voice mode for Ben's Counsel.
- Member attendance-rate statistics.
- Full-text search across meeting notes.

---

## Feature Completion Matrix

| Feature | Free Tier | Standard Tier | Expanded Tier |
|---|---|---|---|
| Junto CRUD | ✅ Works | ✅ Works | ✅ Works |
| Member CRUD | ✅ Works | ✅ Works | ✅ Works |
| Meeting log | ✅ Works | ✅ Works | ✅ Works |
| Meeting history limit | ✅ 1 (per-junto tier) | ✅ 3 (per-junto tier) | ✅ 5 (per-junto tier) |
| Commitments (owner-managed) | ✅ Works | ✅ Works | ✅ Works |
| Commitments (self-reporting) | N/A | ❌ Not built | ❌ Not built |
| Weekly Franklin prompt | ✅ Works | ✅ Works | ✅ Works |
| Custom discussion prompts | N/A | N/A | ❌ Not built |
| Invite links | ✅ Works | ✅ Works | ✅ Works |
| Export CSV/PDF | N/A | ❌ Not built | ❌ Not built |
| Ben's Counsel chatbot (add-on) | ✅ Trial works; ✅ Billing integrated | ✅ Trial works; ✅ Billing integrated | ✅ Trial works; ✅ Billing integrated |
| Junto creation limit (1/3/5) | ❌ Not enforced | ❌ Not enforced | ❌ Not enforced |
| Billing / Stripe | ✅ Chatbot add-on checkout | ✅ Checkout + chatbot add-on | ✅ Checkout + chatbot add-on |
| Mobile layout | ✅ Done | ✅ Done | ✅ Done |

---

## Short Alpha Checklist

The following six items are the minimum to ship a coherent alpha to real users:

- [ ] Fix 4 broken links on the pricing page
- [ ] Add junto-creation limit based on `User.subscription_tier` (Free = 1, Standard = 3, Expanded = 5)
- [x] Meeting-visibility limits confirmed: Free = 1, Standard = 3, Expanded = 5 (per-junto tier)
- [ ] Show "upgrade" banners when free-tier limits are hit
- [ ] Verify end-to-end invite → OAuth → accept flow on production domain
- [ ] Production environment checklist complete (API keys, DB, secret key)
