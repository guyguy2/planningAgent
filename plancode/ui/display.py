"""Rich terminal UI for displaying plans and progress."""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from plancode.models.plan import ImplementationPlan, Phase, PhaseStatus

console = Console()


def display_project_structure(structure_data: dict):
    """Display project structure tree."""
    console.print("\n[bold cyan]Project Structure[/bold cyan]")
    console.print(f"[dim]{structure_data['tree']}[/dim]")

    # Summary table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Files:", f"[cyan]{structure_data['file_count']}[/cyan]")
    table.add_row("Directories:", f"[cyan]{structure_data['directory_count']}[/cyan]")

    if structure_data["languages"]:
        langs = ", ".join(
            f"{lang} ({count})"
            for lang, count in sorted(
                structure_data["languages"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]
        )
        table.add_row("Languages:", f"[cyan]{langs}[/cyan]")

    console.print(table)


def display_plan(plan: ImplementationPlan):
    """Display a complete implementation plan."""
    console.print("\n")
    console.print(
        Panel.fit(
            f"[bold]{plan.task_description}[/bold]\n\n"
            f"Complexity: [yellow]{plan.overall_complexity.value.upper()}[/yellow]\n"
            f"Phases: [cyan]{len(plan.phases)}[/cyan]\n"
            f"Created: [dim]{plan.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]",
            title="[bold cyan]Implementation Plan[/bold cyan]",
            border_style="cyan",
        )
    )

    # Display project context
    if plan.project_context.tech_stack:
        console.print("\n[bold]Tech Stack:[/bold]")
        console.print(f"  {', '.join(plan.project_context.tech_stack)}")

    # Display phases
    console.print("\n[bold]Phases:[/bold]\n")
    for i, phase in enumerate(plan.phases, 1):
        display_phase(phase, number=i)


def display_phase(phase: Phase, number: int = None):
    """Display a single phase."""
    # Status indicator
    status_colors = {
        PhaseStatus.PENDING: "white",
        PhaseStatus.IN_PROGRESS: "yellow",
        PhaseStatus.COMPLETED: "green",
        PhaseStatus.FAILED: "red",
        PhaseStatus.SKIPPED: "dim",
    }
    status_symbols = {
        PhaseStatus.PENDING: "○",
        PhaseStatus.IN_PROGRESS: "◐",
        PhaseStatus.COMPLETED: "●",
        PhaseStatus.FAILED: "✗",
        PhaseStatus.SKIPPED: "⊘",
    }

    color = status_colors[phase.status]
    symbol = status_symbols[phase.status]
    prefix = f"{number}. " if number else ""

    console.print(
        f"[{color}]{symbol}[/{color}] {prefix}[bold]{phase.name}[/bold] "
        f"[dim]({phase.complexity.value})[/dim]"
    )

    # Objective
    console.print(f"   [dim]{phase.objective}[/dim]")

    # File changes
    if phase.file_changes:
        console.print(f"   Files ({len(phase.file_changes)}):")
        for fc in phase.file_changes[:5]:  # Limit display
            action_color = {"create": "green", "modify": "yellow", "delete": "red"}.get(
                fc.action, "white"
            )
            console.print(f"     [{action_color}]{fc.action:8}[/{action_color}] {fc.path}")
        if len(phase.file_changes) > 5:
            console.print(f"     [dim]... and {len(phase.file_changes) - 5} more[/dim]")

    # Key changes
    if phase.key_changes:
        console.print(f"   Key Changes:")
        for change in phase.key_changes[:3]:
            console.print(f"     • {change}")
        if len(phase.key_changes) > 3:
            console.print(f"     [dim]... and {len(phase.key_changes) - 3} more[/dim]")

    console.print()


def display_phase_tree(plan: ImplementationPlan):
    """Display phases as a dependency tree."""
    tree = Tree("[bold cyan]Implementation Phases[/bold cyan]")

    # Build dependency map
    phase_nodes = {}
    for phase in plan.phases:
        status_symbols = {
            PhaseStatus.PENDING: "○",
            PhaseStatus.IN_PROGRESS: "◐",
            PhaseStatus.COMPLETED: "✓",
            PhaseStatus.FAILED: "✗",
            PhaseStatus.SKIPPED: "⊘",
        }
        symbol = status_symbols[phase.status]
        label = f"{symbol} {phase.name} [{phase.complexity.value}]"

        if not phase.dependencies:
            # Top-level phase
            phase_nodes[phase.id] = tree.add(label)
        else:
            # Find parent
            for dep_id in phase.dependencies:
                if dep_id in phase_nodes:
                    phase_nodes[phase.id] = phase_nodes[dep_id].add(label)
                    break
            else:
                # No parent found, add to root
                phase_nodes[phase.id] = tree.add(label)

    console.print(tree)


def display_progress(plan: ImplementationPlan):
    """Display overall progress."""
    total = len(plan.phases)
    completed = sum(1 for p in plan.phases if p.status == PhaseStatus.COMPLETED)
    in_progress = sum(1 for p in plan.phases if p.status == PhaseStatus.IN_PROGRESS)
    failed = sum(1 for p in plan.phases if p.status == PhaseStatus.FAILED)

    table = Table(title="Progress Summary", show_header=False, box=None)
    table.add_row("Total Phases:", f"[cyan]{total}[/cyan]")
    table.add_row("Completed:", f"[green]{completed}[/green]")
    if in_progress:
        table.add_row("In Progress:", f"[yellow]{in_progress}[/yellow]")
    if failed:
        table.add_row("Failed:", f"[red]{failed}[/red]")

    progress_pct = (completed / total * 100) if total > 0 else 0
    table.add_row("Progress:", f"[cyan]{progress_pct:.1f}%[/cyan]")

    console.print(table)


def display_code(code: str, language: str = "python", title: str = None):
    """Display code with syntax highlighting."""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title, border_style="cyan"))
    else:
        console.print(syntax)


def display_search_results(results: list[dict], max_display: int = 10):
    """Display code search results."""
    if not results:
        console.print("[yellow]No matches found[/yellow]")
        return

    console.print(f"\n[bold]Found {len(results)} matches:[/bold]\n")

    for i, result in enumerate(results[:max_display], 1):
        console.print(f"[cyan]{i}. {result['file']}:{result['line_number']}[/cyan]")
        console.print(f"   [dim]{result['line'].strip()}[/dim]\n")

    if len(results) > max_display:
        console.print(f"[dim]... and {len(results) - max_display} more matches[/dim]")


def display_error(message: str, details: str = None):
    """Display an error message."""
    panel_content = f"[bold red]{message}[/bold red]"
    if details:
        panel_content += f"\n\n[dim]{details}[/dim]"

    console.print(Panel(panel_content, border_style="red", title="Error"))


def display_success(message: str):
    """Display a success message."""
    console.print(f"[green]✓[/green] {message}")


def display_warning(message: str):
    """Display a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def display_info(message: str):
    """Display an info message."""
    console.print(f"[cyan]ℹ[/cyan] {message}")


def create_spinner(message: str):
    """Create a progress spinner for long operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
    )
