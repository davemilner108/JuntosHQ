"""Tests for the beta coupon / invite-gating feature."""

import pytest

from juntos import create_app
from juntos.config import TestConfig
from juntos.models import SignupCoupon, User
from juntos.models import db as _db

# ── Config helpers ─────────────────────────────────────────────────


class InviteRequiredConfig(TestConfig):
    """TestConfig variant with INVITE_REQUIRED=True."""

    INVITE_REQUIRED = True
    HARD_CODED_COUPON = "MASTER-TEST-COUPON"
    COUPONS_PER_USER = 3  # small number so tests are fast


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def invite_app():
    app = create_app(InviteRequiredConfig)
    yield app


@pytest.fixture
def invite_client(invite_app):
    return invite_app.test_client()


@pytest.fixture
def invite_db(invite_app):
    with invite_app.app_context():
        yield _db


@pytest.fixture
def unverified_user(invite_db):
    u = User(
        provider="github",
        provider_id="unverified-001",
        email="unverified@example.com",
        name="Unverified User",
        signup_verified=False,
    )
    invite_db.session.add(u)
    invite_db.session.commit()
    return u


@pytest.fixture
def verified_user(invite_db):
    u = User(
        provider="github",
        provider_id="verified-002",
        email="verified@example.com",
        name="Verified User",
        signup_verified=True,
    )
    invite_db.session.add(u)
    invite_db.session.commit()
    return u


@pytest.fixture
def coupon(invite_db, verified_user):
    c = SignupCoupon(
        code="TESTCODE1234",
        created_by_user_id=verified_user.id,
    )
    invite_db.session.add(c)
    invite_db.session.commit()
    return c


# ── Model tests ───────────────────────────────────────────────────


def test_signup_coupon_is_used_false_when_new(invite_db, coupon):
    assert coupon.is_used is False


def test_signup_coupon_is_used_true_after_redemption(
    invite_db, coupon, unverified_user
):
    coupon.used_by_user_id = unverified_user.id
    invite_db.session.commit()
    assert coupon.is_used is True


def test_signup_coupon_code_unique(invite_db, coupon):
    duplicate = SignupCoupon(code=coupon.code)
    invite_db.session.add(duplicate)
    with pytest.raises(Exception):
        invite_db.session.commit()
    invite_db.session.rollback()


def test_user_signup_verified_default_false(invite_db):
    u = User(provider="test", provider_id="new-user-888")
    invite_db.session.add(u)
    invite_db.session.commit()
    assert u.signup_verified is False


# ── Coupon entry page ─────────────────────────────────────────────


