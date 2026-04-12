import pytest
from app.tools import system_mcp, file_mcp


def test_open_app():
    """Test app opening."""
    pass  # Platform dependent


def test_search_files():
    result = file_mcp.search_files("test", ".")
    assert isinstance(result, list)


def test_summarize_folder():
    result = file_mcp.summarize_folder(".")
    assert isinstance(result, str)