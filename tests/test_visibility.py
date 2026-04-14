"""Tests for public/private visibility and tier-based commitment limits."""

import pytest

from juntos.models import (
    Commitment,
    CommitmentStatus,
    Junto,
    JuntoTier,
    Member,
    User,
)

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def junto(db, user):
    j = Junto(
        name="Public Junto", description="Visible",
        owner_id=user.id, is_public=True,
    )
    db.session.add(j)
    db.session.commit()
    return j


@pytest.fixture
def private_junto(db, user):
    j = Junto(
        name="Private Junto", description="Hidden",
        owner_id=user.id, is_public=False,
    )
    db.session.add(j)
    db.session.commit()
    return j


@pytest.fixture
def other_user(db):
    u = User(
        provider="github", provider_id="other-vis-456",
        email="other@example.com", name="Other",
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def member(db, junto):
    m = Member(name="Alice", role="Thinker", junto_id=junto.id)
    db.session.add(m)
    db.session.commit()
    return m


# ── Index Visibility ─────────────────────────────────────────────


def test_anonymous_sees_only_public_juntos(client, db, user, junto, private_junto):
    resp = client.get("/")
    assert b"Public Junto" in resp.data
    assert b"Private Junto" not in resp.data


def test_owner_sees_own_private_junto(logged_in_client, db, user, junto, private_junto):
    resp = logged_in_client.get("/")
    assert b"Public Junto" in resp.data
    assert b"Private Junto" in resp.data


def test_logged_in_sees_participating_private_junto(
    client, db, user, other_user,
):
    private = Junto(
        name="Secret Club", description="Members only",
        owner_id=user.id, is_public=False,
    )
    db.session.add(private)
    db.session.commit()
    m = Member(name="Other", junto_id=private.id, user_id=other_user.id)
    db.session.add(m)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
    resp = client.get("/")
    assert b"Secret Club" in resp.data


def test_logged_in_sees_public_juntos_from_others(client, db, user, other_user, junto):
    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
    resp = client.get("/")
    assert b"Public Junto" in resp.data


def test_private_junto_not_shown_to_non_member(
    client, db, user, other_user, private_junto,
):
    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
    resp = client.get("/")
    assert b"Private Junto" not in resp.data


def test_detail_page_redirects_anonymous_for_private(client, db, private_junto):
    """Anonymous users cannot view a private junto — redirected to login."""
    resp = client.get(f"/juntos/{private_junto.id}")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_detail_page_accessible_for_public(client, db, junto):
    """Anyone can view a public junto."""
    resp = client.get(f"/juntos/{junto.id}")
    assert resp.status_code == 200
    assert b"Public Junto" in resp.data


def test_detail_page_accessible_for_owner(logged_in_client, db, private_junto):
    """Owner can always view their own private junto."""
    resp = logged_in_client.get(f"/juntos/{private_junto.id}")
    assert resp.status_code == 200
    assert b"Private Junto" in resp.data


def test_detail_page_blocked_for_non_member(client, db, user, other_user, private_junto):
    """A logged-in user who is not a member or owner cannot view a private junto."""
    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
    resp = client.get(f"/juntos/{private_junto.id}", follow_redirects=True)
    assert b"Private Junto" not in resp.data


def test_detail_page_accessible_for_member(client, db, user, other_user, private_junto):
    """A linked member can view a private junto."""
    m = Member(name="Other", junto_id=private_junto.id, user_id=other_user.id)
    db.session.add(m)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
    resp = client.get(f"/juntos/{private_junto.id}")
    assert resp.status_code == 200
    assert b"Private Junto" in resp.data


# ── Create / Edit is_public ──────────────────────────────────────


def test_create_junto_private(logged_in_client, db):
    resp = logged_in_client.post(
        "/juntos/",
        data={"name": "My Private", "description": "Hidden group"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    j = Junto.query.filter_by(name="My Private").first()
    assert j is not None
    assert j.is_public is False


def test_create_junto_public(logged_in_client, db):
    resp = logged_in_client.post(
        "/juntos/",
        data={"name": "My Public", "description": "Open group", "is_public": "1"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    j = Junto.query.filter_by(name="My Public").first()
    assert j.is_public is True


def test_edit_junto_toggle_public(logged_in_client, db, junto):
    # Toggle from public to private
    resp = logged_in_client.post(
        f"/juntos/{junto.id}/edit",
        data={"name": junto.name, "description": junto.description or ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.session.refresh(junto)
    assert junto.is_public is False

    # Toggle back to public
    resp = logged_in_client.post(
        f"/juntos/{junto.id}/edit",
        data={
            "name": junto.name,
            "description": junto.description or "",
            "is_public": "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.session.refresh(junto)
    assert junto.is_public is True


# ── Create Button Gated on Login ─────────────────────────────────


def test_anonymous_no_create_button(client, db, user, junto):
    resp = client.get("/")
    assert b"Start your Junto" not in resp.data


def test_logged_in_sees_create_button(logged_in_client):
    resp = logged_in_client.get("/")
    assert b"Start your Junto" in resp.data


# ── Commitment Limits ────────────────────────────────────────────


def _make_junto_with_member(db, user, tier=JuntoTier.FREE):
    j = Junto(name="Tier Test", description="Tier", owner_id=user.id, tier=tier)
    db.session.add(j)
    db.session.commit()
    m = Member(name="Bob", role="Tester", junto_id=j.id)
    db.session.add(m)
    db.session.commit()
    return j, m


def test_free_tier_commitment_limit(db, user):
    j, _ = _make_junto_with_member(db, user, JuntoTier.FREE)
    assert j.commitment_limit == 1


def test_subscription_tier_commitment_limit(db, user):
    j, _ = _make_junto_with_member(db, user, JuntoTier.SUBSCRIPTION)
    assert j.commitment_limit == 3


def test_expanded_tier_commitment_limit(db, user):
    j, _ = _make_junto_with_member(db, user, JuntoTier.EXPANDED)
    assert j.commitment_limit == 5


def test_free_tier_allows_one_commitment(logged_in_client, db, user):
    from juntos.franklin import get_weekly_prompt

    j, m = _make_junto_with_member(db, user, JuntoTier.FREE)
    week = get_weekly_prompt()["week"]

    logged_in_client.post(
        f"/juntos/{j.id}/commitments",
        data={
            f"commitment_desc_{m.id}_0": "Action one",
            f"commitment_status_{m.id}_0": "not_started",
        },
    )
    commitments = Commitment.query.filter_by(member_id=m.id, cycle_week=week).all()
    assert len(commitments) == 1


def test_free_tier_rejects_beyond_limit(logged_in_client, db, user):
    from juntos.franklin import get_weekly_prompt

    j, m = _make_junto_with_member(db, user, JuntoTier.FREE)
    week = get_weekly_prompt()["week"]

    # Submit 2 actions for a FREE tier (limit is 1)
    logged_in_client.post(
        f"/juntos/{j.id}/commitments",
        data={
            f"commitment_desc_{m.id}_0": "Action one",
            f"commitment_status_{m.id}_0": "not_started",
            f"commitment_desc_{m.id}_1": "Action two (over limit)",
            f"commitment_status_{m.id}_1": "not_started",
        },
    )
    commitments = Commitment.query.filter_by(member_id=m.id, cycle_week=week).all()
    assert len(commitments) == 1
    assert commitments[0].description == "Action one"


def test_subscription_tier_allows_three_commitments(logged_in_client, db, user):
    from juntos.franklin import get_weekly_prompt

    j, m = _make_junto_with_member(db, user, JuntoTier.SUBSCRIPTION)
    week = get_weekly_prompt()["week"]

    logged_in_client.post(
        f"/juntos/{j.id}/commitments",
        data={
            f"commitment_desc_{m.id}_0": "A1",
            f"commitment_status_{m.id}_0": "not_started",
            f"commitment_desc_{m.id}_1": "A2",
            f"commitment_status_{m.id}_1": "not_started",
            f"commitment_desc_{m.id}_2": "A3",
            f"commitment_status_{m.id}_2": "not_started",
        },
    )
    commitments = Commitment.query.filter_by(member_id=m.id, cycle_week=week).all()
    assert len(commitments) == 3


def test_multiple_commitments_display_on_show_page(logged_in_client, db, user):
    from juntos.franklin import get_weekly_prompt

    j, m = _make_junto_with_member(db, user, JuntoTier.SUBSCRIPTION)
    week = get_weekly_prompt()["week"]

    for i in range(2):
        db.session.add(
            Commitment(
                member_id=m.id,
                cycle_week=week,
                description=f"Display test {i}",
                status=CommitmentStatus.NOT_STARTED,
            )
        )
    db.session.commit()

    resp = logged_in_client.get(f"/juntos/{j.id}")
    assert b"Display test 0" in resp.data
    assert b"Display test 1" in resp.data


def test_clearing_all_slots_deletes_commitments(logged_in_client, db, user):
    from juntos.franklin import get_weekly_prompt

    j, m = _make_junto_with_member(db, user, JuntoTier.FREE)
    week = get_weekly_prompt()["week"]

    # Create a commitment first
    logged_in_client.post(
        f"/juntos/{j.id}/commitments",
        data={
            f"commitment_desc_{m.id}_0": "Will be cleared",
            f"commitment_status_{m.id}_0": "not_started",
        },
    )
    assert Commitment.query.filter_by(member_id=m.id, cycle_week=week).count() == 1

    # Submit with empty slot
    logged_in_client.post(
        f"/juntos/{j.id}/commitments",
        data={
            f"commitment_desc_{m.id}_0": "",
            f"commitment_status_{m.id}_0": "not_started",
        },
    )
    assert Commitment.query.filter_by(member_id=m.id, cycle_week=week).count() == 0
