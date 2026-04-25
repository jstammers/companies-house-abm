"""Pytest configuration and fixtures."""

import datetime
import sys
from collections.abc import Generator

import pytest


def pytest_sessionstart(session: pytest.Session) -> None:
    """Rebuild optional merge-ref Pydantic models with a runtime datetime namespace.

    The PR CI runs against GitHub's pull-request merge ref, which can include the
    ``uk_data`` package from the base branch even when it is not present in this
    branch checkout. Those models use postponed annotations with
    ``datetime.date`` but import ``datetime`` only under ``TYPE_CHECKING``,
    which leaves the runtime namespace incomplete for Pydantic validation.

    When ``uk_data.api.models`` is importable, rebuild the affected models with
    the real ``datetime`` module injected. This keeps the test environment
    stable across the branch-only and merge-ref layouts without affecting
    branches where ``uk_data`` is absent.
    """
    try:
        from uk_data.api import models as uk_models
    except ImportError:
        return

    uk_models.__dict__.setdefault("datetime", datetime)
    for model_name in (
        "CompanySearchResult",
        "CompanySearchResponse",
        "Filing",
        "FilingHistoryResponse",
    ):
        getattr(uk_models, model_name).model_rebuild(
            _types_namespace={"datetime": datetime}
        )


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
    old = getattr(ru, "FORCE_TERMINAL", None) if ru is not None else None
    if ru is not None:
        ru.FORCE_TERMINAL = None  # type: ignore[attr-defined]
    yield
    if ru is not None:
        ru.FORCE_TERMINAL = old  # type: ignore[attr-defined]


@pytest.fixture
def sample_data() -> dict[str, str]:
    """Provide sample data for tests."""
    return {"key": "value"}
