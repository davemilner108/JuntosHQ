"""Quick debug: visit localhost:5000, capture page source and CSS."""
import os
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    page.goto("http://localhost:5000")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "debug_live.png"), full_page=True)

    # Dump the page HTML
    html = page.content()
    with open(os.path.join(SCREENSHOTS_DIR, "debug_live.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("=== PAGE TITLE ===")
    print(page.title())
    print()

    # Check what CSS is loaded
    print("=== STYLESHEETS ===")
    sheets = page.evaluate("""() => {
        return Array.from(document.styleSheets).map(s => ({
            href: s.href,
            rules: s.cssRules ? s.cssRules.length : 'N/A (cross-origin)',
            disabled: s.disabled
        }));
    }""")
    for s in sheets:
        print(f"  href: {s['href']}")
        print(f"  rules: {s['rules']}, disabled: {s['disabled']}")
        print()

    # Check if key CSS classes are styled
    print("=== CSS DIAGNOSTICS ===")
    checks = {
        "header bg": "getComputedStyle(document.querySelector('header')).backgroundColor",
        "h1 font": "getComputedStyle(document.querySelector('h1')).fontFamily",
        ".hero display": "document.querySelector('.hero') ? getComputedStyle(document.querySelector('.hero')).display : 'ELEMENT NOT FOUND'",
        ".btn-primary bg": "document.querySelector('.btn-primary') ? getComputedStyle(document.querySelector('.btn-primary')).backgroundColor : 'ELEMENT NOT FOUND'",
        ".card-list list-style": "document.querySelector('.card-list') ? getComputedStyle(document.querySelector('.card-list')).listStyleType : 'ELEMENT NOT FOUND'",
        ".nav-row display": "document.querySelector('.nav-row') ? getComputedStyle(document.querySelector('.nav-row')).display : 'ELEMENT NOT FOUND'",
        "a.site-title color": "document.querySelector('a.site-title') ? getComputedStyle(document.querySelector('a.site-title')).color : 'ELEMENT NOT FOUND'",
    }
    for label, js in checks.items():
        val = page.evaluate(js)
        print(f"  {label}: {val}")

    # Check if franklin.svg exists
    print()
    print("=== FRANKLIN SVG ===")
    franklin = page.query_selector(".hero-franklin")
    if franklin:
        bb = franklin.bounding_box()
        print(f"  bounding box: {bb}")
        natural = page.evaluate("""el => ({
            naturalWidth: el.naturalWidth,
            naturalHeight: el.naturalHeight,
            complete: el.complete,
            src: el.src
        })""", franklin)
        print(f"  natural: {natural}")
    else:
        print("  .hero-franklin NOT FOUND in DOM")

    # Print first 200 lines of the actual HTML
    print()
    print("=== FIRST 100 LINES OF HTML ===")
    for i, line in enumerate(html.split("\n")[:100], 1):
        print(f"  {i:3}: {line}")

    browser.close()
