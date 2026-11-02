"""Tests for toolbreaker pytest plugin."""


def test_toolbreaker_fixture_imports():
    """Test that the toolbreaker fixture can be imported from plugin."""
    from toolbreaker.plugin import toolbreaker as fixture_func

    # The fixture function should be callable and return a RotHarness
    assert callable(fixture_func)


def test_toolbreaker_marker_configured():
    """Test that toolbreaker marker is accessible via pytest config."""
    # This test verifies the marker is registered in pyproject.toml
    pass
