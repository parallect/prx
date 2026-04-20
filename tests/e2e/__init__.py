"""End-to-end integration tests for the prx CLI.

These tests shell out to the installed ``prx`` binary via ``uv run`` and
assert real behaviour (return codes, stdout, stderr). They exist because
unit tests that invoke Typer in-process cannot catch a regression where
``prx`` itself has been replaced by a stub binary or where the entry
point is broken — like the "Hello from prx!" squatter issue that hit a
real user trying to run ``prx publish``.
"""
