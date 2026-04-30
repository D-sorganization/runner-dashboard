# Runbook: Maxwell Unreachable (Maxwell tab broken)

The Maxwell tab in the dashboard cannot reach the Maxwell-Daemon HTTP
control plane. The dashboard itself is healthy, every other tab works,
but anything that proxies to Maxwell (`/api/maxwell/*`) returns errors or
empty payloads.

## Symptoms

- The Maxwell tab shows a permanent "Maxwell unreachable" banner, an empty
  pipeline list, or a spinner that never resolves.
- Every other tab (Fleet, Org, Workflows, Queue Health, Remediation) is
  fully functional.
- `GET /api/maxwell/health` from the dashboard returns 502/504 or a body
  with `{"status": "unreachable"}`; `GET /api/maxwell/state` returns a
  similar shape.
- `journalctl -u runner-dashboard | grep -i maxwell` shows
  `httpx.ConnectError`, `read timeout`, or the configured Maxwell URL
  returning a non-2xx.
- The Maxwell-Daemon service on its host is stopped, listening on the
  wrong port, or the Tailscale path between the dashboard host and the
  Maxwell host is broken.

Detection signals:

- HTTP probe (dashboard side):
  `curl -fsS http://localhost:8321/api/maxwell/health` returns 5xx while
  `curl -fsS http://localhost:8321/api/health` returns 200.
- HTTP probe (Maxwell side, from the dashboard host):
  `curl -fsS <MAXWELL_URL>/health` (the URL that the Maxwell tab is
  configured with).
- systemd unit (on the Maxwell host): `maxwell-daemon.service` (lives in
  the `Maxwell-Daemon` repo, not here).
- Logs: `sudo journalctl -u runner-dashboard | grep -i maxwell` on this
  host; `sudo journalctl -u maxwell-daemon` on the Maxwell host.

## Diagnosis

The dashboard never imports from Maxwell at runtime — the only coupling
is HTTP — so all diagnosis is at the network/HTTP layer.

1. Confirm the rest of the dashboard is healthy:
   `curl -fsS http://localhost:8321/api/health`. If this is red the
   primary incident is the dashboard itself; see `dashboard-down.md`.
2. Read which URL the dashboard is using for Maxwell. It is set via env
   (commonly `MAXWELL_URL`) or via the runtime config under
   `~/.config/runner-dashboard/`. Confirm the URL is reachable by name:
   `getent hosts <host>` or `tailscale ip -4 <host>`.
3. From the dashboard host, hit Maxwell directly:
   `curl -fsS -m 5 <MAXWELL_URL>/health`. Note whether you get connection
   refused (daemon down), a timeout (network path), or a 5xx (daemon up
   but failing).
4. If reachability is the issue, check Tailscale on both ends:
   `tailscale status | grep <maxwell-host>` from the dashboard host. If
   the Maxwell host is `offline`, work the `tailscale-offline.md` runbook
   for that host; do not poke at Maxwell while its tunnel is down.
5. If Maxwell is reachable but returning errors, inspect the Maxwell
   daemon logs on its own host:
   `sudo journalctl -u maxwell-daemon --since "30 min ago" | tail -n 100`.
   Anything beyond a restart is owned by the `Maxwell-Daemon` repo and
   should be triaged there.

## Remediation

- **Maxwell daemon down:** restart it on the Maxwell host:
  `sudo systemctl restart maxwell-daemon`. Confirm with
  `curl -fsS <MAXWELL_URL>/health`. Filing the failure as an issue against
  the `Maxwell-Daemon` repo is appropriate even after a successful
  restart, so the root cause gets addressed.
- **Misconfigured URL on the dashboard:** edit
  `~/.config/runner-dashboard/env` (or the equivalent runtime config) so
  `MAXWELL_URL` points at the correct host:port, then
  `sudo systemctl restart runner-dashboard`.
- **Tunnel between hosts broken:** see `tailscale-offline.md` and remediate
  on whichever side is offline. Do not change the dashboard config to
  work around a tunnel outage.
- **Persistent failure with daemon healthy:** isolate by hitting Maxwell
  from a third host on the tailnet; if it succeeds there, the dashboard
  host's Tailscale ACLs are the cause.

The dashboard tab is built to fail open: a Maxwell outage must never
cascade into other tab failures (per the orthogonality principle in
`CLAUDE.md`). If you observe other tabs failing alongside Maxwell, treat
that as a separate incident.

Automated remediation script reference:

- No dashboard-owned restart script targets Maxwell. The Maxwell daemon
  is restarted via plain `systemctl` on its host. The dashboard side
  recovers automatically once `<MAXWELL_URL>/health` returns 200.

Escalation contact: @dieterolson. For daemon-internal issues (pipeline
state machine, ExecutionSandbox), escalate to the `Maxwell-Daemon` repo
owners.

## Postmortem template

```
Incident: maxwell-unreachable YYYY-MM-DD HH:MM UTC
Detected by: <Maxwell tab error | operator report | probe>
Duration: <minutes>
Impact: Maxwell tab only; other dashboard tabs unaffected (verify).

Timeline:
- HH:MM Z — Maxwell tab first reported broken
- HH:MM Z — confirmed dashboard-internal /api/health green
- HH:MM Z — confirmed Maxwell-side state (down / unreachable / 5xx)
- HH:MM Z — Maxwell side recovered

Root cause: <maxwell daemon | network path | dashboard config>
Trigger: <restart | tunnel | config drift | upstream issue>
Resolution: <command(s) run, link to Maxwell-Daemon issue if filed>

Follow-ups:
- [ ] file Maxwell-Daemon issue if root cause is in that repo
- [ ] verify orthogonality (other tabs stayed up during the outage)
- [ ] add a probe that distinguishes Maxwell-side vs network failures
```
