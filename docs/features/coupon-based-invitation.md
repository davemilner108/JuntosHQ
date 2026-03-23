# Feature: Coupon-Based Invitation (Beta Gate)

## What It Is

JuntosHQ uses a coupon-based invitation system to control access during the beta period. New users cannot use the application until they enter a valid one-time coupon code. This keeps the early rollout small and deliberate while giving existing members a way to bring in the people they trust.

Coupon gating is controlled by the `INVITE_REQUIRED` configuration flag. When enabled:

- Every new account starts as **unverified** (`signup_verified = False`).
- Any attempt to access the app redirects the user to the coupon entry page (`/auth/coupon`).
- Entering a valid code sets `signup_verified = True` and immediately grants full access.
- The user is then awarded a personal pool of shareable coupon codes they can pass on to friends.

When `INVITE_REQUIRED` is `False` (e.g., in tests or after the public launch), new accounts are verified automatically and no coupon entry is shown.

---

## How to Sign Up

### Step 1 — Click "Sign in"

Visit JuntosHQ and click the **Sign in** button in the navigation bar. You will be taken to the sign-in page (`/auth/login`).

### Step 2 — Choose an OAuth provider

Click either **Sign in with Google** or **Sign in with GitHub**. You will be redirected to the chosen provider to authenticate. No password is created or stored in JuntosHQ.

### Step 3 — Enter your coupon code

After a successful OAuth login, new users are redirected to the coupon entry page (`/auth/coupon`):

```
┌──────────────────────────────────────────────────────────┐
│  Welcome to JuntosHQ Beta                                │
│                                                          │
│  JuntosHQ is currently in an invite-only beta. Please    │
│  enter your signup coupon code below to activate your    │
│  account.                                                │
│                                                          │
│  Coupon Code: [ _____________________________ ]          │
│                                                          │
│  [ Activate Account ]                                    │
│                                                          │
│  Don't have a coupon? Ask a friend who is already on     │
│  JuntosHQ — each member has sharable invite codes.       │
└──────────────────────────────────────────────────────────┘
```

Enter the code exactly as it was shared with you and click **Activate Account**.

- If the code is valid and unused, your account is activated immediately.
- If the code is invalid or already used, an error message is shown and you can try again.

### Step 4 — You're in

On success you are redirected to the homepage with the message:

> *Welcome to JuntosHQ! Your signup coupon has been accepted.*

Your account is now fully active and you are given a personal set of coupon codes (10 by default) that you can share with friends.

---

## Where to Find Your Coupons

Once your account is verified, your personal coupon codes are always one click away.

**Navigation bar → "My Coupons"** (visible when signed in)

This takes you to `/auth/my-coupons`, which shows a table of every code you own:

```
My Invite Coupons
─────────────────────────────────────────────────
Share these codes with friends so they can join JuntosHQ.
Each code can only be used once.

┌───────────────────────────┬──────────────┐
│ Coupon Code               │ Status       │
├───────────────────────────┼──────────────┤
│ XkQ9vLmR2oPnBcTd          │ Available    │
│ aG7hJwYe1fZsUvNq          │ Available    │
│ Cp3DxMkL8rEiOtWj          │ Used         │
│ …                         │ …            │
└───────────────────────────┴──────────────┘
```

- **Available** — the code has not been used yet and can be shared.
- **Used** — a friend has already redeemed this code.

Each newly verified user receives 10 available codes. The number of codes granted is controlled by the `COUPONS_PER_USER` configuration value.

---

## How to Forward a Coupon to a Friend

There is no automated email or "send invite" button. Sharing is intentionally manual so that you choose who gets your codes:

1. Go to **My Coupons** (`/auth/my-coupons`).
2. Pick any code with the **Available** status.
3. Copy the code (e.g., `XkQ9vLmR2oPnBcTd`).
4. Send it to your friend via any channel — email, text, Slack, etc. — along with the link to JuntosHQ.

Your friend then:

1. Visits JuntosHQ and clicks **Sign in**.
2. Authenticates with Google or GitHub.
3. Is redirected to the coupon entry page and enters the code you gave them.
4. Their account is activated and they receive their own 10 codes to share further.

Once a code is redeemed its status changes to **Used** in your coupon list. Each code works exactly once.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `INVITE_REQUIRED` | `true` | Set to `false` to disable coupon gating entirely (e.g., after public launch). New users are verified automatically. |
| `HARD_CODED_COUPON` | `JUNTOS-BETA-2024` | A single master code accepted by the system without consuming a database coupon row. Useful for onboarding the very first users before the coupon chain has started. |
| `COUPONS_PER_USER` | `10` | How many personal coupon codes each newly verified user receives. |

---

## Data Model

```python
class SignupCoupon(db.Model):
    """A single-use coupon that gates new user signups during beta rollout."""

    __tablename__ = "signup_coupon"

    id                 = db.Column(db.Integer, primary_key=True)
    code               = db.Column(db.String(32), unique=True, nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    used_by_user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at         = db.Column(db.DateTime, nullable=False, default=_utcnow)
    used_at            = db.Column(db.DateTime, nullable=True)
```

- `created_by_user_id` — the user who owns/issued this coupon (or `NULL` for system-generated codes).
- `used_by_user_id` — the user who redeemed this coupon; `NULL` means unused.
- `used_at` — timestamp of redemption; `NULL` when unused.
- A coupon is considered **used** when `used_by_user_id` is not `NULL`.

The `User` model carries a `signup_verified` boolean that is set to `True` when a valid coupon is accepted (or when `INVITE_REQUIRED` is `False`).

---

## Routes

| Method | URL | Auth required | Description |
|---|---|---|---|
| GET | `/auth/coupon` | Signed in, unverified | Show the coupon entry form |
| POST | `/auth/coupon` | Signed in, unverified | Submit a coupon code for validation |
| GET | `/auth/my-coupons` | Signed in, verified | Show the current user's personal coupon codes |

All other routes are protected by `@login_required`, which redirects unverified users to `/auth/coupon` before they can reach any part of the application.

---

## Related Docs

- [Authentication](../authentication.md) — OAuth sign-in flow (Google & GitHub)
- [Configuration](../configuration.md) — all environment variables including coupon settings
- [Data Models](../models.md) — full schema reference including `SignupCoupon` and `User`
