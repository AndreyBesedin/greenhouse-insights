from sqlalchemy import Column, Float, Integer, MetaData, String, Table

metadata = MetaData()

greenhouses = Table(
    "greenhouses",
    metadata,
    Column("greenhouse_id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("description", String, nullable=False),
    Column("source_type", String, nullable=False),
    Column("layout_json", String, nullable=False),
    Column("plants_json", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("current_state_timestamp", String, nullable=True),
    Column("latest_available_timestamp", String, nullable=True),
)

simulation_definitions = Table(
    "simulation_definitions",
    metadata,
    Column("simulation_id", String, primary_key=True),
    Column("greenhouse_id", String, nullable=False, index=True),
    Column("scenario_definition", String, nullable=False),
    Column("start_date", String, nullable=False),
    Column("duration_days", Integer, nullable=False),
    Column("step_duration_seconds", Integer, nullable=False),
    Column("random_seed", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("current_step", Integer, nullable=False),
    Column("total_steps", Integer, nullable=False),
    Column("management_policy", String, nullable=False),
)

observations = Table(
    "observations",
    metadata,
    Column("observation_id", String, primary_key=True),
    Column("greenhouse_id", String, nullable=False, index=True),
    Column("plant_id", String, nullable=True, index=True),
    Column("simulated_day", Integer, nullable=False, index=True),
    Column("timestamp", String, nullable=False),
    Column("observation_type", String, nullable=False),
    Column("value", Float, nullable=False),
    Column("source_type", String, nullable=False),
)

events = Table(
    "events",
    metadata,
    Column("event_id", String, primary_key=True),
    Column("greenhouse_id", String, nullable=False, index=True),
    Column("plant_id", String, nullable=True, index=True),
    Column("simulated_day", Integer, nullable=False, index=True),
    Column("timestamp", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column("source", String, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("parameters_json", String, nullable=False),
)

greenhouse_state_snapshots = Table(
    "greenhouse_state_snapshots",
    metadata,
    Column("greenhouse_id", String, primary_key=True),
    Column("simulated_day", Integer, primary_key=True),
    Column("timestamp", String, nullable=False),
    Column("state_json", String, nullable=False),
)

greenhouse_world_snapshots = Table(
    "greenhouse_world_snapshots",
    metadata,
    Column("greenhouse_id", String, primary_key=True),
    Column("simulated_day", Integer, primary_key=True),
    Column("world_json", String, nullable=False),
)

scenario_configs = Table(
    "scenario_configs",
    metadata,
    Column("greenhouse_id", String, primary_key=True),
    Column("config_json", String, nullable=False),
)

management_traces = Table(
    "management_traces",
    metadata,
    Column("simulation_id", String, primary_key=True),
    Column("simulated_day", Integer, primary_key=True),
    Column("trace_json", String, nullable=False),
)
