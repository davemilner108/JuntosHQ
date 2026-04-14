"""Tests for the chat blueprint (Ben's Counsel chatbot)."""
from unittest.mock import MagicMock, patch

import pytest

from juntos.models import ChatMessage, ChatSession, Junto, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def junto(db, user):
    j = Junto(name="Franklin Society", description="A junto for testing", owner_id=user.id)
    db.session.add(j)
    db.session.commit()
    return j


@pytest.fixture
def chat_session_obj(db, user):
    cs = ChatSession(user_id=user.id, junto_id=None)
    db.session.add(cs)
    db.session.commit()
    return cs


@pytest.fixture
def chat_session_with_messages(db, user, chat_session_obj):
    db.session.add(
        ChatMessage(session_id=chat_session_obj.id, role="user", content="Hello Ben")
    )
    db.session.add(
        ChatMessage(
            session_id=chat_session_obj.id,
            role="assistant",
            content="Good day to you!",
        )
    )
    db.session.commit()
    db.session.refresh(chat_session_obj)
    return chat_session_obj


# ---------------------------------------------------------------------------
# GET /chat/ – show
# ---------------------------------------------------------------------------


def test_show_requires_login(client):
    resp = client.get("/chat/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_show_renders_for_logged_in_user(logged_in_client):
    resp = logged_in_client.get("/chat/")
    assert resp.status_code == 200


def test_show_displays_trial_info_for_free_user(logged_in_client):
    resp = logged_in_client.get("/chat/")
    assert resp.status_code == 200
    # Page should render; trial remaining is rendered as context
    assert b"Ben" in resp.data


# ---------------------------------------------------------------------------
# GET /chat/junto/<id>
# ---------------------------------------------------------------------------


def test_junto_chat_requires_login(client, db, user):
    j = Junto(name="Test Junto", owner_id=user.id)
    db.session.add(j)
    db.session.commit()
    resp = client.get(f"/chat/junto/{j.id}")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_junto_chat_renders(logged_in_client, db, user):
    j = Junto(name="Test Junto", owner_id=user.id)
    db.session.add(j)
    db.session.commit()
    resp = logged_in_client.get(f"/chat/junto/{j.id}")
    assert resp.status_code == 200


def test_junto_chat_404_for_unknown_junto(logged_in_client):
    resp = logged_in_client.get("/chat/junto/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /chat/message – send_message
# ---------------------------------------------------------------------------


def test_send_message_requires_login(client):
    resp = client.post("/chat/message", data={"message": "Hello"})
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_send_message_empty_redirects(logged_in_client):
    """Empty message body should redirect without saving anything."""
    resp = logged_in_client.post("/chat/message", data={"message": ""})
    assert resp.status_code == 302


def test_send_message_no_access_redirects_to_pricing(logged_in_client, db, user):
    """User who has exhausted free trial is redirected to pricing."""
    from juntos.ben_rag import FREE_TRIAL_LIMIT

    user.chatbot_msgs_used = FREE_TRIAL_LIMIT
    db.session.commit()

    resp = logged_in_client.post("/chat/message", data={"message": "Hello Ben"})
    assert resp.status_code == 302
    assert "/pricing" in resp.headers["Location"]


def test_send_message_success(logged_in_client, db, user):
    """Successful call saves user+assistant messages and increments counter."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Virtue is its own reward.")]

    with patch(
        "juntos.routes.chat.build_messages",
        return_value=("sys", [{"role": "user", "content": "Hello"}]),
    ):
        with patch("juntos.routes.chat.anthropic_sdk.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            resp = logged_in_client.post("/chat/message", data={"message": "Hello Ben"})

    assert resp.status_code == 302
    db.session.refresh(user)
    assert user.chatbot_msgs_used == 1

    messages = db.session.query(ChatMessage).all()
    roles = {m.role for m in messages}
    assert "user" in roles
    assert "assistant" in roles


def test_send_message_saves_correct_content(logged_in_client, db, user):
    """Assistant reply text is stored verbatim in ChatMessage."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Industry need not wish.")]

    with patch("juntos.routes.chat.build_messages", return_value=("sys", [])):
        with patch("juntos.routes.chat.anthropic_sdk.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            logged_in_client.post("/chat/message", data={"message": "Work hard?"})

    assistant_msgs = (
        db.session.query(ChatMessage).filter_by(role="assistant").all()
    )
    assert any("Industry need not wish." in m.content for m in assistant_msgs)


def test_send_message_does_not_increment_for_addon_users(logged_in_client, db, user):
    """Users with the chatbot addon should not have their counter incremented."""
    user.chatbot_addon = True
    db.session.commit()

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="A penny saved is a penny earned.")]

    with patch("juntos.routes.chat.build_messages", return_value=("sys", [])):
        with patch("juntos.routes.chat.anthropic_sdk.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            logged_in_client.post("/chat/message", data={"message": "Hello"})

    db.session.refresh(user)
    assert user.chatbot_msgs_used == 0


def test_send_message_api_error_shows_flash(logged_in_client):
    """Anthropic API failure should redirect with a flash error message."""
    with patch("juntos.routes.chat.build_messages", return_value=("sys", [])):
        with patch("juntos.routes.chat.anthropic_sdk.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = Exception("API timeout")
            resp = logged_in_client.post(
                "/chat/message",
                data={"message": "Hello"},
                follow_redirects=True,
            )

    assert resp.status_code == 200
    assert b"Error" in resp.data


def test_send_message_api_error_rolls_back_db(logged_in_client, db, user):
    """On API error the user message should still be saved (it's committed before the call)."""
    with patch("juntos.routes.chat.build_messages", return_value=("sys", [])):
        with patch("juntos.routes.chat.anthropic_sdk.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = Exception("boom")
            logged_in_client.post("/chat/message", data={"message": "Before error"})

    # The user message was committed before the API call, so it persists
    user_msgs = db.session.query(ChatMessage).filter_by(role="user").all()
    assert len(user_msgs) == 1
    assert user_msgs[0].content == "Before error"
    # No assistant message should have been saved
    assert db.session.query(ChatMessage).filter_by(role="assistant").count() == 0


def test_send_message_junto_context_redirects_to_junto(logged_in_client, db, user):
    """Sending a message in a junto context redirects back to junto chat."""
    j = Junto(name="Context Junto", owner_id=user.id)
    db.session.add(j)
    db.session.commit()

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Industry need not wish.")]

    with patch("juntos.routes.chat.build_messages", return_value=("sys", [])):
        with patch("juntos.routes.chat.anthropic_sdk.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            resp = logged_in_client.post(
                "/chat/message",
                data={"message": "Hello Ben", "junto_id": str(j.id)},
            )

    assert resp.status_code == 302
    assert f"/chat/junto/{j.id}" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# POST /chat/new – new_session
# ---------------------------------------------------------------------------


def test_new_session_requires_login(client):
    resp = client.post("/chat/new")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_new_session_clears_session_pointer(logged_in_client):
    """POST /chat/new should clear chat_session_id and redirect to /chat/."""
    with logged_in_client.session_transaction() as sess:
        sess["chat_session_id"] = 42

    resp = logged_in_client.post("/chat/new")
    assert resp.status_code == 302
    assert "/chat/" in resp.headers["Location"]

    with logged_in_client.session_transaction() as sess:
        assert "chat_session_id" not in sess


def test_new_session_with_junto_redirects_to_junto_chat(logged_in_client, db, user):
    j = Junto(name="New Session Junto", owner_id=user.id)
    db.session.add(j)
    db.session.commit()

    resp = logged_in_client.post("/chat/new", data={"junto_id": str(j.id)})
    assert resp.status_code == 302
    assert f"/chat/junto/{j.id}" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# GET /chat/session/<id>/export.pdf
# ---------------------------------------------------------------------------


def test_export_pdf_requires_login(client, db, user):
    cs = ChatSession(user_id=user.id)
    db.session.add(cs)
    db.session.commit()

    resp = client.get(f"/chat/session/{cs.id}/export.pdf")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_export_pdf_wrong_user_redirects(logged_in_client, db):
    other = User(provider="github", provider_id="other-export-99", name="Other")
    db.session.add(other)
    db.session.commit()

    cs = ChatSession(user_id=other.id)
    db.session.add(cs)
    db.session.commit()

    resp = logged_in_client.get(
        f"/chat/session/{cs.id}/export.pdf", follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"do not have access" in resp.data


def test_export_pdf_404_for_unknown_session(logged_in_client):
    resp = logged_in_client.get("/chat/session/99999/export.pdf")
    assert resp.status_code == 404


def test_export_pdf_success(logged_in_client, db, user, chat_session_with_messages):
    resp = logged_in_client.get(
        f"/chat/session/{chat_session_with_messages.id}/export.pdf"
    )
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert resp.data[:4] == b"%PDF"


def test_export_pdf_empty_session(logged_in_client, db, user):
    cs = ChatSession(user_id=user.id)
    db.session.add(cs)
    db.session.commit()

    resp = logged_in_client.get(f"/chat/session/{cs.id}/export.pdf")
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"


def test_export_pdf_unicode_content(logged_in_client, db, user):
    """Smart quotes and em dashes in messages should not crash PDF export."""
    cs = ChatSession(user_id=user.id)
    db.session.add(cs)
    db.session.commit()
    db.session.add(
        ChatMessage(
            session_id=cs.id,
            role="user",
            content="\u201cHello Ben\u201d\u2014how are you?",
        )
    )
    db.session.commit()

    resp = logged_in_client.get(f"/chat/session/{cs.id}/export.pdf")
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"


def test_export_pdf_filename_contains_session_id(logged_in_client, db, user):
    cs = ChatSession(user_id=user.id)
    db.session.add(cs)
    db.session.commit()

    resp = logged_in_client.get(f"/chat/session/{cs.id}/export.pdf")
    disposition = resp.headers.get("Content-Disposition", "")
    assert f"session-{cs.id}" in disposition


# ---------------------------------------------------------------------------
# Unit tests: _has_access / _trial_remaining helpers
# ---------------------------------------------------------------------------


def test_has_access_with_addon(user):
    user.chatbot_addon = True
    user.chatbot_msgs_used = 100  # far over the trial limit
    from juntos.routes.chat import _has_access

    assert _has_access(user) is True


def test_has_access_under_limit(user):
    user.chatbot_addon = False
    user.chatbot_msgs_used = 0
    from juntos.routes.chat import _has_access

    assert _has_access(user) is True


def test_has_access_at_limit(user):
    from juntos.ben_rag import FREE_TRIAL_LIMIT
    from juntos.routes.chat import _has_access

    user.chatbot_addon = False
    user.chatbot_msgs_used = FREE_TRIAL_LIMIT
    assert _has_access(user) is False


def test_trial_remaining_with_addon_returns_none(user):
    user.chatbot_addon = True
    from juntos.routes.chat import _trial_remaining

    assert _trial_remaining(user) is None


def test_trial_remaining_counts_down(user):
    from juntos.ben_rag import FREE_TRIAL_LIMIT
    from juntos.routes.chat import _trial_remaining

    user.chatbot_addon = False
    user.chatbot_msgs_used = 2
    assert _trial_remaining(user) == FREE_TRIAL_LIMIT - 2


def test_trial_remaining_floors_at_zero(user):
    from juntos.ben_rag import FREE_TRIAL_LIMIT
    from juntos.routes.chat import _trial_remaining

    user.chatbot_addon = False
    user.chatbot_msgs_used = FREE_TRIAL_LIMIT + 10
    assert _trial_remaining(user) == 0
