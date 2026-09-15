# Authentication and Authorization Plan

## Status

Design plan for introducing real authentication, multi-tenant authorization, and security-by-design application boundaries.

## Goals

- Real user login through an external identity provider.
- Shared-database multi-tenancy.
- Users may belong to more than one organization.
- Every greenhouse belongs to exactly one organization.
- Internal/demo/research greenhouses belong to an internal SerraPulse organization rather than bypassing tenancy.
- Platform administrators can access and administer everything accessible through the product.
- Customer permissions start deliberately small: viewer, editor, organization admin.
- Authorization must hold outside HTTP: CLI tools, background jobs, ingestion, agents, and future integrations must not bypass it by calling application services directly.
- Frontend authorization is UX only; the backend/application layer remains authoritative.

## Non-goals for the first version

- Per-greenhouse ACLs inside one organization.
- Generic policy languages or a configurable RBAC engine.
- Building password storage, MFA, password reset, or social login ourselves.
- Database-level row-level security as the primary authorization mechanism.
- Full machine/service-account administration in the first implementation.

## Core model

### User

A SerraPulse application identity linked to an external authentication identity.

Suggested fields:

- `id`
- `auth_subject` — stable identity-provider subject; do not key authorization by email
- `email`
- `display_name` where useful
- `is_platform_admin`
- timestamps / disabled state as needed

A user does **not** carry a single `organization_id`.

### Organization

A tenant boundary.

Suggested fields:

- `id`
- `name`
- `slug` if useful for URLs/UI
- status/timestamps as needed

Bootstrap an internal organization such as `SerraPulse Internal`. Demo, research, simulator, and WUR-backed greenhouses that are not customer-owned live here.

### OrganizationMembership

Many-to-many relation between users and organizations.

Suggested fields:

- `user_id`
- `organization_id`
- `role`

Initial roles:

| Role | Read | Operate/write | Manage organization users | Platform configuration |
| --- | --- | --- | --- | --- |
| Viewer | yes | no | no | no |
| Editor | yes | yes | no | no |
| Organization admin | yes | yes | yes | limited to own organization |
| Platform admin | all organizations | all organizations | all organizations | yes |

`Platform admin` is a platform-level capability, not an organization membership role.

### Greenhouse ownership

Every greenhouse has a mandatory `organization_id`.

Avoid nullable ownership. Internal/demo/research resources exercise the same tenancy invariant as customer resources by belonging to `SerraPulse Internal`.

## Platform administrator

Platform admin is the root/royal operational role. It can inspect and administer all product-accessible organizations and resources, including customer setup and greenhouse assignment.

Because this role has exceptional power:

- only an existing platform-level privileged flow may grant or revoke it;
- organization admins can never grant it;
- grants/revocations must be auditable;
- production should normally have very few platform admins (initially one is sufficient);
- do not encode a hard database invariant such as `count(platform_admin) <= 3`; operational controls are preferable because emergency/service identities may eventually require different treatment;
- later hardening may require explicit re-authentication, MFA, confirmation, or multi-party approval for promotion and other destructive platform-admin actions.

## Security boundary

Authentication and authorization are separate concerns.

```text
HTTP / FastAPI ─┐
CLI            ─┤
Agent/tools    ─┼─> ActorContext ─> Application services ─> Repositories ─> PostgreSQL
Workers        ─┘                        ^
                                        |
                                  authorization
```

### Authentication

The entry point authenticates a principal and establishes an `ActorContext`.

FastAPI dependency injection is appropriate for validating the HTTP credential and constructing the request actor. It is **not** the primary authorization boundary.

### ActorContext

Application services are actor-aware regardless of how they are invoked.

Illustrative shape:

```python
@dataclass(frozen=True)
class ActorContext:
    actor_id: UUID
    actor_type: ActorType
    is_platform_admin: bool
```

Possible actor types eventually include:

- `USER`
- `SERVICE`
- `AGENT`
- tightly controlled `SYSTEM`/bootstrap execution

The first implementation only needs what current use cases require, but the boundary must not assume every caller is HTTP.

### Service construction

Prefer constructing application services for an actor:

```python
service = GreenhouseService(
    actor=actor,
    greenhouse_repository=greenhouse_repository,
    membership_repository=membership_repository,
    authorizer=authorizer,
)
```

Construction establishes **who is acting**. It must not eagerly calculate all permissions because authorization is resource-dependent.

For example, the same user can be an admin in organization A and a viewer in organization B.

### Authorization in application services

