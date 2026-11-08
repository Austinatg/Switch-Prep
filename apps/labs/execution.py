from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SparkExecutionRequest:
    exercise_slug: str
    source_code: str
    sample_data: dict[str, Any]


@dataclass(frozen=True)
class SparkExecutionResult:
    status: str
    output: str
    execution_id: str | None = None


class SparkExecutionAdapter(Protocol):
    """Interface for a separately deployed, trusted Spark execution service."""

    def execute(self, request: SparkExecutionRequest) -> SparkExecutionResult:
        """Submit one exercise to a configured external Spark runtime."""
        ...


class SparkRuntimeUnavailable(RuntimeError):
    pass


class UnconfiguredSparkAdapter:
    """Explicit no-runtime adapter; it never evaluates learner code."""

    def execute(self, request: SparkExecutionRequest) -> SparkExecutionResult:
        raise SparkRuntimeUnavailable(
            "Real PySpark execution is not configured. Run this exercise in a local Spark environment."
        )
