# Feature: Subscription Tiers

## Overview

JuntosHQ monetizes through a three-tier subscription model that gates capacity and features, plus an optional AI add-on. The tiers are designed around a natural growth curve: start free with one junto, hit limits as you get serious, and upgrade when the app has proven its value.

Pricing targets individuals and small community leaders — not enterprises. Low enough that a motivated person subscribes without friction.

| Tier       | Price     | Juntos          | Meetings per Junto          | Key Differentiators                          |
|------------|-----------|-----------------|-----------------------------|----------------------------------------------|
| **Free**   | $0        | 1               | Last 3 visible              | Try before you buy; single-group use         |
| **Standard** | $4.99/mo  | Up to 5         | Up to 25 visible per junto  | Multi-group support, decent archive          |
| **Expanded** | $9.99/mo  | Up to 15        | Up to 80 visible per junto  | Serious scaling for dedicated users/leaders  |

**Add-on**: Ben Franklin AI Chatbot — $4.99/mo, available on any tier.

---

## Why Three Tiers

### Free gets people in the door

Run one full junto with prompts, logging, and owner-managed commitments. Limits on visible history (last 3) and no multi-group support create natural upgrade pull.

### Standard captures the typical paying user

Most people run 2–5 groups (book club + mastermind + volunteer team). 5 juntos and 25 meetings (~6 months weekly) cover this comfortably — long enough to prove value, short enough to upsell later.

### Expanded removes most friction

For power users, coaches, organizers, or anyone running multiple active groups. 15 juntos and 80 meetings per junto (~1.5–2 years weekly) feel generous without true unlimited (helps with DB/performance). The $4.99 → $9.99 jump is small — annoyed users upgrade easily.

---

## Revenue Model

(Assumptions unchanged — conservative estimates still apply, with Expanded likely capturing more of the high-engagement tail than old Unlimited would have.)

---

## Feature Matrix

| Feature                      | Free          | Standard                  | Expanded                          |
|------------------------------|---------------|---------------------------|-----------------------------------|
| Create juntos                | 1             | Up to 5                   | Up to 15                          |
| Members per junto            | 12            | 12                        | 12                                |
| Log meetings                 | Yes           | Yes                       | Yes                               |
| View meeting history         | Last 3        | Up to 25 per junto        | Up to 80 per junto                |
| Commitment tracking          | Owner-managed | Self-reporting            | Self-reporting                    |
| Weekly Franklin prompts      | Yes           | Yes                       | Yes                               |
| Custom discussion prompts    | No            | No                        | Yes                               |
| Export meetings (CSV/PDF)    | No            | Yes                       | Yes                               |
| Member invite links          | No            | Yes                       | Yes                               |
| Priority support             | No            | No                        | Yes                               |
| Ben Franklin Chatbot         | Add-on ($4.99)| Add-on ($4.99)            | Add-on ($4.99)                    |

---

## Limit Enforcement Strategy

- **Junto count**: Hard limit. "New Junto" disabled/hidden at cap. Downgrade → extras become read-only.
- **Meeting history visibility**: Soft limit. All stored; view filters by tier. Upgrade reveals instantly.
- **Meeting count per junto**: Hard on Standard/Expanded. Logging disabled at cap with upgrade prompt.

Downgrade behavior: Data preserved, access restricted (read-only extras, hidden history beyond cap, commitments revert to owner-managed).

---

## Payment Infrastructure / Data Model / Helpers / Routes

(Unchanged from original — just update any "unlimited" strings in code/comments to "expanded".)

For example, in helpers:
```python
limits = {"free": 1, "standard": 5, "expanded": 15}
meeting_limits = {"free": 3, "standard": 25, "expanded": 80}