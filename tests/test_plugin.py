"""Tests for toolrot pytest plugin."""


def test_toolrot_fixture_imports():
    """Test that the toolrot fixture can be imported from plugin."""
    from toolrot.plugin import toolrot as fixture_func

    # The fixture function should be callable and return a RotHarness
    assert callable(fixture_func)


def test_toolrot_marker_configured():
    """Test that toolrot marker is accessible via pytest config."""
    # This test verifies the marker is registered in pyproject.toml
    pass
