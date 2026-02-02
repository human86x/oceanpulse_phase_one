# OceanPulse Server Deployment & Access Instructions

This document contains all necessary credentials, commands, and script templates for interacting with the OceanPulse remote server (`oceanpulse.pt`).

## 1. Credentials

*   **Host:** `ftp.oceanpulse.pt` (or `cpp64.webserver.pt`)
*   **Protocol:** FTP (Port 21)
*   **User:** `oceanpul`
*   **Password:** `sagres_2025Xx`
*   **Web Root:** `public_html/`

## 2. Recommended Tools

We recommend using `lftp` for command-line interactions as it supports mirroring and is more robust than standard `ftp`.

**Install lftp (Linux):**
```bash
sudo apt install lftp
```

## 3. Common Operations

### Connect Interactively
```bash
lftp -u oceanpul,sagres_2025Xx ftp.oceanpulse.pt
```

### Upload a Folder (Mirror)
To upload a local folder `Buoy_build` to a remote folder `public_html/buoy`:
```bash
lftp -u oceanpul,sagres_2025Xx -e "set ftp:ssl-allow no; mirror -R Buoy_build public_html/buoy; quit" ftp.oceanpulse.pt
```

### List Remote Files
```bash
lftp -u oceanpul,sagres_2025Xx -e "set ftp:ssl-allow no; ls public_html; quit" ftp.oceanpulse.pt
```

## 4. Helper Scripts

You can save these scripts in your project root to automate tasks.

### `ftp.sh` (Interactive LFTP Shell)
```bash
#!/bin/bash
lftp -u oceanpul,sagres_2025Xx ftp.oceanpulse.pt
```

### `mount_ftp.sh` (Mount as Local Drive via GIO/GVFS)
Useful for browsing files with a file manager.
```bash
#!/bin/bash
gio mount ftp://oceanpul:sagres_2025Xx@ftp.oceanpulse.pt/
# Access point usually at: /run/user/1000/gvfs/ftp:host=ftp.oceanpulse.pt,user=oceanpul
```

### `deploy_legacy.sh` (Standard FTP)
Useful for simple file uploads without `lftp`.
```bash
#!/bin/bash
HOST="ftp.oceanpulse.pt"
USER="oceanpul"
PASS="sagres_2025Xx"

ftp -inv $HOST <<EOF
user $USER $PASS
cd public_html
# Example uploads:
# put local_file.html remote_file.html
bye
EOF
```

## 5. Other Services

*   **Email:** `info@oceanpulse.pt` / `sagres_2025Xx` (IMAP: 993, SMTP: 465)
*   **Database/Finance:** Ensure backups are maintained locally.
