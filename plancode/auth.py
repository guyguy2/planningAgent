"""Authentication and API key management for PlanCode.

This module provides flexible authentication supporting multiple sources:
1. ANTHROPIC_API_KEY environment variable
2. ANTHROPIC_API_KEY_FILE environment variable (path to file containing key)
3. Claude Code environment detection
4. Interactive prompt (optional)
5. .plancode/api_key file (optional, with security warning)
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.prompt import Prompt

console = Console()


def is_running_in_claude_code() -> bool:
    """
    Detect if we're running inside a Claude Code environment.

    Claude Code sets specific environment variables and has certain
    characteristics we can detect.

    Returns:
        True if running in Claude Code, False otherwise
    """
    # Check for actual Claude Code environment variables
    # CLAUDECODE=1 is set in Claude Code sessions
    # CLAUDE_CODE_ENTRYPOINT indicates the entry point (e.g., 'cli')
    if os.getenv("CLAUDECODE") == "1":
        return True

    if os.getenv("CLAUDE_CODE_ENTRYPOINT"):
        return True

    # Fallback: Check for parent process name containing 'claude'
    # This is a heuristic and may need adjustment
    try:
        import psutil

        parent = psutil.Process().parent()
        if parent and "claude" in parent.name().lower():
            return True
    except (ImportError, Exception):
        pass

    return False


def read_api_key_from_file(file_path: Path) -> Optional[str]:
    """
    Read API key from a file.

    Args:
        file_path: Path to file containing the API key

    Returns:
        API key string if found and valid, None otherwise
    """
    try:
        if not file_path.exists():
            return None

        key = file_path.read_text().strip()
        if key and len(key) > 10:  # Basic validation
            return key
        return None
    except Exception as e:
        console.print(f"[yellow]Warning: Could not read API key from {file_path}: {e}[/yellow]")
        return None


def prompt_for_api_key(allow_interactive: bool = False) -> Optional[str]:
    """
    Interactively prompt user for API key.

    Args:
        allow_interactive: Whether to allow interactive prompts

    Returns:
        API key if provided, None otherwise
    """
    if not allow_interactive:
        return None

    if not sys.stdin.isatty():
        return None

    console.print("\n[yellow]No API key found. You can:[/yellow]")
    console.print("  1. Set ANTHROPIC_API_KEY environment variable")
    console.print("  2. Set ANTHROPIC_API_KEY_FILE pointing to a file with your key")
    console.print("  3. Enter your API key now (not recommended - use env vars instead)\n")

    key = Prompt.ask("Enter your Anthropic API key (or press Enter to cancel)", password=True)

    if key and len(key) > 10:
        return key
    return None


def get_api_key(
    allow_interactive: bool = False,
    require_key: bool = True,
    project_path: Optional[Path] = None,
) -> Tuple[Optional[str], str]:
    """
    Get API key from various sources with fallback logic.

    Authentication sources (in order of priority):
    1. ANTHROPIC_API_KEY environment variable (most secure)
    2. ANTHROPIC_API_KEY_FILE environment variable
    3. Claude Code environment detection (no key needed)
    4. .plancode/api_key file in project directory (if exists)
    5. Interactive prompt (if allowed)

    Args:
        allow_interactive: Whether to allow interactive prompts
        require_key: Whether to require an API key (False for Claude Code mode)
        project_path: Optional project path to check for .plancode/api_key

    Returns:
        Tuple of (api_key, source_description)
        api_key will be None if running in Claude Code mode

    Raises:
        SystemExit: If require_key=True and no key could be obtained
    """
    # 1. Check ANTHROPIC_API_KEY environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        return api_key, "ANTHROPIC_API_KEY environment variable"

    # 2. Check ANTHROPIC_API_KEY_FILE environment variable
    key_file_env = os.getenv("ANTHROPIC_API_KEY_FILE")
    if key_file_env:
        key_file_path = Path(key_file_env).expanduser()
        api_key = read_api_key_from_file(key_file_path)
        if api_key:
            return api_key, f"ANTHROPIC_API_KEY_FILE ({key_file_path})"

    # 3. Check if running in Claude Code environment
    if is_running_in_claude_code():
        console.print("[cyan]Detected Claude Code environment - using existing session[/cyan]")
        return None, "Claude Code environment"

    # 4. Check for .plancode/api_key file in project directory
    if project_path:
        project_key_file = project_path / ".plancode" / "api_key"
        if project_key_file.exists():
            console.print(
                "[yellow]Warning: Using API key from .plancode/api_key file. "
                "This is less secure than using environment variables.[/yellow]"
            )
            api_key = read_api_key_from_file(project_key_file)
            if api_key:
                return api_key, ".plancode/api_key file"

    # 5. Try interactive prompt if allowed
    if allow_interactive:
        api_key = prompt_for_api_key(allow_interactive=True)
        if api_key:
            return api_key, "interactive prompt"

    # No key found
    if require_key:
        _display_setup_instructions()
        console.print("[red]Error: No API key found. Cannot proceed.[/red]")
        raise SystemExit(1)

    return None, "no key required"


def _display_setup_instructions():
    """Display helpful instructions for setting up authentication."""
    console.print("\n[bold red]Authentication Required[/bold red]\n")
    console.print("PlanCode needs an Anthropic API key to function. Here's how to set it up:\n")

    console.print("[bold cyan]Option 1: Environment Variable (Recommended)[/bold cyan]")
    console.print("  export ANTHROPIC_API_KEY='your-api-key-here'")
    console.print("  # Add to ~/.bashrc or ~/.zshrc to persist\n")

    console.print("[bold cyan]Option 2: API Key File[/bold cyan]")
    console.print("  echo 'your-api-key-here' > ~/.anthropic_key")
    console.print("  chmod 600 ~/.anthropic_key  # Secure the file")
    console.print("  export ANTHROPIC_API_KEY_FILE=~/.anthropic_key\n")

    console.print("[bold cyan]Option 3: Use within Claude Code[/bold cyan]")
    console.print("  Run PlanCode from within a Claude Code session")
    console.print("  (no separate API key needed)\n")

    console.print("[bold]Get your API key:[/bold]")
    console.print("  Visit: https://console.anthropic.com/settings/keys\n")


def validate_api_key(api_key: str) -> bool:
    """
    Validate that an API key has the correct format.

    Args:
        api_key: The API key to validate

    Returns:
        True if the key appears valid, False otherwise
    """
    if not api_key:
        return False

    # Basic validation: Anthropic API keys typically start with 'sk-ant-'
    # and are reasonably long
    if not api_key.startswith("sk-ant-"):
        console.print(
            "[yellow]Warning: API key doesn't start with 'sk-ant-'. "
            "This may not be a valid Anthropic API key.[/yellow]"
        )
        return False

    if len(api_key) < 40:
        console.print("[yellow]Warning: API key seems too short to be valid.[/yellow]")
        return False

    return True


def setup_api_key_interactive(project_path: Optional[Path] = None):
    """
    Interactive setup wizard for API key configuration.

    Args:
        project_path: Optional project path for project-specific setup
    """
    console.print("\n[bold cyan]PlanCode API Key Setup[/bold cyan]\n")

    # Check if key already exists
    existing_key, source = get_api_key(require_key=False, project_path=project_path)
    if existing_key:
        console.print(f"[green]✓ API key already configured ({source})[/green]")
        return

    console.print("No API key found. Let's set one up!\n")
    console.print("Where would you like to store your API key?\n")
    console.print("  [bold]1.[/bold] Environment variable (Recommended)")
    console.print("  [bold]2.[/bold] File in home directory")
    console.print("  [bold]3.[/bold] Project-specific file (less secure)")
    console.print("  [bold]4.[/bold] Enter manually now (not saved)\n")

    choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"], default="1")

    api_key = Prompt.ask("\nEnter your Anthropic API key", password=True)

    if not validate_api_key(api_key):
        console.print("[red]Invalid API key format. Setup cancelled.[/red]")
        return

    if choice == "1":
        console.print("\n[yellow]Add this to your shell configuration file:[/yellow]")
        console.print(f"  export ANTHROPIC_API_KEY='{api_key}'")
        console.print("\n[yellow]For bash, add to ~/.bashrc or ~/.bash_profile[/yellow]")
        console.print("[yellow]For zsh, add to ~/.zshrc[/yellow]")

    elif choice == "2":
        key_file = Path.home() / ".anthropic_key"
        key_file.write_text(api_key)
        key_file.chmod(0o600)
        console.print(f"\n[green]✓ API key saved to {key_file}[/green]")
        console.print("\n[yellow]Add this to your shell configuration file:[/yellow]")
        console.print(f"  export ANTHROPIC_API_KEY_FILE='{key_file}'")

    elif choice == "3":
        if not project_path:
            console.print("[red]Error: No project path specified[/red]")
            return

        plancode_dir = project_path / ".plancode"
        plancode_dir.mkdir(exist_ok=True)
        key_file = plancode_dir / "api_key"
        key_file.write_text(api_key)
        key_file.chmod(0o600)

        # Update .gitignore
        gitignore = project_path / ".gitignore"
        gitignore_entry = ".plancode/api_key\n"
        if gitignore.exists():
            content = gitignore.read_text()
            if "api_key" not in content:
                with gitignore.open("a") as f:
                    f.write(f"\n{gitignore_entry}")

        console.print(f"\n[green]✓ API key saved to {key_file}[/green]")
        console.print(
            "[yellow]Warning: This is project-specific and less secure than env vars[/yellow]"
        )

    elif choice == "4":
        console.print("\n[yellow]API key entered but not saved.[/yellow]")
        console.print("[yellow]You'll need to enter it again next time.[/yellow]")

    console.print("\n[green]Setup complete![/green]")
