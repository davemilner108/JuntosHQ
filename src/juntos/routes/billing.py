import stripe
from flask import Blueprint, abort, current_app, flash, g, redirect, request, url_for

from juntos.auth_utils import login_required
from juntos.models import JuntoTier, SubscriptionTier, User, db

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

# Map SubscriptionTier → JuntoTier so juntos created/upgraded stay in sync
_SUBSCRIPTION_TO_JUNTO_TIER: dict[SubscriptionTier, JuntoTier] = {
    SubscriptionTier.FREE: JuntoTier.FREE,
    SubscriptionTier.STANDARD: JuntoTier.SUBSCRIPTION,
    SubscriptionTier.EXPANDED: JuntoTier.EXPANDED,
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


@bp.route("/account/addon/chatbot/checkout")
@login_required
def chatbot_checkout():
    """Create a Stripe Checkout session for the Ben's Counsel add-on."""
    user: User = g.current_user

    if user.chatbot_addon:
        flash("Ben's Counsel is already active on your account.", "info")
        return redirect(url_for("main.pricing"))

    stripe_key = current_app.config.get("STRIPE_SECRET_KEY", "")
    price_id = current_app.config.get("STRIPE_PRICE_CHATBOT", "")

    if not stripe_key or not price_id:
        flash(
            "Billing is not yet configured. Please check back soon.",
            "info",
        )
        return redirect(url_for("main.pricing"))

    stripe.api_key = stripe_key

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
        success_url=url_for("billing.chatbot_checkout_success", _external=True),
        cancel_url=url_for("main.pricing", _external=True),
        metadata={"user_id": str(user.id), "addon": "chatbot"},
    )
    return redirect(session.url, code=303)


@bp.route("/account/addon/chatbot/success")
@login_required
def chatbot_checkout_success():
    """Landing page after a successful chatbot add-on checkout."""
    flash(
        "Ben's Counsel is now active on your account. Enjoy the wisdom!",
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

    if not webhook_secret:
        # Reject unsigned webhooks: without a secret we cannot verify the
        # request originates from Stripe, so processing it would be a security
        # risk.  Configure STRIPE_WEBHOOK_SECRET to enable webhook handling.
        abort(400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        abort(400)

    _handle_event(event)
    return "", 200


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PLAN_PRICE_KEYS_REF = _PLAN_PRICE_KEYS  # alias for use inside helpers


def _tier_from_price_id(app, price_id: str) -> SubscriptionTier | None:
    for plan, key in _PLAN_PRICE_KEYS_REF.items():
        if app.config.get(key) == price_id:
            return _PLAN_TIERS[plan]
    return None


def _sync_junto_tiers(user: User, new_sub_tier: SubscriptionTier) -> None:
    """Update all juntos owned by the user to match their new subscription tier.

    This keeps junto-level limits (meetings, commitments) in sync whenever
    a user upgrades or downgrades.
    """
    junto_tier = _SUBSCRIPTION_TO_JUNTO_TIER.get(new_sub_tier, JuntoTier.FREE)
    for junto in user.juntos:
        junto.tier = junto_tier
    db.session.flush()


def _handle_event(event: stripe.Event) -> None:
    etype = event["type"]

    if etype == "checkout.session.completed":
        session_obj = event["data"]["object"]
        _activate_subscription(session_obj)

    elif etype in ("customer.subscription.deleted", "customer.subscription.updated"):
        sub = event["data"]["object"]
        _sync_subscription(sub)

    elif etype == "invoice.payment_failed":
        # A payment attempt failed. The subscription may still be active
        # (Stripe retries), but we log it. If the subscription reaches
        # 'past_due' or 'unpaid', _sync_subscription will handle the downgrade
        # via the customer.subscription.updated event that Stripe also fires.
        invoice = event["data"]["object"]
        current_app.logger.warning(
            "Invoice payment failed: invoice=%s customer=%s",
            invoice.get("id"),
            invoice.get("customer"),
        )

    elif etype == "customer.subscription.updated":
        sub = event["data"]["object"]
        # Handle past_due explicitly — subscription is still technically
        # "active" in Stripe's eyes during retry window, but we want to
        # surface this to the user without immediately downgrading.
        if sub.get("status") == "past_due":
            current_app.logger.warning(
                "Subscription past_due: sub=%s customer=%s",
                sub.get("id"),
                sub.get("customer"),
            )
        _sync_subscription(sub)


def _activate_subscription(session_obj) -> None:
    """Upgrade user tier or enable addon when checkout completes."""
    customer_id = session_obj.get("customer")
    sub_id = session_obj.get("subscription")
    metadata = session_obj.get("metadata") or {}

    user = db.session.execute(
        db.select(User).where(User.stripe_customer_id == customer_id)
    ).scalar_one_or_none()
    if not user:
        return

    if metadata.get("addon") == "chatbot":
        user.chatbot_addon = True
    else:
        plan = metadata.get("plan", "")
        tier = _PLAN_TIERS.get(plan)
        if tier:
            user.subscription_tier = tier
            _sync_junto_tiers(user, tier)
        if sub_id:
            user.stripe_subscription_id = sub_id
    db.session.commit()


def _sync_subscription(sub) -> None:
    """Downgrade user tier or disable addon when subscription is cancelled or lapses."""
    customer_id = sub.get("customer")
    status = sub.get("status", "")

    user = db.session.execute(
        db.select(User).where(User.stripe_customer_id == customer_id)
    ).scalar_one_or_none()
    if not user:
        return

    items = (sub.get("items") or {}).get("data", [])
    price_ids = [item.get("price", {}).get("id", "") for item in items]
    chatbot_price_id = current_app.config.get("STRIPE_PRICE_CHATBOT", "")
    is_chatbot_sub = chatbot_price_id and chatbot_price_id in price_ids

    if status in ("canceled", "unpaid", "incomplete_expired"):
        if is_chatbot_sub:
            user.chatbot_addon = False
        else:
            user.subscription_tier = SubscriptionTier.FREE
            user.stripe_subscription_id = None
            _sync_junto_tiers(user, SubscriptionTier.FREE)
        db.session.commit()
    elif status == "active":
        if not is_chatbot_sub and price_ids:
            tier = _tier_from_price_id(current_app, price_ids[0])
            if tier:
                user.subscription_tier = tier
                _sync_junto_tiers(user, tier)
                db.session.commit()
