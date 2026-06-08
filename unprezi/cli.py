"""Command line entry point for unprezi."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import Options, PreziError, Result, capture, slugify


def _build_pdf(result: Result, out: Path, jpeg_quality: int | None) -> None:
    import img2pdf

    frames = result.frames
    if jpeg_quality is not None:
        from io import BytesIO

        from PIL import Image

        recoded = []
        for png in frames:
            image = Image.open(BytesIO(png)).convert("RGB")
            buffer = BytesIO()
            image.save(buffer, "JPEG", quality=jpeg_quality, optimize=True)
            recoded.append(buffer.getvalue())
        frames = recoded

    out.write_bytes(img2pdf.convert(frames))


def _save_pngs(result: Result, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    width = len(str(len(result.frames)))
    for i, png in enumerate(result.frames, 1):
        (out_dir / f"step-{i:0{width}d}.png").write_bytes(png)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="unprezi",
        description="Export a prezi.com presentation to a PDF (or PNG frames).",
    )
    parser.add_argument("url", help="A public prezi.com/view/ link")
    parser.add_argument(
        "-o", "--output",
        help="Output file (.pdf) or, with --png, a directory. Defaults to the prezi title.",
    )
    parser.add_argument(
        "--png", action="store_true",
        help="Write one PNG per step instead of a PDF.",
    )
    parser.add_argument(
        "--jpeg-quality", type=int, metavar="1-100",
        help="Recompress pages as JPEG at this quality for a much smaller PDF.",
    )
    parser.add_argument(
        "--scale", type=float, default=2.0,
        help="Device pixel ratio. Higher is sharper and heavier (default: 2).",
    )
    parser.add_argument(
        "--width", type=int, default=1440, help="Browser width (default: 1440).",
    )
    parser.add_argument(
        "--height", type=int, default=900, help="Browser height (default: 900).",
    )
    parser.add_argument(
        "--delay", type=float, metavar="SECONDS",
        help="Use a fixed wait per step instead of auto-detecting when it settles. "
        "Bump this if frames look caught mid-zoom.",
    )
    parser.add_argument(
        "--max-steps", type=int, default=600,
        help="Stop after this many steps, just in case (default: 600).",
    )
    parser.add_argument(
        "--headed", action="store_true", help="Show the browser window while it works.",
    )
    parser.add_argument("--quiet", action="store_true", help="Don't print progress.")
    parser.add_argument("--version", action="version", version=f"unprezi {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    opts = Options(
        scale=args.scale,
        viewport_width=args.width,
        viewport_height=args.height,
        headed=args.headed,
        max_steps=args.max_steps,
    )
    if args.delay is not None:
        # Fixed wait: skip settle-polling by making the first read authoritative.
        opts.start_delay = args.delay
        opts.settle_timeout = 0.0

    log = (lambda _: None) if args.quiet else (lambda m: print(f"  {m}", file=sys.stderr))

    try:
        result = capture(args.url, opts, on_progress=log)
    except PreziError as exc:
        print(f"unprezi: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - surface anything else cleanly
        print(f"unprezi: something broke — {exc}", file=sys.stderr)
        return 1

    if not result.frames:
        print("unprezi: didn't capture any frames", file=sys.stderr)
        return 1

    name = slugify(result.title)
    if args.png:
        out_dir = Path(args.output) if args.output else Path(name)
        _save_pngs(result, out_dir)
        print(f"{len(result.frames)} frames -> {out_dir}/")
    else:
        out = Path(args.output) if args.output else Path(f"{name}.pdf")
        if out.suffix.lower() != ".pdf":
            out = out.with_suffix(".pdf")
        _build_pdf(result, out, args.jpeg_quality)
        print(f"{len(result.frames)} pages -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
