#!/usr/bin/env python3
"""
Backfill junto tiers to match their owner's subscription tier.

Fixes juntos that were created before junto.tier was set on creation,
leaving them stuck at FREE even for paid subscribers.

Usage:
    uv run scripts/backfill_junto_tiers.py
"""

from juntos import create_app
from juntos.models import JuntoTier, SubscriptionTier, User, db

_SUBSCRIPTION_TO_JUNTO_TIER = {
    SubscriptionTier.FREE: JuntoTier.FREE,
    SubscriptionTier.STANDARD: JuntoTier.SUBSCRIPTION,
    SubscriptionTier.EXPANDED: JuntoTier.EXPANDED,
}


def backfill():
    updated = 0
    users = User.query.all()
    for user in users:
        correct_tier = _SUBSCRIPTION_TO_JUNTO_TIER.get(
            user.subscription_tier, JuntoTier.FREE
        )
        for junto in user.juntos:
            if junto.tier != correct_tier:
                print(
                    f"  Junto #{junto.id} '{junto.name}': "
                    f"{junto.tier.value} → {correct_tier.value}"
                )
                junto.tier = correct_tier
                updated += 1

    db.session.commit()
    print(f"\nDone. Updated {updated} junto(s).")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        backfill()
