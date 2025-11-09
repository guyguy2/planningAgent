"""Main agent execution loop using Claude's tool-use API."""

import os
from pathlib import Path
from typing import Any, Optional

import anthropic
from rich.console import Console

from plancode.agent.prompts import (
    build_analysis_only_prompt,
    build_system_prompt,
)
from plancode.models.plan import ProjectContext
from plancode.tools import analysis, execution, filesystem, workflow
from plancode.ui import display

console = Console()


def create_tool_definitions() -> list[dict]:
    """Define all available tools for Claude."""
    return [
        {
            "name": "list_project_structure",
            "description": "Get a tree view of the project directory structure with file counts and detected languages.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (default: 3)",
                        "default": 3,
                    }
                },
            },
        },
        {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read (relative to project root)",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (optional)",
                    },
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "search_code",
            "description": "Search for a regex pattern in code files.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for",
                    },
                    "file_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File extensions to include (e.g., ['.py', '.java'])",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines before/after match (default: 2)",
                        "default": 2,
                    },
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "find_definitions",
            "description": "Find class, function, or method definitions by name.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Name of the class/function/method to find",
                    },
                    "file_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File extensions to search in",
                    },
                },
                "required": ["symbol_name"],
            },
        },
        {
            "name": "get_file_imports",
            "description": "Extract import statements from a file (supports Python, JavaScript, Java).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to project root)",
                    },
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "analyze_python_file",
            "description": "Deep AST-based analysis of a Python file. Extracts classes, methods, functions, imports, decorators, and complexity metrics.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the Python file (relative to project root)",
                    },
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "get_project_summary",
            "description": "Comprehensive project analysis: tech stack, frameworks, build tools, testing frameworks, databases, and architecture patterns.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "find_related_files",
            "description": "Find files related to a given file through imports and dependencies.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to project root)",
                    },
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "ask_developer_for_approval",
            "description": "REQUIRED: Pause execution and ask the developer to approve the implementation plan. Must be called before writing any code.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "phase_name": {
                        "type": "string",
                        "description": "Name of the phase/plan being approved",
                    },
                    "plan_summary": {
                        "type": "string",
                        "description": "Detailed summary of what will be implemented",
                    },
                    "files_to_modify": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths that will be created/modified",
                    },
                    "estimated_complexity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Estimated complexity of the implementation",
                    },
                },
                "required": [
                    "phase_name",
                    "plan_summary",
                    "files_to_modify",
                    "estimated_complexity",
                ],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to a file, creating it if it doesn't exist. Automatically creates backups.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to project root)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                    "backup": {
                        "type": "boolean",
                        "description": "Create a backup if file exists (default: true)",
                        "default": True,
                    },
                },
                "required": ["file_path", "content"],
            },
        },
        {
            "name": "run_command",
            "description": "Execute a shell command in the project directory.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 300)",
                        "default": 300,
                    },
                },
                "required": ["cmd"],
            },
        },
        {
            "name": "run_tests",
            "description": "Run the project's test suite. Auto-detects test framework.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Specific test file or directory to run (optional)",
                    },
                    "test_framework": {
                        "type": "string",
                        "description": "Test framework to use (pytest, unittest, jest, maven, gradle)",
                    },
                },
            },
        },
        {
            "name": "verify_build",
            "description": "Verify that the project builds successfully. Auto-detects build system.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "build_command": {
                        "type": "string",
                        "description": "Custom build command (optional)",
                    },
                },
            },
        },
        {
            "name": "run_linter",
            "description": "Run linter/formatter checks. Auto-detects linter configuration.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "linter": {
                        "type": "string",
                        "description": "Specific linter to run (ruff, black, eslint, mypy)",
                    },
                },
            },
        },
    ]


