from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel

from domain.enums import ActionExecutorType, ManagementPolicyType, SimulationStatus


class SimulationDefinition(BaseModel):
    simulation_id: str
    greenhouse_id: str
    scenario_definition: str
    start_date: date
    duration_days: int
    step_duration: timedelta = timedelta(days=1)
    random_seed: int
    status: SimulationStatus = SimulationStatus.NOT_STARTED
    current_step: int = 0
    total_steps: int
    management_policy: ManagementPolicyType = ManagementPolicyType.DETERMINISTIC
    action_executor: ActionExecutorType = ActionExecutorType.SIMULATED_OPERATOR

    def timestamp_for_step(self, step: int) -> datetime:
        """The simulation clock: the instant simulated day `step` (1-based)
        is observed. This is the only place a simulation day becomes a
        timestamp - every generic record the simulator emits (observations,
        events, state snapshots, recommendations) carries the result, never
        the day counter itself
        (docs/design/wur_real_data_ingestion_replay_plan.md section 9)."""
        start = datetime.combine(self.start_date, datetime.min.time(), tzinfo=UTC)
        return start + self.step_duration * (step - 1)

    def step_for_timestamp(self, timestamp: datetime) -> int:
        """Inverse of timestamp_for_step for timestamps the clock produced."""
        start = datetime.combine(self.start_date, datetime.min.time(), tzinfo=UTC)
        elapsed = timestamp.astimezone(UTC) - start
        step, remainder = divmod(elapsed, self.step_duration)
        if remainder or step < 0 or step >= self.total_steps:
            raise ValueError(
                f"{timestamp.isoformat()} is not a step of simulation {self.simulation_id!r}"
            )
        return step + 1
