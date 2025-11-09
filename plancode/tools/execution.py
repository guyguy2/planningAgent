"""Execution tools for running commands and tests."""

import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def run_command(cmd: str, cwd: Path, timeout: int = 300) -> dict:
    """
    Execute a shell command and return the results.

    Args:
        cmd: Command to execute
        cwd: Working directory for command execution
        timeout: Command timeout in seconds

    Returns:
        Dict with stdout, stderr, exit_code, and error
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "success": False,
            "error": str(e),
        }


def run_tests(
    project_path: Path,
    test_path: Optional[str] = None,
    test_framework: Optional[str] = None,
) -> dict:
    """
    Run tests for the project.

    Auto-detects test framework if not specified.

    Args:
        project_path: Root path of the project
        test_path: Specific test file or directory to run
        test_framework: pytest, unittest, jest, etc.

    Returns:
        Dict with test results
    """
    # Auto-detect test framework if not specified
    if not test_framework:
        if (project_path / "pytest.ini").exists() or (project_path / "pyproject.toml").exists():
            test_framework = "pytest"
        elif (project_path / "package.json").exists():
            test_framework = "jest"
        elif (project_path / "pom.xml").exists():
            test_framework = "maven"
        elif (project_path / "build.gradle").exists():
            test_framework = "gradle"
        else:
            test_framework = "pytest"  # Default

    # Build command based on framework
    if test_framework == "pytest":
        cmd = f"pytest {test_path if test_path else 'tests'} -v"
    elif test_framework == "unittest":
        cmd = f"python -m unittest {test_path if test_path else 'discover'}"
    elif test_framework == "jest":
        cmd = f"npm test {test_path if test_path else ''}"
    elif test_framework == "maven":
        cmd = f"mvn test {f'-Dtest={test_path}' if test_path else ''}"
    elif test_framework == "gradle":
        cmd = f"./gradlew test {f'--tests {test_path}' if test_path else ''}"
    else:
        return {
            "success": False,
            "error": f"Unsupported test framework: {test_framework}",
        }

    console.print(f"[cyan]Running tests with {test_framework}...[/cyan]")
    result = run_command(cmd, project_path)

    # Parse test results
    passed = False
    if result["success"]:
        passed = True
    elif "passed" in result["stdout"].lower():
        # Try to extract pass/fail counts
        passed = "failed" not in result["stdout"].lower() or "0 failed" in result["stdout"].lower()

    return {
        **result,
        "framework": test_framework,
        "passed": passed,
    }


def verify_build(project_path: Path, build_command: Optional[str] = None) -> dict:
    """
    Verify that the project builds successfully.

    Auto-detects build system if not specified.

    Args:
        project_path: Root path of the project
        build_command: Custom build command

    Returns:
        Dict with build results
    """
    if build_command:
        cmd = build_command
    elif (project_path / "setup.py").exists() or (project_path / "pyproject.toml").exists():
        cmd = "python -m build"
    elif (project_path / "package.json").exists():
        cmd = "npm run build"
    elif (project_path / "pom.xml").exists():
        cmd = "mvn compile"
    elif (project_path / "build.gradle").exists():
        cmd = "./gradlew build"
    elif (project_path / "Makefile").exists():
        cmd = "make"
    else:
        return {
            "success": False,
            "error": "Could not detect build system",
        }

    console.print(f"[cyan]Running build: {cmd}[/cyan]")
    result = run_command(cmd, project_path)

    return result


def run_linter(project_path: Path, linter: Optional[str] = None) -> dict:
    """
    Run linter/formatter checks.

    Auto-detects linter if not specified.

    Args:
        project_path: Root path of the project
        linter: Specific linter to run (black, ruff, eslint, etc.)

    Returns:
        Dict with linter results
    """
    if not linter:
        if (project_path / "pyproject.toml").exists():
            linter = "ruff"
        elif (project_path / ".eslintrc").exists() or (project_path / ".eslintrc.js").exists():
            linter = "eslint"
        else:
            return {
                "success": True,
                "skipped": True,
                "message": "No linter configuration found",
            }

    if linter == "ruff":
        cmd = "ruff check ."
    elif linter == "black":
        cmd = "black --check ."
    elif linter == "eslint":
        cmd = "eslint ."
    elif linter == "mypy":
        cmd = "mypy ."
    else:
        return {
            "success": False,
            "error": f"Unsupported linter: {linter}",
        }

    console.print(f"[cyan]Running linter: {linter}[/cyan]")
    result = run_command(cmd, project_path)

    return {
        **result,
        "linter": linter,
    }
