# 0005. Agent priority order: user > maxwell-daemon > claude > codex > jules > local > gaai

## Status

Accepted

## Context

Multiple AI agents (Claude, Codex, Jules, GAAI, Maxwell) and human users
all pick up issues from the same backlog. Without coordination, two
agents can claim the same issue and open duplicate PRs. We solve the
common case with the lease protocol described in
`docs/agent-coordination-strategy.md`. But leases race: two agents can
post leases on the same issue within a few seconds, and the redundant-PR
closer needs a deterministic rule to pick a winner.

A priority order has to be:

- **Total** - any pair of agents has a clear winner. No ties.
- **Stable** - changing it should be a deliberate, reviewed decision, not
  drift.
- **Consistent across the fleet** - the dashboard, the redundant-PR
  closer workflow, and any human reviewer must agree on the order.
- **Documented** - new agents need to know where they slot in.

The chosen order is:

`user > maxwell-daemon > claude > codex > jules > local > gaai`

The rationale for each precedence step was debated as the agents joined
the fleet:

1. **`user`** - human contributors always win. A human PR is by
   definition reviewed and intentional; an agent PR that races a human
   should yield. This is non-negotiable.
2. **`maxwell-daemon`** - the autonomous local AI control plane wins over
   other agents because it is the orchestrator: when Maxwell decides to
   take an issue it is acting on policy that already incorporates the
   other agents' availability, so its claim represents a higher-level
   decision.
3. **`claude`** - of the issue-picking coding agents, Claude has produced
   the highest PR-acceptance rate empirically, so a Claude PR is the
   most-likely-merged outcome. Letting it win minimizes wasted work.
4. **`codex`** - second-highest acceptance rate; equivalent capabilities
   to Claude on most tasks but slightly behind on architectural changes.
5. **`jules`** - Jules currently focuses on CI repair and AutoFix loops
   rather than greenfield issue work, so its PR claim is rarer and
   lower-priority on issue work specifically.
6. **`local`** - locally-run agents (developer machines, sandboxes) win
   over GAAI because they represent an operator with hands on the
   keyboard, and that operator intent should not be silently overridden
   by a remote bot.
7. **`gaai`** - GAAI has the highest false-positive rate on issue
   relevance and the lowest acceptance rate; it is intentionally last so
   its claims yield to anything else.

## Decision

Codify the priority order in `CLAUDE.md` (already done) and in
`docs/agent-coordination-strategy.md`. The redundant-PR closer workflow
(`Agent Redundant PR Closer`) and the lease reaper (`Agent Lease Reaper`)
both consume this order from a single source of truth. Any addition or
reordering of agents requires a PR that updates:

1. `CLAUDE.md`
2. `docs/agent-coordination-strategy.md`
3. The agent-priority constant in the redundant-PR closer workflow
4. This ADR (or a superseding ADR)

## Consequences

Positive:

- Race conditions resolve deterministically. Two agents claiming the
  same issue produces exactly one merged PR.
- Human contributors are always protected from being clobbered by an
  agent.
- The order is empirically grounded in PR-acceptance data, so the most
  likely-to-succeed agent wins, minimizing wasted CI time.
- New agents have a clear onboarding step: pick a slot, justify it,
  update the ADR.

Negative:

- The order is opinionated and will become stale as agents improve or
  regress. Acceptance-rate data must be periodically reviewed.
- GAAI being last is demotivating for that team; the rationale is
  documented here so the decision is not personal.
- A single ordering does not capture domain expertise: Claude may be
  best at backend, Codex at frontend, but the priority is global. We
  accept this loss in exchange for simplicity.
- If two new agents are added simultaneously, the PR review must order
  them relative to existing agents - this is a small but real
  coordination cost.

Acceptance-rate data is reviewed quarterly. If the order shifts
materially, this ADR is superseded by a new one rather than edited in
place, so the historical decision is preserved.
