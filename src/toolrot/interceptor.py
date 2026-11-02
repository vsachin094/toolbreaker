"""Sync, async & MCP dispatcher wrapper with fault injection."""

import inspect
import random
from functools import wraps
from typing import Any, Callable, Literal

from .breaker import CircuitBreaker
from .faults import Fault


class RotHarness:
    def __init__(
        self,
        faults: list[Fault],
        mode: Literal["sequence", "random"] = "sequence",
        seed: int | None = None,
        max_identical_retries: int = 3,
        max_total_calls: int = 15,
    ) -> None:
        self.faults = faults
        self.mode = mode
        self._rng = random.Random(seed)
        self.breaker = CircuitBreaker(
            max_identical_retries=max_identical_retries,
            max_total_calls=max_total_calls,
        )
        self.stats = {
            "total_calls": 0,
            "faults_injected": 0,
            "loops_caught": 0,
        }

    def wrap(self, fn: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(fn)

        if is_async:

            @wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                fault = self._select_fault()
                start = self._now()

                try:
                    result = await fn(*args, **kwargs)
                except Exception:
                    self.breaker.record(
                        fn.__name__, args, kwargs, None, self._elapsed(start)
                    )
                    raise

                if fault is not None:
                    result = fault.apply(result, args, kwargs)
                    self.stats["faults_injected"] += 1

                self.breaker.record(
                    fn.__name__, args, kwargs, fault.name, self._elapsed(start)
                )
                self.stats["total_calls"] += 1
                return result

            return async_wrapper

        @wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            fault = self._select_fault()
            start = self._now()

            try:
                result = fn(*args, **kwargs)
            except Exception:
                self.breaker.record(
                    fn.__name__, args, kwargs, None, self._elapsed(start)
                )
                raise

            if fault is not None:
                result = fault.apply(result, args, kwargs)
                self.stats["faults_injected"] += 1

            self.breaker.record(
                fn.__name__, args, kwargs, fault.name, self._elapsed(start)
            )
            self.stats["total_calls"] += 1
            return result

        return sync_wrapper

    def wrap_mcp(self, dispatcher: Callable[..., Any]) -> Callable[..., Any]:
        if isinstance(dispatcher, dict):
            return {name: self.wrap(fn) for name, fn in dispatcher.items()}

        return self.wrap(dispatcher)

    def _select_fault(self) -> Fault | None:
        if not self.faults:
            return None
        if self.mode == "random":
            return self._rng.choice(self.faults)
        return self.faults[self._rng.randint(0, len(self.faults) - 1)]

    @staticmethod
    def _now() -> float:
        import time

        return time.perf_counter() * 1000

    @staticmethod
    def _elapsed(start: float) -> float:
        import time

        return (time.perf_counter() * 1000) - start
