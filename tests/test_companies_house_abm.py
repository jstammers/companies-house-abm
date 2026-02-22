"""Tests for companies_house_abm."""

from typer.testing import CliRunner

from companies_house_abm import __version__
from companies_house_abm.cli import app

# NO_COLOR=1 prevents ANSI colour codes. FORCE_COLOR=None *deletes* the key
# from os.environ during each test invocation (Click CliRunner treats a None
# value as "unset this variable"). This is necessary because CI sets
# FORCE_COLOR=1 globally; merely setting FORCE_COLOR="" leaves the key present
# and some code paths check key presence rather than value truthiness.
runner = CliRunner(env={"NO_COLOR": "1", "FORCE_COLOR": None})


def test_version() -> None:
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_cli_version() -> None:
    """Test CLI version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_hello_default() -> None:
    """Test CLI hello command with default argument."""
    result = runner.invoke(app, ["hello"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.stdout


def test_cli_hello_with_name() -> None:
    """Test CLI hello command with custom name."""
    result = runner.invoke(app, ["hello", "Test"])
    assert result.exit_code == 0
    assert "Hello, Test!" in result.stdout
