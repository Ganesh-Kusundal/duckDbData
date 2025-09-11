# DDD, SOLID, and DI Audit

This document reviews the current codebase against DDD, SOLID, and Dependency Injection (DI) best practices. It highlights strengths, issues with concrete evidence, and proposes pragmatic fixes and guardrails.

## Snapshot Summary

- Strategic DDD: Amber — contexts present but boundaries leak; mixed infra in app.
- Tactical DDD: Amber/Red — repositories exist, but domain events/ACL missing, SQL in app.
- SOLID: Amber — SRP and DIP violations in scanners; factory helps OCP partially.
- DI: Red — no composition root, global event bus, hard-coded paths.
- Persistence/Queries: Amber — SQL leaks into scanners; adapters exist but duplicated.

---

## DDD Compliance

### Strategic Design
- Bounded Contexts: Partial
  - Observed contexts/folders: `src/domain`, `src/application`, `src/infrastructure`, `src/interfaces`, `analytics`, `database`.
  - Issue: Dual infra stacks (`src/infrastructure/*` vs `database/*`) indicate boundary duplication and drift.
    - Evidence: `src/infrastructure/repositories/duckdb_market_repo.py:11` imports `..adapters.duckdb_adapter`, but adapter lives at `database/adapters/duckdb_adapter.py`.
- Ubiquitous Language: Partial
  - Domain terms exist (MarketData, Scanner), but app code mixes technical infra terms.
  - Evidence: scanners directly reference DuckDB and SQL (see Tactical).
- Context Maps: Missing
  - No explicit upstream/downstream contracts or ACL documented. Recommend a short Context Map in `docs/ARCHITECTURE.md`.
- No Shared Domain Model: Partial
  - Analytics types and infra types leak into application; domain is mostly clean.

### Tactical Design
- Aggregates & Invariants: Minimal
  - Domain entities exist (`src/domain/entities/*`), but aggregate roots/invariants not explicit.
- Repositories: Present (good)
  - `src/domain/repositories/market_data_repo.py` defines a port.
  - Adapter exists but misplaced and duplicated (see Persistence).
- Domain Events: Framework present, not used consistently
  - Event bus implemented with globals (anti-pattern). No event types/handlers observed in domain.
  - Evidence: `src/infrastructure/messaging/event_bus.py:175`, `:266`.
- Anti-Corruption Layer (ACL): Missing
  - Application/strategy code imports analytics and DuckDB directly.
  - Evidence: `src/interfaces/api/routes/scanner_api.py:23` imports `duckdb` directly; scanners embed SQL.
- Application vs Domain Services: Mixed
  - `ScannerService` orchestrates, but depends directly on infra `EventBus` (no port).
  - Evidence: `src/application/services/scanner_service.py:24`.
- Factories/Policies: Partial
  - `ScannerFactory` exists, good for OCP, but injects concrete details and hard-coded paths.
  - Evidence: `src/application/infrastructure/scanner_factory.py:33`, `:52`.

### Boundaries & Persistence
- Persistence Ignorance in Domain: Green
  - Domain layer does not depend on DB.
- SQL in Application/Strategies: Red
  - Scanners hold large SQL strings and open DB connections.
  - Evidence:
    - `src/application/scanners/strategies/crp_scanner.py:269` and SQL beginning at `:276`.
    - `src/application/scanners/strategies/breakout_scanner.py:133`, `:233`.
    - `src/application/scanners/base_scanner.py:101` connects DuckDB; `:102` sets memory/threads.
- Idempotency/Versioning: Missing
  - No obvious optimistic concurrency or handler idempotency patterns.

---

## SOLID Violations

### Single Responsibility (S)
- Strategy classes mix business rules and IO/SQL.
  - Evidence: CRP/Breakout scanners construct and execute SQL and print/export CSV.
  - `crp_scanner.py` and `breakout_scanner.py` both handle formatting/printing/export.
- `BaseScanner` handles orchestration, DB connection, retries, analytics integration — too many reasons to change.
  - Evidence: `src/application/scanners/base_scanner.py:45` hard-coded DB path; `:99-102` connection and DB tuning; plus analytics imports at top.

### Open/Closed (O)
- Partially satisfied via `ScannerFactory`, but new scanners still must embed SQL or direct DB access.
  - Evidence: `src/application/infrastructure/scanner_factory.py:17-31`, `:52` shows hard-coded default DB path.

