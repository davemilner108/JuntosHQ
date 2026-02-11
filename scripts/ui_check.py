"""Playwright UI check — starts the Flask app, visits each page, takes screenshots,
and reports visual/structural discrepancies."""

import os
import sys
import threading
import time

# Ensure the src package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from playwright.sync_api import sync_playwright

from juntos import create_app
from juntos.config import TestConfig
from juntos.models import Junto, Member, User, db

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

PORT = 5199
BASE = f"http://127.0.0.1:{PORT}"


def seed_data(app):
    """Create a user, a junto with members, and return the user."""
    with app.app_context():
        db.create_all()
        user = User(
            provider="github",
            provider_id="ui-check-001",
            email="franklin@example.com",
            name="Benjamin Franklin",
            avatar_url="",
        )
        db.session.add(user)
        db.session.flush()

        junto = Junto(
            name="Philadelphia Junto",
            description="A club for mutual improvement in morals, politics and philosophy.",
            owner_id=user.id,
        )
        db.session.add(junto)
        db.session.flush()

        for name, role in [
            ("Thomas Godfrey", "Glazier & Mathematician"),
            ("Joseph Breintnall", "Copier of Deeds"),
            ("William Parsons", "Shoemaker & Astrologer"),
        ]:
            db.session.add(Member(name=name, role=role, junto_id=junto.id))

        db.session.commit()
        return user.id, junto.id


def run_server(app):
    app.run(port=PORT, use_reloader=False)


