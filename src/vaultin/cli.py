from __future__ import annotations

from pathlib import Path

import typer

from vaultin.paths import VaultinPaths
from vaultin.runtime.break_glass import BreakGlassManager
from vaultin.runtime.health import HealthChecker
from vaultin.runtime.queue import SyncQueue


app = typer.Typer(no_args_is_help=True, add_completion=False)


def _print_health(root: Path) -> bool:
    report = HealthChecker(root).run()
    typer.echo(report.status)
    for item in report.checks:
        typer.echo(f"{item.name}: {item.status} - {item.detail}")
    return report.status == "PASS"


@app.command()
def health(root: Path = typer.Option(Path.cwd(), "--root")) -> None:
    """Validate whether Vaultin can safely govern a session."""
    if not _print_health(root):
        raise typer.Exit(code=1)


@app.command()
def doctor(root: Path = typer.Option(Path.cwd(), "--root")) -> None:
    """Print diagnostics without silently mutating governance state."""
    typer.echo(f"runtime_source: {Path(__file__).resolve()}")
    typer.echo(f"configured_root: {Path(root).resolve()}")
    if not _print_health(root):
        typer.echo("Repair the blocked checks before governed execution.")
        raise typer.Exit(code=1)


@app.command()
def status(root: Path = typer.Option(Path.cwd(), "--root")) -> None:
    """Show governance health and pending synchronization count."""
    healthy = _print_health(root)
    paths = VaultinPaths.from_root(root)
    pending = len(SyncQueue(paths.queue_jsonl).pending())
    typer.echo(f"pending_sync: {pending}")
    if not healthy:
        raise typer.Exit(code=1)


@app.command("break-glass")
def break_glass(
    reason: str = typer.Option(..., "--reason"),
    ttl_minutes: int = typer.Option(15, "--ttl-minutes", min=1),
    root: Path = typer.Option(Path.cwd(), "--root"),
) -> None:
    """Manually activate an audited, expiring break-glass token."""
    token = BreakGlassManager(root).activate(reason=reason, ttl_minutes=ttl_minutes)
    typer.echo(f"BREAK_GLASS active id={token.id} expires_at={token.expires_at.isoformat()}")


@app.command()
def session() -> None:
    typer.echo("Use the client adapter to create and inspect governed sessions.")


@app.command()
def route() -> None:
    typer.echo("Use the orchestrator/JEV routing interface for task routing.")


@app.command()
def vaults() -> None:
    typer.echo("Use vaults/registry.yaml as the canonical project-vault registry.")


@app.command()
def sync() -> None:
    typer.echo("Use the configured VaultSync runtime to reconcile pending repositories.")


if __name__ == "__main__":
    app()
