"""
Code analysis tools using AST parsing and static analysis.

Provides deep code understanding for Python, JavaScript, Java, and other languages.
"""

import ast
import json
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict

from .filesystem import should_ignore, read_file, get_gitignore_spec


def analyze_python_file(file_path: str, project_path: Path) -> Dict[str, Any]:
    """
    Analyze a Python file using AST parsing.

    Extracts:
    - Classes (with methods, decorators, base classes)
    - Functions (with decorators, parameters)
    - Imports (standard library, third-party, local)
    - Global variables
    - Docstrings

    Args:
        file_path: Path to Python file (relative to project or absolute)
        project_path: Project root directory

    Returns:
        Dictionary with analysis results
    """
    try:
        # Resolve path
        if Path(file_path).is_absolute():
            full_path = Path(file_path)
        else:
            full_path = project_path / file_path

        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}

        # Read file content
        result = read_file(full_path)
        if result.get("error"):
            return result

        content = result["content"]

        # Parse AST
        try:
            tree = ast.parse(content, filename=str(full_path))
        except SyntaxError as e:
            return {"error": f"Syntax error in {file_path}", "details": f"Line {e.lineno}: {e.msg}"}

        analysis = {
            "file_path": file_path,
            "module_docstring": ast.get_docstring(tree),
            "imports": _extract_imports(tree),
            "classes": _extract_classes(tree),
            "functions": _extract_functions(tree),
            "global_variables": _extract_globals(tree),
            "complexity": _estimate_complexity(tree),
        }

        return analysis

    except Exception as e:
        return {"error": f"Failed to analyze {file_path}: {str(e)}"}


def get_project_summary(project_path: Path) -> Dict[str, Any]:
    """
    Analyze project to determine tech stack, frameworks, and architecture.

    Detects:
    - Primary language(s)
    - Frameworks (Django, Flask, FastAPI, Spring Boot, React, etc.)
    - Build tools (pip, npm, maven, gradle)
    - Testing frameworks
    - Database technologies
    - Architecture patterns

    Args:
        project_path: Project root directory

    Returns:
        Dictionary with project summary
    """
    summary = {
        "languages": {},
        "frameworks": [],
        "build_tools": [],
        "testing_frameworks": [],
        "databases": [],
        "config_files": [],
        "architecture_indicators": [],
        "dependencies": {},
    }

    try:
        # Get gitignore spec
        gitignore_spec = get_gitignore_spec(project_path)

        # Detect languages by file extensions
        language_files = defaultdict(int)
        for path in project_path.rglob("*"):
            if path.is_file() and not should_ignore(path, project_path, gitignore_spec):
                ext = path.suffix.lower()
                if ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb"]:
                    language_files[ext] += 1

        summary["languages"] = dict(language_files)

        # Detect build tools and config files
        config_indicators = {
            "requirements.txt": {"type": "build", "tool": "pip", "language": "python"},
            "pyproject.toml": {"type": "build", "tool": "poetry/uv", "language": "python"},
            "setup.py": {"type": "build", "tool": "setuptools", "language": "python"},
            "package.json": {"type": "build", "tool": "npm", "language": "javascript"},
            "pom.xml": {"type": "build", "tool": "maven", "language": "java"},
            "build.gradle": {"type": "build", "tool": "gradle", "language": "java"},
            "Cargo.toml": {"type": "build", "tool": "cargo", "language": "rust"},
            "go.mod": {"type": "build", "tool": "go modules", "language": "go"},
            "Gemfile": {"type": "build", "tool": "bundler", "language": "ruby"},
        }

        for config_file, info in config_indicators.items():
            if (project_path / config_file).exists():
                summary["config_files"].append(config_file)
                if info["type"] == "build":
                    summary["build_tools"].append(info["tool"])

        # Analyze Python dependencies
        if (project_path / "requirements.txt").exists():
            deps = _parse_requirements(project_path / "requirements.txt")
            summary["dependencies"]["python"] = deps
            summary["frameworks"].extend(_detect_python_frameworks(deps))
            summary["testing_frameworks"].extend(_detect_python_test_frameworks(deps))
            summary["databases"].extend(_detect_python_databases(deps))

        # Analyze pyproject.toml
        if (project_path / "pyproject.toml").exists():
            pyproject_info = _parse_pyproject_toml(project_path / "pyproject.toml")
            if pyproject_info.get("dependencies"):
                summary["dependencies"]["python"] = pyproject_info["dependencies"]
                summary["frameworks"].extend(
                    _detect_python_frameworks(pyproject_info["dependencies"])
                )
                summary["testing_frameworks"].extend(
                    _detect_python_test_frameworks(pyproject_info["dependencies"])
                )
                summary["databases"].extend(
                    _detect_python_databases(pyproject_info["dependencies"])
                )

        # Analyze package.json
        if (project_path / "package.json").exists():
            package_info = _parse_package_json(project_path / "package.json")
            if package_info.get("dependencies"):
                summary["dependencies"]["javascript"] = list(package_info["dependencies"].keys())
                summary["frameworks"].extend(_detect_js_frameworks(package_info["dependencies"]))
                summary["testing_frameworks"].extend(
                    _detect_js_test_frameworks(package_info["dependencies"])
                )

        # Detect architecture patterns
        summary["architecture_indicators"] = _detect_architecture_patterns(project_path)

        # Remove duplicates
        summary["frameworks"] = list(set(summary["frameworks"]))
        summary["testing_frameworks"] = list(set(summary["testing_frameworks"]))
        summary["databases"] = list(set(summary["databases"]))

        return summary

    except Exception as e:
        return {"error": f"Failed to analyze project: {str(e)}"}


