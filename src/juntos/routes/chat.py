"""Chat blueprint: Ben's Counsel AI chatbot."""

import anthropic as anthropic_sdk
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from fpdf import FPDF

from juntos.auth_utils import login_required
from juntos.ben_rag import FREE_TRIAL_LIMIT, build_messages
from juntos.franklin import get_weekly_prompt
from juntos.models import ChatMessage, ChatSession, Junto, db

bp = Blueprint("chat", __name__, url_prefix="/chat")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_access(user) -> bool:
    return user.chatbot_addon or user.chatbot_msgs_used < FREE_TRIAL_LIMIT


def _trial_remaining(user) -> int | None:
    """Returns messages remaining, or None if user has the add-on (unlimited)."""
    if user.chatbot_addon:
        return None
    return max(0, FREE_TRIAL_LIMIT - user.chatbot_msgs_used)


def _get_or_create_session(user_id: int, junto_id: int | None) -> ChatSession:
    """Resume the session stored in Flask session, or start a fresh one."""
    chat_session_id = session.get("chat_session_id")
    if chat_session_id:
        chat_session = db.session.get(ChatSession, chat_session_id)
        if chat_session and chat_session.user_id == user_id:
            return chat_session

    chat_session = ChatSession(user_id=user_id, junto_id=junto_id)
    db.session.add(chat_session)
    db.session.commit()
    session["chat_session_id"] = chat_session.id
    return chat_session


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/")
@login_required
def show():
    chat_session = _get_or_create_session(g.current_user.id, None)
    return render_template(
        "chat/show.html",
        chat_session=chat_session,
        junto=None,
        current_question=None,
        trial_remaining=_trial_remaining(g.current_user),
        has_access=_has_access(g.current_user),
    )


@bp.route("/junto/<int:junto_id>")
@login_required
def junto_chat(junto_id):
    junto = db.get_or_404(Junto, junto_id)
    prompt = get_weekly_prompt()
    current_question = prompt["text"]
    chat_session = _get_or_create_session(g.current_user.id, junto_id)
    return render_template(
        "chat/show.html",
        chat_session=chat_session,
        junto=junto,
        current_question=current_question,
        trial_remaining=_trial_remaining(g.current_user),
        has_access=_has_access(g.current_user),
    )


@bp.route("/message", methods=["POST"])
@login_required
def send_message():
    user = g.current_user

    if not _has_access(user):
        flash(
            "You've used your 5 free messages with Ben Franklin. "
            "Add the chatbot to your plan to continue the conversation.",
            "error",
        )
        return redirect(url_for("main.pricing"))

    junto_id = request.form.get("junto_id", type=int)
    user_message = request.form.get("message", "").strip()

    if not user_message:
        if junto_id:
            return redirect(url_for("chat.junto_chat", junto_id=junto_id))
        return redirect(url_for("chat.show"))

    # Get/create chat session
    chat_session = _get_or_create_session(user.id, junto_id)

    # Save the user's message
    db.session.add(
        ChatMessage(
            session_id=chat_session.id,
            role="user",
            content=user_message,
        )
    )
    db.session.commit()
    db.session.refresh(chat_session)

    # Optional junto context
    junto = db.session.get(Junto, junto_id) if junto_id else None
    current_question = get_weekly_prompt()["text"] if junto else None

    # Build prompt + history and call Claude
    # Pass history without the message we just added (it's appended inside
    # build_messages)
    history = chat_session.messages[:-1]
    system_prompt, messages = build_messages(
        history=history,
        user_message=user_message,
        junto=junto,
        current_question=current_question,
    )

    client = anthropic_sdk.Anthropic()
    model = current_app.config.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    try:
        ai_response = client.messages.create(
            model=model,
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        assistant_content = ai_response.content[0].text
    except Exception:
        current_app.logger.exception("Anthropic API call failed")
        flash(
            "Ben Franklin is momentarily indisposed. Please try again shortly.",
            "error",
        )
        if junto_id:
            return redirect(url_for("chat.junto_chat", junto_id=junto_id))
        return redirect(url_for("chat.show"))

    # Save Ben's reply
    db.session.add(
        ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=assistant_content,
        )
    )

    # Increment free-trial counter
    if not user.chatbot_addon:
        user.chatbot_msgs_used += 1

    db.session.commit()

    if junto_id:
        return redirect(url_for("chat.junto_chat", junto_id=junto_id))
    return redirect(url_for("chat.show"))


@bp.route("/new", methods=["POST"])
@login_required
def new_session():
    """Start a fresh conversation (clear the session pointer)."""
    junto_id = request.form.get("junto_id", type=int)
    session.pop("chat_session_id", None)
    if junto_id:
        return redirect(url_for("chat.junto_chat", junto_id=junto_id))
    return redirect(url_for("chat.show"))


_UNICODE_REPLACEMENTS = str.maketrans({
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u00a0": " ",    # non-breaking space
    "\u2022": "*",    # bullet
})


def _safe(text: str) -> str:
    """Replace Unicode characters unsupported by the Helvetica PDF font."""
    return (
        text.translate(_UNICODE_REPLACEMENTS)
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


@bp.route("/session/<int:session_id>/export.pdf")
@login_required
def export_pdf(session_id):
    """Export a chat session as a PDF transcript."""
    chat_session = db.get_or_404(ChatSession, session_id)

    if chat_session.user_id != g.current_user.id:
        flash("You do not have access to that conversation.", "error")
        return redirect(url_for("chat.show"))

    junto = (
        db.session.get(Junto, chat_session.junto_id)
        if chat_session.junto_id
        else None
    )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Ben's Counsel", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    if junto:
        pdf.cell(0, 6, _safe(f"Junto: {junto.name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 6,
        f"Session: {chat_session.created_at.strftime('%B %d, %Y')}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(6)

    # Messages
    for msg in chat_session.messages:
        if msg.role == "user":
            label = "You"
            pdf.set_font("Helvetica", "B", 10)
        else:
            label = "B. Franklin"
            pdf.set_font("Helvetica", "BI", 10)

        pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _safe(msg.content))
        pdf.ln(3)

    response = make_response(bytes(pdf.output()))
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=bens-counsel-session-{session_id}.pdf"
    )
    return response
