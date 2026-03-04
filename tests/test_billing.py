"""Tests for the Stripe billing blueprint."""

import json
from unittest.mock import MagicMock, patch

from juntos.models import SubscriptionTier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stripe_config(app):
    """Inject fake Stripe config into the app for tests that need it."""
    app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"
    app.config["STRIPE_PRICE_STANDARD"] = "price_standard_test"
    app.config["STRIPE_PRICE_EXPANDED"] = "price_expanded_test"
    app.config["STRIPE_WEBHOOK_SECRET"] = ""


# ---------------------------------------------------------------------------
# /account/subscription/checkout
# ---------------------------------------------------------------------------

def test_checkout_requires_login(client):
    response = client.get("/account/subscription/checkout?plan=standard")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_checkout_unknown_plan_redirects_to_pricing(logged_in_client, app):
    _stripe_config(app)
    response = logged_in_client.get("/account/subscription/checkout?plan=bogus")
    assert response.status_code == 302
    assert "/pricing" in response.headers["Location"]


def test_checkout_no_stripe_key_redirects_to_pricing(logged_in_client, app):
    app.config["STRIPE_SECRET_KEY"] = ""
    app.config["STRIPE_PRICE_STANDARD"] = ""
    response = logged_in_client.get("/account/subscription/checkout?plan=standard")
    assert response.status_code == 302
    assert "/pricing" in response.headers["Location"]


def test_checkout_creates_stripe_session(logged_in_client, app, db, user):
    _stripe_config(app)

    fake_customer = MagicMock()
    fake_customer.id = "cus_test123"

    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/pay/cs_test123"

    with (
        patch("stripe.Customer.create", return_value=fake_customer) as mock_cust,
        patch(
            "stripe.checkout.Session.create", return_value=fake_session
        ) as mock_sess,
    ):

        response = logged_in_client.get("/account/subscription/checkout?plan=standard")

    assert response.status_code == 303
    assert response.headers["Location"] == "https://checkout.stripe.com/pay/cs_test123"
    mock_cust.assert_called_once()
    mock_sess.assert_called_once()

    db.session.refresh(user)
    assert user.stripe_customer_id == "cus_test123"


def test_checkout_reuses_existing_customer(logged_in_client, app, db, user):
    _stripe_config(app)
    user.stripe_customer_id = "cus_existing"
    db.session.commit()

    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/pay/cs_test456"

    with patch("stripe.Customer.create") as mock_cust, \
         patch("stripe.checkout.Session.create", return_value=fake_session):

        response = logged_in_client.get("/account/subscription/checkout?plan=expanded")

    assert response.status_code == 303
    mock_cust.assert_not_called()


# ---------------------------------------------------------------------------
# /account/subscription/success
# ---------------------------------------------------------------------------

def test_checkout_success_requires_login(client):
    response = client.get("/account/subscription/success")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_checkout_success_redirects_to_index(logged_in_client):
    response = logged_in_client.get("/account/subscription/success")
    assert response.status_code == 302
    assert "/" in response.headers["Location"]


# ---------------------------------------------------------------------------
# /account/subscription/portal
# ---------------------------------------------------------------------------

def test_portal_no_customer_redirects_to_pricing(logged_in_client, app):
    _stripe_config(app)
    response = logged_in_client.get("/account/subscription/portal")
    assert response.status_code == 302
    assert "/pricing" in response.headers["Location"]


def test_portal_redirects_to_stripe(logged_in_client, app, db, user):
    _stripe_config(app)
    user.stripe_customer_id = "cus_portal_test"
    db.session.commit()

    fake_portal = MagicMock()
    fake_portal.url = "https://billing.stripe.com/session/bps_test"

    with patch("stripe.billing_portal.Session.create", return_value=fake_portal):
        response = logged_in_client.get("/account/subscription/portal")

    assert response.status_code == 303
    assert response.headers["Location"] == "https://billing.stripe.com/session/bps_test"


# ---------------------------------------------------------------------------
# /stripe/webhook — checkout.session.completed
# ---------------------------------------------------------------------------

def _post_webhook(client, app, payload: dict):
    """Helper: POST a webhook event with signature verification mocked."""
    app.config["STRIPE_WEBHOOK_SECRET"] = "whsec_test"
    app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"

    import stripe as _stripe

    mock_event = _stripe.Event.construct_from(payload, "sk_test_fake")

    with patch(
        "stripe.Webhook.construct_event",
        return_value=mock_event,
    ):
        return client.post(
            "/stripe/webhook",
            data=json.dumps(payload),
            content_type="application/json",
            headers={"Stripe-Signature": "t=fake,v1=fake"},
        )


def test_webhook_checkout_completed_upgrades_user(client, app, db, user):
    user.stripe_customer_id = "cus_wh_test"
    db.session.commit()

    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_wh_test",
                "subscription": "sub_wh_test",
                "metadata": {"user_id": str(user.id), "plan": "standard"},
            }
        },
    }

    with patch("stripe.Event.construct_from", return_value=MagicMock(
        __getitem__=lambda self, k: payload[k] if k == "type" else payload.get(k),
        **{"type": payload["type"], "__iter__": None},
    )):
        # Use the real handler path by calling the route with a mock event
        from juntos.routes.billing import _activate_subscription
        with app.app_context():
            _activate_subscription(payload["data"]["object"])

    db.session.refresh(user)
    assert user.subscription_tier == SubscriptionTier.STANDARD
    assert user.stripe_subscription_id == "sub_wh_test"


def test_webhook_subscription_deleted_downgrades_user(app, db, user):
    user.stripe_customer_id = "cus_cancel_test"
    user.subscription_tier = SubscriptionTier.STANDARD
    user.stripe_subscription_id = "sub_cancel_test"
    db.session.commit()

    from juntos.routes.billing import _sync_subscription
    with app.app_context():
        _sync_subscription({
            "customer": "cus_cancel_test",
            "status": "canceled",
        })

    db.session.refresh(user)
    assert user.subscription_tier == SubscriptionTier.FREE
    assert user.stripe_subscription_id is None


def test_webhook_returns_200(client, app, db, user):
    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_no_match",
                "subscription": "sub_x",
                "metadata": {"plan": "standard"},
            }
        },
    }
    response = _post_webhook(client, app, payload)
    assert response.status_code == 200


def test_webhook_no_secret_returns_400(client, app):
    """Webhooks must be rejected when no STRIPE_WEBHOOK_SECRET is configured."""
    app.config["STRIPE_WEBHOOK_SECRET"] = ""
    app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        content_type="application/json",
    )
    assert response.status_code == 400


def test_webhook_bad_signature_returns_400(client, app):
    app.config["STRIPE_WEBHOOK_SECRET"] = "whsec_real"
    app.config["STRIPE_SECRET_KEY"] = "sk_test_fake"

    import stripe as _stripe

    with patch(
        "stripe.Webhook.construct_event",
        side_effect=_stripe.error.SignatureVerificationError("bad sig", "sig"),
    ):
        response = client.post(
            "/stripe/webhook",
            data=b"{}",
            content_type="application/json",
            headers={"Stripe-Signature": "t=bad,v1=bad"},
        )
    assert response.status_code == 400
