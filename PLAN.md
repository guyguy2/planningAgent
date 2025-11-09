# PlanCode: AI-Powered Code Planning & Implementation Tool

## Overview

A Python CLI tool that uses Claude's API to implement a **Plan-First methodology** for software development. The tool analyzes codebases, creates detailed implementation plans, gets developer approval, and executes changes safely.

## Core Philosophy

**Plan → Approve → Execute → Verify**

Never write code before creating and approving a detailed plan. This ensures thoughtful architecture, minimal changes, and clear communication.

---

## Architecture

### Agent-First with Smart Orchestration

- **Python CLI** using Claude's tool-use API
- **Sophisticated codebase analysis** (AST parsing, static analysis)
- **Plan persistence** as JSON/YAML for iteration and reuse
- **Optional Claude Code integration** for complex execution tasks

---

## Implementation Phases

### Phase 1: Foundation & CLI

**Goal:** Solid CLI foundation with beautiful output

**Example Usage:**
```bash
plancode "Add health check endpoint" --project ./my-app
plancode --resume last-plan.json
plancode --analyze-only
```

**Tech Stack:**
- **Typer** - Modern CLI framework
- **Anthropic SDK** - Claude API integration
- **Rich** - Beautiful terminal output (progress bars, syntax highlighting, tables)
- **Pydantic** - Data models for plans and validation

---

### Phase 2: Smart Codebase Analysis Tools

Claude needs to understand your codebase. These tools provide comprehensive analysis:

#### File System Tools
1. `list_project_structure(max_depth=3)` - Tree view with file counts, languages
2. `read_file(path)` - With syntax highlighting hints
3. `search_code(pattern, file_types=None)` - Regex/grep with context lines
4. `find_definitions(symbol_name)` - Find class/method definitions
5. `get_file_imports(path)` - Extract dependencies

#### Code Analysis Tools (AST-based)
6. `analyze_java_class(path)` - Parse Spring annotations, methods, dependencies
7. `get_project_summary()` - Tech stack, frameworks, build tools, architecture patterns
8. `find_related_files(path)` - Files that import/use this file

#### Optional (Advanced)
- Tree-sitter integration for multi-language parsing
- Integration with Java analysis tools (jdeps for dependencies)

---

### Phase 3: Agent Workflow Tools

Tools that control the workflow and enforce the Plan-First methodology:

#### Critical Tool: Human-in-the-Loop

```python
def ask_developer_for_approval(
    phase_name: str,
    plan_summary: str,
    files_to_modify: list[str],
    estimated_complexity: str
) -> dict:
    """
    Pauses execution and asks developer for approval.
    Returns: {"approved": bool, "feedback": str}
    """
    # Beautiful Rich table showing the plan
    # input() to wait for response
    # Allow 'y', 'n', or 'modify [feedback]'
```

#### Plan Management Tools

```python
def save_plan(plan: dict, filename: str)
def load_plan(filename: str) -> dict
def update_plan_step(step_id: str, changes: dict)
```

#### Execution Tools

```python
def write_file(path: str, content: str, backup=True)
def run_command(cmd: str, cwd: str) -> dict  # stdout, stderr, exit_code
def run_tests(test_path: str = None)
```

---

### Phase 4: The System Prompt

Enhanced prompt that enforces the methodology:

