"""Smoke tests for the package bootstrap."""

from krithika import __version__


def test_package_version_is_defined() -> None:
    assert __version__ == "0.1.0"
