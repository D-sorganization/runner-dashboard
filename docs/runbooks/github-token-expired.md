# Runbook: GitHub Token Expired (5xx from /api/runs)

The dashboard's `GITHUB_TOKEN` (a fine-grained PAT or GitHub App installation
token) has expired, been revoked, or lost the scopes the dashboard requires.
Every `/api/*` route that proxies the GitHub REST API starts returning 5xx.

## Symptoms

- The Workflows, Fleet, Queue, and Org tabs all show error toasts at once;
  isolated tab failures are unlikely to be a token problem.
- `GET /api/runs`, `GET /api/runners`, and `GET /api/workflows` return
  `500` or `502` with bodies referencing `401 Unauthorized` from
  `api.github.com`.
- `GET /api/health` may still return `ok` because health does not exercise
  the GitHub client.
- `journalctl -u runner-dashboard` shows repeated lines containing
  `httpx.HTTPStatusError: 401` or `Bad credentials`.
- The token's expiry date in the GitHub UI (Settings → Developer settings →
  Personal access tokens) is in the past, or the Maxwell-rotated token file
  on disk has not been refreshed in days.

Detection signals:

- HTTP probe: `curl -fsS -o /dev/null -w "%{http_code}\n"
  http://localhost:8321/api/runs?per_page=1` returns `500`/`502` while
  `/api/health` returns `200`.
- systemd unit: `runner-dashboard.service`.
- Logs: `sudo journalctl -u runner-dashboard | grep -E "401|Bad credentials"`.

## Diagnosis

1. Probe the dashboard surface to confirm the failure is broad: hit
   `/api/health`, `/api/runs?per_page=1`, and `/api/runners` from the host
   itself with `curl`. If health is green and the GitHub-backed routes are
   red, that is the token-expiry fingerprint.
2. Read the env file the service uses:
   `sudo -u runner cat ~/.config/runner-dashboard/env | grep -E
   "GITHUB_TOKEN|GH_TOKEN"`. Note the suffix of the token (last 4 chars) so
   you can confirm a swap later.
3. Test the token directly against GitHub:
   `curl -fsS -H "Authorization: Bearer $TOKEN" https://api.github.com/user
   | head`. A `401` confirms expiry/revocation; a `403` with
   `X-RateLimit-Remaining: 0` is a different incident (rate limit, not
   expiry).
4. Check the token's expiry and scope policy in GitHub. For PATs, the UI
   lists expiry; for GitHub App installation tokens, the `expires_at`
   appears in the install-token response. Confirm the token still owns
   `repo`, `workflow`, and `actions:read` (or the equivalent fine-grained
   scopes the deployment relies on).
5. Inspect the journal around the first failure to rule out a different
   root cause:
   `sudo journalctl -u runner-dashboard --since "30 min ago" | grep -E
   "401|403|httpx"`. Confirm the failures cluster and started together,
   not staggered (which would suggest a network or upstream incident).

## Remediation

- **Refresh on the host:** run `bash deploy/refresh-token.sh`. This script
  is the canonical way to rotate the dashboard token; it writes the new
  value to `~/.config/runner-dashboard/env` and restarts
  `runner-dashboard.service`.
- **Manual rotation if `refresh-token.sh` is unavailable:** generate a new
  PAT or app token in the GitHub UI with the documented scope set, edit
  `~/.config/runner-dashboard/env` to update `GITHUB_TOKEN`, then
  `sudo systemctl restart runner-dashboard`. Verify with
  `curl -fsS http://localhost:8321/api/runs?per_page=1`.
- **Verify post-rotation:** confirm `/api/runs`, `/api/runners`, and
  `/api/workflows` all return 200, and that the journal stops emitting
  `401` lines.

Automated remediation script reference:

- `deploy/refresh-token.sh` — rotates the dashboard token in place and
  restarts the service.
- `deploy/configure-env-vars.sh` — interactive helper for editing the
  service env file when a clean rewrite is needed.

Escalation contact: @dieterolson.

## Postmortem template

```
Incident: github-token-expired YYYY-MM-DD HH:MM UTC
Detected by: <alert | operator report | dashboard probe>
Duration: <minutes>
Impact: <which tabs / which org operations were affected>

Timeline:
- HH:MM Z — first 5xx burst observed
- HH:MM Z — token confirmed expired/revoked against api.github.com
- HH:MM Z — replacement token issued
- HH:MM Z — service restarted, traffic recovered

Root cause: <one paragraph — expired PAT, missed rotation, scope removal>
Trigger: <scheduled expiry | manual revocation | scope policy change>
Resolution: <which token, which scope set, when it next expires>

Follow-ups:
- [ ] add calendar reminder before next expiry (owner: @, due: YYYY-MM-DD)
- [ ] confirm refresh-token.sh ran in cron (owner: @, due: YYYY-MM-DD)
- [ ] add /api/health subprobe that exercises GitHub auth (owner: @)
```
