"""Deterministic fault mutators for chaos engineering."""

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True, frozen=True)
class Fault:
    name: str
    apply: Callable[[Any, tuple, dict], Any]


def truncate_json(ratio: float = 0.5) -> Fault:
    """Serialize output to JSON and slice at ratio."""

    def apply(result: Any, args: tuple, kwargs: dict) -> Any:
        if isinstance(result, str):
            payload = result
        else:
            payload = json.dumps(result)

        sliced = int(len(payload) * ratio)
        return payload[:sliced]

    return Fault(name="truncate_json", apply=apply)


def rate_limit(retry_after: int = 30, as_exception: bool = False) -> Fault:
    """Return a realistic MCP/HTTP 429 error dict or raise RuntimeError."""

    def apply(result: Any, args: tuple, kwargs: dict) -> Any:
        error = {
            "isError": True,
            "error": {
                "code": 429,
                "message": "Too Many Requests",
                "retry_after": retry_after,
            },
        }
        if as_exception:
            raise RuntimeError("429 Too Many Requests")
        return error

    return Fault(name="rate_limit", apply=apply)


def payload_bomb(size_kb: int = 128) -> Fault:
    """Generate a repetitive stack trace and memory dump string."""

    line = "Traceback (most recent call last):\n"
    dump = "Memory dump: 0x" + "ab" * 40 + "\n"
    block = line + dump

    total = size_kb * 1024
    bomb = (block * (total // len(block) + 1))[:total]

    def apply(result: Any, args: tuple, kwargs: dict) -> Any:
        return bomb

    return Fault(name="payload_bomb", apply=apply)


def latency_spike(seconds: float = 2.0) -> Fault:
    """Inject blocking delay before returning output."""

    def apply(result: Any, args: tuple, kwargs: dict) -> Any:
        import time

        time.sleep(seconds)
        return result

    return Fault(name="latency_spike", apply=apply)


def empty_lie() -> Fault:
    """Return {'status': 'success', 'data': None} to test hallucination handling."""

    def apply(result: Any, args: tuple, kwargs: dict) -> Any:
        return {"status": "success", "data": None}

    return Fault(name="empty_lie", apply=apply)


def server_fault(code: int = 502) -> Fault:
    """Return {'isError': True, 'error': {'code': code}}."""

    def apply(result: Any, args: tuple, kwargs: dict) -> Any:
        return {
            "isError": True,
            "error": {
                "code": code,
                "message": "Bad Gateway: upstream tool process crashed",
            },
        }

    return Fault(name="server_fault", apply=apply)
