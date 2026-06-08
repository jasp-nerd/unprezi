"""Render the README demo GIF: a styled terminal running unprezi.

    python assets/src/make_demo.py

Writes assets/demo.gif. The output mirrors a real run; the step count is
representative so the clip stays short.
"""

import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "demo.gif"
W, H = 900, 560
STEPS = 16
VISIBLE = 12  # body lines kept on screen before it scrolls

CMD = '<span class="d">$</span> unprezi "https://prezi.com/view/abc123/"'


def build_lines():
    """Each entry is (html_lines, duration_ms) for one frame."""
    frames = [([CMD + '<span class="cur">▋</span>'], 1100)]
    body = [
        '  opening https://prezi.com/view/abc123/',
        '  starting the presentation',
    ]
    out = [CMD]
    for line in body:
        out.append(line)
        frames.append((out.copy(), 520))
    for n in range(1, STEPS + 1):
        out.append(f'  captured step {n}')
        frames.append((out.copy(), 165))
    out.append(f'<span class="ok">{STEPS} pages -&gt; product-roadmap.pdf</span>')
    frames.append((out.copy(), 2400))
    return frames


def window(lines):
    """Keep the prompt line plus the last VISIBLE body lines."""
    if len(lines) <= VISIBLE + 1:
        return lines
    return [lines[0], *lines[-VISIBLE:]]


SHELL = """
<!doctype html><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  * { margin:0; box-sizing:border-box; }
  body { width:900px; height:560px; background:#0b0d12; display:flex;
         align-items:center; justify-content:center; font-family:"Space Mono",monospace; }
  .term { width:820px; height:480px; background:#0e1117; border-radius:14px;
          box-shadow:0 30px 80px -30px rgba(0,0,0,.8); overflow:hidden;
          border:1px solid rgba(255,255,255,.08); }
  .bar { height:42px; display:flex; align-items:center; gap:9px; padding:0 18px;
         background:#141923; border-bottom:1px solid rgba(255,255,255,.06); }
  .dot { width:13px; height:13px; border-radius:50%; }
  .r{background:#ff5f57}.y{background:#febc2e}.g{background:#28c840}
  .name { margin-left:12px; color:#6b7385; font-size:14px; }
  .body { padding:20px 24px; font-size:19px; line-height:1.62; color:#c7ccd6; white-space:pre; }
  .d { color:#5563ff; }
  .cur { color:#8b7bff; }
  .ok { color:#3ddc84; font-weight:700; }
</style>
<body><div class="term">
  <div class="bar"><span class="dot r"></span><span class="dot y"></span><span class="dot g"></span><span class="name">zsh</span></div>
  <div class="body" id="body"></div>
</div></body>
"""


def main():
    frames_spec = build_lines()
    images, durations = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=2).new_page()
        page.set_content(SHELL, wait_until="load")
        page.evaluate("document.fonts.ready")
        for lines, dur in frames_spec:
            html = "\n".join(window(lines))
            page.evaluate("h => document.getElementById('body').innerHTML = h", html)
            png = page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H})
            images.append(Image.open(io.BytesIO(png)).convert("RGB"))
            durations.append(dur)
        browser.close()

    # 2x screenshots -> downscale for a crisp, lighter GIF
    images = [im.resize((W, H), Image.LANCZOS) for im in images]
    palette = images[0].convert("P", palette=Image.ADAPTIVE, colors=128)
    frames = [im.quantize(palette=palette, dither=Image.NONE) for im in images]
    frames[0].save(
        OUT, save_all=True, append_images=frames[1:], duration=durations,
        loop=0, optimize=True, disposal=2,
    )
    print(f"wrote {OUT} ({len(frames)} frames, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
