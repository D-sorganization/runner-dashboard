# Runbook: Queue Stuck (/api/queue/stale returns hundreds)

The workflow run queue has filled up with hundreds of stale entries. The
Queue Health tab is red, the Workflows tab shows long-pending runs that
never start, and the stale-queue cleanup is either disabled, mis-tuned,
or has not been able to keep up with bursty inflow.

## Symptoms

- Queue Health tab shows a stale-run count in the hundreds (or higher)
  with the "stale runs detected" banner red.
- `GET /api/queue/stale` returns a JSON list whose length is hundreds; in
  steady state this list should be small (a few stragglers at most).
- Workflows tab shows runs in `queued` for far longer than the runner
  fleet's normal pickup time.
- `journalctl -u runner-dashboard | grep -i queue` shows the
  `queue_cleanup` helpers running but failing to clear entries, or the
  hourly maintenance cron has not been firing.
- Operators report new dispatches "look queued forever" and runners are
  idle even though the queue is deep.

Detection signals:

- HTTP probe: `curl -fsS http://localhost:8321/api/queue/stale | jq
  'length'`. Anything above a low double-digit count is a problem.
- HTTP probe: `curl -fsS http://localhost:8321/api/queue/purge-stale -X
  POST` (operator-driven only — see remediation before running).
- systemd unit: `runner-dashboard.service` (queue cleanup runs in-process)
  plus the hourly cron defined by
  `deploy/scheduled-dashboard-maintenance.sh`.
- Logs: `sudo journalctl -u runner-dashboard | grep queue_cleanup`,
  `/var/log/syslog` for the cron entry.

## Diagnosis

1. Get the current stale list size and a sample of the entries:
   `curl -fsS http://localhost:8321/api/queue/stale | jq 'length,
   (.[0:3])'`. Note the workflow names — if they cluster on one
   workflow, the issue is workflow-scoped, not fleet-wide.
2. Check whether the maintenance cron has been running:
   `grep scheduled-dashboard-maintenance /var/log/syslog | tail -n 20`
   (or `journalctl --since "24 hours ago" | grep maintenance`). The cron
   should fire hourly; gaps are a strong signal.
3. Confirm runners are alive:
   `curl -fsS http://localhost:8321/api/runners | jq '[.[] |
   select(.status=="online")] | length'`. If zero, this is a runner
   incident and the queue is a downstream symptom — see
   `dashboard-down.md` or fleet-side runner runbooks.
4. Look at the dashboard log for `queue_cleanup` activity over the last
   hour. The helpers in `backend/queue_cleanup.py` log per pass and per
   batch; recurring exceptions there explain why stale entries are not
   being purged automatically.
5. Cross-check GitHub directly for the same workflow:
   `curl -fsS -H "Authorization: Bearer $TOKEN"
   "https://api.github.com/repos/<org>/<repo>/actions/runs?status=queued"
   | jq '.workflow_runs | length'`. This rules out a dashboard-side
   miscount vs a real server-side queue.

## Remediation

- **Trigger an immediate purge from the dashboard:** `curl -fsS -X POST
  http://localhost:8321/api/queue/purge-stale`. This calls the same
  helpers as the hourly cron (`backend/queue_cleanup.py`) but on demand.
  Re-probe `/api/queue/stale` until the count returns to its normal
  baseline.
- **Re-enable / fix the hourly cron** if it has been silent: confirm
  `deploy/scheduled-dashboard-maintenance.sh` is wired into crontab on
  this host; re-install with `bash deploy/install-runner-maintenance.sh`
  if needed. Verify with `crontab -l | grep maintenance`.
- **If the purge keeps re-filling:** the real problem is on the dispatch
  side, not the cleanup side. Pause the offending workflow's schedule,
  investigate the source of the burst, and only re-enable once the
  inflow rate is back below the runner pickup rate.
- **Operator-driven cancel for a single workflow:** use the Workflows
  tab's bulk-cancel control, or hit
  `POST /api/runs/{run_id}/cancel` per-run for a targeted cleanup.

Automated remediation script reference:

- `backend/queue_cleanup.py` — async helpers behind `/api/queue/stale`
  and `/api/queue/purge-stale`.
- `deploy/scheduled-dashboard-maintenance.sh` — hourly cron that triggers
  the purge plus token refresh and log rotation.
- `deploy/install-runner-maintenance.sh` — installs the cron entry on a
  fresh host.

Escalation contact: @dieterolson.

## Postmortem template

```
Incident: queue-stuck YYYY-MM-DD HH:MM UTC
Detected by: <Queue Health red | operator report | external probe>
Duration: <minutes>
Impact: <which workflows backed up, how many runs>

Timeline:
- HH:MM Z — stale count first crossed alert threshold
- HH:MM Z — operator initiated /api/queue/purge-stale
- HH:MM Z — cron / inflow root cause confirmed
- HH:MM Z — queue back to baseline

Root cause: <cron silent | cleanup helper exception | dispatch burst>
Trigger: <recent deploy | workflow change | runner outage>
Resolution: <command(s) run, link to fix PR if any>

Follow-ups:
- [ ] add alert if /api/queue/stale length > N for > 30 min
- [ ] confirm scheduled-dashboard-maintenance.sh runs hourly on every host
- [ ] reduce burst-dispatch source if the inflow itself is the problem
```
