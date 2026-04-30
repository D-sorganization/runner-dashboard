# Runbook: Host Rebuild (re-image / state restore)

The dashboard host has been re-imaged, replaced, or otherwise wiped and
must be restored from backups. As of issue #417 (closed), backups for the
dashboard's runtime state, env files, and config are in place; this
runbook walks through the restore.

## Symptoms

This is rarely a discovered incident — usually you initiate it. Trigger
conditions include:

- Disk failure or corruption beyond recovery on the dashboard host.
- Planned hardware migration to a new node.
- Compromise that requires a clean rebuild.

You should reach this runbook with the following already true: the new
host has the operating system installed, network connectivity, Tailscale
auth keys to hand, and access to the off-host backup archive.

Detection signals on the new host (before remediation):

- HTTP probe: `curl -fsS http://localhost:8321/api/health` fails (no
  service listening).
- systemd unit: `runner-dashboard.service` does not exist (`systemctl
  status runner-dashboard` returns "Unit not found").
- Logs: no `runner-dashboard` entries in `journalctl`.
- Files: `~/actions-runners/dashboard/` and
  `~/.config/runner-dashboard/` do not exist.

## Diagnosis

Use diagnosis to confirm the new host is ready to receive the restore;
this runbook is the steady-state restore plan, not the incident-triage
plan.

1. Confirm the OS prerequisites: Python 3.11+ available
   (`python3.11 --version`), `git` installed, `systemd` running, and the
   user the dashboard runs as exists with sudo rights.
2. Confirm Tailscale is installed and the new host can be enrolled to
   the tailnet (`tailscale up` will be run during remediation).
3. Locate the most recent backup archive. Per #417, backups capture the
   deploy tree (`~/actions-runners/dashboard/`), the env directory
   (`~/.config/runner-dashboard/`), and any state files (lease store,
   schedule, usage sources). Confirm the archive's checksum and date.
4. Confirm GitHub credentials for the new host: a fresh PAT or app-token
   with the documented scope set, plus the org/registry secrets that
   `deploy/setup.sh` consumes. Have these available before starting.
5. Confirm there is no other host claiming the same role or the same
   Tailscale node name. Two hubs simultaneously is a worse state than a
   short outage; resolve naming first.

## Remediation

Restore is sequential — each step depends on the previous succeeding.

1. **Provision Tailscale:** `bash deploy/setup-tailscale.sh` (or
   equivalent steps from `docs/tailscale-funnel.md`) to enroll the host
   and re-establish the Funnel mapping. Verify with `tailscale status`
   and `tailscale funnel status`.
2. **Run the dashboard setup script:** `bash deploy/setup.sh --runners
   <N> --machine-name <Name> --role <hub|node>`. This installs Python
   deps into a venv, installs the systemd unit, and starts the service.
   See SPEC §6.2 for canonical invocation patterns.
3. **Restore env files from backup:** copy the backed-up
   `~/.config/runner-dashboard/env` into place and confirm permissions
   (`chmod 600`). Re-run `bash deploy/configure-env-vars.sh` only if you
   need to regenerate any of the values.
4. **Restore state files from backup:** the lease store, runner-schedule
   JSON, usage-source JSON, and any other content under `config/` go
   back from the backup archive. If the lease store is suspect, follow
   `lease-store-corrupted.md` to reset it instead of restoring.
5. **Restart and verify:** `sudo systemctl restart runner-dashboard`,
   then `curl -fsS http://localhost:8321/api/health` (expect 200) and
   `curl -fsS http://localhost:8321/api/version` (expect the version
   matching the rest of the fleet — see `deployment-drift.md` if it
   does not).

If the new host is a node (not the hub), update the hub's
`backend/machine_registry.yml` and `--fleet-nodes` configuration to
reflect the new Tailscale URL, then redeploy the hub with
`deploy/update-deployed.sh`.

Automated remediation script reference:

- `deploy/setup-tailscale.sh` — Tailscale install + Funnel mapping.
- `deploy/setup.sh` — full machine setup, idempotent.
- `deploy/configure-env-vars.sh` — env-file rewrite.
- `deploy/update-deployed.sh` — for any post-restore version sync.

Escalation contact: @dieterolson.

## Postmortem template

```
Incident: host-rebuild YYYY-MM-DD HH:MM UTC
Type: <planned migration | disk failure | compromise>
Duration: <total outage minutes for this host>
Impact: <which fleet role was offline, what tabs/operators affected>

Timeline:
- HH:MM Z — host wiped / decision to rebuild
- HH:MM Z — backup archive identified (path, checksum, date)
- HH:MM Z — Tailscale enrolled / setup.sh complete
- HH:MM Z — env + state restored
- HH:MM Z — /api/health green, /api/version matches fleet

Root cause: <hardware | OS | compromise | planned>
Trigger: <hardware event | migration plan | incident response>
Resolution: <which backup was used, which scripts were re-run>

Follow-ups:
- [ ] confirm next backup ran successfully on the rebuilt host
- [ ] document any setup-step gap that bit us during rebuild
- [ ] confirm machine_registry.yml on the hub matches reality
```