```
You are an expert AI Software Architect specializing in {language} and {framework}.
Your goal is to help implement the user's task using a strict PLAN-FIRST methodology.

## YOUR WORKFLOW (MANDATORY):

### Phase 1: ANALYZE (DO NOT SKIP)
1. Use `get_project_summary()` to understand tech stack
2. Use `list_project_structure()` to see architecture
3. Use `search_code()` and `read_file()` to understand relevant code
4. For Java projects: use `analyze_java_class()` on key files

### Phase 2: PLAN
Create a detailed implementation plan with:
- Clear phases (each phase = 1 logical unit of work)
- For each phase:
  * Objective (what and why)
  * Files to create/modify (specific paths)
  * Key changes (concrete, not vague)
  * Dependencies on other phases
  * Testing strategy

### Phase 3: APPROVAL (REQUIRED - DO NOT SKIP)
You MUST call `ask_developer_for_approval()` with your complete plan.
DO NOT write any files until you receive approval.
If developer provides feedback, revise the plan and ask again.

### Phase 4: EXECUTE
Only after approval:
- Execute each phase step-by-step
- Use `write_file()` for code changes
- After each file: briefly explain what you did
- Save progress: use `save_plan()` after each phase

### Phase 5: VERIFY
- Use `run_tests()` to validate changes
- Use `run_command()` to check builds/linting
- Report results clearly

## IMPORTANT RULES:
- NEVER write code before getting approval
- NEVER modify files outside the approved plan without asking
- If you discover issues during execution, STOP and ask for guidance
- Keep your changes focused and minimal
- Provide clear commit-ready summaries
```

---

### Phase 5: Python Execution Loop

Simplified main loop:

```python
def main(task: str, project_path: Path):
    # 1. Initialize
    client = anthropic.Anthropic()
    tools = [list_project_structure, read_file, ..., ask_developer_for_approval, ...]

    # 2. Build system prompt with project context
    system_prompt = build_system_prompt(project_path)

    # 3. Start conversation
    messages = [{"role": "user", "content": task}]

    # 4. Agent loop
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            system=system_prompt,
            messages=messages,
            tools=tools,
            max_tokens=4096
        )

        # Handle tool calls
        if response.stop_reason == "tool_use":
            tool_results = execute_tools(response.content)
            messages.append(...)  # Add assistant response
            messages.append(...)  # Add tool results
        else:
            # Task complete
            break
```

---

### Phase 6: Hybrid Enhancement (Optional)

For complex execution, hand off to Claude Code:

```python
def execute_with_claude_code(plan: dict, phase: dict):
    """
    Generate a detailed prompt from the plan and invoke Claude Code.
    This leverages Claude Code's file editing capabilities.
    """
    prompt = generate_claude_code_prompt(plan, phase)
    subprocess.run([
        "claude", "code",
        "--message", prompt,
        "--project", str(project_path)
    ])
```

---

## MVP Roadmap

### Week 1: Core Foundation
1. CLI skeleton with Typer
2. Basic file system tools (list, read, write)
3. Simple agent loop with approval tool
4. Hardcoded system prompt for Python projects

### Week 2: Analysis & Persistence
5. Rich terminal UI for plan display
6. Plan persistence (JSON)
7. Basic Java/Spring Boot code analysis
8. Test execution tool

### Week 3: Polish & Documentation
9. Refinement: better error handling, resume capability
10. Documentation and examples

---

## Key Differentiators

1. **Smart Analysis** - AST-based code understanding, not just text search
2. **Iterative Plans** - Save/load/modify plans across sessions
3. **Language-Aware** - Java/Spring Boot specific analysis capabilities
4. **Hybrid Execution** - Option to use Claude Code for complex implementations
5. **Beautiful UX** - Rich terminal UI, not just plain text
6. **Safety First** - Backups, git integration, test verification

---

## Project Structure

```
plancode/
├── cli/
│   ├── __init__.py
│   └── main.py              # Typer CLI entry point
├── agent/
│   ├── __init__.py
│   ├── loop.py              # Main agent execution loop
│   └── prompts.py           # System prompt templates
├── tools/
│   ├── __init__.py
│   ├── filesystem.py        # File operations
│   ├── analysis.py          # Code analysis (AST, etc.)
│   ├── workflow.py          # Approval, plan management
│   └── execution.py         # Write files, run commands
├── models/
│   ├── __init__.py
│   └── plan.py              # Pydantic models for plans
├── ui/
│   ├── __init__.py
│   └── display.py           # Rich terminal formatting
└── tests/
    └── ...
```

