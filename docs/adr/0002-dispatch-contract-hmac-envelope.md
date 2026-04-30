# 0002. Dispatch contract uses HMAC-signed envelope, not JWT

## Status

Accepted

## Context

The dashboard issues commands to runner nodes (start runner, cancel
workflow, dispatch agent, drain machine) over HTTP. Every command needs to
be authenticated end-to-end so a compromised intermediary cannot forge or
replay actions. The candidates considered were:

1. **JWT (RS256 or HS256)** - the de-facto industry default. Tokens carry
   a payload, are signed, and have well-known libraries.
2. **HMAC-signed envelope** - a custom but small envelope format with a
   handful of fields, signed with HMAC-SHA256 and a shared secret.
3. **mTLS only** - rely on transport-layer auth and skip payload signing.

JWT is attractive because of library availability, but it brought
non-trivial drawbacks for our use case:

- The JWT spec has a long history of well-known footguns (alg=none, key
  confusion, weak signature algorithm negotiation). Hand-rolling around
  these is risky; using a library means pinning and auditing it.
- JWT requires either a shared symmetric key (HS*) which buys nothing over
  HMAC, or asymmetric keys (RS*/ES*) which need a key distribution story
  the dashboard does not currently have.
- JWT bodies are base64url-encoded JSON, but the canonical form for
  signing is the unparsed token string. This makes test vectors and audit
  logs harder to reason about than a flat JSON envelope.
- The dispatch envelope is small and fully owned: action, source, target,
  requested_by, issued_at, envelope_version. We do not need JWT's
  registered claims (`iss`, `aud`, `exp`, etc.) - we have our own
  freshness check (`_validate_timestamp_freshness`) and our own action
  catalog.

mTLS was ruled out because the dashboard runs behind a reverse proxy that
terminates TLS, and we want auditability of the signed payload at the
application layer, not just at the transport.

## Decision

Use a custom HMAC-SHA256 envelope, defined in
`backend/dispatch_contract.py`:

- Envelope fields: `action`, `source`, `target`, `requested_by`,
  `issued_at`, `envelope_version`, `nonce`, plus an action-specific
  `payload`.
- Signature is HMAC-SHA256 over a deterministic JSON serialization of the
  envelope, base64-encoded.
- Signing secret is loaded from `DISPATCH_SIGNING_SECRET` env var or
  generated and persisted at `~/.config/runner-dashboard/dispatch_signing_key`
  with `0600` permissions.
- Schema version is pinned (`dispatch-envelope.v1`) so future envelope
  changes are explicit and forward/backward compatible.
- Timestamps are validated to be within +/- 300 seconds of server time to
  bound replay windows.
- Every accepted or rejected envelope produces an audit-log record.

## Consequences

Positive:

- Tiny attack surface: there is no algorithm negotiation, no library
  vulnerability surface beyond `hmac` and `hashlib` from the stdlib.
- The envelope is plain JSON, trivially inspectable in logs and tests.
- Schema evolution is explicit via `envelope_version` and
  `SCHEMA_VERSION`.
- The signing secret can be rotated by writing a new key and restarting
  the service; no PKI machinery required.
- Implementation is ~200 lines of code, all stdlib, easy to audit.

Negative:

- We do not get to use any of the JWT ecosystem (introspection endpoints,
  OIDC, off-the-shelf middleware). If we ever need cross-organization
  federation we will have to migrate.
- Symmetric secrets must be distributed to every signer/verifier and kept
  in sync. There is no public-key story.
- Each new client (e.g. a sibling repo, a CLI) must implement the envelope
  format. We lift the canonical implementation into
  `Repository_Management/shared_scripts/` to avoid forks (DRY principle).
- Custom format means custom tooling: there is no `jwt.io` equivalent for
  debugging.

For our threat model (a small fleet, a single trust boundary, no external
identity provider), the simplicity and auditability of an HMAC envelope
beat JWT. If the threat model expands to include external organizations
or rotating per-machine keys, this ADR will be superseded.
