# Architecture Decision Records (ADRs)

This directory records significant architectural decisions made in the runner-dashboard project.

## Format

Each ADR is a Markdown file following this naming convention:

    NNNN-title-with-dashes.md

## Template

```markdown
# NNNN. Title

## Status

- Proposed / Accepted / Deprecated / Superseded by [NNNN](./NNNN-title.md)

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing or have agreed to implement?

## Consequences

What becomes easier or more difficult to do because of this change?
```

## Index

- [0001. Single-file SPA to Vite + React + TypeScript migration](./0001-vite-spa-migration.md)
- [0002. Dispatch contract uses HMAC-signed envelope, not JWT](./0002-dispatch-contract-hmac-envelope.md)
- [0003. Runner lease store is a YAML file, not a SQLite database](./0003-lease-store-yaml-not-sqlite.md)
- [0004. WebAuthn ships fail-closed scaffold first, real verifier in Phase 2](./0004-webauthn-fail-closed-scaffold.md)
- [0005. Agent priority order: user > maxwell-daemon > claude > codex > jules > local > gaai](./0005-agent-priority-order.md)
