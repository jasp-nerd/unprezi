---
name: Bug report
about: Something didn't export right
labels: bug
---

**The Prezi**
The link you ran it on (if you can share it), or what kind of link it was
(`prezi.com/view/...` vs `prezi.com/<id>/...`).

**The command**
```
unprezi ...
```

**What happened**
What you got vs what you expected. Wrong page count, blank/cut-off frames,
crash, hang, whatever it was. If it crashed, paste the error.

**Setup**
- OS:
- Python: `python --version`
- Playwright: `playwright --version`

**Tip:** re-run with `--headed` and watch the browser; it usually shows exactly
where it goes off the rails.
