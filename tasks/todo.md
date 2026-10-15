# Todo: One-liner Windows install

- [x] Task 1: `bootstrap.ps1` (Small: 1 file)
  - Acceptance: bare machine (no Python) reaches verified install via one-liner;
    existing Python/repo cases reuse without re-clone; PATH fixed for session + user;
    crawl4ai failure never aborts; ends with working command or exact fallback.
  - Verification: PS parser clean; e2e bootstrap run green 2026-10-15
    (pip rebuild+reinstall ok, Scripts dir resolved, crawl4ai-setup completed,
    doctor healthy, `synthsrch` resolves in-session).
  - Dependencies: none. Files: `bootstrap.ps1`.
- [x] Task 2: README Install restructure (XS: 1 file)
  - Acceptance: prereqs stated; one-liner primary with copy-paste block;
    manual path kept; explicit that helper replaces (not follows) manual steps;
    Python auto-install behavior documented.
  - Verification: read-back of section; push to main.
  - Dependencies: Task 1 (one-liner URL must exist). Files: `README.md`.

## Checkpoint: Complete
- [x] Parser clean, tests pass, doctor healthy, pushed, other-machine info requested
