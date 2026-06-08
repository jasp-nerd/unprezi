"""Walk a Prezi presentation in a headless browser and grab every step.

Prezi used to expose a storyboard API that handed you the slides as images.
They locked it down, so the old prezi2pdf approach 404s/403s now. This takes
the other route: open the presentation in a real browser, step through the
path with the arrow key, and screenshot the WebGL canvas at each stop. What
you see is what you get.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout

# The viewer paints chrome on top of the canvas: nav arrows, the bottom
# progress bar, the cookie banner, a hamburger menu. We screenshot the canvas
# element, and anything sitting inside its box lands in the shot too, so hide it.
_HIDE_CSS = """
header,
[class*="viewer-header"],
[class*="navigation-button"],
[class*="on-screen-navigation"],
[class*="webgl-viewer-navbar"],
[class*="hamburger"],
[class*="viewer-logo"],
[class*="info-overlay"],
[class*="footer"],
#onetrust-banner-sdk,
#ot-sdk-btn-floating,
#onetrust-consent-sdk { display: none !important; }
"""

# OneTrust cookie banner. First one that exists gets clicked.
_COOKIE_BUTTONS = (
    "#onetrust-reject-all-handler",
    "#onetrust-accept-btn-handler",
)

# When the path runs out the viewer shows a replay/restart overlay. We don't
# want that frame in the PDF, so we stop the moment one of these shows up.
_END_SELECTORS = (
    "[class*='restart' i]",
    "[class*='replay' i]",
    "[class*='ended' i]",
    "[class*='end-screen' i]",
    "[class*='overview-button' i]",
)

CANVAS = "#canvas"

ProgressFn = Callable[[str], None]


class PreziError(RuntimeError):
    """Something about the presentation or the page didn't go as expected."""


@dataclass
class Options:
    scale: float = 2.0
    viewport_width: int = 1440
    viewport_height: int = 900
    headed: bool = False
    # How long to wait for a step's zoom animation to settle, and how often to
    # re-check. A step is "settled" once two consecutive screenshots match.
    settle_timeout: float = 8.0
    settle_interval: float = 0.4
    # Give the animation a beat to start before we begin checking for settle,
    # otherwise the first two reads match and we capture mid-transition.
    start_delay: float = 0.6
    # Hard cap so a looping or runaway presentation can't spin forever.
    max_steps: int = 600
    # Extra headless flags help WebGL render off-screen on some machines.
    browser_args: list[str] = field(
        default_factory=lambda: ["--use-gl=angle", "--use-angle=swiftshader"]
    )


@dataclass
class Result:
    title: str
    frames: list[bytes]


def _noop(_: str) -> None:
    pass


def slugify(text: str, fallback: str = "prezi") -> str:
    text = re.sub(r"\s+", "-", (text or "").strip())
    text = re.sub(r"[^A-Za-z0-9._-]", "", text)
    return text.strip("-")[:120] or fallback


def _dismiss_cookies(page: Page) -> None:
    for selector in _COOKIE_BUTTONS:
        try:
            button = page.locator(selector)
            if button.count() and button.first.is_visible():
                button.first.click(timeout=2000)
                page.wait_for_timeout(400)
                return
        except PlaywrightError:
            continue


def _start_presenting(page: Page, timeout_ms: int = 30_000) -> None:
    """Click the Present button and wait for the WebGL canvas to mount."""
    # The play button is an <img> sitting next to a "Present" label. Try the
    # obvious handles in order; after each, give the canvas a chance to appear.
    candidates = (
        lambda: page.get_by_text("Present", exact=True).first.click(timeout=2500),
        lambda: page.locator(".viewer-common-info-overlay-button-label")
        .first.click(timeout=2500),
        lambda: page.get_by_role("img").first.click(timeout=2500),
        lambda: page.mouse.click(
            page.viewport_size["width"] / 2, page.viewport_size["height"] / 2
        ),
    )
    deadline = time.monotonic() + timeout_ms / 1000
    for click in candidates:
        if page.locator(CANVAS).count():
            break
        try:
            click()
        except PlaywrightError:
            pass
        try:
            page.wait_for_selector(CANVAS, timeout=4000, state="attached")
            break
        except PlaywrightTimeout:
            continue

    try:
        page.wait_for_selector(CANVAS, timeout=max(1000, int((deadline - time.monotonic()) * 1000)))
    except PlaywrightTimeout as exc:
        raise PreziError(
            "Couldn't start the presentation — no canvas appeared. "
            "Is this a public prezi.com/view/ link? Try again with --headed to watch."
        ) from exc


def _canvas_png(page: Page) -> bytes:
    return page.locator(CANVAS).screenshot(type="png")


def _settle(page: Page, opts: Options) -> bytes:
    """Wait for the current step to stop animating, return its screenshot."""
    page.wait_for_timeout(int(opts.start_delay * 1000))
    previous = _canvas_png(page)
    waited = 0.0
    while waited < opts.settle_timeout:
        page.wait_for_timeout(int(opts.settle_interval * 1000))
        waited += opts.settle_interval
        current = _canvas_png(page)
        if current == previous:
            return current
        previous = current
    return previous


def _at_end(page: Page) -> bool:
    for selector in _END_SELECTORS:
        try:
            loc = page.locator(selector)
            if loc.count() and loc.first.is_visible():
                return True
        except PlaywrightError:
            continue
    return False


def capture(url: str, opts: Options | None = None, on_progress: ProgressFn = _noop) -> Result:
    """Open a Prezi and return one screenshot per step along its path."""
    opts = opts or Options()
    if "prezi.com" not in url:
        raise PreziError(f"That doesn't look like a Prezi URL: {url!r}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not opts.headed, args=opts.browser_args)
        context = browser.new_context(
            viewport={"width": opts.viewport_width, "height": opts.viewport_height},
            device_scale_factor=opts.scale,
            reduced_motion="reduce",
        )
        page = context.new_page()
        try:
            on_progress(f"opening {url}")
            page.goto(url, wait_until="load", timeout=60_000)
            _dismiss_cookies(page)
            title = (page.title() or "").replace(" on Prezi", "").strip()

            on_progress("starting the presentation")
            _start_presenting(page)
            page.add_style_tag(content=_HIDE_CSS)
            page.wait_for_timeout(1200)  # let the first frame paint

            frames = [_settle(page, opts)]
            seen = {hashlib.md5(frames[0]).digest()}
            on_progress("captured step 1")

            while len(frames) < opts.max_steps:
                page.keyboard.press("ArrowRight")
                frame = _settle(page, opts)
                digest = hashlib.md5(frame).digest()

                if digest == hashlib.md5(frames[-1]).digest():
                    break  # canvas stopped moving — end of the path
                if _at_end(page):
                    break  # replay/restart overlay showed up
                frames.append(frame)
                on_progress(f"captured step {len(frames)}")

            return Result(title=title or "prezi", frames=frames)
        finally:
            context.close()
            browser.close()
