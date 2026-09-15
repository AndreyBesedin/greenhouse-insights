"""Tenancy: who can act, and on whose behalf.

A `User` is a SerraPulse identity linked to an external identity-provider
subject; an `Organization` is the tenant boundary every greenhouse belongs
to; an `OrganizationMembership` gives a user a role inside one organization.
A user may belong to many organizations with a different role in each.
Platform admin is a property of the user, not a membership role
(docs/design/authentication_authorization_plan.md, "Core model").
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

# Demo, research, simulator and WUR-backed greenhouses that no customer
# owns live in this organization, so internal resources exercise the same
# tenancy invariant as customer resources instead of bypassing it. The row
# itself is created by the migration that made ownership mandatory, so it
# exists in every database that has been upgraded to head.
SERRAPULSE_INTERNAL_ORGANIZATION_ID = "org_serrapulse_internal"
SERRAPULSE_INTERNAL_ORGANIZATION_NAME = "SerraPulse Internal"
SERRAPULSE_INTERNAL_ORGANIZATION_SLUG = "serrapulse-internal"


class OrganizationRole(StrEnum):
    """What a member may do inside one organization, smallest first.
    Each role includes everything the roles before it may do."""

    VIEWER = "VIEWER"
    EDITOR = "EDITOR"
    ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"


class Organization(BaseModel):
    organization_id: str
    name: str
    # URL/UI-friendly unique handle, e.g. "serrapulse-internal".
    slug: str
    created_at: datetime


class User(BaseModel):
    user_id: str
    # The identity provider's stable subject claim. Authorization is keyed
    # by this, never by email, which a provider may let a user change.
    auth_subject: str
    email: str
    display_name: str | None = None
    is_platform_admin: bool = False
    created_at: datetime


class OrganizationMembership(BaseModel):
    user_id: str
    organization_id: str
    role: OrganizationRole
    created_at: datetime
