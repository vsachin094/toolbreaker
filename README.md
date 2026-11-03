# `toolbreaker`

[![PyPI version](https://img.shields.io/pypi/v/toolbreaker.svg)](https://pypi.org/project/toolbreaker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/vsachin094/toolbreaker/actions/workflows/ci.yml/badge.svg)](https://github.com/vsachin094/toolbreaker/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

## Why this exists

AI agents don't fail gracefully. When an upstream tool returns truncated JSON, a `429 Too Many Requests`, or a 502 Bad Gateway, the agent doesn't back off — it retries. And retries. And retries. Burning tokens, burning time, and burning your budget on infinite retry loops that never change their arguments.

We call this **"upstream degradation"**: the silent degradation of agent reliability when external tools fail in realistic ways. Unit tests with 200 OK responses don't catch it. Integration tests against a live MCP server don't catch it either, because they pass until they don't.

`toolbreaker` is a chaos-engineering harness and circuit breaker for AI agent tools. You wrap your tool functions (sync or async), inject realistic faults, and watch your agent fail — before it fails in production.

## What it does

- **Injects faults** — truncated JSON, HTTP 429s, latency spikes, stack-trace bombs, empty `{"data": null}` responses, and server errors
- **Detects retry loops** — trips `AgentRetryLoopError` when an agent calls the same failing tool with the same arguments too many times
- **Preserves signatures** — `inspect.signature(fn)` still works on wrapped functions, so LangChain, MCP, CrewAI, and OpenAI function-calling schemas keep working
- **Deterministic chaos** — a seeded `random.Random` makes CI runs reproducible

## Install

```bash
pip install toolbreaker
```

## Quickstart

```bash
toolbreaker demo
```

This runs a zero-config simulation comparing a naive retry agent against a resilient one:

```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Tool              ┃ Injected Fault ┃ Calls Made ┃ Loop Status ┃ Verdict     ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Naive Retry Agent │ server_fault   │ 3          │ Caught      │ LOOP CAUGHT │
│ Resilient Agent   │ server_fault   │ 3          │ Caught      │ LOOP CAUGHT │
└───────────────────┴────────────────┴────────────┴─────────────┴─────────────┘
```

## Pytest plugin

Add `--toolbreaker-seed` to any test run:

```bash
pytest --toolbreaker-seed=42
```

Use the `toolbreaker` fixture in your tests:

```python
def test_agent_handles_truncation(toolbreaker):
    harness = toolbreaker  # RotHarness, seeded from --toolbreaker-seed (default 42)
    wrapped_tool = harness.wrap(my_mcp_tool)
    result = wrapped_tool({"query": "users"})
    assert result is not None
```

If a test fails with `AgentRetryLoopError`, pytest appends a reproduction line:

```
Reproduce with: pytest --toolbreaker-seed=42
```

## MCP wrapper example

```python
from toolbreaker import RotHarness, truncate_json, rate_limit


def call_tool(name: str, arguments: dict):
    # your MCP dispatch logic
    ...


harness = RotHarness(
    faults=[truncate_json(ratio=0.5), rate_limit(retry_after=30)],
    seed=42,
)
wrapped = harness.wrap_mcp(call_tool)
```

`wrap_mcp` accepts a single `call_tool(name, arguments)` function or a dict of `{tool_name: callable}`.

## CLI: `toolbreaker run`

Inspect how your function's output mutates under every built-in fault:

```bash
toolbreaker run my_module:my_function
```

## API

```python
from toolbreaker import (
    RotHarness,
    CircuitBreaker,
    AgentRetryLoopError,
    truncate_json,
    rate_limit,
    payload_bomb,
    latency_spike,
    empty_lie,
    server_fault,
)
```

| Fault | What it simulates |
|-------|-------------------|
| `truncate_json(ratio=0.5)` | Mid-stream socket drop — output cut in half |
| `rate_limit(retry_after=30)` | MCP/HTTP 429 — return dict or raise |
| `payload_bomb(size_kb=128)` | Stack-trace + memory dump — context window overflow |
| `latency_spike(seconds=2.0)` | Upstream latency — blocking sleep before return |
| `empty_lie()` | `{"status": "success", "data": None}` — hallucination bait |
| `server_fault(code=502)` | Bad Gateway — upstream process crashed |

## CI

GitHub Actions runs `ruff check`, `ruff format --check`, and `pytest` on Python 3.11, 3.12, and 3.13. Publishing to PyPI happens automatically on GitHub Release via OIDC Trusted Publishing.

## License

MIT
