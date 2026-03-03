import stripe
from flask import Blueprint, abort, current_app, flash, g, redirect, request, url_for

from juntos.auth_utils import login_required
from juntos.models import SubscriptionTier, User, db

bp = Blueprint("billing", __name__)

# Map plan names to SubscriptionTier values and Stripe price env-config keys
_PLAN_TIERS: dict[str, SubscriptionTier] = {
    "standard": SubscriptionTier.STANDARD,
    "expanded": SubscriptionTier.EXPANDED,
}

_PLAN_PRICE_KEYS: dict[str, str] = {
    "standard": "STRIPE_PRICE_STANDARD",
    "expanded": "STRIPE_PRICE_EXPANDED",
}


@bp.route("/account/subscription/checkout")
@login_required
def checkout():
    """Create a Stripe Checkout session and redirect the user to it."""
    plan = request.args.get("plan", "").lower()
    if plan not in _PLAN_TIERS:
        flash("Unknown plan. Please choose Standard or Expanded.", "error")
        return redirect(url_for("main.pricing"))

    stripe_key = current_app.config.get("STRIPE_SECRET_KEY", "")
    price_id = current_app.config.get(_PLAN_PRICE_KEYS[plan], "")

    if not stripe_key or not price_id:
        flash(
            "Billing is not yet configured. Please check back soon.",
            "info",
        )
        return redirect(url_for("main.pricing"))

    stripe.api_key = stripe_key
    user: User = g.current_user

    # Re-use existing Stripe customer when available
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email or "",
            name=user.name or "",
            metadata={"user_id": str(user.id)},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        db.session.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=url_for("billing.checkout_success", _external=True)
        + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=url_for("main.pricing", _external=True),
        metadata={"user_id": str(user.id), "plan": plan},
    )
    return redirect(session.url, code=303)


@bp.route("/account/subscription/success")
@login_required
def checkout_success():
    """Landing page after a successful Stripe Checkout."""
    flash(
        "Your subscription is being activated. "
        "Your account will be upgraded within a few seconds.",
        "success",
    )
    return redirect(url_for("main.index"))


@bp.route("/account/subscription/portal")
@login_required
def portal():
    """Redirect to the Stripe Customer Portal for self-service billing management."""
    stripe_key = current_app.config.get("STRIPE_SECRET_KEY", "")
    if not stripe_key or not g.current_user.stripe_customer_id:
        flash("No active subscription found.", "info")
        return redirect(url_for("main.pricing"))

    stripe.api_key = stripe_key
    portal_session = stripe.billing_portal.Session.create(
        customer=g.current_user.stripe_customer_id,
        return_url=url_for("main.index", _external=True),
    )
    return redirect(portal_session.url, code=303)


@bp.route("/stripe/webhook", methods=["POST"])
def webhook():
    """Handle Stripe webhook events to keep subscription state in sync."""
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            abort(400)
    else:
        import json

        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

    _handle_event(event)
    return "", 200


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PRICE_TO_TIER: dict[str, SubscriptionTier] = {}  # populated lazily at runtime


def _price_id_for_tier(app, plan: str) -> str:
    return app.config.get(_PLAN_PRICE_KEYS.get(plan, ""), "")


def _tier_from_price_id(app, price_id: str) -> SubscriptionTier | None:
    for plan, key in _PLAN_PRICE_KEYS.items():
        if app.config.get(key) == price_id:
            return _PLAN_TIERS[plan]
    return None


def _handle_event(event: stripe.Event) -> None:
    etype = event["type"]

    if etype == "checkout.session.completed":
        session_obj = event["data"]["object"]
        _activate_subscription(session_obj)

    elif etype in ("customer.subscription.deleted", "customer.subscription.updated"):
        sub = event["data"]["object"]
        _sync_subscription(sub)


def _activate_subscription(session_obj) -> None:
    """Upgrade user tier when checkout completes."""
    customer_id = session_obj.get("customer")
    sub_id = session_obj.get("subscription")
    plan = (session_obj.get("metadata") or {}).get("plan", "")

    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return

    tier = _PLAN_TIERS.get(plan)
    if tier:
        user.subscription_tier = tier
    if sub_id:
        user.stripe_subscription_id = sub_id
    db.session.commit()


def _sync_subscription(sub) -> None:
    """Downgrade user tier when subscription is cancelled or lapses."""
    customer_id = sub.get("customer")
    status = sub.get("status", "")

    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return

    if status in ("canceled", "unpaid", "incomplete_expired"):
        user.subscription_tier = SubscriptionTier.FREE
        user.stripe_subscription_id = None
        db.session.commit()
    elif status == "active":
        # Determine tier from price ID on first item
        items = (sub.get("items") or {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id", "")
            tier = _tier_from_price_id(current_app, price_id)
            if tier:
                user.subscription_tier = tier
                db.session.commit()
