# Runbook: Dashboard Down (systemd flapping)

The dashboard FastAPI service (`runner-dashboard.service`) is failing to stay
up, restarting in a loop, or completely off.

## Symptoms

- Operators report the dashboard URL (http://localhost:8321 or the Tailscale
  Funnel hostname) returns connection refused, 502, or the browser hangs.
- `GET /api/health` returns nothing or a connection error.
- `systemctl status runner-dashboard` shows `activating (auto-restart)` or
  repeated `failed` states; the `Active:` line flips between states inside a
  single minute.
- `journalctl -u runner-dashboard` shows repeated `Main process exited`
  followed by `Service RestartSec=...` messages.
- Frontend tabs show a permanent loading skeleton because no `/api/*`
  endpoint responds.

Detection signals:

- HTTP probe: `curl -fsS http://localhost:8321/api/health` exits non-zero or
  hangs past the 5s connect timeout.
- systemd unit: `runner-dashboard.service` (defined in
  `deploy/runner-dashboard.service`).
- Logs: `sudo journalctl -u runner-dashboard -n 200 --no-pager` and
  `/tmp/runner-dashboard.log` (when started via `start-dashboard.sh --bg`).

## Diagnosis

Work through these manual checks in order; stop at the first one that
explains the failure.

1. Confirm the unit state: `systemctl status runner-dashboard --no-pager`.
   Note the `Active:` line, the `Main PID`, and the most recent restart
   counter shown in the unit log lines.
2. Tail the journal for the last failure:
   `sudo journalctl -u runner-dashboard -n 200 --no-pager | tail -n 80`.
   Look for Python tracebacks, `ModuleNotFoundError`, port-bind failures
   (`Address already in use`), or `permission denied` on
   `~/.config/runner-dashboard/env`.
3. Verify no other process owns port 8321:
   `sudo ss -tlnp | grep 8321` (or `sudo lsof -iTCP:8321 -sTCP:LISTEN`).
   A stray dev `start-dashboard.sh` from a prior session is the most common
   cause of bind failures.
4. Check the venv referenced by the unit's `ExecStart` exists and has the
   pinned dependencies. From the deploy directory run
   `./.venv/bin/python -c "import fastapi, uvicorn, httpx"` and confirm it
   exits 0. A missing import here is what most "flapping" boils down to
   after a botched `update-deployed.sh` run.
5. Inspect the env file referenced by the unit:
   `sudo -u runner cat ~/.config/runner-dashboard/env`. Confirm
   `GITHUB_TOKEN`, `GITHUB_ORG`, and any required overrides are present and
   not blank. An empty `GITHUB_TOKEN` causes the service to crash on startup
   in some code paths.

## Remediation

Pick the path that matches the diagnosis.

- **Stale port owner / zombie process:** kill the offending PID
  (`sudo kill <pid>`), then `sudo systemctl restart runner-dashboard`.
- **Bad deploy / missing dependency:** roll back to the most recent backup:
  `bash deploy/rollback.sh` (preview first with `--dry-run`). The rollback
  marker is written by `deploy/update-deployed.sh` on every deploy, so the
  prior known-good tree is always available.
- **Corrupt env file:** restore from `~/.config/runner-dashboard/env.bak` if
  present, or re-run `bash deploy/configure-env-vars.sh` to rewrite it. Then
  `sudo systemctl daemon-reload && sudo systemctl restart runner-dashboard`.
- **Generic restart after recovering the underlying issue:**
  `sudo systemctl restart runner-dashboard` and verify with
  `curl -fsS http://localhost:8321/api/health`.

Automated remediation script reference:

- `deploy/update-deployed.sh` — re-deploys and restarts the service end to
  end (creates a fresh backup first).
- `deploy/rollback.sh` — restores the most recent deploy backup and
  restarts the service.

If two consecutive `systemctl restart` attempts both flap within five
minutes, escalate.

Escalation contact: @dieterolson.

## Postmortem template

```
Incident: dashboard-down YYYY-MM-DD HH:MM UTC
Detected by: <alert | operator report | dashboard probe>
Duration: <minutes>
Impact: <which operators / which tabs were unreachable>

Timeline:
- HH:MM Z — first failed health probe
- HH:MM Z — operator paged
- HH:MM Z — root cause identified (<one line>)
- HH:MM Z — service restored

Root cause: <one paragraph>
Trigger: <deploy | env change | host event | unknown>
Resolution: <command(s) run, link to PR if a fix shipped>

Follow-ups:
- [ ] <preventative action> (owner: @, due: YYYY-MM-DD)
- [ ] <detection improvement> (owner: @, due: YYYY-MM-DD)
```
