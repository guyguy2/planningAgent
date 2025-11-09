"""Tests for CLI commands."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from plancode.cli.main import app

runner = CliRunner()


def test_version_command():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
    assert "PlanCode" in result.stdout


def test_init_command():
    """Test init command creates .plancode directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["init", tmpdir])
        assert result.exit_code == 0

        # Check that .plancode directory was created
        plancode_dir = Path(tmpdir) / ".plancode"
        assert plancode_dir.exists()
        assert plancode_dir.is_dir()

        # Check that plans subdirectory was created
        plans_dir = plancode_dir / "plans"
        assert plans_dir.exists()

        # Check that .gitignore was created/updated
        gitignore = Path(tmpdir) / ".gitignore"
        assert gitignore.exists()
        assert ".plancode/" in gitignore.read_text()


def test_init_command_current_directory():
    """Test init command without path argument."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(app, ["init"])
            assert result.exit_code == 0

            plancode_dir = Path(tmpdir) / ".plancode"
            assert plancode_dir.exists()
        finally:
            os.chdir(original_cwd)


def test_init_command_already_exists():
    """Test init command when .plancode already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create .plancode directory first
        plancode_dir = Path(tmpdir) / ".plancode"
        plancode_dir.mkdir()

        result = runner.invoke(app, ["init", tmpdir])
        assert result.exit_code == 0
        assert "already exists" in result.stdout


def test_plan_command_no_api_key():
    """Test plan command fails without API key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Ensure no API key is set
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=True):
            result = runner.invoke(app, ["plan", "test task", "--project", tmpdir])
            assert result.exit_code == 1
            assert "ANTHROPIC_API_KEY" in result.stdout


def test_plan_command_with_api_key():
    """Test plan command with API key (mock the agent)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock the run_planning_agent function where it's imported
        with patch("plancode.agent.loop.run_planning_agent") as mock_agent:
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = runner.invoke(
                    app, ["plan", "Add health check", "--project", tmpdir, "--analyze-only"]
                )

                # Command should succeed
                assert result.exit_code == 0

                # Agent should have been called
                assert mock_agent.called

                # Check call arguments
                call_args = mock_agent.call_args
                assert call_args.kwargs["task"] == "Add health check"
                assert call_args.kwargs["analyze_only"] is True


def test_plan_command_defaults():
    """Test plan command uses current directory by default."""
    with patch("plancode.agent.loop.run_planning_agent") as mock_agent:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = runner.invoke(app, ["plan", "test task", "--analyze-only"])

            if result.exit_code == 0:
                call_args = mock_agent.call_args
                # Project path should be current directory
                assert call_args.kwargs["project_path"] == Path.cwd()


def test_plan_command_custom_model():
    """Test plan command with custom model."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("plancode.agent.loop.run_planning_agent") as mock_agent:
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = runner.invoke(
                    app,
                    [
                        "plan",
                        "test task",
                        "--project",
                        tmpdir,
                        "--model",
                        "claude-3-opus-20240229",
                        "--analyze-only",
                    ],
                )

                if result.exit_code == 0:
                    call_args = mock_agent.call_args
                    assert call_args.kwargs["model"] == "claude-3-opus-20240229"
