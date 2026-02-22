"""Pytest configuration and fixtures."""

import sys
from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def reset_typer_force_terminal() -> Generator[None]:
    """Reset typer.rich_utils.FORCE_TERMINAL before each test.

    When FORCE_COLOR=1 is set in CI, the first CLI ``--help`` invocation
    imports ``typer.rich_utils`` which sets the module-level constant
    ``FORCE_TERMINAL = True`` at import time.  Because Python caches imported
    modules, this value persists for the rest of the test session.  Later
    tests that attempt to suppress colours via ``CliRunner(env={"FORCE_COLOR":
    None})`` patch ``os.environ`` too late: ``_get_rich_console()`` already
    reads the cached ``FORCE_TERMINAL = True``, causing Rich to inject ANSI
    escape codes that split option names such as ``--zip-dir`` across multiple
    sequences, breaking ``"zip-dir" in result.stdout`` assertions.

    This fixture resets ``FORCE_TERMINAL`` to ``None`` before every test so
    that each CLI invocation creates a console that auto-detects terminal
    capabilities from the (possibly patched) environment rather than using the
    stale cached value.
    """
    ru = sys.modules.get("typer.rich_utils")
    old = ru.FORCE_TERMINAL if ru is not None else None
    if ru is not None:
        ru.FORCE_TERMINAL = None
    yield
    if ru is not None:
        ru.FORCE_TERMINAL = old


@pytest.fixture
def sample_data() -> dict[str, str]:
    """Provide sample data for tests."""
    return {"key": "value"}
