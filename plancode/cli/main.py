"""Main CLI entry point for PlanCode."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from plancode.auth import get_api_key, setup_api_key_interactive

app = typer.Typer(
    name="plancode",
    help="AI-Powered Code Planning & Implementation Tool",
    add_completion=False,
)
console = Console()


@app.command()
def plan(
    task: str = typer.Argument(..., help="Description of the task to implement"),
    project: Optional[Path] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project directory path (defaults to current directory)",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    resume: Optional[Path] = typer.Option(
        None,
        "--resume",
        "-r",
        help="Resume from a saved plan file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    analyze_only: bool = typer.Option(
        False,
        "--analyze-only",
        help="Only analyze the codebase and create a plan, don't execute",
    ),
    model: str = typer.Option(
        "claude-sonnet-4-5-20250929",
        "--model",
        "-m",
        help="Claude model to use",
    ),
    save_plan: Optional[Path] = typer.Option(
        None,
        "--save-plan",
        "-s",
        help="Save the plan to a file (JSON format)",
    ),
):
    """
    Create and optionally execute an implementation plan for a coding task.

    Examples:
        plancode "Add health check endpoint" --project ./my-app
        plancode "Refactor user service" --analyze-only
        plancode --resume last-plan.json
    """
    # Set project directory
    project_path = project if project else Path.cwd()

    # Get API key with flexible authentication
    # This will try multiple sources and provide helpful error messages
    api_key, source = get_api_key(
        allow_interactive=False,
        require_key=True,
        project_path=project_path,
    )

    if api_key:
        console.print(f"[dim]Using API key from: {source}[/dim]")

    # Display banner
    console.print(
        Panel.fit(
            "[bold cyan]PlanCode[/bold cyan]\n" "AI-Powered Code Planning & Implementation",
            border_style="cyan",
        )
    )

    if resume:
        console.print(f"\n[yellow]Resuming from plan: {resume}[/yellow]")
        from plancode.agent.loop import resume_plan

        resume_plan(resume, project_path, model, api_key=api_key)
    else:
        console.print(f"\n[bold]Task:[/bold] {task}")
        console.print(f"[bold]Project:[/bold] {project_path}")
        console.print(f"[bold]Model:[/bold] {model}")
        console.print(
            f"[bold]Mode:[/bold] {'Analyze Only' if analyze_only else 'Plan & Execute'}\n"
        )

        from plancode.agent.loop import run_planning_agent

        run_planning_agent(
            task=task,
            project_path=project_path,
            model=model,
            analyze_only=analyze_only,
            save_plan_path=save_plan,
            api_key=api_key,
        )


@app.command()
def version():
    """Show version information."""
    console.print("[cyan]PlanCode[/cyan] version [bold]0.1.0[/bold]")


@app.command()
def init(
    path: Optional[Path] = typer.Argument(
        None,
        help="Directory to initialize (defaults to current directory)",
    )
):
    """Initialize a new project for PlanCode usage."""
    target_path = path if path else Path.cwd()
    plans_dir = target_path / ".plancode"

    if plans_dir.exists():
        console.print(f"[yellow]PlanCode directory already exists at {plans_dir}[/yellow]")
    else:
        plans_dir.mkdir(exist_ok=True)
        (plans_dir / "plans").mkdir(exist_ok=True)
        console.print(f"[green]Initialized PlanCode directory at {plans_dir}[/green]")

    # Create .gitignore if needed
    gitignore = target_path / ".gitignore"
    gitignore_entry = ".plancode/\n"
    if gitignore.exists():
        content = gitignore.read_text()
        if ".plancode/" not in content:
            with gitignore.open("a") as f:
                f.write(f"\n{gitignore_entry}")
            console.print("[green]Added .plancode/ to .gitignore[/green]")
    else:
        gitignore.write_text(gitignore_entry)
        console.print("[green]Created .gitignore with .plancode/[/green]")


@app.command()
def setup(
    path: Optional[Path] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project directory for project-specific setup",
    )
):
    """
    Interactive setup wizard for configuring API key authentication.

    This command helps you set up your Anthropic API key through various methods:
    - Environment variable (recommended)
    - File in home directory
    - Project-specific file (less secure)

    Example:
        plancode setup
        plancode setup --project ./my-app
    """
    project_path = path if path else Path.cwd()
    setup_api_key_interactive(project_path=project_path)


if __name__ == "__main__":
    app()
