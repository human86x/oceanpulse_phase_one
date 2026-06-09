#!/bin/bash
# SPEC-032 Internal Roadmap Panel — FTP deploy to oceanpulse.pt/deployment/
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRETS="$SCRIPT_DIR/secrets.env"
if [ ! -f "$SECRETS" ]; then
    echo "ERROR: $SECRETS not found. Copy ops/secrets.env.example and fill it in." >&2
    exit 1
fi
set -a; . "$SECRETS"; set +a

HOST="${OP_FTP_HOST:?OP_FTP_HOST missing in secrets.env}"
USER="${OP_FTP_USER:?OP_FTP_USER missing in secrets.env}"
PASS="${OP_FTP_PASS:?OP_FTP_PASS missing in secrets.env}"
REMOTE_PATH="public_html/deployment"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$PROJECT_ROOT/web_presentation/deployment"

echo "=== OceanPulse Deployment Panel — FTP Upload ==="
echo "Source: $SRC_DIR"
echo "Target: $HOST/$REMOTE_PATH"
echo ""

if [ ! -d "$SRC_DIR" ]; then
    echo "ERROR: source directory not found: $SRC_DIR"
    exit 1
fi

lftp -u "$USER","$PASS" "$HOST" <<EOF
set ssl:verify-certificate no
set ftp:ssl-allow yes
set ftp:ssl-force no
mkdir -p $REMOTE_PATH
mkdir -p $REMOTE_PATH/assets
mkdir -p $REMOTE_PATH/data
mkdir -p $REMOTE_PATH/data/backups
cd $REMOTE_PATH
put $SRC_DIR/index.php
put $SRC_DIR/login.php
put $SRC_DIR/logout.php
put $SRC_DIR/api.php
put $SRC_DIR/config.php
put $SRC_DIR/.htaccess
put $SRC_DIR/robots.txt
cd assets
put $SRC_DIR/assets/app.js
put $SRC_DIR/assets/app.css
cd ..
cd data
put $SRC_DIR/data/.htaccess
put $SRC_DIR/data/roadmap_v3.json
bye
EOF

echo ""
echo "=== Deploy complete ==="
echo "URL:      https://oceanpulse.pt/deployment/"
echo "Password: (see web_presentation/deployment/config.php — hash only)"