---

## Development Notes

### Initial Focus
- Start with Python projects (simpler AST parsing)
- Expand to Java/Spring Boot after core functionality is solid
- Keep the approval mechanism simple (stdin input) initially

### Future Enhancements
- Web UI for plan visualization
- Integration with issue trackers (GitHub Issues, Jira)
- Team collaboration features (shared plans)
- Cost tracking for API usage
- Multi-agent collaboration (separate agents for planning vs. execution)

---

## Implementation Progress

**Last Updated:** 2025-11-09

### ✅ Completed (Week 1 - Core Foundation)

#### 1. Project Setup
- ✅ Created project structure with all required directories
- ✅ Set up as uv project with pyproject.toml
- ✅ Installed core dependencies: anthropic, typer, rich, pydantic, pyyaml, pathspec
- ✅ Configured build system with hatchling

#### 2. Data Models (`plancode/models/plan.py`)
- ✅ Pydantic models for implementation plans
- ✅ Phase management with status tracking (PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED)
- ✅ File change tracking and complexity estimation
- ✅ Test strategy models
- ✅ Approval response models

#### 3. CLI Skeleton (`plancode/cli/main.py`)
- ✅ Typer-based CLI with beautiful Rich output
- ✅ Commands: `plan`, `version`, `init`
- ✅ Options: --project, --resume, --analyze-only, --model, --save-plan
- ✅ .plancode directory initialization
- ✅ .gitignore integration

#### 4. Filesystem Tools (`plancode/tools/filesystem.py`)
- ✅ `list_project_structure()` - Tree view with language detection
- ✅ `read_file()` - File reading with error handling
- ✅ `search_code()` - Regex pattern search with context
- ✅ `find_definitions()` - Find class/function definitions
- ✅ `get_file_imports()` - Extract imports (Python, JS, Java)
- ✅ `write_file()` - Write with automatic backups
- ✅ .gitignore aware filtering

#### 5. Workflow Tools (`plancode/tools/workflow.py`)
- ✅ `ask_developer_for_approval()` - Interactive approval with Rich UI
- ✅ `save_plan()` / `load_plan()` - JSON/YAML persistence
- ✅ `update_plan_step()` - Modify plan phases
- ✅ `auto_save_plan()` - Automatic plan saving

#### 6. Execution Tools (`plancode/tools/execution.py`)
- ✅ `run_command()` - Shell command execution
- ✅ `run_tests()` - Auto-detect test framework (pytest, jest, maven, gradle)
- ✅ `verify_build()` - Auto-detect build system
- ✅ `run_linter()` - Auto-detect linter (ruff, black, eslint, mypy)

#### 7. Rich UI (`plancode/ui/display.py`)
- ✅ `display_plan()` - Beautiful plan visualization
- ✅ `display_phase()` - Phase details with status indicators
- ✅ `display_progress()` - Progress summary
- ✅ `display_project_structure()` - Tree visualization
- ✅ `display_code()` - Syntax highlighted code
- ✅ `display_search_results()` - Search results formatting
- ✅ Error/success/warning/info message helpers

#### 8. System Prompts (`plancode/agent/prompts.py`)
- ✅ `build_system_prompt()` - Comprehensive agent instructions
- ✅ Enforces Plan-First methodology (Analyze → Plan → Approve → Execute → Verify)
- ✅ Project-aware prompting with tech stack context
- ✅ `build_resume_prompt()` - Resume existing plans
- ✅ `build_analysis_only_prompt()` - Analyze-only mode

#### 9. Agent Loop (`plancode/agent/loop.py`)
- ✅ Claude API integration with tool use
- ✅ 12 tool definitions for Claude (expanded to 15 in Week 2)
- ✅ Tool execution dispatcher
- ✅ Project analysis and context building
- ✅ Main planning agent loop with progress UI
- ✅ Error handling and iteration limits

