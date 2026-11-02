"""Infinite retry loop detector and circuit breaker."""

import json
import hashlib
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CallRecord:
    tool_name: str
    args_hash: str
    fault_injected: str | None
    duration_ms: float


class AgentRetryLoopError(AssertionError):
    """Raised when an agent repeats the exact same failing call."""

    def __init__(self, records: list[CallRecord]) -> None:
        self.records = records
        lines = [
            f"Agent retry loop detected after {len(records)} calls.",
        ]
        for r in records:
            lines.append(
                f"  - {r.tool_name} (hash={r.args_hash}, fault={r.fault_injected}, "
                f"duration={r.duration_ms:.1f}ms)"
            )
        super().__init__("\n".join(lines))


def _hash_args(args: tuple, kwargs: dict) -> str:
    snapshot = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(snapshot.encode()).hexdigest()[:12]


class CircuitBreaker:
    def __init__(
        self,
        max_identical_retries: int = 3,
        max_total_calls: int = 15,
    ) -> None:
        self.max_identical_retries = max_identical_retries
        self.max_total_calls = max_total_calls
        self._calls: dict[str, list[CallRecord]] = {}
        self._total_calls = 0

    def record(
        self,
        tool_name: str,
        args: tuple,
        kwargs: dict,
        fault_injected: str | None,
        duration_ms: float,
    ) -> None:
        self._total_calls += 1
        args_hash = _hash_args(args, kwargs)

        if tool_name not in self._calls:
            self._calls[tool_name] = []

        records = self._calls[tool_name]
        records.append(
            CallRecord(
                tool_name=tool_name,
                args_hash=args_hash,
                fault_injected=fault_injected,
                duration_ms=duration_ms,
            )
        )

        consecutive = 0
        for r in reversed(records):
            if r.args_hash == args_hash:
                consecutive += 1
            else:
                break

        if consecutive >= self.max_identical_retries:
            raise AgentRetryLoopError(records)

        if self._total_calls >= self.max_total_calls:
            raise AgentRetryLoopError(records)

    def reset(self) -> None:
        self._calls = {}
        self._total_calls = 0
