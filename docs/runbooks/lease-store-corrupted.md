# Runbook: Lease Store Corrupted (leases.yml)

The agent coordination lease store on the dashboard host is corrupted.
Agents cannot acquire or renew leases, the Lease Reaper sweep is failing,
and redundant agents may be picking up the same issue.

## Symptoms

- The Agent Lease Reaper workflow run shows YAML parse errors against
  `leases.yml` (or the equivalent JSON store) — typically
  `yaml.parser.ParserError` or `yaml.scanner.ScannerError`.
- Multiple `claim:<agent>` labels appear on the same issue, or stale
  claims persist long past the documented 2-hour expiry without being
  reaped.
- `/api/leases` (or whichever endpoint surfaces lease state in the
  Remediation tab) returns 500, an empty list, or a body containing
  parse-error text.
- `journalctl -u runner-dashboard | grep -i lease` shows repeated
  exceptions when the dashboard tries to read or rewrite the store.
- Two agents open PRs against the same issue within minutes of each
  other — the redundancy guard depends on a healthy lease store.

Detection signals:

- HTTP probe: `curl -fsS http://localhost:8321/api/leases` — non-200 or a
  body containing `ParserError` is the smoking gun.
- File probe: `python -c "import yaml; yaml.safe_load(open('<path to
  leases.yml>'))"` — fails with a parse error when corrupted.
- systemd unit: `runner-dashboard.service` (the lease store is read by
  the dashboard process; the Reaper workflow lives in
  `Repository_Management`).
- Logs: `sudo journalctl -u runner-dashboard | grep -i lease`, the
  Lease Reaper workflow run output on GitHub.

## Diagnosis

1. Locate the lease store on this host. The canonical path is documented
   in `docs/agent-coordination-strategy.md`; common defaults are
   `~/.config/runner-dashboard/leases.yml` or a path under the dashboard
   data directory. Confirm the file exists and is non-empty.
2. Validate the file as YAML:
   `python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))"
   <path>`. A parse error shows the offending line/column. If the file is
   JSON in this deployment, swap `yaml.safe_load` for `json.load`.
3. Inspect git/backup history. The dashboard's deploy backups
   (`deploy/update-deployed.sh`) capture timestamped copies; check the
   most recent `.bak.YYYYMMDD_HHMMSS` directory for a healthy
   `leases.yml`.
4. Look at the dashboard log for the first failed read:
   `sudo journalctl -u runner-dashboard --since "2 hours ago" | grep -i
   lease | head -n 20`. The first traceback identifies which writer
   produced the bad value (usually a partial flush or a crash mid-write).
5. Cross-check the Lease Reaper workflow run history in
   `Repository_Management` to confirm the parse failure is reproducible
   and to capture the exact bytes the Reaper saw.

## Remediation

- **Restore from the most recent backup:** copy the healthy `leases.yml`
  out of the latest deploy backup
  (`~/actions-runners/dashboard.bak.YYYYMMDD_HHMMSS/...`) into the live
  path, then `sudo systemctl restart runner-dashboard`.
- **If no backup is acceptable, reset the store:** the lease store is
  intentionally ephemeral — every entry expires in 2 hours and live
  agents will repost their leases on their next renewal cycle. Move the
  bad file aside (`mv leases.yml leases.yml.corrupt.$(date +%s)`),
  recreate it as `{}` (or `--- {}` for YAML), restart the dashboard, and
  let the next Reaper run reconcile.
- **Deploy backup recovery:** `bash deploy/rollback.sh --dry-run` to
  preview, then `bash deploy/rollback.sh` if rolling back the entire
  dashboard tree is preferable to extracting one file.
- **Re-trigger the Lease Reaper** in `Repository_Management` after
  restoring, so any orphaned `claim:*` labels get cleaned up promptly.

After remediation, re-probe `/api/leases` and confirm at least one fresh
lease appears within 30 minutes (the next Reaper sweep cadence). If
redundant `claim:*` labels remain, the Reaper will clear them once the
expiry passes.

Automated remediation script reference:

- `deploy/rollback.sh` — restores the prior deploy tree, including any
  state files captured in the backup.
- The Lease Reaper workflow lives in `Repository_Management` and runs
  every 30 minutes; re-triggering it manually is the fastest way to
  resync after the file is restored.

Escalation contact: @dieterolson.

## Postmortem template

```
Incident: lease-store-corrupted YYYY-MM-DD HH:MM UTC
Detected by: <Reaper workflow failure | duplicate PRs | /api/leases 500>
Duration: <minutes>
Impact: <duplicate agent dispatch, stuck claim:* labels, etc.>

Timeline:
- HH:MM Z — first parse failure observed
- HH:MM Z — cause of corruption identified (writer, crash, disk)
- HH:MM Z — store restored from <backup | reset to empty>
- HH:MM Z — Reaper sweep confirmed clean

Root cause: <partial write | crash during rewrite | bad merge | disk full>
Trigger: <deploy | crash | concurrent writers>
Resolution: <restore method, follow-up code changes if any>

Follow-ups:
- [ ] add atomic write (tmp + rename) if not already in place
- [ ] add /api/leases content-validation probe
- [ ] document store path in docs/agent-coordination-strategy.md if missing
```
