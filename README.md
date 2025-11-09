# PlanCode

> AI-Powered Code Planning & Implementation Tool

PlanCode is a Python CLI tool that uses Claude's API to implement a **Plan-First methodology** for software development. It analyzes your codebase, creates detailed implementation plans, gets your approval, and executes changes safely.

## Core Philosophy

**Plan → Approve → Execute → Verify**

Never write code before creating and approving a detailed plan. This ensures thoughtful architecture, minimal changes, and clear communication.

## Features

- 🤖 **AI-Powered Planning**: Claude analyzes your codebase and creates detailed implementation plans
- ✅ **Human-in-the-Loop**: Get approval before any code is written
- 🎯 **Smart Analysis**: Understands project structure, languages, and frameworks
- 💾 **Plan Persistence**: Save and resume plans across sessions
- 🎨 **Beautiful UI**: Rich terminal output with progress tracking
- 🔒 **Safety First**: Automatic backups, test verification, build checks

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd planningAgent

# Install with uv
uv sync

# Set up authentication (see Authentication section below)
uv run plancode setup
```

## Quick Start

```bash
# Basic usage
uv run plancode "Add health check endpoint" --project ./my-app

# Analyze only (create plan without executing)
uv run plancode "Refactor user service" --analyze-only

# Resume from saved plan
uv run plancode --resume .plancode/plans/plan_abc123.json

# Initialize a project
uv run plancode init
```

## How It Works

### 1. Analysis Phase
PlanCode analyzes your codebase to understand:
- Project structure and organization
- Programming languages and frameworks
- Existing code patterns and dependencies
- Relevant files and components

### 2. Planning Phase
Claude creates a detailed implementation plan including:
- Clear objectives for each phase
- Specific files to modify
- Key implementation details
- Testing strategies
- Complexity estimates

### 3. Approval Phase
You review the plan and either:
- ✅ Approve it to proceed
- ❌ Reject with feedback for revision
- ✏️ Request modifications

### 4. Execution Phase
After approval, PlanCode:
- Implements changes phase by phase
- Creates automatic backups
- Saves progress continuously
- Communicates each step clearly

### 5. Verification Phase
Finally, PlanCode verifies the implementation:
- Runs test suite
- Checks build status
- Runs linters
- Reports results

## Example Session

```bash
$ uv run plancode "Add a /health endpoint to the API" --project ./my-api

PlanCode
AI-Powered Code Planning & Implementation

Task: Add a /health endpoint to the API
Project: /Users/me/my-api
Model: claude-sonnet-4-5-20250929
Mode: Plan & Execute

ℹ Analyzing project structure...

Project Structure
my-api/
├── src/
│   ├── routes/
│   ├── models/
│   └── app.py
└── tests/

Files: 15
Directories: 5
Languages: Python (12)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Approval Required
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add Health Check Endpoint
Complexity: LOW

Plan Summary:
Add a simple /health endpoint that returns service status
and basic metadata (version, uptime, dependencies).

Files to Modify:
  • create   src/routes/health.py
  • modify   src/app.py

Approve this plan? [Y/n]: y

✓ Wrote src/routes/health.py
✓ Wrote src/app.py
✓ Tests passed!
✓ Build successful!

Task completed!
```

## Available Tools

PlanCode provides Claude with these tools:

### Analysis Tools
- `list_project_structure` - Get project directory tree
- `read_file` - Read file contents
- `search_code` - Search for patterns in code
- `find_definitions` - Find class/function definitions
- `get_file_imports` - Extract import statements

### Planning & Workflow Tools
- `ask_developer_for_approval` - Get approval before coding
- `save_plan` / `load_plan` - Plan persistence

### Execution Tools
- `write_file` - Create or modify files with backups
- `run_command` - Execute shell commands
- `run_tests` - Run test suite (auto-detects framework)
- `verify_build` - Check build status
- `run_linter` - Run code quality checks

## Configuration

### Authentication

PlanCode supports flexible authentication with multiple options:

#### Option 1: Environment Variable (Recommended)
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
# Add to ~/.bashrc or ~/.zshrc to persist
```

#### Option 2: API Key File
```bash
echo 'your-api-key-here' > ~/.anthropic_key
chmod 600 ~/.anthropic_key  # Secure the file
export ANTHROPIC_API_KEY_FILE=~/.anthropic_key
```

#### Option 3: Interactive Setup
```bash
uv run plancode setup
# Follow the interactive wizard to configure authentication
```

#### Option 4: Use Within Claude Code (No API Key Needed)

When running PlanCode from within a Claude Code session, no separate API key is required. PlanCode automatically detects the Claude Code environment and uses the existing session.

**How to use:**

1. Start a Claude Code session (at [claude.ai/code](https://claude.ai/code))
2. Clone or navigate to your PlanCode installation:
   ```bash
   git clone <repository-url>
   cd planningAgent
   uv sync
   ```
3. Run PlanCode commands directly:
   ```bash
   uv run plancode "Add health check endpoint" --project ./my-app
   ```

**Benefits:**
- ✅ No API key configuration needed
- ✅ Uses your existing Claude Code subscription
- ✅ Seamless integration with Claude's environment
- ✅ Perfect for testing and development

PlanCode will detect environment variables like `CLAUDE_CODE_SESSION`, `ANTHROPIC_SESSION_ID`, or `CLAUDE_AGENT_MODE` to determine it's running in Claude Code.

#### Option 5: Project-Specific Key (Less Secure)
```bash
# Not recommended for production
echo 'your-api-key-here' > .plancode/api_key
chmod 600 .plancode/api_key
```

**Get your API key**: Visit [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

### Project Initialization
Run `uv run plancode init` in your project to create:
- `.plancode/` directory for storing plans
- `.gitignore` entry for `.plancode/`

## Architecture

```
plancode/
├── cli/          # Typer CLI entry point
├── agent/        # Agent loop and prompts
├── tools/        # Analysis, workflow, and execution tools
├── models/       # Pydantic data models
└── ui/           # Rich terminal UI
```

## Development Status

✅ **Week 1: Core Foundation** - COMPLETE
- CLI framework
- Tool definitions
- Agent loop
- Approval workflow
- File operations
- Test/build/lint execution

🚧 **Week 2: Analysis & Persistence** - IN PROGRESS
- Advanced AST parsing
- Java/Spring Boot analysis
- Enhanced resume functionality

📋 **Week 3: Polish & Documentation** - PLANNED
- Comprehensive testing
- Examples and tutorials
- Performance optimization

See [PLAN.md](PLAN.md) for detailed implementation progress.

## Contributing

Contributions are welcome! This project follows the Plan-First methodology for all changes.

## License

MIT

## Credits

Built with:
- [Anthropic Claude](https://www.anthropic.com/) - AI planning and code generation
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [Pydantic](https://docs.pydantic.dev/) - Data validation
