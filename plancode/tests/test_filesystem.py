"""Tests for filesystem tools."""

import tempfile
from pathlib import Path

import pytest

from plancode.tools.filesystem import (
    get_gitignore_spec,
    list_project_structure,
    should_ignore,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create some test files and directories
        (project_path / "src").mkdir()
        (project_path / "src" / "main.py").write_text("print('hello')")
        (project_path / "src" / "utils.py").write_text("def util(): pass")

        (project_path / "tests").mkdir()
        (project_path / "tests" / "test_main.py").write_text("def test(): pass")

        (project_path / "README.md").write_text("# Test Project")
        (project_path / "requirements.txt").write_text("pytest>=7.0.0")

        # Create node_modules to test ignore
        (project_path / "node_modules").mkdir()
        (project_path / "node_modules" / "package.json").write_text("{}")

        yield project_path


@pytest.fixture
def project_with_gitignore():
    """Create a temporary project with .gitignore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .gitignore
        gitignore_content = """
*.pyc
__pycache__/
.env
dist/
"""
        (project_path / ".gitignore").write_text(gitignore_content)

        # Create some files
        (project_path / "main.py").write_text("print('hello')")
        (project_path / "main.pyc").write_text("compiled")
        (project_path / ".env").write_text("SECRET=123")

        yield project_path


def test_get_gitignore_spec(project_with_gitignore):
    """Test loading .gitignore patterns."""
    spec = get_gitignore_spec(project_with_gitignore)
    assert spec is not None

    # Test that patterns work
    assert spec.match_file("main.pyc")
    assert spec.match_file(".env")
    assert not spec.match_file("main.py")


def test_get_gitignore_spec_no_file(temp_project):
    """Test when no .gitignore exists."""
    spec = get_gitignore_spec(temp_project)
    assert spec is None


def test_should_ignore_common_patterns(temp_project):
    """Test common ignore patterns."""
    gitignore_spec = get_gitignore_spec(temp_project)

    # Should ignore node_modules
    node_path = temp_project / "node_modules" / "package.json"
    assert should_ignore(node_path, temp_project, gitignore_spec)

    # Should not ignore source files
    src_path = temp_project / "src" / "main.py"
    assert not should_ignore(src_path, temp_project, gitignore_spec)


def test_should_ignore_with_gitignore(project_with_gitignore):
    """Test should_ignore with .gitignore patterns."""
    gitignore_spec = get_gitignore_spec(project_with_gitignore)

    # Should ignore .pyc files
    pyc_path = project_with_gitignore / "main.pyc"
    assert should_ignore(pyc_path, project_with_gitignore, gitignore_spec)

    # Should ignore .env files
    env_path = project_with_gitignore / ".env"
    assert should_ignore(env_path, project_with_gitignore, gitignore_spec)

    # Should not ignore .py files
    py_path = project_with_gitignore / "main.py"
    assert not should_ignore(py_path, project_with_gitignore, gitignore_spec)


def test_list_project_structure(temp_project):
    """Test listing project structure."""
    result = list_project_structure(temp_project, max_depth=3)

    # Check result has expected keys
    assert "tree" in result
    assert "file_count" in result
    assert "directory_count" in result
    assert "languages" in result

    # Check file count (should not include node_modules)
    assert result["file_count"] > 0

    # Check that Python files are detected
    assert "Python" in result["languages"]

    # Check tree contains some expected files
    tree = result["tree"]
    assert "src/" in tree
    assert "README.md" in tree


def test_list_project_structure_depth_limit(temp_project):
    """Test that max_depth is respected."""
    # Create a deep directory structure
    deep_dir = temp_project / "a" / "b" / "c" / "d"
    deep_dir.mkdir(parents=True)
    (deep_dir / "deep.txt").write_text("deep file")

    # List with shallow depth
    result_shallow = list_project_structure(temp_project, max_depth=1)
    assert "deep.txt" not in result_shallow["tree"]

    # List with deeper depth
    result_deep = list_project_structure(temp_project, max_depth=5)
    assert "deep.txt" in result_deep["tree"]


def test_list_project_structure_ignores_common_dirs(temp_project):
    """Test that common directories don't have their contents listed."""
    # Create directories with nested content
    pycache_dir = temp_project / "src" / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "test.pyc").write_text("compiled")
    (pycache_dir / "nested.pyc").write_text("compiled")

    node_dir = temp_project / "node_modules" / "package"
    node_dir.mkdir(parents=True)
    (node_dir / "index.js").write_text("code")

    result = list_project_structure(temp_project, max_depth=5)
    tree = result["tree"]

    # Files inside ignored directories should not appear
    # (directories themselves may appear but not their contents)
    assert "test.pyc" not in tree
    assert "nested.pyc" not in tree
    assert "index.js" not in tree
