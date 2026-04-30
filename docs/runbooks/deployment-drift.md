# Runbook: Deployment Drift (partial fleet update)

The fleet is running mixed dashboard versions. A `update-deployed.sh` run
landed on some hosts but not others, leaving the hub on (say) 4.0.1 while
one or more nodes are still on 3.x. Cross-fleet endpoints can mis-handle
each other's payloads, and the Fleet tab flags drift.

## Symptoms

- Fleet tab shows nodes with different `version` values in the per-node
  card.
- Deployment Drift detection (`backend/deployment_drift.py`) reports
  non-zero drift; a banner appears on the Fleet tab.
- Cross-node calls (e.g. hub fan-out to node `/api/runners`) return
  unexpected 4xx because the schema differs by version.
- `GET /api/version` on each node returns a different `version` string.
- Operators report some nodes "look ancient" or are missing recently
  added tabs/features.

Detection signals:

- HTTP probe: `for url in <node-urls>; do curl -fsS "$url/api/version" |
  jq -r '.version'; done`. Any divergence is the signal.
- HTTP probe: `curl -fsS http://localhost:8321/api/deployment/drift` (the
  endpoint backed by `backend/deployment_drift.py`).
- systemd unit: `runner-dashboard.service` on every node.
- Logs: `sudo journalctl -u runner-dashboard | grep -i drift`,
  `~/actions-runners/dashboard/deployment.json` on each host, and the
  list of timestamped `.bak.YYYYMMDD_HHMMSS` directories left by prior
  deploys.

## Diagnosis

1. List the node URLs from `backend/machine_registry.yml` on the hub, or
   from the `--fleet-nodes` argument used by `setup.sh`. These are the
   authoritative endpoints to probe.
2. Hit `GET /api/version` on every node and tabulate the versions. The
   hub is the source of truth; any node that does not match is drifted.
3. Read each drifted node's `deployment.json`
   (`cat ~/actions-runners/dashboard/deployment.json` on that host or
   over Tailscale SSH). Note `version`, `git_sha`, and the install
   timestamp. Compare to the hub's `deployment.json` to see how far back
   the drift is.
4. Check whether the most recent `update-deployed.sh` on that node
   succeeded or failed. The deploy log is captured in journalctl on the
   target host; a failed run will leave the `.bak.YYYYMMDD_HHMMSS`
   directory but no version bump in `deployment.json`.
5. Re-probe `/api/deployment/drift` after step 4 to confirm the hub agrees
   with what you found by hand. A mismatch between the hub's drift
   report and reality points at a problem in
   `backend/deployment_drift.py` itself, not at the fleet.

## Remediation

- **Catch the lagging node up:** SSH to the drifted node (over Tailscale)
  and run `bash deploy/update-deployed.sh`. The script creates a
  timestamped backup before any changes and restarts the service on
  success.
- **Use the artifact path for repeatable deploys:**
  `bash deploy/update-deployed.sh --artifact runner-dashboard-vX.Y.Z.tar.gz`
  ensures every host installs the same bytes.
- **If the update-deployed run fails on the lagging node:** read its
  journalctl, fix the underlying issue (commonly a venv permission, a
  pinned-dep mismatch, or disk space), and re-run. Do not roll the hub
  back to match the laggard.
- **Rollback as last resort:** if a recent hub deploy is itself broken,
  `bash deploy/rollback.sh` on every node returns the fleet to the
  previous known-good version. Drift is preferable to a fleet-wide
  outage; only roll back when the new version is the cause of a real
  incident.

After every remediation step, re-probe `/api/version` on all nodes and
confirm `/api/deployment/drift` reports clean.

Automated remediation script reference:

- `deploy/update-deployed.sh` — pulls and installs the new deploy on a
  single host (idempotent).
- `deploy/rollback.sh` — restores the most recent backup on a single
  host.
- `backend/deployment_drift.py` — the drift detector consumed by the
  dashboard's drift endpoint and the Fleet tab banner.

Escalation contact: @dieterolson.

## Postmortem template

```
Incident: deployment-drift YYYY-MM-DD HH:MM UTC
Detected by: <Fleet tab banner | drift endpoint | operator>
Duration: <minutes / hours / days drifted>
Impact: <which nodes, which features missing on which nodes>

Timeline:
- HH:MM Z — drift first observed
- HH:MM Z — laggard nodes identified (list)
- HH:MM Z — update-deployed re-run / rollback executed
- HH:MM Z — drift endpoint clean

Root cause: <failed deploy on node N | network during rollout | manual
                skip>
Trigger: <rollout script issue | host-side error | operator skipped node>
Resolution: <which nodes received which version, artifact ID if used>

Follow-ups:
- [ ] add per-node deploy verification to the rollout script
- [ ] alert on /api/deployment/drift non-empty for > 30 min
- [ ] document any host-side prerequisite that bit us this time
```
