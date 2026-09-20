#!/usr/bin/env bash
# ==============================================================================
# JioPC XRDP Session Keeper Uninstaller
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BOLD}Uninstalling JioPC XRDP Session Keeper...${NC}"

systemctl --user stop xrdp-session-keeper.service 2>/dev/null || true
systemctl --user disable xrdp-session-keeper.service 2>/dev/null || true

rm -f "${HOME}/.config/systemd/user/xrdp-session-keeper.service"
rm -f "${HOME}/bin/xrdp-session-keeper.py"

systemctl --user daemon-reload

echo -e "${BOLD}${GREEN}✓ JioPC XRDP Session Keeper successfully uninstalled.${NC}"
