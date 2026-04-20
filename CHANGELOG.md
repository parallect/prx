# Changelog

## 0.2.0 (2026-04-20)

New features:

- `prx --version` / `prx -V` flag — prints the installed version without running any subcommand. Useful for CI, docs, and "am I actually running the right package" sanity checks.
- `prx publish --collection <slug>` — publish a bundle directly into a named collection; auto-creates the collection if it doesn't exist yet.

Testing:

- End-to-end integration test suite (`tests/e2e/`) that drives the installed `prx` binary as a subprocess — verifies real entry-point wiring, `--version`, `--help` listing all subcommands, and full `prx publish` against a fake prxhub (happy path + missing-key + missing-file + hub-500 error paths). Guards against "binary prints a stub" regressions.
- CI now runs the E2E suite on every PR across the Python 3.10–3.13 matrix.

Dependencies:

- `prx-spec>=0.2.0` (was `>=0.1.0`) — picks up manifest v1.1 support.

Docs:

- README rewritten for public release with a clear mission statement and explanation of the "PRX" expansion.
- TUI install hint fixed: `pip install "prx-cli[tui]"` (not `prx[tui]` — the `prx` name on PyPI is an unrelated squatter stub).

## 0.1.0 (2026-04-01)

Initial open source release.

- CLI toolkit for the .prx bundle format: `prx read`, `prx export`, `prx validate`, `prx verify`, `prx diff`, `prx list`
- PRXHub operations: `prx publish`, `prx search`, `prx clone`, `prx fork`, `prx star`, `prx repo`, `prx branch`, `prx push`, `prx mr`
- Key management: `prx keys generate`, `prx keys show`
- Configuration: `prx config` with TOML config file support
- Optional Textual TUI bundle browser via `prx open` (`pip install prx-cli[tui]`)
