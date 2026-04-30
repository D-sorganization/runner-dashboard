# 0004. WebAuthn ships fail-closed scaffold first, real verifier in Phase 2

## Status

Accepted

## Context

Mobile-biometric unlock for privileged dashboard actions is a multi-quarter
feature. It needs:

- A registration ceremony (browser collects a passkey, server stores
  credential metadata).
- An assertion ceremony (browser signs a server challenge, server verifies
  signature against the stored public key).
- Pinned cryptography for COSE key parsing, attestation statement
  verification, and assertion signature verification.
- Operator UX (enroll device, list devices, revoke device).
- Audit trail for every ceremony.

The full implementation has a non-trivial cryptographic dependency surface
(`cryptography`, `cbor2`, a WebAuthn server library). Each addition is a
supply-chain risk that has to be vetted and pinned. We do not want to
delay every other Wave 5 feature behind that vetting.

At the same time, leaving "WebAuthn coming soon" as an unguarded surface
is dangerous. If a route exists at `/api/auth/webauthn/*` but does no
verification, a misconfigured deploy could ship a soft-fail that grants
access on any payload. Several real-world auth bypasses have shipped
exactly this way.

Two options were considered:

1. **Wait** - merge nothing under `auth/webauthn` until Phase 2 lands the
   verifier. Mobile-biometric is blocked behind library vetting.
2. **Fail-closed scaffold** - ship the route surface, the
   challenge issuance, the credential storage shape, and the audit log
   now, but make every ceremony return `501 Not Implemented` (or
   equivalent denial) until the verifier is wired in.

## Decision

Ship the fail-closed scaffold in `backend/auth_webauthn.py`:

- The router is mounted at `/api/auth/webauthn` and authenticated by the
  same `require_principal` dependency as every other privileged route.
- `register_begin` and `assert_begin` issue server-signed challenges so
  the frontend can be built and tested against a real challenge format.
- `register_complete` and `assert_complete` accept the credential payload,
  validate the challenge HMAC, and then **deny by default** because no
  verifier is wired in. There is no path through the code that returns
  success without a verifier present.
- Credential metadata is stored in a JSON file at
  `~/.config/runner-dashboard/webauthn_credentials.json` so the storage
  shape is exercised before Phase 2.
- The denial path is the default branch, not an `if not verifier:`
  short-circuit at the top of the function. This means a future bug that
  bypasses the verifier check still falls through to denial.

Phase 2 will add the verifier (a pinned WebAuthn library) and remove the
denial path. No other behavior changes.

## Consequences

Positive:

- Frontend, audit log, credential storage, and challenge issuance are all
  exercised in production now, surfacing bugs before Phase 2.
- Fail-closed semantics mean a misconfigured Phase 2 deploy cannot
  accidentally grant access. The worst case is "biometric unlock returns
  501", not "biometric unlock returns 200 without verification".
- The route surface is stable, so frontend code written against the
  Phase 1 scaffold continues to work in Phase 2.
- Library vetting (cryptography pinning, supply-chain audit) does not
  block the rest of the auth migration.

Negative:

- Operators see a `/api/auth/webauthn` surface that does not yet do the
  thing the route name promises. The denial response includes a
  `phase: "scaffold"` flag so this is unambiguous, but it is still a
  partial feature in production.
- A reviewer scanning the code may mistake the scaffold for a complete
  implementation. Comments and the module docstring call this out
  explicitly.
- The credential storage format is set in stone before the verifier
  exists; if Phase 2 needs additional fields we have to migrate.

This ADR will be superseded once Phase 2 lands the verifier, at which
point the status here moves to `Superseded by 00NN`.
