# Runbook: Tailscale Offline (Funnel down, remote operators locked out)

The Tailscale daemon (`tailscaled`) is down or the Funnel that exposes the
dashboard to remote operators has stopped serving. Operators on the local
network can still reach the dashboard at `http://localhost:8321`; remote
operators get connection refused on the public Funnel hostname.

## Symptoms

- Remote operators report the public Funnel hostname is unreachable
  (`Could not resolve host` or TLS handshake fails).
- `tailscale status` shows the local node `offline`, or
  `tailscale funnel status` shows no listeners on port 443.
- `journalctl -u tailscaled` shows repeated `magicsock: disco` errors,
  `auth expired`, or `control plane unreachable`.
- Dashboard works locally but every remote `/api/*` request times out.
- The Tailscale tray indicator (or `tailscale ip -4`) shows no assigned
  Tailnet IP.

Detection signals:

- HTTP probe (from a remote host): `curl -fsS https://<funnel-host>/api/health`
  fails with connection refused or DNS error.
- HTTP probe (locally): `curl -fsS http://localhost:8321/api/health` still
  returns `200` — this is the diagnostic that distinguishes Tailscale
  problems from dashboard problems.
- systemd unit: `tailscaled.service` (and the dashboard's own
  `runner-dashboard.service` is unaffected).
- Logs: `sudo journalctl -u tailscaled -n 200 --no-pager`,
  `tailscale debug daemon-logs` (recent versions),
  `/var/log/syslog` filtered for `tailscaled`.

## Diagnosis

1. Confirm the local dashboard is healthy:
   `curl -fsS http://localhost:8321/api/health`. If this fails, this is a
   different incident — see `dashboard-down.md`.
2. Check Tailscale daemon health: `systemctl status tailscaled --no-pager`
   and `tailscale status`. Note whether the node is `online`, `offline`,
   or `needs login`.
3. Inspect Funnel state explicitly:
   `tailscale funnel status` and
   `tailscale serve status`. Confirm that port 443 is mapped to
   `http://127.0.0.1:8321` (or whichever local port the dashboard binds).
   Compare to the documented configuration in `docs/tailscale-funnel.md`.
4. Tail the daemon log:
   `sudo journalctl -u tailscaled --since "1 hour ago" | tail -n 100`.
   Look for `auth expired`, `control plane unreachable`,
   `derp: connect failed`, or repeated `magicsock` errors.
5. Probe outbound connectivity to the control plane:
   `curl -fsS https://login.tailscale.com/`. A failure here points at the
   host's egress (firewall, DNS, ISP) rather than at Tailscale itself.

## Remediation

- **Daemon flapping or wedged:**
  `sudo systemctl restart tailscaled`, then re-verify with
  `tailscale status` and `tailscale funnel status`.
- **Auth expired / node logged out:**
  `sudo tailscale up --ssh --advertise-tags=tag:dashboard` (substitute the
  tag set documented in `docs/tailscale-funnel.md`). Use a non-interactive
  auth key from the admin console if running on a headless host.
- **Funnel listener missing:** re-run `bash deploy/setup-tailscale.sh`
  which is the canonical helper for re-establishing the Funnel mapping for
  this dashboard. Re-check `tailscale funnel status` afterwards.
- **Control plane unreachable but daemon healthy locally:** treat as an
  upstream Tailscale incident — fall back to LAN access and the Tailscale
  status page; do not keep restarting the daemon.

After any of the above, confirm with a remote probe of the Funnel hostname
(`curl -fsS https://<funnel-host>/api/health`).

Automated remediation script reference:

- `deploy/setup-tailscale.sh` — installs/repairs Tailscale and the Funnel
  mapping for the dashboard.
- The dashboard service (`runner-dashboard.service`) does not need to
  restart for Tailscale-only incidents.

Escalation contact: @dieterolson.

## Postmortem template

```
Incident: tailscale-offline YYYY-MM-DD HH:MM UTC
Detected by: <remote operator report | external probe | tailnet alert>
Duration: <minutes>
Impact: remote operators locked out; local operators unaffected.

Timeline:
- HH:MM Z — first remote failure reported
- HH:MM Z — local /api/health confirmed green (so dashboard intact)
- HH:MM Z — tailscaled state confirmed (offline / needs login / etc.)
- HH:MM Z — Funnel restored, remote probe green

Root cause: <expired auth | daemon wedge | upstream control plane | host network>
Trigger: <node reboot | auth key expiry | Tailscale upstream | unknown>
Resolution: <commands run, links to admin console actions>

Follow-ups:
- [ ] document auth key rotation cadence (owner: @, due: YYYY-MM-DD)
- [ ] add remote-probe alert that pages on Funnel-only failures
- [ ] confirm setup-tailscale.sh covers the recovery path that worked
```
