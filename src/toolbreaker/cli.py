"""Typer + Rich terminal CLI for toolbreaker."""

import importlib

import typer
from rich.console import Console
from rich.table import Table

from .breaker import AgentRetryLoopError
from .faults import (
    truncate_json,
    rate_limit,
    payload_bomb,
    latency_spike,
    empty_lie,
    server_fault,
)
from .interceptor import RotHarness

app = typer.Typer()


@app.command()
def demo() -> None:
    """Run instant simulation: Naive Retry Agent vs Resilient Agent."""

    def naive_agent(name: str) -> str:
        fault = truncate_json(ratio=0.5)
        result = name
        result = fault.apply(result, (), {})
        return result

    def resilient_agent(name: str) -> str:
        import json

        result = name
        try:
            parsed = json.loads(result)
            return str(parsed) if parsed else "empty result"
        except (json.JSONDecodeError, TypeError):
            return "handled: malformed JSON"

    faults = [
        truncate_json(ratio=0.5),
        rate_limit(retry_after=30, as_exception=False),
        payload_bomb(size_kb=64),
        latency_spike(seconds=0.5),
        empty_lie(),
        server_fault(code=502),
    ]

    harness = RotHarness(
        faults=faults,
        mode="random",
        seed=42,
        max_identical_retries=3,
        max_total_calls=15,
    )

    wrapped_naive = harness.wrap(naive_agent)
    wrapped_resilient = harness.wrap(resilient_agent)

    agents = [
        ("Naive Retry Agent", wrapped_naive),
        ("Resilient Agent", wrapped_resilient),
    ]

    rows = []
    for name, wrapped_fn in agents:
        calls_made = 0
        loop_caught = False
        fault_injected = "none"

        try:
            for _ in range(5):
                wrapped_fn(name)
                calls_made += 1
        except AgentRetryLoopError as e:
            loop_caught = True
            calls_made = len(e.records)
            fault_injected = e.records[0].fault_injected if e.records else "none"

        verdict = "LOOP CAUGHT" if loop_caught else "PASS"
        rows.append(
            (
                name,
                fault_injected,
                calls_made,
                "Caught" if loop_caught else "OK",
                verdict,
            )
        )

    table = Table(title="toolbreaker Demo: Agent Fault Tolerance")
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Injected Fault", style="magenta")
    table.add_column("Calls Made", style="green")
    table.add_column("Loop Status", style="yellow")
    table.add_column("Verdict", style="red")

    for row in rows:
        table.add_row(*[str(c) for c in row])

    Console().print(table)


@app.command()
def run(target: str) -> None:
    """Import target function and run all built-in faults against it."""

    try:
        module_name, func_name = target.split(":")
    except ValueError:
        typer.echo("Usage: toolbreaker run <module:function>", err=True)
        raise typer.Exit(code=1)

    mod = importlib.import_module(module_name)
    fn = getattr(mod, func_name, None)

    if fn is None:
        typer.echo(f"Function {func_name} not found in module {module_name}", err=True)
        raise typer.Exit(code=1)

    faults = [
        truncate_json(ratio=0.5),
        rate_limit(retry_after=30, as_exception=False),
        payload_bomb(size_kb=64),
        latency_spike(seconds=1.0),
        empty_lie(),
        server_fault(code=502),
    ]

    console = Console()
    console.print(f"[bold]Running faults against:[/bold] {target}")

    for fault in faults:
        try:
            result = fault.apply(fn(), (), {})
            preview = str(result)[:200] if result else "<None>"
            console.print(f"[green]{fault.name}[/green]: OK -> {preview}")
        except Exception as e:
            console.print(f"[red]{fault.name}[/red]: ERROR -> {e}")


if __name__ == "__main__":
    app()