### Liskov Substitution (L)
- Risks where some strategy implementations expect DB manager attributes that don’t exist in base.
  - Evidence: `breakout_scanner.py:233` uses `self.db_manager.get_connection()` but `BaseScanner` does not define `db_manager`.

### Interface Segregation (I)
- Interfaces exist (`IBaseScanner`, runner/service interfaces), good start.
  - Evidence: `src/application/interfaces/base_scanner_interface.py`.

### Dependency Inversion (D)
- High-level modules depend on concretions.
  - `ScannerService` depends on concrete `EventBus` instead of port.
    - Evidence: `src/application/services/scanner_service.py:24`.
  - Strategies depend on DuckDB driver directly (via BaseScanner).
    - Evidence: `src/application/scanners/base_scanner.py:101`.

---

## Dependency Injection (DI)

### Composition Root & Lifetime
- No single composition root wiring dependencies; constructors and globals used instead.
  - Evidence: no `main`/startup wiring for app/services; factory carries infra concerns itself.
- Global Service Locator anti-pattern
  - `get_event_bus()` returns global bus.
  - Evidence: `src/infrastructure/messaging/event_bus.py:266`.

### Configuration & Environment
- Hard-coded paths and DB tuning in code.
  - Evidence: `src/application/scanners/base_scanner.py:45`, `:102`.
  - `src/infrastructure/core/database.py:23` default paths include local absolute directories.
- Config objects exist under `src/infrastructure/config/*` but not uniformly injected.

### Cycles & Coupling
- Cross-layer imports in multiple places (app → infra, interfaces → infra → domain ok; app → analytics direct).
- Duplicate “infra” stacks (`src/infrastructure/*` vs `database/*`) create coupling and path drift.

### Testability
- Ports exist for MarketData; fakes not observed.
- Strategies hard to unit-test in isolation due to embedded SQL and global DB connection.

---

## Persistence & Query Smells

- SQL embedded in application/strategy classes.
  - Evidence: `crp_scanner.py` and `breakout_scanner.py`.
- Interfaces expose DataFrames and concrete DB constructs instead of domain read models for read paths.
  - API routes import `duckdb` directly (leak): `src/interfaces/api/routes/scanner_api.py:23`.
- Multiple adapters/DB managers exist with inconsistent configuration and paths.
  - Evidence: `src/infrastructure/core/database.py` and `database/adapters/duckdb_adapter.py`.

---

## Anti-Patterns Observed

- Global singletons for cross-cutting concerns (EventBus).
  - Evidence: `src/infrastructure/messaging/event_bus.py:266`.
- Hard-coded absolute paths in app layer.
  - Evidence: `src/application/scanners/base_scanner.py:45`.
- Strategy code importing infra/DB directly and embedding SQL.
  - Evidence: CRP/Breakout scanners; base scanner DB connect.
- Inconsistent dependencies (attribute missing):
  - Evidence: `breakout_scanner.py:233` expects `self.db_manager` not defined in `BaseScanner`.

---

## Recommendations (Actionable)

1) Establish a Composition Root
- Create a single startup module (e.g., `src/app/startup.py`) that wires:
  - Ports: `MarketDataRepository`, `EventBusPort`, `AnalyticsPort`.
  - Adapters: `DuckDBMarketDataRepository(DuckDBAdapter)`, `RxEventBus`, analytics adapter.
  - Lifetimes: settings/config singletons, DB adapter as singleton, repositories scoped to request/run.
- Remove all `get_event_bus()` globals; inject via constructor.

2) Clean Ports and Adapters
- Keep `src/domain/repositories/market_data_repo.py` as port. Move adapter to `src/infrastructure/adapters/duckdb_adapter.py` and fix imports.
- Provide an `AnalyticsPort` in `src/domain/services` and a DuckDB/SQL-backed adapter in infra.
- Ensure app/services depend only on ports.

3) Extract SQL from Strategies
- Move scanner SQL into an `AnalyticsPort` or specialized `ScannerReadModel` adapter:
  - Example: `ScannerReadPort.top_crp_candidates(scan_date, cutoff, config) -> List[CRPCandidate]`.
- Strategies compute logic on domain/read models, not execute SQL or manage connections.

4) Fix Configuration Flow
- Replace hard-coded paths with `Settings` injected at edges.
  - Remove `BaseScanner` DB default path and connection logic.
  - Centralize DuckDB config (memory/threads) in adapter only.

