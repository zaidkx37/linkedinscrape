"""Shared fixtures for linkedinscrape tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from linkedinscrape.models import TestScore  # noqa: F401

# Prevent pytest from trying to collect TestScore as a test class
TestScore.__test__ = False  # type: ignore[attr-defined]


@pytest.fixture
def output_dir(tmp_path) -> Path:
    return tmp_path / "test_output"
