# Implementation Plan: One-liner Windows install (PATH-proof)

## Overview
Fresh Windows machines fail Synthsrch install in three places: no Python,
`Scripts` dir not on PATH (pip warns, exes unresolvable), and `.ps1`
execution friction (double-click opens Notepad, `Run with PowerShell`
closes instantly, RemoteSigned blocks). A single remote one-liner
(`irm <bootstrap.ps1> | iex` with Bypass) takes a bare machine to a
verified install, and the README is restructured so the one-liner is the
primary path with ordering unambiguous.

## Architecture Decisions
- `bootstrap.ps1` is self-contained (mirrors `install.ps1` steps inline)
  rather than downloading-then-calling `install.ps1`, so session-PATH
  fixes apply to the user's current terminal.
- Everything standardizes on the `py` launcher (falls back to `python`);
  bare `pip` is never used (multi-Python mismatch guard).
- Python bootstrap via pinned winget id `Python.Python.3.12`
  (meta-package `Python.Python.3` is unreliable); PATH re-read from the
  registry in-session after winget install.
- Git optional: clone if present, else zip download + Expand-Archive.
- `crawl4ai-setup` stays optional/non-fatal (trafilatura covers plain pages).
- `install.ps1` kept as-is for users who already cloned the repo.

## Task List

### Phase 1: Bootstrap script
- [ ] Task 1: `bootstrap.ps1` — Python ensure, code acquire, pip install,
  PATH fix, optional browser engine, doctor verify, end-state messaging

### Checkpoint: script
- [ ] PowerShell parser reports zero errors on `bootstrap.ps1`
- [ ] Safe blocks dry-tested (PATH detect, repo-root detect)

### Phase 2: Docs
- [ ] Task 2: README Install section — prereqs, Option A one-liner
  (primary), Option B manual, ordering unambiguous

### Checkpoint: Complete
- [ ] `py -m pytest -q` passes (no backend changes expected, sanity)
- [ ] `py -m synthsrch doctor` still healthy
- [ ] Commit + push to `main` (GitHub raw URL must serve new files)

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| winget missing on target machine | Med | Detect + print python.org manual fallback, exit clearly |
| winget Python install needs new terminal for PATH | Med | Re-read Machine+User PATH from registry in-session after install |
| Multiple Pythons on target | Med | Standardize on `py`; doctor `exe:` line reports status |
| `irm \| iex` trust concern | Low | URL pinned to this repo's `main`; user can open it first |

## Open Questions (need user / other-machine info)
- `winget --version` on the other machine (Python auto-install path?)
- Windows 10 or 11 there; how Python was installed (python.org / Store / winget)
- Pending diagnostic output: `py --version` vs `pip --version`, `py -m pip show synthsrch`