def find_related_files(file_path: str, project_path: Path) -> Dict[str, Any]:
    """
    Find files related to the given file through imports/dependencies.

    For Python files:
    - Files that import this file
    - Files imported by this file

    Args:
        file_path: Path to file (relative to project)
        project_path: Project root directory

    Returns:
        Dictionary with related files categorized by relationship
    """
    try:
        full_path = project_path / file_path

        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}

        # Determine file type
        ext = full_path.suffix.lower()

        if ext == ".py":
            return _find_related_python_files(file_path, project_path)
        else:
            return {
                "file_path": file_path,
                "message": f"Relationship analysis not yet supported for {ext} files",
            }

    except Exception as e:
        return {"error": f"Failed to find related files: {str(e)}"}


# Helper functions for AST extraction


def _extract_imports(tree: ast.AST) -> Dict[str, List[str]]:
    """Extract imports categorized by type."""
    imports = {
        "standard_library": [],
        "third_party": [],
        "local": [],
    }

    stdlib_modules = {
        "os",
        "sys",
        "json",
        "re",
        "time",
        "datetime",
        "pathlib",
        "typing",
        "collections",
        "itertools",
        "functools",
        "asyncio",
        "subprocess",
        "logging",
        "unittest",
        "argparse",
        "dataclasses",
        "abc",
        "enum",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in stdlib_modules:
                    imports["standard_library"].append(alias.name)
                elif module.startswith("."):
                    imports["local"].append(alias.name)
                else:
                    imports["third_party"].append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if node.level > 0:  # Relative import
                    imports["local"].append(f"{'.' * node.level}{node.module or ''}")
                elif module in stdlib_modules:
                    imports["standard_library"].append(node.module)
                else:
                    imports["third_party"].append(node.module)

    return imports


def _extract_classes(tree: ast.AST) -> List[Dict[str, Any]]:
    """Extract class definitions with methods and metadata."""
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "line_number": node.lineno,
                "docstring": ast.get_docstring(node),
                "decorators": [_get_decorator_name(d) for d in node.decorator_list],
                "base_classes": [_get_base_class_name(base) for base in node.bases],
                "methods": [],
            }

            # Extract methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_info = {
                        "name": item.name,
                        "line_number": item.lineno,
                        "decorators": [_get_decorator_name(d) for d in item.decorator_list],
                        "parameters": [arg.arg for arg in item.args.args],
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                    }
                    class_info["methods"].append(method_info)

            classes.append(class_info)

    return classes


def _extract_functions(tree: ast.AST) -> List[Dict[str, Any]]:
    """Extract top-level function definitions."""
    functions = []

    # Only get top-level functions (not methods inside classes)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = {
                "name": node.name,
                "line_number": node.lineno,
                "docstring": ast.get_docstring(node),
                "decorators": [_get_decorator_name(d) for d in node.decorator_list],
                "parameters": [arg.arg for arg in node.args.args],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            }
            functions.append(func_info)

    return functions


