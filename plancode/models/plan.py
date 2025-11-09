"""Pydantic models for implementation plans."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PhaseStatus(str, Enum):
    """Status of a phase in the implementation plan."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Complexity(str, Enum):
    """Estimated complexity level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FileChange(BaseModel):
    """Represents a file to be created or modified."""

    path: str = Field(..., description="Relative path to the file")
    action: str = Field(..., description="Action to perform: create, modify, delete")
    description: str = Field(..., description="Brief description of changes")


class TestStrategy(BaseModel):
    """Testing strategy for a phase."""

    __test__ = False  # Tell pytest not to collect this as a test class

    test_files: list[str] = Field(default_factory=list, description="Test files to run")
    commands: list[str] = Field(default_factory=list, description="Test commands to execute")
    description: str = Field(default="", description="Testing approach description")


class Phase(BaseModel):
    """A phase in the implementation plan."""

    id: str = Field(..., description="Unique identifier for the phase")
    name: str = Field(..., description="Human-readable phase name")
    objective: str = Field(..., description="What and why for this phase")
    status: PhaseStatus = Field(default=PhaseStatus.PENDING, description="Current status")
    dependencies: list[str] = Field(
        default_factory=list, description="IDs of phases this depends on"
    )
    file_changes: list[FileChange] = Field(
        default_factory=list, description="Files to create/modify"
    )
    key_changes: list[str] = Field(default_factory=list, description="Key implementation details")
    test_strategy: TestStrategy = Field(
        default_factory=TestStrategy, description="How to test this phase"
    )
    complexity: Complexity = Field(default=Complexity.MEDIUM, description="Estimated complexity")
    started_at: Optional[datetime] = Field(default=None, description="When phase started")
    completed_at: Optional[datetime] = Field(default=None, description="When phase completed")
    error_message: Optional[str] = Field(default=None, description="Error if phase failed")


class ProjectContext(BaseModel):
    """Context about the project being modified."""

    path: str = Field(..., description="Project root path")
    language: Optional[str] = Field(default=None, description="Primary language")
    framework: Optional[str] = Field(default=None, description="Primary framework")
    tech_stack: list[str] = Field(default_factory=list, description="Technologies used")
    architecture_notes: str = Field(default="", description="Architecture observations")


class ImplementationPlan(BaseModel):
    """Complete implementation plan for a task."""

    id: str = Field(..., description="Unique plan identifier")
    task_description: str = Field(..., description="Original user task")
    created_at: datetime = Field(default_factory=datetime.now, description="Plan creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    project_context: ProjectContext = Field(..., description="Project information")
    phases: list[Phase] = Field(default_factory=list, description="Implementation phases")
    approved: bool = Field(default=False, description="Whether plan is approved by developer")
    approved_at: Optional[datetime] = Field(default=None, description="Approval timestamp")
    approval_feedback: Optional[str] = Field(
        default=None, description="Developer feedback on the plan"
    )
    overall_complexity: Complexity = Field(
        default=Complexity.MEDIUM, description="Overall task complexity"
    )

    def get_phase(self, phase_id: str) -> Optional[Phase]:
        """Get a phase by ID."""
        for phase in self.phases:
            if phase.id == phase_id:
                return phase
        return None

    def get_pending_phases(self) -> list[Phase]:
        """Get all pending phases whose dependencies are met."""
        completed_ids = {p.id for p in self.phases if p.status == PhaseStatus.COMPLETED}
        pending = []
        for phase in self.phases:
            if phase.status == PhaseStatus.PENDING:
                deps_met = all(dep in completed_ids for dep in phase.dependencies)
                if deps_met:
                    pending.append(phase)
        return pending

    def get_current_phase(self) -> Optional[Phase]:
        """Get the currently in-progress phase, if any."""
        for phase in self.phases:
            if phase.status == PhaseStatus.IN_PROGRESS:
                return phase
        return None

    def mark_phase_complete(self, phase_id: str) -> None:
        """Mark a phase as completed."""
        phase = self.get_phase(phase_id)
        if phase:
            phase.status = PhaseStatus.COMPLETED
            phase.completed_at = datetime.now()
            self.updated_at = datetime.now()

    def mark_phase_failed(self, phase_id: str, error: str) -> None:
        """Mark a phase as failed with an error message."""
        phase = self.get_phase(phase_id)
        if phase:
            phase.status = PhaseStatus.FAILED
            phase.error_message = error
            self.updated_at = datetime.now()

    def start_phase(self, phase_id: str) -> None:
        """Mark a phase as in progress."""
        phase = self.get_phase(phase_id)
        if phase:
            phase.status = PhaseStatus.IN_PROGRESS
            phase.started_at = datetime.now()
            self.updated_at = datetime.now()


class ApprovalResponse(BaseModel):
    """Response from developer approval request."""

    approved: bool = Field(..., description="Whether the plan is approved")
    feedback: Optional[str] = Field(default=None, description="Developer feedback/modifications")
