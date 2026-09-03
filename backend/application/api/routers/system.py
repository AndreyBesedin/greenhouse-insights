from fastapi import APIRouter

from management.agent.provider import AgentProviderStatus, describe_agent_provider

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/agent-provider")
def get_agent_provider() -> AgentProviderStatus:
    return describe_agent_provider()