def execute_tool(tool_name: str, tool_input: dict, project_path: Path) -> Any:
    """Execute a tool and return its result."""
    try:
        # Filesystem tools
        if tool_name == "list_project_structure":
            result = filesystem.list_project_structure(
                project_path, max_depth=tool_input.get("max_depth", 3)
            )
            display.display_project_structure(result)
            return result

        elif tool_name == "read_file":
            file_path = project_path / tool_input["file_path"]
            result = filesystem.read_file(file_path, tool_input.get("max_lines"))
            if result.get("error"):
                display.display_error(f"Failed to read {tool_input['file_path']}", result["error"])
            return result

        elif tool_name == "search_code":
            result = filesystem.search_code(
                project_path,
                tool_input["pattern"],
                tool_input.get("file_types"),
                tool_input.get("context_lines", 2),
            )
            display.display_search_results(result)
            return result

        elif tool_name == "find_definitions":
            result = filesystem.find_definitions(
                project_path,
                tool_input["symbol_name"],
                tool_input.get("file_types"),
            )
            return result

        elif tool_name == "get_file_imports":
            file_path = project_path / tool_input["file_path"]
            return filesystem.get_file_imports(file_path)

        # Analysis tools
        elif tool_name == "analyze_python_file":
            result = analysis.analyze_python_file(tool_input["file_path"], project_path)
            if result.get("error"):
                display.display_error(
                    f"Failed to analyze {tool_input['file_path']}", result["error"]
                )
            else:
                display.display_success(f"Analyzed Python file: {tool_input['file_path']}")
                # Display key metrics
                if result.get("classes"):
                    display.display_info(f"Found {len(result['classes'])} classes")
                if result.get("functions"):
                    display.display_info(f"Found {len(result['functions'])} functions")
            return result

        elif tool_name == "get_project_summary":
            result = analysis.get_project_summary(project_path)
            if result.get("error"):
                display.display_error("Failed to analyze project", result["error"])
            else:
                display.display_success("Project analysis complete")
                # Display key findings
                if result.get("frameworks"):
                    display.display_info(f"Frameworks: {', '.join(result['frameworks'])}")
                if result.get("languages"):
                    langs = ", ".join([f"{k}: {v} files" for k, v in result["languages"].items()])
                    display.display_info(f"Languages: {langs}")
            return result

        elif tool_name == "find_related_files":
            result = analysis.find_related_files(tool_input["file_path"], project_path)
            if result.get("error"):
                display.display_error("Failed to find related files", result["error"])
            else:
                imports_count = len(result.get("imports_from_this_file", []))
                importers_count = len(result.get("files_that_import_this", []))
                display.display_info(
                    f"Found {imports_count} imports, {importers_count} files that import this file"
                )
            return result

        # Workflow tools
        elif tool_name == "ask_developer_for_approval":
            result = workflow.ask_developer_for_approval(
                tool_input["phase_name"],
                tool_input["plan_summary"],
                tool_input["files_to_modify"],
                tool_input["estimated_complexity"],
            )
            return result.model_dump()

        elif tool_name == "write_file":
            file_path = project_path / tool_input["file_path"]
            result = filesystem.write_file(
                file_path,
                tool_input["content"],
                tool_input.get("backup", True),
            )
            if result["success"]:
                display.display_success(f"Wrote {tool_input['file_path']}")
                if result.get("backup_path"):
                    display.display_info(f"Backup created: {result['backup_path']}")
            else:
                display.display_error(f"Failed to write {tool_input['file_path']}", result["error"])
            return result

        # Execution tools
        elif tool_name == "run_command":
            result = execution.run_command(
                tool_input["cmd"],
                project_path,
                tool_input.get("timeout", 300),
            )
            if result["success"]:
                display.display_success(f"Command completed: {tool_input['cmd']}")
            else:
                display.display_error(f"Command failed: {tool_input['cmd']}", result.get("error"))
            return result

        elif tool_name == "run_tests":
            result = execution.run_tests(
                project_path,
                tool_input.get("test_path"),
                tool_input.get("test_framework"),
            )
            if result.get("passed"):
                display.display_success("Tests passed!")
            else:
                display.display_error("Tests failed", result.get("stderr"))
            return result

        elif tool_name == "verify_build":
            result = execution.verify_build(
                project_path,
                tool_input.get("build_command"),
            )
            if result.get("success"):
                display.display_success("Build successful!")
            else:
                display.display_error("Build failed", result.get("error"))
            return result

        elif tool_name == "run_linter":
            result = execution.run_linter(
                project_path,
                tool_input.get("linter"),
            )
            if result.get("success"):
                display.display_success("Linter checks passed!")
            elif result.get("skipped"):
                display.display_info(result.get("message", "Linter skipped"))
            else:
                display.display_warning("Linter found issues")
            return result

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        error_msg = f"Error executing {tool_name}: {str(e)}"
        display.display_error(error_msg)
        return {"error": error_msg}


