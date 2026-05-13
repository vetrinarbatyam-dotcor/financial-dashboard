#!/bin/bash
# OR Finance — deploy to Contabo /home/claude-user/Finance/
# Run from local: bash Finance/deploy.sh

set -e

SERVER="claude-user@167.86.69.208"
REMOTE_DIR="/home/claude-user/Finance"

echo "==> Syncing backend files..."
rsync -avz --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  Finance/backend/ ${SERVER}:${REMOTE_DIR}/backend/

echo "==> Setting up environment on server..."
ssh ${SERVER} << 'REMOTE'
set -e
cd /home/claude-user/Finance

# Create venv if missing
if [ ! -d "venv" ]; then
  python3.12 -m venv venv
  echo "Virtual environment created."
fi

# Install / upgrade dependencies
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r backend/requirements.txt -q

# Ensure DB directory exists
mkdir -p /home/claude-user/Finance

# Reload systemd service
if systemctl is-active --quiet or-finance; then
  sudo systemctl restart or-finance
  echo "Service restarted."
else
  echo "Service 'or-finance' not found — install finance.service first."
fi
REMOTE

echo ""
echo "==> First-time setup (if service not yet installed):"
echo "    scp Finance/finance.service claude-user@167.86.69.208:/tmp/"
echo "    ssh claude-user@167.86.69.208 'sudo mv /tmp/finance.service /etc/systemd/system/or-finance.service && sudo systemctl daemon-reload && sudo systemctl enable or-finance && sudo systemctl start or-finance'"
echo ""
echo "==> Deploy complete."
