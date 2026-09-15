# Infrastructure Update Plan

## Purpose

Incrementally evolve SerraPulse from a solo-developer prototype/research codebase into a production-capable system without introducing heavyweight process before it provides value.

The current development model remains intentionally lightweight: a solo developer can commit small, coherent changes directly to `main` while CI is healthy. Pull requests should become useful because they add an independent review/control layer, not because a process convention says every solo change needs a PR.

## Principles

- Keep commits small, coherent, and independently understandable.
- Keep `main` green.
- Automate checks before adding manual process.
- Security-sensitive and high-blast-radius changes deserve stronger gates than ordinary low-risk work.
- Add infrastructure in response to an actual reliability/security/deployment need.
- Prefer reversible, provider-light application boundaries where practical.

## 1. Authentication and authorization

Implement the architecture described in `docs/design/authentication_authorization_plan.md`.

Infrastructure implications:

- external identity provider;
- separate development and production credentials/configuration;
- secrets supplied by deployment environment, never committed;
- shared PostgreSQL with application-enforced tenant authorization;
- explicit actor identities for HTTP first, then workers/agents as required;
- auditability for privileged operations.

## 2. CI as the first merge gate

Before requiring PRs, CI should provide deterministic feedback on every pushed branch and on `main`.

Maintain/extend checks for:

- backend tests;
- PostgreSQL-backed tests/migrations;
- frontend tests/build;
- formatting/linting/type checks where they provide signal;
- migration upgrade/downgrade or migration-integrity checks where appropriate;
- dependency/security scanning.

Flaky CI is a production problem: fix flakes rather than normalizing retries.

## 3. Introduce an independent PR reviewer agent

### Why

A solo developer has no human reviewer. As AI-assisted coding increases, an independent reviewer can provide a useful second pass for:

- authorization bypasses;
- tenant-isolation mistakes;
- migrations and data-loss risks;
- concurrency/idempotency issues;
- missing failure handling;
- tests that validate implementation rather than behavior;
- accidental architecture-boundary erosion.

The goal is not stylistic commentary. Configure the reviewer for high-signal correctness, security, and architectural feedback.

### Candidate tools to evaluate

#### Aikido Security

Evaluate first for security posture. Aikido combines SAST, dependency/secrets/IaC scanning and AI-assisted analysis. Its free developer tier is useful for repository security scanning, but current pricing should be checked carefully: advanced PR security/code-quality review features may require a paid tier.

Useful even before paid PR review if the free tier improves SAST, dependency, secret, and IaC coverage.

#### CodeRabbit

Evaluate as a dedicated AI PR reviewer. It provides agentic PR reviews and codebase-aware feedback. For a private repository, current paid pricing should be checked before adoption; its free long-term offering is oriented toward public/open-source repositories.

#### GitHub-native / coding-agent review

Also evaluate whether the existing GitHub/coding-agent stack can provide independent PR review at lower operational cost. The important property is reviewer independence from the implementation pass, not the vendor name.

### Trial protocol

Do not immediately make the reviewer blocking.

1. Enable it on a small number of representative PRs.
2. Track useful findings versus noise/false positives.
3. Give it SerraPulse-specific review instructions, especially tenant isolation and service-layer authorization.
4. Tune or replace it if it mostly comments on style.
5. Only make checks blocking once they are reliable enough not to train us to ignore them.

### Suggested review focus

The reviewer should prioritize:

- cross-tenant data access / IDOR;
- authentication and authorization boundaries;
- direct repository calls that bypass protected application services;
- platform-admin privilege escalation;
- secrets and unsafe configuration;
- SQL/migration correctness and destructive schema changes;
- missing transaction/idempotency behavior;
- background-task failure/retry behavior;
- public API contract changes;
- insufficient tests around security boundaries.

## 4. PR policy evolution

### Now: solo development

Direct-to-`main` is acceptable for small, coherent, low-risk changes while CI remains mandatory and commits stay separable.

