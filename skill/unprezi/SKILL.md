---
name: unprezi
description: Export a prezi.com presentation to a PDF. Use when the user wants to download, save, archive, or convert a Prezi (a prezi.com/view/ or prezi.com/<id>/ link) to PDF or images. Works on current Prezi share links by driving a browser and screenshotting each step of the presentation path.
---

# unprezi — export a Prezi to PDF

Prezi presentations are rendered live in a WebGL canvas, and Prezi has locked down
the old storyboard API that tools like `prezi2pdf` relied on. The way that still
works: open the presentation in a browser, step through its path one stop at a
time, and screenshot the canvas at each stop. This skill does that.

There are two ways to run it. Prefer the CLI; fall back to the manual browser
route if the CLI isn't installed and the user only has the Playwright MCP browser.

## Option A — the `unprezi` CLI (preferred)

If Python is available, this is the fast, reliable path.

```bash
pip install unprezi          # or: pip install git+https://github.com/jasp-nerd/unprezi
playwright install chromium  # one-time, downloads the browser
unprezi "https://prezi.com/view/XXXXXXXX/"
```

It writes `<presentation-title>.pdf` in the current directory. Useful flags:

- `-o out.pdf` — set the output path
- `--jpeg-quality 82` — much smaller PDF
- `--png -o frames/` — write one PNG per step instead of a PDF
- `--headed` — watch the browser work (good for debugging)
- `--delay 2.5` — fixed wait per step instead of auto-settle (bump if frames look mid-zoom)

If `unprezi` isn't installed and the repo is checked out locally, run it from there:
`python -m unprezi "<url>"`.

## Option B — drive the Playwright MCP browser by hand

Use this when you can't install the CLI but you do have the Playwright browser
tools. The procedure mirrors what the CLI automates.

1. **Open** the prezi URL (`browser_navigate`). Wait a few seconds for it to load.
2. **Cookies:** if a OneTrust banner is showing, click `#onetrust-reject-all-handler`
   (or `#onetrust-accept-btn-handler`).
3. **Start presenting:** click the "Present" play button (an `<img>` next to a
   "Present" label). Wait until a `#canvas` element exists and the first frame paints.
4. **Hide the overlays** so screenshots are just the slide. Run this via
   `browser_evaluate`:
   ```js
   () => {
     const css = `header,[class*="viewer-header"],[class*="navigation-button"],
       [class*="on-screen-navigation"],[class*="webgl-viewer-navbar"],
       [class*="hamburger"],[class*="viewer-logo"],[class*="info-overlay"],
       [class*="footer"],#onetrust-banner-sdk,#ot-sdk-btn-floating
       {display:none !important;}`;
     const s = document.createElement('style'); s.textContent = css;
     document.head.appendChild(s);
   }
   ```
5. **Capture the loop.** For each step:
   - Screenshot the canvas element only: `browser_take_screenshot` with the `#canvas`
     element target, saved as `step-001.png`, `step-002.png`, …
   - Press `ArrowRight` (`browser_press_key`).
   - Wait ~2.5s for the zoom animation to settle.
   - Repeat.
   - **Stop** when a new screenshot is identical to the previous one (the canvas
     stopped moving — you've hit the end), or when a "Restart"/replay overlay shows.
     Don't include the restart frame.

   Note: `canvas.toDataURL()` returns a stale buffer here — always use real
   screenshots, and compare them by file hash to detect the end.

6. **Build the PDF** from the frames (drop any restart frame):
   ```bash
   python3 -c "import img2pdf,glob; \
     f=sorted(glob.glob('step-*.png')); \
     open('prezi.pdf','wb').write(img2pdf.convert(f))"
   ```

## Good to know

- Capture is **what-you-see**: a step's final, settled frame. Animated transitions
  and embedded video/audio don't carry into a PDF.
- The same overview frame can legitimately repeat — Prezi zooms back out between
  sections. That's part of the path, not a bug.
- Only works on presentations you can already open from the link. It doesn't get
  past logins or private/paywalled content. Only export presentations you have the
  right to.
