"""Tests for toolbreaker fault mutators."""

import json

import pytest

from toolbreaker.faults import (
    truncate_json,
    rate_limit,
    payload_bomb,
    latency_spike,
    empty_lie,
    server_fault,
)


def test_truncate_json_full_ratio():
    """Test JSON truncation with ratio=1.0 returns original."""
    result = truncate_json(ratio=1.0).apply("hello world", (), {})
    assert result == "hello world"


def test_truncate_json_string_ratio():
    """Test JSON truncation slices string output."""
    result = truncate_json(ratio=0.5).apply("hello world", (), {})
    # Returns truncated string, not parsed JSON
    assert len(result) == 5  # "hello"


def test_truncate_json_dict_ratio():
    """Test JSON truncation slices dict output as string."""
    result = truncate_json(ratio=0.5).apply({"a": "b" * 100}, (), {})
    # Returns truncated string (invalid JSON due to mid-stream drop simulation)
    assert isinstance(result, str)
    assert len(result) < len(json.dumps({"a": "b" * 100}))  # Should be truncated


def test_rate_limit():
    """Test rate limit fault."""
    # As exception
    fault = rate_limit(retry_after=60, as_exception=True)
    with pytest.raises(RuntimeError, match="429 Too Many Requests"):
        fault.apply(None, (), {})

    # As return value
    fault = rate_limit(retry_after=30, as_exception=False)
    result = fault.apply(None, (), {})
    assert result["isError"] is True
    assert result["error"]["code"] == 429
    assert result["error"]["retry_after"] == 30


def test_payload_bomb():
    """Test payload bomb size."""
    fault = payload_bomb(size_kb=1)
    result = fault.apply(None, (), {})
    assert isinstance(result, str)
    # Should be approximately 1KB
    assert len(result) <= 1024 + 100  # allow some buffer


def test_latency_spike_sync():
    """Test latency spike in sync mode."""
    import time

    start = time.perf_counter()
    fault = latency_spike(seconds=0.1)
    result = fault.apply("test", (), {})
    elapsed = time.perf_counter() - start
    # Should have slept at least 0.05 seconds
    assert elapsed >= 0.05
    assert result == "test"


def test_empty_lie():
    """Test empty lie fault."""
    fault = empty_lie()
    result = fault.apply(None, (), {})
    assert result == {"status": "success", "data": None}


def test_server_fault():
    """Test server fault."""
    fault = server_fault(code=502)
    result = fault.apply(None, (), {})
    assert result["isError"] is True
    assert result["error"]["code"] == 502
    assert "Bad Gateway" in result["error"]["message"]
