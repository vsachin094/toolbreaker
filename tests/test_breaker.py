"""Tests for toolrot breaker circuit breaker and retry loop detection."""

import pytest

from toolrot.breaker import CallRecord, CircuitBreaker, AgentRetryLoopError


def test_call_record():
    """Test CallRecord dataclass."""
    record = CallRecord(
        tool_name="test_tool",
        args_hash="abc123",
        fault_injected="truncate_json",
        duration_ms=42.5,
    )
    assert record.tool_name == "test_tool"
    assert record.args_hash == "abc123"
    assert record.fault_injected == "truncate_json"
    assert record.duration_ms == 42.5


def test_agent_retry_loop_error():
    """Test AgentRetryLoopError raised and has records."""
    CircuitBreaker(max_identical_retries=2, max_total_calls=10)
    records = [
        CallRecord("tool", "hash1", None, 10.0),
        CallRecord("tool", "hash1", None, 12.0),
    ]
    try:
        raise AgentRetryLoopError(records)
    except AgentRetryLoopError as e:
        assert e.records == records


def test_circuit_breaker_no_loop():
    """Test breaker does not trip when calls vary."""
    breaker = CircuitBreaker(max_identical_retries=2, max_total_calls=10)
    # Different hashes should not trigger loop
    try:
        breaker.record("tool", ("arg1",), {}, None, 10.0)
        breaker.record("tool", ("arg2",), {}, None, 11.0)
    except AgentRetryLoopError:
        pytest.fail("Breaker tripped without loop")


def test_circuit_breaker_trips_on_identical():
    """Test breaker trips on max_identical_retries identical calls."""
    breaker = CircuitBreaker(max_identical_retries=2, max_total_calls=10)
    # Same args should trigger loop after threshold
    try:
        breaker.record("tool", ("same",), {}, None, 10.0)
        breaker.record("tool", ("same",), {}, None, 11.0)
        # Third identical call should trip
        breaker.record("tool", ("same",), {}, None, 12.0)
        pytest.fail("Breaker should have tripped on 3rd identical call")
    except AgentRetryLoopError:
        pass  # Expected


def test_circuit_breaker_max_total_calls():
    """Test breaker trips on max_total_calls."""
    breaker = CircuitBreaker(max_identical_retries=10, max_total_calls=3)
    try:
        breaker.record("tool", ("a",), {}, None, 10.0)
        breaker.record("tool", ("b",), {}, None, 11.0)
        breaker.record("tool", ("c",), {}, None, 12.0)
        pytest.fail("Breaker should have tripped at max_total_calls")
    except AgentRetryLoopError:
        pass  # Expected


def test_normalize_hash():
    """Test hash normalization is deterministic."""
    from toolrot.breaker import _hash_args

    hash1 = _hash_args(("arg1",), {"k": "v"})
    hash2 = _hash_args(("arg1",), {"k": "v"})
    hash3 = _hash_args(("arg2",), {"k": "v"})

    assert hash1 == hash2
    assert hash1 != hash3
    assert hash1 == hash2
    assert hash1 != hash3