def _extract_globals(tree: ast.AST) -> List[Dict[str, Any]]:
    """Extract global variable assignments."""
    globals_list = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    globals_list.append(
                        {
                            "name": target.id,
                            "line_number": node.lineno,
                        }
                    )

    return globals_list


def _estimate_complexity(tree: ast.AST) -> Dict[str, int]:
    """Estimate code complexity metrics."""
    metrics = {
        "total_lines": 0,
        "classes": 0,
        "functions": 0,
        "imports": 0,
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            metrics["classes"] += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            metrics["functions"] += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            metrics["imports"] += 1

    return metrics


def _get_decorator_name(decorator: ast.expr) -> str:
    """Extract decorator name from AST node."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Call):
        if isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator.func, ast.Attribute):
            return decorator.func.attr
    elif isinstance(decorator, ast.Attribute):
        return decorator.attr
    return str(decorator)


def _get_base_class_name(base: ast.expr) -> str:
    """Extract base class name from AST node."""
    if isinstance(base, ast.Name):
        return base.id
    elif isinstance(base, ast.Attribute):
        return base.attr
    return str(base)


# Helper functions for project analysis


def _parse_requirements(req_file: Path) -> List[str]:
    """Parse requirements.txt file."""
    try:
        deps = []
        with open(req_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before ==, >=, etc.)
                    pkg = line.split("==")[0].split(">=")[0].split("~=")[0].strip()
                    deps.append(pkg)
        return deps
    except Exception:
        return []


def _parse_pyproject_toml(toml_file: Path) -> Dict[str, Any]:
    """Parse pyproject.toml file."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}

    try:
        with open(toml_file, "rb") as f:
            data = tomllib.load(f)

        # Extract dependencies from various sections
        deps = []

        # Poetry style
        if "tool" in data and "poetry" in data["tool"]:
            poetry_deps = data["tool"]["poetry"].get("dependencies", {})
            deps.extend([k for k in poetry_deps.keys() if k != "python"])

        # PEP 621 style
        if "project" in data:
            project_deps = data["project"].get("dependencies", [])
            for dep in project_deps:
                pkg = dep.split("==")[0].split(">=")[0].split("~=")[0].strip()
                deps.append(pkg)

        return {"dependencies": deps}
    except Exception:
        return {}


def _parse_package_json(json_file: Path) -> Dict[str, Any]:
    """Parse package.json file."""
    try:
        with open(json_file) as f:
            data = json.load(f)
        return {
            "dependencies": data.get("dependencies", {}),
            "devDependencies": data.get("devDependencies", {}),
        }
    except Exception:
        return {}


def _detect_python_frameworks(deps: List[str]) -> List[str]:
    """Detect Python frameworks from dependencies."""
    frameworks = []
    framework_indicators = {
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "starlette": "Starlette",
        "tornado": "Tornado",
        "aiohttp": "aiohttp",
        "sanic": "Sanic",
        "pyramid": "Pyramid",
        "bottle": "Bottle",
        "cherrypy": "CherryPy",
        "typer": "Typer (CLI)",
        "click": "Click (CLI)",
        "anthropic": "Anthropic SDK",
    }

    for dep in deps:
        dep_lower = dep.lower()
        for indicator, framework in framework_indicators.items():
            if indicator in dep_lower:
                frameworks.append(framework)

    return frameworks


def _detect_python_test_frameworks(deps: List[str]) -> List[str]:
    """Detect Python testing frameworks."""
    frameworks = []
    test_indicators = {
        "pytest": "pytest",
        "unittest": "unittest",
        "nose": "nose",
        "behave": "behave (BDD)",
        "hypothesis": "hypothesis",
    }

    for dep in deps:
        dep_lower = dep.lower()
        for indicator, framework in test_indicators.items():
            if indicator in dep_lower:
                frameworks.append(framework)

    return frameworks


def _detect_python_databases(deps: List[str]) -> List[str]:
    """Detect database technologies from Python dependencies."""
    databases = []
    db_indicators = {
        "psycopg": "PostgreSQL",
        "pymysql": "MySQL",
        "mysql-connector": "MySQL",
        "pymongo": "MongoDB",
        "redis": "Redis",
        "sqlalchemy": "SQLAlchemy (ORM)",
        "django-orm": "Django ORM",
        "peewee": "Peewee (ORM)",
        "tortoise": "Tortoise ORM",
    }

    for dep in deps:
        dep_lower = dep.lower()
        for indicator, db in db_indicators.items():
            if indicator in dep_lower:
                databases.append(db)

    return databases


def _detect_js_frameworks(deps: Dict[str, str]) -> List[str]:
    """Detect JavaScript frameworks."""
    frameworks = []
    framework_indicators = {
        "react": "React",
        "vue": "Vue",
        "angular": "Angular",
        "svelte": "Svelte",
        "next": "Next.js",
        "nuxt": "Nuxt",
        "express": "Express",
        "koa": "Koa",
        "fastify": "Fastify",
        "nest": "NestJS",
    }

    for dep_name in deps.keys():
        dep_lower = dep_name.lower()
        for indicator, framework in framework_indicators.items():
            if indicator in dep_lower:
                frameworks.append(framework)

    return frameworks


def _detect_js_test_frameworks(deps: Dict[str, str]) -> List[str]:
    """Detect JavaScript testing frameworks."""
    frameworks = []
    test_indicators = {
        "jest": "Jest",
        "mocha": "Mocha",
        "jasmine": "Jasmine",
        "vitest": "Vitest",
        "cypress": "Cypress",
        "playwright": "Playwright",
    }

    for dep_name in deps.keys():
        dep_lower = dep_name.lower()
        for indicator, framework in test_indicators.items():
            if indicator in dep_lower:
                frameworks.append(framework)

    return frameworks


def _detect_architecture_patterns(project_path: Path) -> List[str]:
    """Detect common architecture patterns from directory structure."""
    patterns = []

    # Common directory indicators
    if (project_path / "api").exists():
        patterns.append("API Layer")
    if (project_path / "models").exists() or (project_path / "src" / "models").exists():
        patterns.append("Model Layer")
    if (project_path / "views").exists() or (project_path / "src" / "views").exists():
        patterns.append("View Layer")
    if (project_path / "controllers").exists() or (project_path / "src" / "controllers").exists():
        patterns.append("MVC Pattern")
    if (project_path / "services").exists() or (project_path / "src" / "services").exists():
        patterns.append("Service Layer")
    if (project_path / "repositories").exists() or (project_path / "src" / "repositories").exists():
        patterns.append("Repository Pattern")
    if (project_path / "components").exists() or (project_path / "src" / "components").exists():
        patterns.append("Component Architecture")
    if (project_path / "middleware").exists():
        patterns.append("Middleware Pattern")
    if (project_path / "cli").exists():
        patterns.append("CLI Tool")
    if (project_path / "agent").exists() or (project_path / "agents").exists():
        patterns.append("Agent-Based Architecture")

    return patterns


def _find_related_python_files(file_path: str, project_path: Path) -> Dict[str, Any]:
    """Find Python files related through imports."""
    related = {
        "file_path": file_path,
        "imports_from_this_file": [],
        "files_that_import_this": [],
    }

    # Get imports from target file
    analysis = analyze_python_file(file_path, project_path)
    if analysis.get("error"):
        return analysis

    # Collect all imported modules
    for import_type in ["standard_library", "third_party", "local"]:
        related["imports_from_this_file"].extend(analysis["imports"].get(import_type, []))

    # Search for files that import this file
    # Convert file path to module path (e.g., plancode/tools/analysis.py -> plancode.tools.analysis)
    module_path = str(Path(file_path).with_suffix("")).replace("/", ".")

    # Get gitignore spec
    gitignore_spec = get_gitignore_spec(project_path)

    # Search all Python files
    for py_file in project_path.rglob("*.py"):
        if should_ignore(py_file, project_path, gitignore_spec):
            continue

        try:
            rel_path = py_file.relative_to(project_path)
            if str(rel_path) == file_path:
                continue

            # Analyze this file's imports
            file_analysis = analyze_python_file(str(rel_path), project_path)
            if not file_analysis.get("error"):
                all_imports = []
                for import_type in ["standard_library", "third_party", "local"]:
                    all_imports.extend(file_analysis["imports"].get(import_type, []))

                # Check if it imports our target module
                if any(module_path in imp for imp in all_imports):
                    related["files_that_import_this"].append(str(rel_path))

        except Exception:
            continue

    return related
