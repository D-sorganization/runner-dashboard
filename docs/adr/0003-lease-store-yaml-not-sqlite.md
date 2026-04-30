# 0003. Runner lease store is a YAML file, not a SQLite database

## Status

Accepted

## Context

The dashboard tracks per-principal runner leases (claim a runner, hold it
for a task, release it) and per-issue agent coordination leases. Both stores
need to:

- Persist across dashboard restarts.
- Be inspected and edited by operators when something goes wrong.
- Survive a process crash without corruption.
- Scale to a few hundred entries at most. The fleet has < 30 runners and a
  bounded set of in-flight issues.

Three options were considered:

1. **YAML file at `config/leases.yml`** - human-readable, diffable, edits
   land in pull requests like any config change.
2. **SQLite database** - ACID writes, indexed lookups, query-able from the
   shell with `sqlite3`.
3. **Redis or another networked store** - shared state for a multi-process
   future.

SQLite is the textbook answer for "I need a small persistent store with
concurrent access". It would solve concurrent-write correctness for free.
But:

- Operators routinely inspect and tweak runtime config by running
  `cat config/principals.yml`, `cat config/tokens.yml`, etc. They cannot
  do that with a SQLite file.
- The lease set is small (< 100 entries) and changes infrequently
  (seconds-to-minutes scale, not hundreds per second). Indexing buys
  nothing.
- A YAML file Pull Request is a perfectly good audit log: every change is
  diffable, attributable, and reviewable.
- We do not currently run multiple dashboard processes. The dashboard is
  a single FastAPI server per node. Concurrent writes inside that one
  process can be serialized with a `threading.Lock` without coordinating
  across processes.
- A corrupt YAML file is recoverable by hand. A corrupt SQLite file
  requires `.recover` and is operator-hostile.

Redis was rejected outright because it would introduce a runtime
dependency we do not currently have, and the multi-process scenario is
explicitly not a goal (CLAUDE.md: orthogonality means tabs are independent
within one process; clustering the dashboard is not in scope).

## Decision

Persist runner leases at `config/leases.yml` as a YAML list of
`LeaseRecord` entries (see `backend/runner_lease.py`). Writes are
serialized inside the dashboard process and flushed atomically via a
temp-file-then-rename pattern. The file is checked into the operator's
runtime config tree, not committed to git, but is structurally identical
to other YAML files in `config/` (`principals.yml`, `tokens.yml`).

## Consequences

Positive:

- Operators can `cat`, `grep`, and edit the lease file in an emergency.
  The contract is "release a stuck lease" = "delete that line".
- No new runtime dependency. Python stdlib + PyYAML, both already in use.
- Backups are trivial: copy the file.
- Test fixtures are trivial: write a YAML file in a `tmp_path`.
- Schema migrations are diffable Pydantic model changes.

Negative:

- Concurrent writes from multiple processes are not safe. The lease store
  assumes a single dashboard process per node.
- No indexed lookups; the whole file is parsed on every load. Acceptable
  at < 100 entries, would be a problem at 10k.
- No transactional multi-record updates. If we ever need to atomically
  swap multiple leases, we will need either a write-ahead-log shim or a
  migration to SQLite.
- The atomic rename pattern depends on POSIX rename semantics. On Windows
  this would require additional care; the dashboard does not target
  Windows.

If the dashboard ever runs as a multi-process or multi-node service, or
the lease set grows beyond a few thousand records, this ADR will be
superseded by a SQLite-backed store. The Pydantic models in
`backend/runner_lease.py` are designed to make that migration mechanical:
the storage layer is isolated from the domain logic.
