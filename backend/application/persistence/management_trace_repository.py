from sqlalchemy import Engine, delete, select

from application.persistence.schema import management_traces
from application.persistence.upsert import upsert
from domain.management_trace import ManagementTrace


class ManagementTraceRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, trace: ManagementTrace) -> None:
        row = {
            "simulation_id": trace.simulation_id,
            "simulated_day": trace.simulated_day,
            "trace_json": trace.model_dump_json(),
        }
        with self._engine.begin() as connection:
            upsert(connection, management_traces, row, key=("simulation_id", "simulated_day"))

    def list_for_simulation(self, simulation_id: str) -> list[ManagementTrace]:
        statement = (
            select(management_traces.c.trace_json)
            .where(management_traces.c.simulation_id == simulation_id)
            .order_by(management_traces.c.simulated_day)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).scalars().all()
        return [ManagementTrace.model_validate_json(trace_json) for trace_json in rows]

    def delete_for_simulation(self, simulation_id: str) -> None:
        statement = delete(management_traces).where(
            management_traces.c.simulation_id == simulation_id
        )
        with self._engine.begin() as connection:
            connection.execute(statement)
