"""Turning external greenhouse data into canonical domain records.

Everything dataset-specific (archive layouts, column names, unit quirks)
stays inside an adapter package under ingestion/wur/...; what comes out is
the same Observation / Event / Greenhouse the simulator produces, so nothing
downstream needs to know where a record came from
(docs/design/wur_real_data_ingestion_replay_plan.md sections 8-10).
"""
