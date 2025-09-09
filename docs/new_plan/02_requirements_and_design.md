# 2) Requirements and Design

Purpose: Translate the prompt into formal requirements and a technical design.

Outputs
- Requirements doc with user stories and acceptance criteria.
- Technical design with data flows, interfaces, schemas.

Requirements Structure
- Context: background and current state
- User Stories: As a <user>, I want <capability> so that <benefit>
- Acceptance Criteria: Given/When/Then scenarios per story
- Out of Scope: explicit exclusions

Design Structure
- Architecture Impact: affected layers (domain/application/infra/interfaces)
- Data Flow: sequence from input to output
- Interfaces: function signatures, DTOs, ports
- Persistence: tables/columns or files, partitioning
- Error Handling: failure modes, retries, idempotency
- Performance: target latencies and volumes
- Security: authN/Z, secrets, PII, audit

Artifacts
- templates/requirements.md (filled)
- templates/design.md (filled)