Prefer a PR even while solo for changes with unusually high blast radius, such as:

- authentication/authorization;
- production database migrations with destructive potential;
- deployment/network/security configuration;
- secrets/credential handling;
- large cross-cutting refactors.

The value of such a PR is to create a review checkpoint for the independent reviewer agent and a readable change set.

### Later: reliable automated reviewer

Once the reviewer proves useful, use short-lived branches + PRs for material code changes and require:

- CI green;
- automated review completed;
- high-severity findings resolved or explicitly dismissed.

Documentation-only/trivial changes can remain lighter if desired.

### Team stage

When another developer joins, revisit branch protection and require human review for appropriate changes. Do not assume today's solo workflow is the permanent policy.

## 5. Environments and deployment

As the application moves beyond local/research use, establish at least:

- local development;
- a non-production deployed environment for migrations/auth/integration tests;
- production.

Keep environment-specific configuration externalized. Production credentials must not be reused in development.

Prefer automated, reproducible deployments from known commits. Add rollback/runbook procedures before customer-critical usage makes them urgent.

## 6. Database production readiness

The shared-database tenancy model increases the importance of database discipline.

Plan for:

- PostgreSQL as the production source of truth;
- migration checks in CI;
- backups and tested restore procedure;
- connection-pool limits appropriate to deployment scaling;
- indexes driven by real tenant/resource queries;
- explicit transaction boundaries for multi-write operations;
- tenant-isolation tests for every resource family;
- monitoring for migration failures, saturation, and slow queries.

Do not use separate databases per customer without a demonstrated isolation/regulatory need.

## 7. Observability

Introduce observability around user-visible and operational failure modes rather than infrastructure metrics alone.

Minimum direction:

- structured logs with request/job correlation IDs;
- actor and organization identifiers where safe and useful (never credentials/tokens);
- error reporting;
- API latency/error metrics;
- ingestion/job success, lag, retry, and failure metrics;
- database health;
- later, traces across API/background processing when complexity warrants them.

Alerts should correspond to actionable service symptoms/SLOs rather than generic thresholds such as CPU usage alone.

## 8. Audit trail

Before platform administration and customer user management become real production operations, add an audit trail for privileged mutations such as:

- platform-admin grants/revocations;
- organization creation/configuration;
- membership/role changes;
- greenhouse ownership/configuration changes;
- security-sensitive configuration changes.

Audit records should identify actor, action, target, timestamp, and relevant before/after context without storing secrets.

## 9. Secrets and supply-chain security

- No secrets in repository or frontend bundles.
- Rotate any credential suspected of exposure.
- Enable dependency and secret scanning.
- Scan containers/IaC when those become deployment inputs.
- Pin/lock dependencies appropriately and keep automated update signal manageable.
- Give CI/deployment identities least privilege.

Aikido is one candidate for consolidating several of these checks; vendor adoption should follow a short signal/cost evaluation rather than becoming architecture.

## 10. Near-term execution order

1. Keep current CI stable and green.
2. Implement authentication/authorization with explicit security boundaries.
3. Trial Aikido's free security scanning and assess its useful signal.
4. Trial an independent AI PR reviewer on security-sensitive PRs; compare Aikido paid PR review, CodeRabbit, and available GitHub/coding-agent review options on signal and cost.
5. Introduce PR gating only after the reviewer proves useful.
6. Establish staging/production separation before real customer access.
7. Add audit logging, backups/restore verification, and operational observability before customer-critical data/actions depend on the system.

## Decision record: why not require PRs immediately?

The repository currently has one developer. A PR with no independent reviewer mostly adds ceremony around the same author approving the same work. Small commits plus CI provide more value today.

The calculus changes once a reviewer agent is installed: PRs then become the unit on which an independent system can reason about a complete change before merge. At that point, adopting PRs for material changes has a concrete control benefit rather than being process for its own sake.
