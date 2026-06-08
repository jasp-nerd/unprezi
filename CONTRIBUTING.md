# Contributing

Bug reports and PRs are welcome.

## Running it locally

```bash
git clone https://github.com/jasp-nerd/unprezi
cd unprezi
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
unprezi "https://prezi.com/view/XXXXXXXX/"
```

## Filing a bug

The thing that helps most: the **Prezi link** you ran it on (if you can share it),
the exact command, and your OS + Playwright version (`playwright --version`). Run
with `--headed` and watch where it goes wrong; that usually tells the whole story.

Prezi changes their viewer from time to time, so most breakage is a selector that
needs updating in `unprezi/core.py`. The constants near the top (`_HIDE_CSS`,
`_COOKIE_BUTTONS`, `_END_SELECTORS`, the present-button handles in
`_start_presenting`) are the usual suspects.

## A note

This is a small tool with a small surface. I'd rather keep it sharp at one job
than grow a pile of flags. If you have a bigger idea, open an issue first so we
can talk it through before you spend time on it.