def check_ui():
    issues = []

    app = create_app(TestConfig)
    user_id, junto_id = seed_data(app)

    server = threading.Thread(target=run_server, args=(app,), daemon=True)
    server.start()
    time.sleep(2)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # Desktop viewport
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # Inject session cookie to simulate login
        page.goto(BASE)
        page.context.add_cookies([{
            "name": "session",
            "value": "",
            "domain": "127.0.0.1",
            "path": "/",
        }])

        # --- 1. Index page (logged out) ---
        page.goto(BASE)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_index.png"), full_page=True)

        # Check hero section
        hero = page.query_selector(".hero")
        if not hero:
            issues.append("Index: .hero section is missing")
        hero_img = page.query_selector(".hero-franklin")
        if not hero_img:
            issues.append("Index: .hero-franklin image is missing")
        else:
            bb = hero_img.bounding_box()
            if bb and (bb["width"] < 10 or bb["height"] < 10):
                issues.append(f"Index: .hero-franklin image too small ({bb['width']}x{bb['height']})")

        # Check nav
        site_title = page.query_selector("a.site-title")
        if not site_title:
            issues.append("Index: Site title link is missing from nav")
        else:
            title_text = site_title.inner_text()
            if "JuntosHQ" not in title_text:
                issues.append(f"Index: Site title text unexpected: '{title_text}'")

        press_mark = page.query_selector("a.site-title img")
        if not press_mark:
            issues.append("Index: Press-mark SVG missing from site title")
        else:
            bb = press_mark.bounding_box()
            if bb and (bb["width"] < 10 or bb["height"] < 10):
                issues.append(f"Index: Press-mark SVG too small ({bb['width']}x{bb['height']})")

        about_link = page.query_selector("a.nav-link")
        if not about_link:
            issues.append("Index: About nav link is missing")

        sign_in_btn = page.query_selector(".nav-auth .btn-primary")
        if not sign_in_btn:
            issues.append("Index: Sign-in button missing (logged out)")

        tagline = page.query_selector(".tagline")
        if not tagline:
            issues.append("Index: Tagline is missing")
        elif not tagline.is_visible():
            issues.append("Index: Tagline is not visible")

        # Check card list
        cards = page.query_selector_all(".card")
        if len(cards) == 0:
            issues.append("Index: No .card elements found (expected at least 1 seeded junto)")
        else:
            for i, card in enumerate(cards):
                link = card.query_selector("a")
                if not link:
                    issues.append(f"Index: Card {i} has no link")
                desc = card.query_selector(".card-description")
                if not desc:
                    issues.append(f"Index: Card {i} has no .card-description")

        # Footer check
        footer = page.query_selector("footer")
        if not footer:
            issues.append("Index: Footer is missing")
        # Check Create Junto button
        create_btn = page.query_selector("a.btn.btn-primary[href*='new']")
        if not create_btn:
            issues.append("Index: 'Create Junto' button is missing")

        # --- 2. About page ---
        page.goto(f"{BASE}/about")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_about.png"), full_page=True)

        about_h1 = page.query_selector("h1")
        if not about_h1 or "About" not in about_h1.inner_text():
            issues.append("About: h1 missing or wrong text")

        about_prose = page.query_selector(".about-prose")
        if not about_prose:
            issues.append("About: .about-prose container is missing")

        about_h2s = page.query_selector_all(".about-prose h2")
        if len(about_h2s) < 3:
            issues.append(f"About: Expected 3 h2 subheads, found {len(about_h2s)}")

        # --- 3. Login page ---
        page.goto(f"{BASE}/auth/login")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_login.png"), full_page=True)

        auth_container = page.query_selector(".auth-container")
        if not auth_container:
            issues.append("Login: .auth-container is missing")

        google_btn = page.query_selector("a.btn-primary[href*='google']")
        if not google_btn:
            issues.append("Login: Google sign-in button is missing")

        github_btn = page.query_selector("a.btn-secondary[href*='github']")
        if not github_btn:
            issues.append("Login: GitHub sign-in button is missing")

        auth_providers = page.query_selector(".auth-providers")
        if auth_providers:
            # Check buttons are stacked or side by side
            btns = auth_providers.query_selector_all(".btn")
            if len(btns) >= 2:
                b1 = btns[0].bounding_box()
                b2 = btns[1].bounding_box()
                if b1 and b2:
                    # Check for overlap
                    if (b1["y"] < b2["y"] + b2["height"] and b2["y"] < b1["y"] + b1["height"]
                            and b1["x"] < b2["x"] + b2["width"] and b2["x"] < b1["x"] + b1["width"]):
                        issues.append("Login: Auth provider buttons overlap")

        # --- 4. Log in via session to check authenticated pages ---
        context.close()

        # Build a signed session cookie using Flask's session interface
        from flask.sessions import SecureCookieSessionInterface
        si = SecureCookieSessionInterface()
        serializer = si.get_signing_serializer(app)
        session_val = serializer.dumps({"user_id": user_id})

        context2 = browser.new_context(viewport={"width": 1280, "height": 900})
        page2 = context2.new_page()
        # Seed the cookie before navigating
        page2.context.add_cookies([{
            "name": "session",
            "value": session_val,
            "domain": "127.0.0.1",
            "path": "/",
        }])

        if True:

            # --- 5. Index page (logged in) ---
            page2.goto(BASE)
            page2.wait_for_load_state("networkidle")
            page2.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_index_logged_in.png"), full_page=True)

            nav_username = page2.query_selector(".nav-username")
            if not nav_username:
                issues.append("Index (auth): .nav-username is missing")
            else:
                name_text = nav_username.inner_text()
                if "Benjamin Franklin" not in name_text:
                    issues.append(f"Index (auth): nav-username shows '{name_text}', expected 'Benjamin Franklin'")

            sign_out = page2.query_selector("button[type='submit']")
            if not sign_out or "Sign out" not in (sign_out.inner_text() or ""):
                issues.append("Index (auth): Sign out button missing or wrong text")

            # --- 6. Junto show page ---
            page2.goto(f"{BASE}/juntos/{junto_id}")
            page2.wait_for_load_state("networkidle")
            page2.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_junto_show.png"), full_page=True)

            show_h1 = page2.query_selector("h1")
            if not show_h1 or "Philadelphia Junto" not in show_h1.inner_text():
                issues.append("Show: h1 missing or wrong text")

            detail_desc = page2.query_selector(".detail-description")
            if not detail_desc:
                issues.append("Show: .detail-description is missing")

            action_bar = page2.query_selector(".action-bar")
            if not action_bar:
                issues.append("Show: .action-bar is missing for owner")
            else:
                edit_btn = action_bar.query_selector("a.btn-secondary")
                delete_btn = action_bar.query_selector("button.btn-danger")
                if not edit_btn:
                    issues.append("Show: Edit button missing in action bar")
                if not delete_btn:
                    issues.append("Show: Delete button missing in action bar")

            member_items = page2.query_selector_all(".member-item")
            if len(member_items) != 3:
                issues.append(f"Show: Expected 3 member items, found {len(member_items)}")

            for i, mi in enumerate(member_items):
                info = mi.query_selector(".member-info")
                if not info:
                    issues.append(f"Show: Member item {i} has no .member-info")
                actions = mi.query_selector(".member-actions")
                if not actions:
                    issues.append(f"Show: Member item {i} has no .member-actions (for owner)")

            add_member_btn = page2.query_selector("a.btn-primary[href*='members/new']")
            if not add_member_btn:
                issues.append("Show: 'Add Member' button is missing")

            back_link = page2.query_selector("a[href='/']")
            if not back_link:
                issues.append("Show: Back link to index is missing")

            # --- 7. New Junto form ---
            page2.goto(f"{BASE}/juntos/new")
            page2.wait_for_load_state("networkidle")
            page2.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_new_junto.png"), full_page=True)

            form_groups = page2.query_selector_all(".form-group")
            if len(form_groups) < 2:
                issues.append(f"New Junto: Expected 2 form groups, found {len(form_groups)}")

            name_input = page2.query_selector("input#name")
            if not name_input:
                issues.append("New Junto: Name input is missing")

            desc_textarea = page2.query_selector("textarea#description")
            if not desc_textarea:
                issues.append("New Junto: Description textarea is missing")

            form_actions = page2.query_selector(".form-actions")
            if not form_actions:
                issues.append("New Junto: .form-actions bar is missing")
            else:
                create_submit = form_actions.query_selector("button.btn-primary")
                cancel_link = form_actions.query_selector("a.btn-secondary")
                if not create_submit:
                    issues.append("New Junto: Create submit button is missing")
                if not cancel_link:
                    issues.append("New Junto: Cancel link is missing")

            # --- 8. Edit Junto form ---
            page2.goto(f"{BASE}/juntos/{junto_id}/edit")
            page2.wait_for_load_state("networkidle")
            page2.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_edit_junto.png"), full_page=True)

            edit_name_input = page2.query_selector("input#name")
            if edit_name_input:
                val = edit_name_input.get_attribute("value")
                if val != "Philadelphia Junto":
                    issues.append(f"Edit Junto: Name input value is '{val}', expected 'Philadelphia Junto'")
            else:
                issues.append("Edit Junto: Name input is missing")

            # --- 9. New Member form ---
            page2.goto(f"{BASE}/juntos/{junto_id}/members/new")
            page2.wait_for_load_state("networkidle")
            page2.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_new_member.png"), full_page=True)

            member_h1 = page2.query_selector("h1")
            if member_h1 and "Philadelphia Junto" not in member_h1.inner_text():
                issues.append(f"New Member: h1 does not mention junto name, says: '{member_h1.inner_text()}'")

            role_input = page2.query_selector("input#role")
            if not role_input:
                issues.append("New Member: Role input is missing")

            # --- 10. Check CSS classes are styled (not unstyled) ---
            page2.goto(BASE)
            page2.wait_for_load_state("networkidle")

            # Check that .btn-primary has the colonial-blue background
            btn = page2.query_selector(".btn.btn-primary")
            if btn:
                bg = page2.evaluate("el => getComputedStyle(el).backgroundColor", btn)
                if bg == "rgba(0, 0, 0, 0)" or bg == "transparent":
                    issues.append(f"CSS: .btn-primary has no background color (got: {bg})")

            # Check header background
            header = page2.query_selector("header")
            if header:
                hdr_bg = page2.evaluate("el => getComputedStyle(el).backgroundColor", header)
                if hdr_bg == "rgba(0, 0, 0, 0)" or hdr_bg == "transparent":
                    issues.append(f"CSS: header has no background color (got: {hdr_bg})")

            # Check h1 font-family includes Playfair
            h1_el = page2.query_selector("h1")
            if h1_el:
                h1_ff = page2.evaluate("el => getComputedStyle(el).fontFamily", h1_el)
                if "Playfair" not in h1_ff and "playfair" not in h1_ff.lower():
                    issues.append(f"CSS: h1 fontFamily does not include Playfair: '{h1_ff}'")

            # --- 11. Mobile viewport check ---
            context2.close()
            mobile_ctx = browser.new_context(viewport={"width": 375, "height": 812})
            mobile_page = mobile_ctx.new_page()
            mobile_page.goto(BASE)
            mobile_page.wait_for_load_state("networkidle")
            mobile_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "09_mobile_index.png"), full_page=True)

            # Check hero stacks vertically on mobile
            hero_m = mobile_page.query_selector(".hero")
            if hero_m:
                hero_dir = mobile_page.evaluate("el => getComputedStyle(el).flexDirection", hero_m)
                if hero_dir != "column":
                    issues.append(f"Mobile: .hero flex-direction is '{hero_dir}', expected 'column'")

            # Check nav wraps
            nav_row = mobile_page.query_selector(".nav-row")
            if nav_row:
                wrap = mobile_page.evaluate("el => getComputedStyle(el).flexWrap", nav_row)
                if wrap != "wrap":
                    issues.append(f"Mobile: .nav-row flex-wrap is '{wrap}', expected 'wrap'")

            # Check h1 fleuron hidden on mobile
            h1_m = mobile_page.query_selector("h1")
            if h1_m:
                after_display = mobile_page.evaluate(
                    "el => getComputedStyle(el, '::after').display", h1_m
                )
                if after_display != "none":
                    issues.append(f"Mobile: h1::after display is '{after_display}', expected 'none' on mobile")

            mobile_page.goto(f"{BASE}/about")
            mobile_page.wait_for_load_state("networkidle")
            mobile_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "10_mobile_about.png"), full_page=True)

            mobile_page.goto(f"{BASE}/auth/login")
            mobile_page.wait_for_load_state("networkidle")
            mobile_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "11_mobile_login.png"), full_page=True)

            # Check auth buttons don't overflow on mobile
            auth_prov_m = mobile_page.query_selector(".auth-providers")
            if auth_prov_m:
                vp_width = 375
                box = auth_prov_m.bounding_box()
                if box and box["x"] + box["width"] > vp_width + 2:
                    issues.append(f"Mobile: .auth-providers overflows viewport (right edge at {box['x'] + box['width']}px)")

            mobile_ctx.close()
        else:
            issues.append("Could not extract session cookie — skipping authenticated page checks")

        browser.close()

    return issues


if __name__ == "__main__":
    print("=" * 60)
    print("JuntosHQ — Playwright UI Check")
    print("=" * 60)
    found = check_ui()
    print()
    if found:
        print(f"Found {len(found)} issue(s):")
        for i, issue in enumerate(found, 1):
            print(f"  {i}. {issue}")
    else:
        print("No UI discrepancies found.")
    print()
    print(f"Screenshots saved to: {os.path.abspath(SCREENSHOTS_DIR)}")
    print("=" * 60)
