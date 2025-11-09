"""File system tools for codebase analysis and manipulation."""

import os
import re
import shutil
from pathlib import Path
from typing import Optional

import pathspec


def get_gitignore_spec(project_path: Path) -> Optional[pathspec.PathSpec]:
    """Load .gitignore patterns if available."""
    gitignore = project_path / ".gitignore"
    if gitignore.exists():
        with open(gitignore) as f:
            patterns = f.read().splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return None


def should_ignore(
    path: Path, project_root: Path, gitignore_spec: Optional[pathspec.PathSpec]
) -> bool:
    """Check if a path should be ignored based on common patterns."""
    relative_path = path.relative_to(project_root)
    path_str = str(relative_path)

    # Common ignore patterns
    ignore_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        ".egg-info",
    }
    ignore_patterns = {".pyc", ".pyo", ".so", ".dylib", ".dll", ".class"}

    # Check if the path itself is an ignored directory
    if path.is_dir() and path.name in ignore_dirs:
        return True

    # Check if any parent is in ignore_dirs
    for parent in relative_path.parents:
        if parent.name in ignore_dirs:
            return True

    # Check file extension
    if any(path_str.endswith(ext) for ext in ignore_patterns):
        return True

    # Check gitignore
    if gitignore_spec and gitignore_spec.match_file(path_str):
        return True

    return False


def list_project_structure(
    project_path: Path, max_depth: int = 3, include_file_count: bool = True
) -> dict:
    """
    Generate a tree view of the project structure.

    Returns a dict with structure information including:
    - tree: string representation
    - file_count: total files
    - directory_count: total directories
    - languages: detected programming languages
    """
    gitignore_spec = get_gitignore_spec(project_path)

    tree_lines = []
    file_count = 0
    dir_count = 0
    language_extensions = {}

    def add_tree_line(path: Path, prefix: str, depth: int):
        nonlocal file_count, dir_count

        if depth > max_depth:
            return

        if should_ignore(path, project_path, gitignore_spec):
            return

        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except PermissionError:
            return

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            next_prefix = "    " if is_last else "│   "

            if item.is_file():
                tree_lines.append(f"{prefix}{current_prefix}{item.name}")
                file_count += 1
                ext = item.suffix
                if ext:
                    language_extensions[ext] = language_extensions.get(ext, 0) + 1
            elif item.is_dir():
                tree_lines.append(f"{prefix}{current_prefix}{item.name}/")
                dir_count += 1
                add_tree_line(item, prefix + next_prefix, depth + 1)

    tree_lines.append(f"{project_path.name}/")
    add_tree_line(project_path, "", 1)

    # Determine primary languages
    ext_to_lang = {
        ".py": "Python",
        ".java": "Java",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React",
        ".tsx": "React/TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
        ".cpp": "C++",
        ".c": "C",
        ".kt": "Kotlin",
        ".swift": "Swift",
    }

    languages = {}
    for ext, count in language_extensions.items():
        lang = ext_to_lang.get(ext, f"Other ({ext})")
        languages[lang] = languages.get(lang, 0) + count

    return {
        "tree": "\n".join(tree_lines),
        "file_count": file_count,
        "directory_count": dir_count,
        "languages": languages,
        "max_depth": max_depth,
    }