5) Replace Global Event Bus
- Introduce `EventBusPort` in domain/app; provide `RxEventBusAdapter` in infra; wire in composition root.
- Remove global state and `get_event_bus()`.

6) Untangle Duplicated Infra
- Consolidate `database/*` into `src/infrastructure/*` (or vice versa) and update imports.
- Provide a migration note for old paths; add an `__init__.py` deprecation shim if necessary.

7) Strengthen Tactical DDD
- Define aggregate roots and invariants where applicable (e.g., Portfolio, StrategyRun, ScannerExecution).
- Introduce domain events for meaningful changes (e.g., `ScannerRunCompleted`).

8) Improve Testability
- Add in-memory fakes for `MarketDataRepository` and `AnalyticsPort` (return fixed DataFrames/records).
- Strategy unit tests run without DuckDB or filesystem.

---

## Evidence Index (Selected)

- App opens DB and sets tuning flags directly:
  - `src/application/scanners/base_scanner.py:45`
  - `src/application/scanners/base_scanner.py:101`
  - `src/application/scanners/base_scanner.py:102`
- Scanners embed SQL and run queries:
  - `src/application/scanners/strategies/crp_scanner.py:269`
  - `src/application/scanners/strategies/crp_scanner.py:276`
  - `src/application/scanners/strategies/breakout_scanner.py:133`
  - `src/application/scanners/strategies/breakout_scanner.py:233`
- Global event bus (service locator):
  - `src/infrastructure/messaging/event_bus.py:175`
  - `src/infrastructure/messaging/event_bus.py:266`
- API leaking DB driver:
  - `src/interfaces/api/routes/scanner_api.py:23`
- Adapter duplication/misplaced import:
  - `src/infrastructure/repositories/duckdb_market_repo.py:11`
  - `database/adapters/duckdb_adapter.py:1`

---

## Automated Guardrails (Starter Plan)

- Architecture tests (pytest):
  - Forbid imports from `src/infrastructure` or `duckdb` inside `src/domain` and `src/application/scanners/strategies/*`.
  - Enforce `src/interfaces` → `src/application` → `src/domain` (no reverse).
- Cyclic dependency detector:
  - Add `deptry` or `pydeps` in CI.
- Linters:
  - Flag files > 600 LOC and functions > 80 LOC; forbid `get_event_bus()` usage.
- Contract tests for ports:
  - Shared test suite every `MarketDataRepository` adapter must pass.
- Snapshot tests:
  - Config-driven strategy scenarios produce stable signals from fixed fixture data.

---

## Trading-Engine–Specific Spot-Checks

- Strategy code imports only domain/ports; never DuckDB/WS.
  - Action: Refactor scanners to accept `AnalyticsPort` and `MarketDataRepository` only.
- Tick/rounding rules in Execution adapter; domain uses abstract `OrderAck`.
  - N/A in current snapshot; plan for when order flow is added.
- 09:50 shortlist & LeaderScore via `AnalyticsPort`; no SQL in strategies.
- Risk guardrails in Portfolio/Risk context; not in adapters.
- Backtest vs Live parity test (same bars) yields identical signals/intents.

---

## Refactor Roadmap (90-day, incremental)

Phase 1 (Weeks 1–2): Safety and Guardrails
- Add arch tests to block new leaks (no `duckdb` import in scanners/app; forbid `get_event_bus`).
- Introduce `EventBusPort` and adapt `ScannerService` to depend on it.

Phase 2 (Weeks 3–5): Composition Root + Config
- Create `src/app/startup.py` wiring ports/adapters/settings.
- Remove hard-coded paths from `BaseScanner`; inject config/db via constructor.

Phase 3 (Weeks 6–8): Scanner Ports
- Define `AnalyticsPort`/`ScannerReadPort` with methods needed by CRP/Breakout.
- Move SQL from CRP/Breakout to an infra adapter that implements these ports.

Phase 4 (Weeks 9–12): Consolidate Infra
- Migrate `database/*` into `src/infrastructure/*`; delete duplicates.
- Update imports; add deprecation shim if needed.

---

## Optional Outputs

- One-pager printable checklist (can generate from this doc upon request).
- GitHub issue template to gate PRs (copy sections: Evidence, Fix, Arch-tests delta).
- CI “arch-tests” starter (pytest rules + deptry config) — available on request.

