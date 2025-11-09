#!/usr/bin/env bash
# run.sh - Convenient wrapper to run plancode using uv

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if ANTHROPIC_API_KEY is set (warn if not)
if [ -z "$ANTHROPIC_API_KEY" ]; then
    print_warning "ANTHROPIC_API_KEY environment variable is not set"
    print_info "Set it with: export ANTHROPIC_API_KEY=your_key_here"
fi

# If no arguments provided, show help
if [ $# -eq 0 ]; then
    print_info "Running plancode with --help"
    uv run plancode --help
    exit 0
fi

# Special commands
case "$1" in
    test)
        print_info "Running tests with pytest"
        shift  # Remove 'test' from arguments
        uv run pytest "$@"
        exit 0
        ;;
    format)
        print_info "Formatting code with black"
        uv run black plancode/
        exit 0
        ;;
    lint)
        print_info "Linting code with ruff"
        uv run ruff check plancode/
        exit 0
        ;;
    typecheck)
        print_info "Type checking with mypy"
        uv run mypy plancode/
        exit 0
        ;;
    sync)
        print_info "Syncing dependencies with uv"
        uv sync
        exit 0
        ;;
    *)
        # Pass all arguments to plancode
        print_info "Running: uv run plancode $*"
        uv run plancode "$@"
        ;;
esac
