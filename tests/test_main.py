"""Tests for the main module."""

import pytest
from src.main import main


def test_main_runs_without_error(capsys) -> None:
    """Test that main function runs without error."""
    main()
    captured = capsys.readouterr()
    assert "IAVideoEditor" in captured.out
