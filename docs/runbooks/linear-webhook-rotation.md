# Runbook: Linear Webhook Secret Rotation

Rotate the shared secret used to sign inbound Linear webhooks. Triggered
either on a regular cadence (planned) or on suspicion of compromise
(unplanned). Until the rotation completes, the dashboard will reject
inbound Linear webhooks (deliberately — that is the safe failure mode).

## Symptoms

Planned rotation has no failure symptoms; you initiate it on schedule.
Unplanned rotation is triggered by one of:

- Linear-driven dashboard updates (issue create/update reflected in the
  Linear tab) stop arriving even though the Linear app shows the
  webhook delivered successfully.
- `journalctl -u runner-dashboard | grep -i "webhook\|signature"` shows
  repeated `signature mismatch` rejections on `/api/linear/webhook`.
- A leak audit (e.g. found in a chat log, a commit, or an old backup)
  forces immediate rotation.
- Linear's webhook-delivery log shows `401` from the dashboard endpoint.

Detection signals:

- HTTP probe: `curl -fsS -X POST -H "Linear-Signature: bogus"
  http://localhost:8321/api/linear/webhook -d '{}'` — a healthy endpoint
  returns 401 quickly. After a successful rotation, real Linear-signed
  payloads should return 200 again.
- systemd unit: `runner-dashboard.service`.
- Logs: `sudo journalctl -u runner-dashboard | grep -E "linear|webhook"`,
  Linear admin → Webhooks → Recent deliveries.

## Diagnosis

1. Confirm the rotation is actually needed. If unplanned, capture the
   evidence (leak source, time of suspected compromise) so the postmortem
   has a starting point.
2. Locate the current secret on the dashboard host:
   `sudo -u runner cat ~/.config/runner-dashboard/env | grep -i
   LINEAR_WEBHOOK_SECRET`. Note the suffix (last 4 chars) for confirmation
   later. If multiple env files exist (deploy vs. dev), confirm which one
   the running service is loading.
3. Confirm the dashboard is currently verifying signatures. Send a
   bogus-signature request as in the detection probe; expect 401. If you
   get 200, the verification path is broken and that is a bigger
   incident than rotation.
4. Open the Linear admin Webhooks page and identify the webhook entry
   that points at the dashboard's Funnel hostname. Confirm only one
   entry exists; multiples are an opportunity for stale secrets.
5. Coordinate timing. Webhook deliveries during the rotation window will
   fail and Linear will retry. For planned rotations, schedule during a
   low-activity window; for unplanned rotations, accept the gap.

## Remediation

Rotation is a four-step swap. The dashboard supports a brief overlap by
accepting either of two secrets if both env vars are set; if your build
does not, expect a sub-minute gap and let Linear's retry handle it.

1. Generate a new secret: `python -c "import secrets;
   print(secrets.token_urlsafe(48))"`. Store it in the password manager
   immediately.
2. Update the secret in Linear's webhook UI to the new value. Capture the
   new value displayed there in the password manager.
3. On the dashboard host, edit `~/.config/runner-dashboard/env` and set
   `LINEAR_WEBHOOK_SECRET=<new>` (and the overlap variable if your build
   supports it). Then `sudo systemctl restart runner-dashboard`.
4. From the Linear admin UI, click "Send test event" on the webhook.
   Confirm a 200 response and that
   `sudo journalctl -u runner-dashboard --since "5 min ago" | grep
   linear` shows the test delivery succeeded. Re-probe with a bogus
   signature to confirm rejection still works.

Automated remediation script reference:

- `deploy/configure-env-vars.sh` — interactive helper that rewrites the
  service env file; useful when a clean rewrite is preferred to an
  in-place edit.
- The dashboard service is restarted with `sudo systemctl restart
  runner-dashboard`. There is no Linear-specific deploy script.

Escalation contact: @dieterolson. For Linear-side problems (webhook UI,
delivery retries) escalate to whoever owns the Linear workspace admin.

## Postmortem template

```
Incident: linear-webhook-rotation YYYY-MM-DD HH:MM UTC
Type: <planned | unplanned (compromise)>
Duration: <gap during which webhooks were rejected, in seconds>
Impact: <missed Linear updates, retry pressure, etc.>

Timeline:
- HH:MM Z — rotation initiated
- HH:MM Z — Linear UI updated
- HH:MM Z — dashboard env updated and service restarted
- HH:MM Z — test event delivered successfully

Root cause (unplanned only): <leak source, time of compromise>
Trigger: <scheduled rotation | leak audit | external report>
Resolution: <new secret in vault, old secret invalidated>

Follow-ups:
- [ ] confirm calendar reminder for next planned rotation
- [ ] add overlap-secret support if not present (planned-zero-downtime)
- [ ] audit any place the old secret might still be cached
```
