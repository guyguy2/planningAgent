# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PlanCode is a Python CLI tool that uses Claude's API to implement a **Plan-First methodology** for software development. It analyzes codebases, creates detailed implementation plans, gets developer approval, and executes changes safely following the workflow: **Plan → Approve → Execute → Verify**.

## Development Commands

### Environment Setup
```bash
# Install dependencies with uv
uv sync

# Set up authentication (multiple options available)
uv run plancode setup  # Interactive wizard
# OR
export ANTHROPIC_API_KEY=your_key_here  # Direct env var
```

### Running PlanCode
```bash
# Basic usage
uv run plancode "Add health check endpoint" --project ./my-app

# Analyze only (no execution)
uv run plancode "Refactor user service" --analyze-only

# Resume from saved plan
uv run plancode --resume .plancode/plans/plan_abc123.json

# Initialize a project
uv run plancode init
```

### Development Tools
```bash
# Code formatting
black plancode/
ruff check plancode/

# Type checking
mypy plancode/

# Run tests (when implemented)
pytest
pytest --cov=plancode
```

## Architecture Overview

### Core Design: Agent-Based Tool-Use Pattern

PlanCode is built around Claude's tool-use API with a sophisticated agent loop that enforces the Plan-First methodology. The system provides Claude with 12 specialized tools for analysis, planning, and execution.

### Critical Architectural Components

#### 1. Agent Loop (`plancode/agent/loop.py`)
- Main execution engine that orchestrates Claude's tool calls
- Implements conversation loop with tool result handling
- Manages project context and tool execution dispatch
- Tool definitions specify exact schemas for Claude's API

#### 2. System Prompts (`plancode/agent/prompts.py`)
The system prompt is the most critical component - it **enforces the mandatory workflow**:
- **Phase 1: ANALYZE** - Must explore codebase before planning
- **Phase 2: PLAN** - Create detailed, specific implementation plans
- **Phase 3: APPROVE** - MUST call `ask_developer_for_approval()` before any code changes
- **Phase 4: EXECUTE** - Implement approved changes phase-by-phase
- **Phase 5: VERIFY** - Run tests, builds, linters

The prompt is dynamically built with project context (language, framework, tech stack).

#### 3. Tools Architecture (`plancode/tools/`)

**Filesystem Tools** (`filesystem.py`):
- `list_project_structure()` - Tree view with language detection
- `read_file()` - File reading with .gitignore awareness
- `search_code()` - Regex search with context lines
- `find_definitions()` - Locate class/function definitions
- `get_file_imports()` - Extract imports (Python, JS, Java)
- `write_file()` - Write with automatic backups

**Workflow Tools** (`workflow.py`):
- `ask_developer_for_approval()` - **Critical human-in-the-loop approval mechanism**
- `save_plan()` / `load_plan()` - JSON/YAML plan persistence
- `update_plan_step()` - Modify plan phases
- `auto_save_plan()` - Continuous progress saving

**Execution Tools** (`execution.py`):
- `run_command()` - Shell command execution
- `run_tests()` - Auto-detect test framework (pytest, jest, maven, gradle)
- `verify_build()` - Auto-detect build system
- `run_linter()` - Auto-detect linter (ruff, black, eslint, mypy)

#### 4. Data Models (`plancode/models/plan.py`)

Pydantic models that structure the entire planning system:
- `ImplementationPlan` - Complete plan with phases and metadata
- `Phase` - Individual work unit with objectives, file changes, test strategy
- `PhaseStatus` - Enum: PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
- `FileChange` - Tracks create/modify/delete operations
- `TestStrategy` - Testing approach for each phase
- `ProjectContext` - Project metadata (language, framework, tech stack)
- `ApprovalResponse` - Developer approval with optional feedback

#### 5. Rich UI (`plancode/ui/display.py`)

Beautiful terminal interface using Rich library:
- `display_plan()` - Visual plan representation with status indicators
- `display_phase()` - Detailed phase information
- `display_progress()` - Progress tracking across phases
- `display_project_structure()` - Tree visualization
- `display_code()` - Syntax-highlighted code display

### Key Design Patterns

1. **Human-in-the-Loop Enforcement**: The system prompt and tool architecture ensure Claude CANNOT skip the approval step. `ask_developer_for_approval()` is called before ANY file modifications.

2. **Stateful Conversation with Tools**: The agent loop maintains conversation state and executes tool calls synchronously, allowing Claude to iteratively explore, plan, and execute.

3. **Project-Aware Analysis**: The system analyzes the project upfront to build `ProjectContext`, which is injected into the system prompt for context-aware planning.