def read_file(file_path: Path, max_lines: Optional[int] = None) -> dict:
    """
    Read a file and return its contents with metadata.

    Returns:
        - content: file contents
        - lines: number of lines
        - size: file size in bytes
        - extension: file extension
        - error: error message if read fails
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if max_lines:
                lines = []
                for _ in range(max_lines):
                    try:
                        lines.append(next(f))
                    except StopIteration:
                        break
                content = "".join(lines)
                truncated = len(lines) == max_lines
            else:
                content = f.read()
                truncated = False

        return {
            "content": content,
            "lines": len(content.splitlines()),
            "size": file_path.stat().st_size,
            "extension": file_path.suffix,
            "truncated": truncated,
            "error": None,
        }
    except UnicodeDecodeError:
        return {
            "content": None,
            "error": "Binary file or encoding issue",
        }
    except Exception as e:
        return {
            "content": None,
            "error": str(e),
        }


def search_code(
    project_path: Path,
    pattern: str,
    file_types: Optional[list[str]] = None,
    context_lines: int = 2,
    max_results: int = 50,
) -> list[dict]:
    """
    Search for a pattern in code files.

    Args:
        project_path: Root path to search
        pattern: Regex pattern to search for
        file_types: List of file extensions to include (e.g., ['.py', '.java'])
        context_lines: Number of context lines before/after match
        max_results: Maximum number of results to return

    Returns:
        List of matches with file path, line number, and context
    """
    gitignore_spec = get_gitignore_spec(project_path)
    regex = re.compile(pattern)
    results = []

    for root, dirs, files in os.walk(project_path):
        root_path = Path(root)

        # Filter directories
        dirs[:] = [
            d for d in dirs if not should_ignore(root_path / d, project_path, gitignore_spec)
        ]

        for file in files:
            file_path = root_path / file

            if should_ignore(file_path, project_path, gitignore_spec):
                continue

            if file_types and file_path.suffix not in file_types:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for i, line in enumerate(lines):
                    if regex.search(line):
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        context = "".join(lines[start:end])

                        results.append(
                            {
                                "file": str(file_path.relative_to(project_path)),
                                "line_number": i + 1,
                                "line": line.rstrip(),
                                "context": context,
                            }
                        )

                        if len(results) >= max_results:
                            return results
            except (UnicodeDecodeError, PermissionError):
                continue

    return results


def write_file(file_path: Path, content: str, backup: bool = True) -> dict:
    """
    Write content to a file, optionally creating a backup.

    Returns:
        - success: boolean
        - backup_path: path to backup if created
        - error: error message if failed
    """
    try:
        # Create backup if file exists
        backup_path = None
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + ".backup")
            shutil.copy2(file_path, backup_path)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "backup_path": str(backup_path) if backup_path else None,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "backup_path": None,
            "error": str(e),
        }


def find_definitions(
    project_path: Path, symbol_name: str, file_types: Optional[list[str]] = None
) -> list[dict]:
    """
    Find class/function/method definitions.

    Simple pattern matching for common definition patterns.
    """
    patterns = [
        rf"^class\s+{symbol_name}\b",  # Python/Java class
        rf"^def\s+{symbol_name}\b",  # Python function
        rf"function\s+{symbol_name}\b",  # JavaScript function
        rf"const\s+{symbol_name}\s*=",  # JavaScript const
        rf"public\s+.*\s+{symbol_name}\s*\(",  # Java method
        rf"private\s+.*\s+{symbol_name}\s*\(",  # Java method
    ]

    combined_pattern = "|".join(f"({p})" for p in patterns)
    return search_code(project_path, combined_pattern, file_types, context_lines=5)


def get_file_imports(file_path: Path) -> dict:
    """
    Extract import statements from a file.

    Supports Python, JavaScript, Java.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        imports = []
        ext = file_path.suffix

        if ext == ".py":
            # Python imports
            import_pattern = r"^(?:from\s+[\w.]+\s+)?import\s+[\w,\s.*]+"
            imports = re.findall(import_pattern, content, re.MULTILINE)
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            # JavaScript/TypeScript imports
            import_pattern = r"import\s+.*?from\s+['\"].*?['\"]"
            imports = re.findall(import_pattern, content)
        elif ext == ".java":
            # Java imports
            import_pattern = r"^import\s+[\w.]+;"
            imports = re.findall(import_pattern, content, re.MULTILINE)

        return {
            "file": str(file_path),
            "imports": imports,
            "count": len(imports),
            "error": None,
        }
    except Exception as e:
        return {
            "file": str(file_path),
            "imports": [],
            "count": 0,
            "error": str(e),
        }
