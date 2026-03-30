"""
Fix existing juntos that have tier=FREE even though their owner has a paid subscription.

Run once after deploying the billing fixes:
    flask shell < scripts/backfill_junto_tiers.py
or:
    python scripts/backfill_junto_tiers.py  (with FLASK_APP set)
"""

from juntos.models import Junto, JuntoTier, SubscriptionTier, User, db

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
    # Allow running directly with `flask shell < this_file.py`
    # or as a standalone script if app context is available
    try:
        backfill()
    except RuntimeError:
        # No app context — set up manually
        import os
        from juntos import create_app  # adjust import if your factory is named differently

        app = create_app()
        with app.app_context():
            backfill()
