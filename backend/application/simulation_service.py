import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine

from application.persistence.recommendation_repository import RecommendationRepository
from application.persistence.simulation_repository import SimulationRepository
from application.recommendation_builder import build_recommendation
from domain.enums import (
    ApprovalSource,
    ManagementPolicyType,
    RecommendationStatus,
    SimulationStatus,
    SourceType,
)
from domain.management_progress import ManagementProgress
from domain.provenance import RecordSource
from domain.recommendation import Recommendation
from management.validation.actions import ActionResult, RequestedAction
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


class ManualActionNotAllowed(Exception):
    """Raised when an operator tries to act on a greenhouse before its
    simulation has ever advanced a day - there is no world snapshot yet to
    validate or execute against."""

    def __init__(self, greenhouse_id: str) -> None:
        self.greenhouse_id = greenhouse_id
        super().__init__(f"{greenhouse_id!r} has not started yet - advance a day first")


class SimulationService:
    def __init__(self, engine: Engine, *, step_delay_seconds: float = 1.0) -> None:
        self._simulations = SimulationRepository(engine)
        self._recommendations = RecommendationRepository(engine)
        self._runner = SimulationRunner(engine, step_delay_seconds=step_delay_seconds)
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._progress: dict[str, ManagementProgress] = {}
        # One lock per simulation, held for the duration of anything that
        # reads-then-writes a simulation's world/recommendations (advancing
        # a day, approving/dismissing one or all recommendations, a manual
        # action) - without it, e.g. a next-day request racing an in-flight
        # approve-all could advance the day while the approval is still
        # applying actions meant for the day just left behind.
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, simulation_id: str) -> asyncio.Lock:
        lock = self._locks.get(simulation_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[simulation_id] = lock
        return lock

    def _simulation_id_for(self, recommendation: Recommendation) -> str:
        """Every recommendation today is simulation-produced (the only
        ActionExecutorType is SIMULATED_OPERATOR), so its source.source_id
        is the execution scope to lock/act against. Recommendation itself
        no longer requires a simulation_id (PR 1) - this is where that
        assumption now lives, in one place instead of on the domain
        object."""
        simulation_id = recommendation.source.source_id
        if simulation_id is None:
            raise LookupError(
                f"recommendation {recommendation.recommendation_id!r} has no source_id"
            )
        return simulation_id

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
        async with self._lock_for(simulation_id):
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
                                update={
                                    "status": RecommendationStatus.DISMISSED,
                                    "reviewed_at": now,
                                }
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

    async def submit_manual_action(
        self, greenhouse_id: str, action: RequestedAction
    ) -> Recommendation:
        """Lets an operator act on a plant directly on the current day,
        without waiting for (or regardless of) any policy proposal. Recorded
        as a Recommendation like any other action for a consistent audit
        trail, with source_policy=NONE - reusing NONE's existing meaning of
        "no automated policy involved" rather than adding a new enum member
        - and both approved_by and (if accepted) executed_by filled in
        immediately, since there is no separate propose/approve step here.

        Raises ManualActionNotAllowed if the simulation has not started yet
        (current_step == 0, so no world snapshot exists to act against).
        """
        definition = self._simulations.get_by_greenhouse(greenhouse_id)
        if definition is None:
            raise LookupError(f"no simulation found for greenhouse {greenhouse_id!r}")
        simulation_id = definition.simulation_id
        async with self._lock_for(simulation_id):
            definition = self._simulations.get(simulation_id)
            if definition is None:
                raise LookupError(f"no simulation found for greenhouse {greenhouse_id!r}")
            if definition.current_step == 0:
                raise ManualActionNotAllowed(greenhouse_id)
            day = definition.current_step

            result = await asyncio.to_thread(
                self._runner.execute_recommendation_action, simulation_id, day, action
            )
            now = datetime.now(UTC)
            recommendation = Recommendation(
                recommendation_id=f"rec_{uuid4().hex[:10]}",
                source=RecordSource(type=SourceType.SIMULATION, source_id=simulation_id),
                greenhouse_id=greenhouse_id,
                simulated_day=day,
                plant_id=action.plant_id,
                action=action,
                source_policy=ManagementPolicyType.NONE,
                status=(
                    RecommendationStatus.EXECUTED
                    if result.accepted
                    else RecommendationStatus.REJECTED_BY_VALIDATOR
                ),
                reason="Manually requested by operator.",
                rejection_reason=None if result.accepted else result.reason,
                approved_by=ApprovalSource.HUMAN,
                executed_by=definition.action_executor if result.accepted else None,
                requested_at=now,
                reviewed_at=now,
                executed_at=now if result.accepted else None,
            )
            self._recommendations.save(recommendation)
            if result.accepted:
                await asyncio.to_thread(self._runner.refresh_day_state, simulation_id, day)
            return recommendation

    async def approve_recommendation(self, recommendation_id: str) -> Recommendation | None:
        recommendation = self._recommendations.get(recommendation_id)
        if recommendation is None:
            return None

        async with self._lock_for(self._simulation_id_for(recommendation)):
            # Re-fetch inside the lock: another operation (e.g. an
            # approve-all that was already in flight) may have reviewed
            # this recommendation while we were waiting for the lock.
            recommendation = self._recommendations.get(recommendation_id)
            if recommendation is None:
                return None
            if recommendation.status != RecommendationStatus.PENDING:
                raise RecommendationAlreadyReviewed(recommendation_id, recommendation.status)

            simulation_id = self._simulation_id_for(recommendation)
            definition = self._simulations.get(simulation_id)
            if definition is None:
                raise LookupError(f"no simulation definition found for {simulation_id!r}")

            results = await asyncio.to_thread(
                self._runner.execute_recommendation_actions,
                simulation_id,
                recommendation.simulated_day,
                [recommendation.action],
            )
            updated = self._review(recommendation, results[0], definition)
            self._recommendations.save(updated)
            await asyncio.to_thread(
                self._runner.refresh_day_state,
                simulation_id,
                recommendation.simulated_day,
            )
            return updated

    async def approve_all_pending(self, greenhouse_id: str, day: int) -> list[Recommendation]:
        """Approves and executes every PENDING recommendation for a day in
        one go (docs/design/demo_readiness_plan.md section 6: a
        presentation-layer convenience, not a new simulator primitive -
        each action is still validated and persisted individually,
        exactly like approving one at a time). Executes them as a single
        batch against the runner rather than one at a time, so the
        (potentially large) world snapshot is read and saved once instead
        of once per recommendation - approving many actions on a large
        greenhouse was previously O(pending count) world round-trips.
        """
        definition = self._simulations.get_by_greenhouse(greenhouse_id)
        if definition is None:
            raise LookupError(f"no simulation definition found for greenhouse {greenhouse_id!r}")
        simulation_id = definition.simulation_id
        async with self._lock_for(simulation_id):
            pending = self._recommendations.list_pending_for_day(greenhouse_id, day)
            if not pending:
                return []

            definition = self._simulations.get(simulation_id)
            if definition is None:
                raise LookupError(f"no simulation definition found for {simulation_id!r}")

            results = await asyncio.to_thread(
                self._runner.execute_recommendation_actions,
                simulation_id,
                day,
                [recommendation.action for recommendation in pending],
            )
            updated = []
            for recommendation, result in zip(pending, results, strict=True):
                reviewed = self._review(recommendation, result, definition)
                self._recommendations.save(reviewed)
                updated.append(reviewed)

            await asyncio.to_thread(self._runner.refresh_day_state, simulation_id, day)
            return updated

    def _review(
        self,
        recommendation: Recommendation,
        result: ActionResult,
        definition: SimulationDefinition,
    ) -> Recommendation:
        now = datetime.now(UTC)
        if result.accepted:
            return recommendation.model_copy(
                update={
                    "status": RecommendationStatus.EXECUTED,
                    "approved_by": ApprovalSource.HUMAN,
                    "executed_by": definition.action_executor,
                    "reviewed_at": now,
                    "executed_at": now,
                }
            )
        return recommendation.model_copy(
            update={
                "status": RecommendationStatus.REJECTED_BY_VALIDATOR,
                "approved_by": ApprovalSource.HUMAN,
                "rejection_reason": result.reason,
                "reviewed_at": now,
            }
        )

    async def dismiss_recommendation(self, recommendation_id: str) -> Recommendation | None:
        recommendation = self._recommendations.get(recommendation_id)
        if recommendation is None:
            return None

        async with self._lock_for(self._simulation_id_for(recommendation)):
            recommendation = self._recommendations.get(recommendation_id)
            if recommendation is None:
                return None
            if recommendation.status != RecommendationStatus.PENDING:
                raise RecommendationAlreadyReviewed(recommendation_id, recommendation.status)

            updated = recommendation.model_copy(
                update={
                    "status": RecommendationStatus.DISMISSED,
                    "reviewed_at": datetime.now(UTC),
                }
            )
            self._recommendations.save(updated)
            return updated