### ✅ Completed (Week 2 - Advanced Analysis)

#### 10. Advanced Code Analysis (`plancode/tools/analysis.py`)
- ✅ AST-based Python file analysis with `analyze_python_file()`
  - Extracts classes with methods, decorators, base classes
  - Extracts functions with parameters, decorators, async status
  - Categorizes imports (stdlib, third-party, local)
  - Extracts global variables and docstrings
  - Estimates complexity metrics
- ✅ Comprehensive project summary with `get_project_summary()`
  - Auto-detects languages and file counts
  - Identifies frameworks (Django, Flask, FastAPI, React, etc.)
  - Detects build tools (pip, npm, maven, gradle, cargo)
  - Discovers testing frameworks (pytest, jest, etc.)
  - Identifies databases from dependencies
  - Detects architecture patterns from directory structure
  - Parses requirements.txt, pyproject.toml, package.json
- ✅ Dependency analysis with `find_related_files()`
  - Finds files that import a given file
  - Lists imports from a given file
  - Enables impact analysis for changes

#### 11. Enhanced Agent Loop Integration
- ✅ Added 3 new tool definitions (total: 15 tools)
- ✅ Integrated analysis tools into tool dispatcher
- ✅ Updated `analyze_project()` to use `get_project_summary()`
- ✅ Rich terminal feedback for analysis operations
- ✅ Proper error handling for AST parsing

#### 12. System Prompt Enhancements (`plancode/agent/prompts.py`)
- ✅ Updated Phase 1 (ANALYZE) to recommend new tools
- ✅ Added "Advanced Analysis Tools" section
- ✅ Guidance on when to use AST-based vs. basic tools
- ✅ Better workflow for Python projects

#### 13. Testing & Validation
- ✅ Created comprehensive test script (`test_analysis.py`)
- ✅ Validated all 3 analysis tools on plancode project
- ✅ Verified AST parsing correctness
- ✅ Confirmed project summary accuracy
- ✅ Tested dependency relationship detection

### 🚧 Week 2: Remaining Items

- [ ] Java/Spring Boot specific analysis tools
- [ ] Enhanced resume plan functionality (restore full conversation state)
- [ ] Improved plan auto-save during execution
- [ ] Better error recovery and rollback mechanisms

#### Week 3: Polish & Documentation
- [ ] Comprehensive testing suite
- [ ] Example projects and walkthroughs
- [ ] README with usage examples
- [ ] Better error messages and user guidance
- [ ] Performance optimization
- [ ] Add code analysis tool (`tools/analysis.py`)

### 📊 Status Summary

**Core Functionality:** ~90% complete
- ✅ CLI framework
- ✅ Tool definitions (15 tools total)
- ✅ Agent loop
- ✅ Approval workflow
- ✅ File operations
- ✅ Test/build/lint execution
- ✅ Advanced AST analysis for Python
- ✅ Comprehensive project analysis
- ⚠️ Resume functionality (basic implementation)
- ❌ Java/Spring Boot specific analysis

**Next Milestone:** Test the MVP with a real task!

### 🎯 Ready to Test

The core implementation is functional and ready for initial testing. To test:

```bash
# Set up environment
export ANTHROPIC_API_KEY=your_key_here

# Run PlanCode
uv run plancode "Add a simple health check endpoint" --project ./test-project

# Or analyze only
uv run plancode "Refactor authentication" --project ./my-app --analyze-only
```

### 📝 Known Limitations

1. Resume functionality is partially implemented
2. No advanced AST parsing yet (planned for Week 2)
3. Java/Spring Boot specific analysis not yet implemented
4. No cost tracking or usage monitoring
5. Limited test coverage

### 🔧 Technical Debt

- Add comprehensive unit tests
- Implement proper logging
- Add configuration file support (.plancode.yaml)
- Better handling of large codebases
- Streaming responses for better UX
- Plan diff visualization when modifying plans
