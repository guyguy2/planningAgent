"""Workflow tools for plan management and developer approval."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from plancode.models.plan import ApprovalResponse, ImplementationPlan

console = Console()


def ask_developer_for_approval(
    phase_name: str,
    plan_summary: str,
    files_to_modify: list[str],
    estimated_complexity: str,
) -> ApprovalResponse:
    """
    Pause execution and ask developer for approval.

    This is the critical human-in-the-loop tool that enforces the Plan-First methodology.

    Args:
        phase_name: Name of the phase being approved
        plan_summary: High-level summary of what will be done
        files_to_modify: List of file paths that will be changed
        estimated_complexity: low/medium/high complexity estimate

    Returns:
        ApprovalResponse with approval status and optional feedback
    """
    console.print("\n")
    console.print(
        Panel.fit(
            f"[bold cyan]{phase_name}[/bold cyan]\n"
            f"Complexity: [yellow]{estimated_complexity.upper()}[/yellow]",
            title="[bold]Approval Required[/bold]",
            border_style="yellow",
        )
    )

    console.print("\n[bold]Plan Summary:[/bold]")
    console.print(plan_summary)

    if files_to_modify:
        console.print("\n[bold]Files to Modify:[/bold]")
        table = Table(show_header=False, box=None)
        for file_path in files_to_modify:
            table.add_row(f"  • {file_path}")
        console.print(table)

    console.print("\n")
    approved = Confirm.ask("[bold cyan]Approve this plan?[/bold cyan]", default=True)

    feedback = None
    if not approved:
        feedback = Prompt.ask(
            "[yellow]Please provide feedback or modifications[/yellow]",
            default="",
        )

    return ApprovalResponse(approved=approved, feedback=feedback)


def save_plan(plan: ImplementationPlan, filename: Path, format: str = "json") -> dict:
    """
    Save an implementation plan to disk.

    Args:
        plan: The ImplementationPlan to save
        filename: Path to save the plan
        format: "json" or "yaml"

    Returns:
        Dict with success status and path
    """
    try:
        # Ensure parent directory exists
        filename.parent.mkdir(parents=True, exist_ok=True)

        plan_dict = plan.model_dump(mode="json")

        if format == "yaml":
            with open(filename, "w") as f:
                yaml.dump(plan_dict, f, default_flow_style=False, sort_keys=False)
        else:
            with open(filename, "w") as f:
                json.dump(plan_dict, f, indent=2, default=str)

        return {
            "success": True,
            "path": str(filename),
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "path": None,
            "error": str(e),
        }


def load_plan(filename: Path) -> Optional[ImplementationPlan]:
    """
    Load an implementation plan from disk.

    Args:
        filename: Path to the plan file

    Returns:
        ImplementationPlan object or None if loading fails
    """
    try:
        suffix = filename.suffix.lower()

        if suffix in [".yaml", ".yml"]:
            with open(filename, "r") as f:
                plan_dict = yaml.safe_load(f)
        else:
            with open(filename, "r") as f:
                plan_dict = json.load(f)

        # Convert string datetimes back to datetime objects
        for key in ["created_at", "updated_at", "approved_at"]:
            if key in plan_dict and plan_dict[key]:
                if isinstance(plan_dict[key], str):
                    plan_dict[key] = datetime.fromisoformat(plan_dict[key])

        for phase in plan_dict.get("phases", []):
            for key in ["started_at", "completed_at"]:
                if key in phase and phase[key]:
                    if isinstance(phase[key], str):
                        phase[key] = datetime.fromisoformat(phase[key])

        return ImplementationPlan(**plan_dict)
    except Exception as e:
        console.print(f"[red]Error loading plan: {e}[/red]")
        return None


def update_plan_step(plan: ImplementationPlan, step_id: str, changes: dict) -> dict:
    """
    Update a specific phase in the plan.

    Args:
        plan: The ImplementationPlan to update
        step_id: ID of the phase to update
        changes: Dict of changes to apply to the phase

    Returns:
        Dict with success status
    """
    try:
        phase = plan.get_phase(step_id)
        if not phase:
            return {
                "success": False,
                "error": f"Phase {step_id} not found",
            }

        # Apply changes
        for key, value in changes.items():
            if hasattr(phase, key):
                setattr(phase, key, value)

        plan.updated_at = datetime.now()

        return {
            "success": True,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def auto_save_plan(plan: ImplementationPlan, project_path: Path) -> Path:
    """
    Automatically save a plan to the .plancode directory.

    Args:
        plan: The plan to save
        project_path: Root path of the project

    Returns:
        Path to the saved plan file
    """
    plancode_dir = project_path / ".plancode" / "plans"
    plancode_dir.mkdir(parents=True, exist_ok=True)

    # Create filename from plan ID and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = plancode_dir / f"plan_{plan.id}_{timestamp}.json"

    save_plan(plan, filename)
    return filename