def test_coupon_page_renders_for_unverified(invite_client, unverified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.get("/auth/coupon")
    assert resp.status_code == 200
    assert b"Coupon Code" in resp.data


def test_coupon_page_redirects_verified_to_home(invite_client, verified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = verified_user.id
    resp = invite_client.get("/auth/coupon")
    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


def test_coupon_page_unauthenticated_redirects_to_login(invite_client):
    resp = invite_client.get("/auth/coupon")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# ── Hard-coded master coupon ──────────────────────────────────────


def test_master_coupon_verifies_user(invite_client, invite_db, unverified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.post(
        "/auth/coupon",
        data={"code": "MASTER-TEST-COUPON"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    invite_db.session.refresh(unverified_user)
    assert unverified_user.signup_verified is True


def test_master_coupon_case_insensitive(invite_client, invite_db, unverified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.post(
        "/auth/coupon",
        data={"code": "master-test-coupon"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    invite_db.session.refresh(unverified_user)
    assert unverified_user.signup_verified is True


def test_master_coupon_does_not_create_coupon_row(
    invite_client, invite_db, unverified_user
):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    count_before = SignupCoupon.query.count()
    invite_client.post(
        "/auth/coupon",
        data={"code": "MASTER-TEST-COUPON"},
        follow_redirects=True,
    )
    # Only the generated coupons should be new, not a redeemed row for master
    new_total = SignupCoupon.query.count()
    # All new rows should be coupons *created by* the newly verified user
    new_coupons = SignupCoupon.query.filter_by(
        created_by_user_id=unverified_user.id
    ).all()
    assert new_total - count_before == len(new_coupons)
    # None of those rows should have been "used" by the master coupon redemption
    for c in new_coupons:
        assert c.used_by_user_id is None


# ── Personal coupon redemption ────────────────────────────────────


def test_valid_coupon_verifies_user(invite_client, invite_db, unverified_user, coupon):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.post(
        "/auth/coupon",
        data={"code": coupon.code},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    invite_db.session.refresh(unverified_user)
    assert unverified_user.signup_verified is True


def test_valid_coupon_marks_coupon_used(
    invite_client, invite_db, unverified_user, coupon
):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    invite_client.post(
        "/auth/coupon",
        data={"code": coupon.code},
        follow_redirects=True,
    )
    invite_db.session.refresh(coupon)
    assert coupon.used_by_user_id == unverified_user.id
    assert coupon.used_at is not None


def test_invalid_coupon_shows_error(invite_client, invite_db, unverified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.post(
        "/auth/coupon",
        data={"code": "TOTALLY-WRONG"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Invalid coupon" in resp.data
    invite_db.session.refresh(unverified_user)
    assert unverified_user.signup_verified is False


def test_used_coupon_shows_error(
    invite_client, invite_db, unverified_user, coupon, verified_user
):
    # Mark coupon as already used
    coupon.used_by_user_id = verified_user.id
    invite_db.session.commit()

    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.post(
        "/auth/coupon",
        data={"code": coupon.code},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"already been used" in resp.data
    invite_db.session.refresh(unverified_user)
    assert unverified_user.signup_verified is False


def test_empty_code_shows_error(invite_client, unverified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.post(
        "/auth/coupon",
        data={"code": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"enter a coupon" in resp.data


# ── Coupon auto-generation after verification ─────────────────────


def test_coupons_generated_after_verification(
    invite_client, invite_db, unverified_user, coupon
):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    invite_client.post(
        "/auth/coupon",
        data={"code": coupon.code},
        follow_redirects=True,
    )
    generated = SignupCoupon.query.filter_by(
        created_by_user_id=unverified_user.id
    ).all()
    # InviteRequiredConfig sets COUPONS_PER_USER=3
    assert len(generated) == 3


def test_coupons_generated_are_unused(
    invite_client, invite_db, unverified_user, coupon
):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    invite_client.post(
        "/auth/coupon",
        data={"code": coupon.code},
        follow_redirects=True,
    )
    generated = SignupCoupon.query.filter_by(
        created_by_user_id=unverified_user.id
    ).all()
    for c in generated:
        assert c.is_used is False


# ── Unverified user redirect (login_required gate) ────────────────


def test_unverified_user_blocked_from_protected_route(
    invite_client, unverified_user
):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.get("/juntos/new")
    assert resp.status_code == 302
    assert "/auth/coupon" in resp.headers["Location"]


def test_verified_user_can_access_protected_route(invite_client, verified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = verified_user.id
    resp = invite_client.get("/juntos/new")
    assert resp.status_code == 200


# ── My coupons page ───────────────────────────────────────────────


def test_my_coupons_shows_codes(invite_client, invite_db, verified_user):
    c1 = SignupCoupon(code="AAA111", created_by_user_id=verified_user.id)
    c2 = SignupCoupon(code="BBB222", created_by_user_id=verified_user.id)
    invite_db.session.add_all([c1, c2])
    invite_db.session.commit()

    with invite_client.session_transaction() as sess:
        sess["user_id"] = verified_user.id
    resp = invite_client.get("/auth/my-coupons")
    assert resp.status_code == 200
    assert b"AAA111" in resp.data
    assert b"BBB222" in resp.data


def test_my_coupons_empty_state(invite_client, verified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = verified_user.id
    resp = invite_client.get("/auth/my-coupons")
    assert resp.status_code == 200
    assert b"no invite coupons" in resp.data.lower()


def test_my_coupons_unverified_redirected(invite_client, unverified_user):
    with invite_client.session_transaction() as sess:
        sess["user_id"] = unverified_user.id
    resp = invite_client.get("/auth/my-coupons")
    assert resp.status_code == 302
    assert "/auth/coupon" in resp.headers["Location"]


def test_my_coupons_unauthenticated_redirects_to_login(invite_client):
    resp = invite_client.get("/auth/my-coupons")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# ── INVITE_REQUIRED=False (default TestConfig) ────────────────────


def test_invite_not_required_user_auto_verified(client, db):
    """When INVITE_REQUIRED is False, users skip coupon verification."""
    u = User(
        provider="github",
        provider_id="no-invite-needed-999",
        email="free@example.com",
        name="Free User",
        signup_verified=True,  # set by auth callback when INVITE_REQUIRED=False
    )
    db.session.add(u)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = u.id
    resp = client.get("/juntos/new")
    assert resp.status_code == 200


def test_invite_not_required_coupon_page_redirect(client, db):
    """When INVITE_REQUIRED is False, a verified user visiting /auth/coupon
    is redirected home."""
    u = User(
        provider="github",
        provider_id="no-invite-needed-998",
        signup_verified=True,
    )
    db.session.add(u)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = u.id
    resp = client.get("/auth/coupon")
    assert resp.status_code == 302
