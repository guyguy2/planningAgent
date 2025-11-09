"""Tests for Pydantic models."""

from datetime import datetime

import pytest

from plancode.models.plan import (
    ApprovalResponse,
    Complexity,
    FileChange,
    ImplementationPlan,
    Phase,
    PhaseStatus,
    ProjectContext,
    TestStrategy,
)


def test_phase_status_enum():
    """Test PhaseStatus enum values."""
    assert PhaseStatus.PENDING == "pending"
    assert PhaseStatus.IN_PROGRESS == "in_progress"
    assert PhaseStatus.COMPLETED == "completed"
    assert PhaseStatus.FAILED == "failed"
    assert PhaseStatus.SKIPPED == "skipped"


def test_complexity_enum():
    """Test Complexity enum values."""
    assert Complexity.LOW == "low"
    assert Complexity.MEDIUM == "medium"
    assert Complexity.HIGH == "high"


def test_file_change_creation():
    """Test FileChange model creation."""
    change = FileChange(
        path="src/main.py", action="modify", description="Add health check endpoint"
    )
    assert change.path == "src/main.py"
    assert change.action == "modify"
    assert change.description == "Add health check endpoint"


def test_test_strategy_defaults():
    """Test TestStrategy with default values."""
    strategy = TestStrategy()
    assert strategy.test_files == []
    assert strategy.commands == []
    assert strategy.description == ""


def test_test_strategy_with_values():
    """Test TestStrategy with custom values."""
    strategy = TestStrategy(
        test_files=["test_main.py"], commands=["pytest test_main.py"], description="Run unit tests"
    )
    assert len(strategy.test_files) == 1
    assert len(strategy.commands) == 1
    assert strategy.description == "Run unit tests"


def test_phase_creation():
    """Test Phase model creation."""
    phase = Phase(
        id="phase-1",
        name="Setup Database",
        objective="Initialize database schema",
    )
    assert phase.id == "phase-1"
    assert phase.name == "Setup Database"
    assert phase.objective == "Initialize database schema"
    assert phase.status == PhaseStatus.PENDING
    assert phase.dependencies == []
    assert phase.file_changes == []
    assert phase.complexity == Complexity.MEDIUM


def test_phase_with_dependencies():
    """Test Phase with dependencies."""
    phase = Phase(
        id="phase-2",
        name="Add API Routes",
        objective="Create REST endpoints",
        dependencies=["phase-1"],
        complexity=Complexity.HIGH,
    )
    assert phase.dependencies == ["phase-1"]
    assert phase.complexity == Complexity.HIGH


def test_project_context():
    """Test ProjectContext model."""
    context = ProjectContext(
        path="/home/user/project",
        language="Python",
        framework="FastAPI",
        tech_stack=["PostgreSQL", "Redis"],
        architecture_notes="Microservices architecture",
    )
    assert context.path == "/home/user/project"
    assert context.language == "Python"
    assert context.framework == "FastAPI"
    assert len(context.tech_stack) == 2
    assert "PostgreSQL" in context.tech_stack


def test_implementation_plan_creation():
    """Test ImplementationPlan model creation."""
    context = ProjectContext(path="/test/project")
    plan = ImplementationPlan(
        id="plan-123", task_description="Add user authentication", project_context=context
    )
    assert plan.id == "plan-123"
    assert plan.task_description == "Add user authentication"
    assert plan.approved is False
    assert plan.phases == []
    assert plan.overall_complexity == Complexity.MEDIUM


def test_implementation_plan_get_phase():
    """Test getting a phase by ID."""
    context = ProjectContext(path="/test/project")
    plan = ImplementationPlan(
        id="plan-123",
        task_description="Test task",
        project_context=context,
        phases=[
            Phase(id="phase-1", name="Phase 1", objective="Do something"),
            Phase(id="phase-2", name="Phase 2", objective="Do something else"),
        ],
    )

    phase = plan.get_phase("phase-1")
    assert phase is not None
    assert phase.id == "phase-1"

    missing = plan.get_phase("phase-99")
    assert missing is None


def test_implementation_plan_get_pending_phases():
    """Test getting pending phases with met dependencies."""
    context = ProjectContext(path="/test/project")
    plan = ImplementationPlan(
        id="plan-123",
        task_description="Test task",
        project_context=context,
        phases=[
            Phase(id="phase-1", name="Phase 1", objective="First", status=PhaseStatus.COMPLETED),
            Phase(id="phase-2", name="Phase 2", objective="Second", dependencies=["phase-1"]),
            Phase(id="phase-3", name="Phase 3", objective="Third", dependencies=["phase-2"]),
        ],
    )

    pending = plan.get_pending_phases()
    assert len(pending) == 1
    assert pending[0].id == "phase-2"


def test_implementation_plan_get_current_phase():
    """Test getting the current in-progress phase."""
    context = ProjectContext(path="/test/project")
    plan = ImplementationPlan(
        id="plan-123",
        task_description="Test task",
        project_context=context,
        phases=[
            Phase(id="phase-1", name="Phase 1", objective="First", status=PhaseStatus.COMPLETED),
            Phase(id="phase-2", name="Phase 2", objective="Second", status=PhaseStatus.IN_PROGRESS),
            Phase(id="phase-3", name="Phase 3", objective="Third"),
        ],
    )

    current = plan.get_current_phase()
    assert current is not None
    assert current.id == "phase-2"
    assert current.status == PhaseStatus.IN_PROGRESS


def test_implementation_plan_mark_phase_complete():
    """Test marking a phase as completed."""
    context = ProjectContext(path="/test/project")
    plan = ImplementationPlan(
        id="plan-123",
        task_description="Test task",
        project_context=context,
        phases=[
            Phase(id="phase-1", name="Phase 1", objective="First"),
        ],
    )

    plan.mark_phase_complete("phase-1")
    phase = plan.get_phase("phase-1")
    assert phase.status == PhaseStatus.COMPLETED
    assert phase.completed_at is not None


def test_implementation_plan_mark_phase_failed():
    """Test marking a phase as failed."""
    context = ProjectContext(path="/test/project")
    plan = ImplementationPlan(
        id="plan-123",
        task_description="Test task",
        project_context=context,
        phases=[
            Phase(id="phase-1", name="Phase 1", objective="First"),
        ],
    )

    plan.mark_phase_failed("phase-1", "Database connection failed")
    phase = plan.get_phase("phase-1")
    assert phase.status == PhaseStatus.FAILED
    assert phase.error_message == "Database connection failed"


def test_implementation_plan_start_phase():
    """Test starting a phase."""
    context = ProjectContext(path="/test/project")
    plan = ImplementationPlan(
        id="plan-123",
        task_description="Test task",
        project_context=context,
        phases=[
            Phase(id="phase-1", name="Phase 1", objective="First"),
        ],
    )

    plan.start_phase("phase-1")
    phase = plan.get_phase("phase-1")
    assert phase.status == PhaseStatus.IN_PROGRESS
    assert phase.started_at is not None


def test_approval_response():
    """Test ApprovalResponse model."""
    response = ApprovalResponse(approved=True, feedback="Looks good, but add more tests")
    assert response.approved is True
    assert response.feedback == "Looks good, but add more tests"

    rejection = ApprovalResponse(approved=False)
    assert rejection.approved is False
    assert rejection.feedback is None
