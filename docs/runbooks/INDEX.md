# Operator Runbooks

This index links every operator runbook for the Runner Dashboard. Each
runbook follows a consistent structure: `## Symptoms`, `## Diagnosis`,
`## Remediation`, `## Postmortem template`. The CI check
`runbook-lint.yml` enforces those four H2 sections on every failure-mode
runbook in this directory; `INDEX.md` and the legacy
`dev-environment.md` quick-reference are explicitly excluded.

## Failure-mode runbooks

| Runbook | When to use it |
| --- | --- |
| [Dashboard down](dashboard-down.md) | systemd `runner-dashboard.service` flapping or off; `/api/health` not responding. |
| [GitHub token expired](github-token-expired.md) | All GitHub-backed `/api/*` routes return 5xx with `401 Unauthorized` from `api.github.com`. |
| [Tailscale offline](tailscale-offline.md) | Funnel offline; remote operators locked out while local access still works. |
| [Maxwell unreachable](maxwell-unreachable.md) | Maxwell tab broken while the rest of the dashboard is healthy. |
| [Queue stuck](queue-stuck.md) | `/api/queue/stale` returns hundreds of entries; runs queued forever. |
| [Lease store corrupted](lease-store-corrupted.md) | `leases.yml` (or equivalent) parse errors; duplicate `claim:*` labels. |
| [Deployment drift](deployment-drift.md) | Fleet nodes report different `/api/version` values; partial rollout. |
| [Linear webhook rotation](linear-webhook-rotation.md) | Rotating the Linear webhook signing secret (planned or after suspected compromise). |
| [Host rebuild](host-rebuild.md) | Re-imaging or replacing the dashboard host; restoring state from backups (#417). |

## Adjacent runbooks

| Runbook | When to use it |
| --- | --- |
| [Dev environment](dev-environment.md) | Local development quickstart — not an incident runbook, but useful context for diagnosis. |

## Conventions every runbook follows

- **Symptoms** — the observable signal an operator first sees.
- **Diagnosis** — five manual steps, in order; stop at the first that
  explains the failure.
- **Remediation** — concrete commands, with the canonical
  automated-remediation script (e.g. `deploy/rollback.sh`,
  `deploy/refresh-token.sh`) noted in line.
- **Postmortem template** — fill-in-the-blanks block to drop into the
  incident write-up.

Every runbook lists detection signals (which `/api/*` route, which
systemd unit, which log file) and an escalation contact (@dieterolson).
