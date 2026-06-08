"""Render the marketing HTML to PNGs at 2x with Playwright.

    python assets/src/render.py

Outputs into assets/. Re-run whenever the source HTML changes.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent  # assets/

# (source html, css width, css height, output png)
JOBS = [
    ("social.html", 1280, 640, "social-preview.png"),
    ("hero.html", 1280, 420, "hero.png"),
]


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for html, width, height, out in JOBS:
            ctx = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2,
                reduced_motion="reduce",
            )
            page = ctx.new_page()
            page.goto((HERE / html).as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / out), clip={"x": 0, "y": 0, "width": width, "height": height})
            ctx.close()
            print(f"rendered {out} ({width*2}x{height*2})")
        browser.close()


if __name__ == "__main__":
    main()
