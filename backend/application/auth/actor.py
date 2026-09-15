"""Who is acting. Every entry point - HTTP, CLI, a worker, an agent -
authenticates a principal and hands application services an ActorContext;
the services then authorize each operation against the resource it
targets, however they were invoked
(docs/design/authentication_authorization_plan.md, "Security boundary").

Construction says who is acting, nothing more: permissions depend on the
resource (the same user can be an admin in one organization and a viewer
in another), so they are decided per operation by the Authorizer, not
precomputed here.
"""

from dataclasses import dataclass
from enum import StrEnum


class ActorType(StrEnum):
    USER = "USER"


@dataclass(frozen=True)
class ActorContext:
    # The local User.user_id for a USER actor - never the identity
    # provider's subject, which stays behind the authentication boundary.
    actor_id: str
    actor_type: ActorType
    is_platform_admin: bool

    @classmethod
    def user(cls, user_id: str, *, is_platform_admin: bool = False) -> "ActorContext":
        return cls(actor_id=user_id, actor_type=ActorType.USER, is_platform_admin=is_platform_admin)