def analyze_project(project_path: Path) -> ProjectContext:
    """Analyze the project to build context."""
    display.display_info("Analyzing project structure...")

    # Get comprehensive project summary using new analysis tools
    summary = analysis.get_project_summary(project_path)

    # Determine primary language
    languages = summary.get("languages", {})
    if languages:
        # Find language with most files
        primary_language = max(languages.items(), key=lambda x: x[1])[0] if languages else "Unknown"
        # Clean up extension to just language name
        lang_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
        }
        primary_language = lang_map.get(primary_language, primary_language.lstrip("."))
    else:
        primary_language = "Unknown"

    # Get framework(s)
    frameworks = summary.get("frameworks", [])
    framework = frameworks[0] if frameworks else "various frameworks"

    # Get tech stack
    tech_stack = summary.get("build_tools", [])
    if frameworks:
        tech_stack.extend(frameworks)
    if summary.get("testing_frameworks"):
        tech_stack.extend(summary.get("testing_frameworks", []))

    # Remove duplicates
    tech_stack = list(set(tech_stack))

    # Display summary
    if frameworks:
        display.display_info(f"Detected frameworks: {', '.join(frameworks)}")
    if summary.get("databases"):
        display.display_info(f"Databases: {', '.join(summary['databases'])}")
    if summary.get("architecture_indicators"):
        display.display_info(f"Architecture: {', '.join(summary['architecture_indicators'][:3])}")

    return ProjectContext(
        path=str(project_path),
        language=primary_language,
        framework=framework,
        tech_stack=tech_stack,
    )


def run_planning_agent(
    task: str,
    project_path: Path,
    model: str,
    analyze_only: bool = False,
    save_plan_path: Optional[Path] = None,
):
    """Run the main planning agent loop."""
    # Initialize Claude client
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Analyze project
    project_context = analyze_project(project_path)

    # Build system prompt
    system_prompt = build_system_prompt(project_context)
    if analyze_only:
        system_prompt += "\n\n" + build_analysis_only_prompt()

    # Initialize conversation
    messages = [{"role": "user", "content": task}]

    # Get tool definitions
    tools = create_tool_definitions()

    # Agent loop
    max_iterations = 50
    iteration = 0

    with display.create_spinner("Planning...") as progress:
        task_id = progress.add_task("Thinking...", total=None)

        while iteration < max_iterations:
            iteration += 1

            try:
                # Call Claude
                response = client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )

                # Add assistant response to messages
                messages.append({"role": "assistant", "content": response.content})

                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Agent is done
                    progress.stop()

                    # Display final message
                    for block in response.content:
                        if hasattr(block, "text"):
                            console.print(f"\n[bold cyan]Agent:[/bold cyan] {block.text}\n")

                    display.display_success("Task completed!")
                    break

                elif response.stop_reason == "tool_use":
                    # Execute tools
                    tool_results = []

                    for block in response.content:
                        if block.type == "tool_use":
                            progress.update(task_id, description=f"Executing: {block.name}")

                            result = execute_tool(block.name, block.input, project_path)

                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": str(result),
                                }
                            )

                    # Add tool results to messages
                    messages.append({"role": "user", "content": tool_results})

                elif response.stop_reason == "max_tokens":
                    display.display_warning("Response truncated due to token limit. Continuing...")
                    # Continue the conversation
                    messages.append(
                        {"role": "user", "content": "Please continue from where you left off."}
                    )

            except anthropic.APIError as e:
                progress.stop()
                display.display_error(f"API Error: {str(e)}")
                break
            except Exception as e:
                progress.stop()
                display.display_error(f"Unexpected error: {str(e)}")
                break

        if iteration >= max_iterations:
            display.display_warning(f"Reached maximum iterations ({max_iterations})")


def resume_plan(plan_path: Path, project_path: Path, model: str):
    """Resume execution of a saved plan."""
    display.display_info(f"Loading plan from {plan_path}")

    plan = workflow.load_plan(plan_path)
    if not plan:
        display.display_error("Failed to load plan")
        return

    # Display plan
    display.display_plan(plan)
    display.display_progress(plan)

    # Build resume prompt
    plan_summary = f"Task: {plan.task_description}\n"
    plan_summary += f"Phases: {len(plan.phases)}\n"
    plan_summary += f"Completed: {sum(1 for p in plan.phases if p.status == 'completed')}"

    # TODO: Use build_resume_prompt(plan_summary) when resume is fully implemented

    # Continue with agent loop
    # (Implementation similar to run_planning_agent)
    display.display_info("Resume functionality - full implementation pending")
