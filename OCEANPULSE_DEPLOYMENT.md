# OceanPulse Server Deployment

This document covers how the OceanPulse public dashboard is deployed to
`oceanpulse.pt`. The actual FTP credentials live in `ops/secrets.env`
(gitignored). See `ops/secrets.env.example` for the schema.

## 1. Connection

The public site is served from a shared host reached via FTP.

```
Host:     ftp.oceanpulse.pt
Port:     21 (FTP)
Web root: public_html/
User:     $OP_FTP_USER       # from ops/secrets.env
Password: $OP_FTP_PASS       # from ops/secrets.env
```

## 2. Recommended Tool

We use `lftp` for command-line transfers (supports mirroring, SSL toggle):

```bash
sudo apt install lftp
```

## 3. Deploy Scripts

Two scripts handle the standard deploy paths. Both source
`ops/secrets.env` automatically:

| Script | Target | Purpose |
|---|---|---|
| `ops/deploy_vps.sh` | VPS Obs Center (`vps-ovh`) | Sync `obs_center/` to the VPS |
| `ops/deploy_roadmap_panel.sh` | `oceanpulse.pt/deployment/` | Push the internal roadmap panel |

Example interactive session (after `secrets.env` is in place):

```bash
set -a; . ops/secrets.env; set +a
lftp -u "$OP_FTP_USER,$OP_FTP_PASS" "$OP_FTP_HOST"
```

## 4. Public Dashboard FTP Relay

The Flask backend (`obs_center/app.py`) also publishes summary frames to
the public dashboard via FTP on a fixed cadence. The credentials come
from `OP_FTP_HOST`, `OP_FTP_USER`, `OP_FTP_PASS` in `secrets.env` and are
loaded by systemd via `EnvironmentFile=` in `ops/obs-center.service`.

## 5. Other Services

- **Email:** `info@oceanpulse.pt` (IMAP 993, SMTP 465) — credentials in
  `ops/secrets.env` if scripted access is needed.