4. **Auto-Detection Pattern**: Execution tools (tests, builds, linters) automatically detect the appropriate framework/tooling rather than requiring configuration.

5. **Backup-First Safety**: `write_file()` creates automatic backups before modifications, enabling rollback if needed.

## Project Structure

```
plancode/
├── cli/
│   └── main.py              # Typer CLI entry point, commands: plan, init, setup, version
├── agent/
│   ├── loop.py              # Agent execution loop, tool definitions, tool dispatcher
│   └── prompts.py           # System prompt templates (enforces methodology)
├── auth.py                  # Flexible authentication with multiple sources
├── tools/
│   ├── filesystem.py        # File operations and codebase analysis
│   ├── workflow.py          # Approval and plan management
│   └── execution.py         # Command execution, tests, builds, linters
├── models/
│   └── plan.py              # Pydantic models for plans, phases, context
├── ui/
│   └── display.py           # Rich terminal UI components
└── tests/
    └── __init__.py          # (Tests to be implemented)
```

## Implementation Guidelines

### When Working on the Agent Loop
- Tool definitions MUST match Anthropic's tool-use API schema exactly
- Tool execution dispatcher in `execute_tool()` maps tool names to function calls
- Always maintain conversation history (messages list) correctly
- Handle both text and tool_use content blocks in responses

### When Modifying Tools
- Each tool function receives `project_path: Path` as context
- Tools return dictionaries that become tool results in the conversation
- Error handling should return structured error info, not raise exceptions
- Tools are .gitignore-aware (use `is_ignored()` helper)

### When Updating System Prompts
- The prompt enforces the MANDATORY workflow - do not relax requirements
- Project context is injected dynamically - use `ProjectContext` model
- Different prompts for different modes: analysis-only, resume, standard execution
- Be specific about what Claude MUST do vs. what is optional

### When Adding New Features
- Follow the existing tool pattern: define schema, implement function, register in loop
- Update `create_tool_definitions()` in `agent/loop.py`
- Add corresponding UI display functions in `ui/display.py`
- Update Pydantic models if new data structures are needed

### Code Style
- Line length: 100 characters (configured in pyproject.toml)
- Python >= 3.10 (uses modern type hints)
- Format with: `black plancode/`
- Lint with: `ruff check plancode/`
- Type checking is enabled but `disallow_untyped_defs = false` (permissive)

## Current Status

**Week 1 (Core Foundation): COMPLETE**
- CLI framework with Typer
- All 12 tool definitions and implementations
- Agent loop with tool execution
- Approval workflow with Rich UI
- File operations with backups
- Test/build/lint auto-detection

**Week 2 (Analysis & Persistence): IN PROGRESS**
- Advanced AST parsing (Python) - NOT YET IMPLEMENTED
- Java/Spring Boot analysis tools - NOT YET IMPLEMENTED
- Enhanced resume functionality - PARTIALLY IMPLEMENTED
- Plan auto-save during execution - BASIC IMPLEMENTATION

**Week 3 (Polish): PLANNED**
- Comprehensive test suite
- Example projects and walkthroughs
- Performance optimization

## Authentication Architecture

PlanCode implements flexible authentication through `plancode/auth.py`:

### Authentication Sources (Priority Order)
1. **ANTHROPIC_API_KEY** environment variable (most secure)
2. **ANTHROPIC_API_KEY_FILE** environment variable (points to file with key)
3. **Claude Code environment detection** (no key needed when running in Claude Code)
4. **.plancode/api_key** file in project directory (less secure, for testing)
5. **Interactive prompt** (optional, not saved)

### Key Functions
- `get_api_key()` - Main function that tries all sources in order
- `is_running_in_claude_code()` - Detects Claude Code environment
- `setup_api_key_interactive()` - Interactive setup wizard
- `validate_api_key()` - Validates key format

### CLI Integration
- `plancode setup` - Interactive authentication setup wizard
- API key passed through to `run_planning_agent()` and `resume_plan()`
- Helpful error messages guide users when authentication fails

## Configuration Files

- `pyproject.toml` - Project metadata, dependencies, tool configuration
- `.plancode/` - Created by `plancode init`, stores saved plans (git-ignored)
- `.plancode/api_key` - Optional project-specific API key (if using that auth method)

## Known Limitations

1. Resume functionality is basic - doesn't fully restore conversation state
2. No AST-based analysis yet (searches are regex-based)
3. Java/Spring Boot specific analysis tools planned but not implemented
4. Limited test coverage
5. No cost tracking or usage monitoring
6. No configuration file support (.plancode.yaml) yet
