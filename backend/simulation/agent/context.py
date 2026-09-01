from pydantic import BaseModel

from domain.state import PlantState


class GreenhouseManagementContext(BaseModel):
    """The observable boundary a management policy is allowed to see.

    No hidden simulator truth (GreenhouseWorld) — only reconstructed,
    production-plausible plant state, matching the agentic-management design
    doc's information boundary (docs/design/greenhouse_agentic_management_design.md, §5/§32).
    """

    greenhouse_id: str
    day: int
    plant_states: list[PlantState]

    def plant_state(self, plant_id: str) -> PlantState | None:
        return next((p for p in self.plant_states if p.plant_id == plant_id), None)
