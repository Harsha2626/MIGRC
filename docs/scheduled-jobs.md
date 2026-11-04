# Scheduled jobs

MIGRC has no built-in scheduler. Run `flask run-daily-jobs` once a day from cron or a
systemd timer. The job is idempotent: for every organization it creates today's compliance and
dashboard snapshots (once per day) and generates due/overdue notifications (policy reviews, vendor
assessments, audit deadlines, training SLAs, stale/expiring evidence), de-duplicated by
`dedupe_key`. Re-running it, or loading the dashboard afterwards, never creates duplicates.
The command exits non-zero if any organization fails (others are still processed).

Other commands:

- `flask seed-frameworks` - additively load the shared framework library (safe to re-run).
- `flask jobs-status` - per-organization latest snapshot dates and library size.

These examples assume the app lives in `/opt/migrc`, with a virtualenv at `/opt/migrc/venv`
and environment (DATABASE_URL, SECRET_KEY, ...) in `/opt/migrc/.env` (loaded by the app).
Adjust paths and user. Nothing here is installed automatically.

## cron

```cron
# m h dom mon dow  command
15 1 * * * cd /opt/migrc && FLASK_APP=app:create_app /opt/migrc/venv/bin/flask run-daily-jobs >> /var/log/migrc-daily-jobs.log 2>&1
```

## systemd timer

`/etc/systemd/system/migrc-daily-jobs.service`

```ini
[Unit]
Description=MIGRC daily jobs (snapshots and notifications)
After=network.target

[Service]
Type=oneshot
User=migrc
WorkingDirectory=/opt/migrc
EnvironmentFile=-/opt/migrc/.env
Environment=FLASK_APP=app:create_app
ExecStart=/opt/migrc/venv/bin/flask run-daily-jobs
```

`/etc/systemd/system/migrc-daily-jobs.timer`

```ini
[Unit]
Description=Run MIGRC daily jobs every day

[Timer]
OnCalendar=*-*-* 01:15:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

Enable and inspect:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now migrc-daily-jobs.timer
systemctl list-timers migrc-daily-jobs.timer
journalctl -u migrc-daily-jobs.service -n 50
```

A failed run leaves the service in `failed` state (non-zero exit), which monitoring can alert on.

## Notes

- Do not run several instances at the same moment. Snapshot creation is protected by database
  unique constraints, but notification de-duplication is a check-then-insert, so truly
  simultaneous runs could rarely double-notify.
- Dates use the server's local date (`date.today()`); keep the host timezone consistent.
