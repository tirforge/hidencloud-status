# 🐕 hidencloud-status — public watchdog dashboard

Read-only monitor for the HidenCloud renew pipeline. Shows: login health,
per-service days-left, last renew run, next cron. Alerts via Telegram on trouble.

**No secrets live in this repo. Ever.** Only `public/status.json` (health facts).

## Required secrets (repo Settings → Secrets → Actions)

| Secret | Required | Purpose |
|---|---|---|
| `HIDEN_COOKIE` | ✅ | read-only dashboard probe (same format as renew repo) |
| `STATUS_PAT` | ⚠️ recommended | classic PAT (`repo`, `workflow:read`) to read `tirforge/hidencloud_renew` runs + cron. Without it, the renew-workflow panel shows "unknown" |
| `TG_BOT_TOKEN` / `TG_CHAT_ID` | optional | Telegram alerts on unhealthy (skipped silently if unset) |

## Setup

1. Create this repo **public** (Pages on free plan needs public): `hidencloud-status`
2. Push these files, add secrets above
3. Repo Settings → Pages → Source: **Deploy from branch**, branch `main`, folder `/docs`
4. Dashboard: `https://<you>.github.io/hidencloud-status/`
5. Actions → run **HidenCloud Watchdog** once manually to seed `status.json`

## Why this exists

The renew workflow once went 11 days silent (frozen self-updating cron) and the
server got suspended with nobody noticing. This watchdog runs daily, publishes
proof-of-life, and shouts on Telegram when anything smells wrong. Its own daily
commits also keep the repo active, defeating GitHub's 60-day scheduled-workflow
auto-disable.
