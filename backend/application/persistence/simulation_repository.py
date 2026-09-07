from datetime import timedelta

from sqlalchemy import Engine, delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import RowMapping

from application.persistence.schema import simulation_definitions
from simulation.definitions import SimulationDefinition


class SimulationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, definition: SimulationDefinition) -> None:
        row = {
            "simulation_id": definition.simulation_id,
            "greenhouse_id": definition.greenhouse_id,
            "scenario_definition": definition.scenario_definition,
            "start_date": definition.start_date.isoformat(),
            "duration_days": definition.duration_days,
            "step_duration_seconds": int(definition.step_duration.total_seconds()),
            "random_seed": definition.random_seed,
            "status": definition.status.value,
            "current_step": definition.current_step,
            "total_steps": definition.total_steps,
            "management_policy": definition.management_policy.value,
            "action_executor": definition.action_executor.value,
        }
        statement = insert(simulation_definitions).values(**row)
        statement = statement.on_conflict_do_update(
            index_elements=["simulation_id"],
            set_={key: value for key, value in row.items() if key != "simulation_id"},
        )
        with self._engine.begin() as connection:
            connection.execute(statement)

    def get(self, simulation_id: str) -> SimulationDefinition | None:
        statement = select(simulation_definitions).where(
            simulation_definitions.c.simulation_id == simulation_id
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_definition(row)

    def get_by_greenhouse(self, greenhouse_id: str) -> SimulationDefinition | None:
        """The simulation run for a greenhouse, looked up rather than
        derived from the greenhouse id - a greenhouse's simulation is a
        real relationship, not a naming convention
        (docs/design/domain_model_eval_refactor_plan.md, PR 1)."""
        statement = select(simulation_definitions).where(
            simulation_definitions.c.greenhouse_id == greenhouse_id
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_definition(row)

    def delete(self, simulation_id: str) -> None:
        statement = delete(simulation_definitions).where(
            simulation_definitions.c.simulation_id == simulation_id
        )
        with self._engine.begin() as connection:
            connection.execute(statement)


def _row_to_definition(mapping: RowMapping) -> SimulationDefinition:
    return SimulationDefinition(
        simulation_id=mapping["simulation_id"],
        greenhouse_id=mapping["greenhouse_id"],
        scenario_definition=mapping["scenario_definition"],
        start_date=mapping["start_date"],
        duration_days=mapping["duration_days"],
        step_duration=timedelta(seconds=mapping["step_duration_seconds"]),
        random_seed=mapping["random_seed"],
        status=mapping["status"],
        current_step=mapping["current_step"],
        total_steps=mapping["total_steps"],
        management_policy=mapping["management_policy"],
        action_executor=mapping["action_executor"],
    )
