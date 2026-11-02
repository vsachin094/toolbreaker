"""Pytest plugin for toolrot chaos engineering."""

from __future__ import annotations

import pytest

from .interceptor import RotHarness


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --toolbreaker-seed CLI option."""
    parser.addoption(
        "--toolbreaker-seed",
        action="store",
        default=None,
        help="Seed for deterministic chaos engineering runs.",
    )


@pytest.fixture
def toolrot(request: pytest.FixtureRequest) -> "RotHarness":
    """Return a configured RotHarness seeded from --toolbreaker-seed (default 42)."""
    seed = request.config.getoption("--toolbreaker-seed")
    if seed is None:
        seed = 42
    from .faults import (
        truncate_json,
        rate_limit,
        payload_bomb,
        latency_spike,
        empty_lie,
        server_fault,
    )

    faults = [
        truncate_json(ratio=0.3),
        rate_limit(retry_after=30, as_exception=False),
        payload_bomb(size_kb=64),
        latency_spike(seconds=0.1),
        empty_lie(),
        server_fault(code=502),
    ]
    harness = RotHarness(
        faults=faults,
        mode="sequence",
        seed=int(seed),
        max_identical_retries=3,
        max_total_calls=15,
    )
    return harness
