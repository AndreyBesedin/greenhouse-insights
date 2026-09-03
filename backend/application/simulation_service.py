import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine

from application.persistence.recommendation_repository import RecommendationRepository
from application.persistence.simulation_repository import SimulationRepository
from application.recommendation_builder import build_recommendation
from domain.enums import ApprovalSource, RecommendationStatus, SimulationStatus
from domain.management_progress import ManagementProgress
from domain.recommendation import Recommendation
from simulation.definitions import SimulationDefinition
from simulation.runner import SimulationRunner


class PendingRecommendationsExist(Exception):
    """Raised by advance_one_day when the current day still has PENDING
    recommendations and the caller did not pass confirm_dismiss_remaining -
    docs/design/demo_readiness_plan.md section 12: never silently lose an
    agent suggestion by advancing past it."""

    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(f"{count} pending recommendation(s) must be reviewed before advancing")


class RecommendationAlreadyReviewed(Exception):
    """Raised when approving/dismissing a recommendation that is not
    PENDING - repeated review must be rejected safely, not silently
    re-applied (docs/design/demo_readiness_plan.md section 23)."""

    def __init__(self, recommendation_id: str, status: RecommendationStatus) -> None:
        self.recommendation_id = recommendation_id
        self.status = status
        super().__init__(f"recommendation {recommendation_id!r} is already {status.value}")


class SimulationService:
    def __init__(self, engine: Engine, *, step_delay_seconds: float = 1.0) -> None:
        self._simulations = SimulationRepository(engine)
        self._recommendations = RecommendationRepository(engine)
        self._runner = SimulationRunner(engine, step_delay_seconds=step_delay_seconds)
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._progress: dict[str, ManagementProgress] = {}

    async def start_simulation(self, simulation_id: str) -> SimulationDefinition | None:
        definition = self._simulations.get(simulation_id)
        if definition is None or definition.status == SimulationStatus.COMPLETED:
            return definition

        if not self.is_running(simulation_id):
            self._tasks[simulation_id] = asyncio.create_task(
                self._runner.run_to_completion(simulation_id)
            )
        return definition

    def get_status(self, simulation_id: str) -> SimulationDefinition | None:
        return self._simulations.get(simulation_id)

    def is_running(self, simulation_id: str) -> bool:
        task = self._tasks.get(simulation_id)
        return task is not None and not task.done()

    def cancel(self, simulation_id: str) -> None:
        task = self._tasks.pop(simulation_id, None)
        if task is not None and not task.done():
            task.cancel()

    async def advance_one_day(
        self, simulation_id: str, *, confirm_dismiss_remaining: bool = False
    ) -> SimulationDefinition | None:
        """Advances exactly one simulated day: evolves the world and asks
        the management policy what it would propose, persisting those
        proposals as PENDING recommendations, then stops - the manual,
        human-in-the-loop counterpart to start_simulation's auto-run-to-
        completion. Returns the definition unchanged (a no-op) if the
        simulation does not exist, is already completed, or is currently
        auto-running via start_simulation.

        Raises PendingRecommendationsExist if the current day still has
        unreviewed recommendations and confirm_dismiss_remaining is False;
        pass True to dismiss them and proceed.
        """
        definition = self._simulations.get(simulation_id)
        if definition is None or definition.status == SimulationStatus.COMPLETED:
            return definition
        if self.is_running(simulation_id):
            return definition

        next_day = definition.current_step + 1
        if next_day > definition.total_steps:
            return definition

        if definition.current_step > 0:
            pending = self._recommendations.list_pending_for_day(
                definition.greenhouse_id, definition.current_step
            )
            if pending:
                if not confirm_dismiss_remaining:
                    raise PendingRecommendationsExist(len(pending))
                now = datetime.now(UTC)
                for recommendation in pending:
                    self._recommendations.save(
                        recommendation.model_copy(
                            update={"status": RecommendationStatus.DISMISSED, "reviewed_at": now}
                        )
                    )

        await asyncio.to_thread(self._propose_day, simulation_id, next_day)
        return self._simulations.get(simulation_id)

    def _propose_day(self, simulation_id: str, day: int) -> None:
        try:
            proposal = self._runner.prepare_day(
                simulation_id, day, progress_reporter=self._report_progress(simulation_id)
            )
            requested_at = datetime.now(UTC)
            for action in proposal.proposed_actions:
                recommendation = build_recommendation(
                    proposal,
                    action,
                    recommendation_id=f"rec_{uuid4().hex[:10]}",
                    requested_at=requested_at,
                )
                self._recommendations.save(recommendation)
        finally:
            self._progress.pop(simulation_id, None)

    def _report_progress(self, simulation_id: str) -> Callable[[ManagementProgress], None]:
        def report(progress: ManagementProgress) -> None:
            self._progress[simulation_id] = progress

        return report

    def get_management_progress(self, simulation_id: str) -> ManagementProgress | None:
        """The latest high-level progress for an in-flight agentic day
        analysis, or None if nothing is currently in progress for this
        simulation - polled by the frontend while a next-day request is
        outstanding (section 14)."""
        return self._progress.get(simulation_id)

    def list_recommendations(self, greenhouse_id: str, day: int) -> list[Recommendation]:
        return self._recommendations.list_for_day(greenhouse_id, day)

    async def approve_recommendation(self, recommendation_id: str) -> Recommendation | None:
        recommendation = self._recommendations.get(recommendation_id)
        if recommendation is None:
            return None
        if recommendation.status != RecommendationStatus.PENDING:
            raise RecommendationAlreadyReviewed(recommendation_id, recommendation.status)

        definition = self._simulations.get(recommendation.simulation_id)
        if definition is None:
            raise LookupError(
                f"no simulation definition found for {recommendation.simulation_id!r}"
            )

        result = await asyncio.to_thread(
            self._runner.execute_recommendation_action,
            recommendation.simulation_id,
            recommendation.simulated_day,
            recommendation.action,
        )
        now = datetime.now(UTC)
        if result.accepted:
            updated = recommendation.model_copy(
                update={
                    "status": RecommendationStatus.EXECUTED,
                    "approved_by": ApprovalSource.HUMAN,
                    "executed_by": definition.action_executor,
                    "reviewed_at": now,
                    "executed_at": now,
                }
            )
        else:
            updated = recommendation.model_copy(
                update={
                    "status": RecommendationStatus.REJECTED_BY_VALIDATOR,
                    "approved_by": ApprovalSource.HUMAN,
                    "rejection_reason": result.reason,
                    "reviewed_at": now,
                }
            )
        self._recommendations.save(updated)
        await asyncio.to_thread(
            self._runner.refresh_day_state,
            recommendation.simulation_id,
            recommendation.simulated_day,
        )
        return updated

    async def dismiss_recommendation(self, recommendation_id: str) -> Recommendation | None:
        recommendation = self._recommendations.get(recommendation_id)
        if recommendation is None:
            return None
        if recommendation.status != RecommendationStatus.PENDING:
            raise RecommendationAlreadyReviewed(recommendation_id, recommendation.status)

        updated = recommendation.model_copy(
            update={"status": RecommendationStatus.DISMISSED, "reviewed_at": datetime.now(UTC)}
        )
        self._recommendations.save(updated)
        return updated