Sensitive application operations authorize the actor against the target resource/action before performing the operation.

Illustrative calls:

```python
service.get_greenhouse(greenhouse_id)      # read required
service.update_greenhouse(greenhouse_id)   # write required
service.create_greenhouse(...)             # platform admin initially
```

A small `Authorizer` component may centralize the rules:

```python
authorizer.require(actor, Action.GREENHOUSE_WRITE, greenhouse)
```

Keep it explicit and boring. Do not introduce a policy DSL or external authorization framework until requirements justify it.

### Repositories

Repositories remain security-unaware persistence primitives. They retrieve and persist domain/application data; they do not decide whether an actor may access it.

Direct repository access is therefore privileged infrastructure code and should not become the normal path for product operations.

## HTTP/API behavior

FastAPI should:

1. validate the identity-provider token;
2. resolve/create the local user identity as designed;
3. construct `ActorContext`;
4. inject actor-aware application services;
5. translate authentication/authorization failures to `401`/`403`.

Do not rely on route guards alone. Calling a protected API manually must enforce exactly the same authorization as the UI.

Likely initial API additions include:

- current user / session (`GET /me`);
- organizations visible to the current actor;
- greenhouses filtered by organization access;
- membership administration for organization admins;
- platform-admin organization/customer setup endpoints.

## Frontend behavior

The frontend consumes authenticated identity and effective access from the backend.

It should provide:

- login/logout;
- authenticated application shell;
- organization selector when a user belongs to multiple organizations;
- route/page guards for UX;
- mutations hidden or disabled for viewers;
- organization administration UI for organization admins;
- platform administration UI only for platform admins.

Frontend checks are never treated as security controls.

## Agents, workers, ingestion, and CLI

Internal execution must not become an implicit authorization bypass.

An agent or worker should eventually execute with an explicit actor/service context and the minimum capabilities needed. For example, an ingestion worker may be permitted to write observations for assigned greenhouses without receiving user-management privileges.

Avoid making every internal process a platform admin merely because it runs in trusted infrastructure.

Bootstrap/migration code that must bypass ordinary product authorization should be narrow, explicit, and kept outside normal application flows.

## Identity provider boundary

Keep application authorization provider-independent:

- external provider proves identity and issues/verifies credentials;
- `auth_subject` links that identity to the local `User`;
- organizations, memberships, greenhouse ownership, and authorization live in SerraPulse;
- application services never depend on Auth0/another provider-specific user objects.

This makes a future identity-provider migration meaningful work but not an authorization rewrite.

Auth0 is the initial preferred provider if its current free tier remains sufficient. See implementation-time provider/pricing validation before committing configuration.

## Implementation sequence

### 1. Authorization domain and persistence

- Add users, organizations, memberships, roles, and migrations.
- Add mandatory greenhouse organization ownership.
- Bootstrap `SerraPulse Internal` and migrate existing non-customer greenhouses to it.
- Add explicit authorization model tests.

### 2. Real authentication

- Configure the chosen external identity provider.
- Add token validation.
- Introduce current-user/actor resolution.
- Add login/logout frontend integration.
- Do not add provider-specific authorization semantics to the domain.

### 3. Application authorization boundary

- Add `ActorContext`.
- Add the small authorizer/policy implementation.
- Make application services actor-aware.
- Protect existing read/write operations at service level.
- Keep repositories authorization-free.

### 4. Tenant-aware API

- Add `/me` and organization visibility.
- Filter/list greenhouses through authorized application services.
- Add membership administration.
- Add platform-admin organization/greenhouse setup operations.

### 5. Frontend authorization UX

- Current-user/access context.
- Organization switching.
- Viewer/editor/admin UI behavior.
- Admin pages and mutation controls.

### 6. Security and end-to-end tests

At minimum prove:

- unauthenticated requests fail with `401`;
- user A cannot read organization B by guessing identifiers;
- viewer can read but cannot mutate;
- editor can mutate but cannot administer memberships;
- organization admin can administer its organization but not another organization;
- platform admin can access all tenants;
- CLI/agent/service calls through application services enforce the same rules without FastAPI;
- frontend hiding a control is not required for backend protection.

## Open questions to resolve during implementation

- Exact identity provider and environment setup.
- Whether customer organization admins may invite users immediately or whether invitations remain platform-admin mediated initially.
- Audit-event schema and retention.
- Whether any first customer requires greenhouse-level permissions; do not build them before that requirement exists.
- Machine actor/service identity model once ingestion/agents require independent production credentials.
