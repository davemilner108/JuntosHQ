import secrets
from datetime import UTC, datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from juntos.models import SignupCoupon, User, db

bp = Blueprint("coupons", __name__, url_prefix="/auth")


def _generate_coupons_for_user(user: User) -> list[SignupCoupon]:
    """Create COUPONS_PER_USER new unused coupons owned by *user*."""
    count = current_app.config.get("COUPONS_PER_USER", 10)
    coupons = []
    for _ in range(count):
        coupon = SignupCoupon(
            code=secrets.token_urlsafe(12),
            created_by_user_id=user.id,
        )
        db.session.add(coupon)
        coupons.append(coupon)
    db.session.commit()
    return coupons


def _redeem_coupon(code: str, user: User) -> tuple[bool, str]:
    """Validate and redeem *code* for *user*.

    Returns (success, error_message).  On success the coupon row (if any) is
    updated and user.signup_verified is set to True but NOT committed — the
    caller must commit.
    """
    hard_coded = current_app.config.get("HARD_CODED_COUPON", "")
    if hard_coded and code.strip().upper() == hard_coded.upper():
        user.signup_verified = True
        return True, ""

    coupon = db.session.execute(
        db.select(SignupCoupon).where(SignupCoupon.code == code.strip())
    ).scalar_one_or_none()

    if coupon is None:
        return False, "Invalid coupon code. Please check and try again."

    if coupon.is_used:
        return False, "This coupon has already been used."

    coupon.used_by_user_id = user.id
    coupon.used_at = datetime.now(UTC)
    user.signup_verified = True
    return True, ""


@bp.route("/coupon", methods=["GET", "POST"])
def enter_coupon():
    """Coupon entry page shown to new users who need to verify their signup."""
    if g.current_user is None:
        flash("Please sign in to continue.", "error")
        return redirect(url_for("auth.login"))

    if g.current_user.signup_verified:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if not code:
            flash("Please enter a coupon code.", "error")
            return render_template("auth/coupon.html")

        success, err = _redeem_coupon(code, g.current_user)
        if not success:
            flash(err, "error")
            return render_template("auth/coupon.html")

        db.session.commit()

        # Award personal coupons to the newly verified user
        _generate_coupons_for_user(g.current_user)

        flash("Welcome to JuntosHQ! Your signup coupon has been accepted.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/coupon.html")


@bp.route("/my-coupons")
def my_coupons():
    """Show the current user's sharable personal coupon codes."""
    if g.current_user is None:
        flash("Please sign in to continue.", "error")
        return redirect(url_for("auth.login"))

    if current_app.config.get("INVITE_REQUIRED") and not g.current_user.signup_verified:
        flash("Please enter your signup coupon to continue.", "info")
        return redirect(url_for("coupons.enter_coupon"))

    coupons = (
        db.session.execute(
            db.select(SignupCoupon)
            .where(SignupCoupon.created_by_user_id == g.current_user.id)
            .order_by(SignupCoupon.created_at)
        )
        .scalars()
        .all()
    )
    return render_template("auth/my_coupons.html", coupons=coupons)
