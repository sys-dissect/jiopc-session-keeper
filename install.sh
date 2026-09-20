#!/usr/bin/env bash
# ==============================================================================
# JioPC XRDP Session Keeper Installer
# Keeps desktop sessions permanently alive across disconnections without root/sudo.
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}=================================================================${NC}"
echo -e "${BOLD}${CYAN}          JioPC XRDP Session Keeper Installation                 ${NC}"
echo -e "${BOLD}${CYAN}=================================================================${NC}"

# Determine repository root or download source directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_SRC="${SCRIPT_DIR}/bin/xrdp-session-keeper.py"
SVC_SRC="${SCRIPT_DIR}/systemd/xrdp-session-keeper.service"

DEST_BIN_DIR="${HOME}/bin"
DEST_BIN="${DEST_BIN_DIR}/xrdp-session-keeper.py"
DEST_SVC_DIR="${HOME}/.config/systemd/user"
DEST_SVC="${DEST_SVC_DIR}/xrdp-session-keeper.service"
VENV_DIR="${HOME}/.local/venv"

echo -e "\n${BOLD}[1/5] Setting up Python environment...${NC}"
mkdir -p "${HOME}/.local"
if [ ! -f "${VENV_DIR}/bin/python" ]; then
    if command -v uv >/dev/null 2>&1; then
        echo "Using uv to create virtual environment..."
        uv venv "${VENV_DIR}"
    else
        echo "Using python3 -m venv..."
        python3 -m venv "${VENV_DIR}"
    fi
fi

# Ensure grpcio is available
if ! "${VENV_DIR}/bin/python" -c "import grpc" 2>/dev/null; then
    echo "Installing grpcio & protobuf in ${VENV_DIR}..."
    if command -v uv >/dev/null 2>&1; then
        uv pip install --python "${VENV_DIR}/bin/python" grpcio protobuf
    else
        "${VENV_DIR}/bin/python" -m pip install --quiet grpcio protobuf
    fi
else
    echo -e "${GREEN}✓ grpcio already installed.${NC}"
fi

echo -e "\n${BOLD}[2/5] Installing Session Keeper daemon...${NC}"
mkdir -p "${DEST_BIN_DIR}"
cp "${BIN_SRC}" "${DEST_BIN}"
chmod +x "${DEST_BIN}"
echo -e "${GREEN}✓ Installed ${DEST_BIN}${NC}"

echo -e "\n${BOLD}[3/5] Installing systemd user service...${NC}"
mkdir -p "${DEST_SVC_DIR}"
cp "${SVC_SRC}" "${DEST_SVC}"
echo -e "${GREEN}✓ Installed ${DEST_SVC}${NC}"

echo -e "\n${BOLD}[4/5] Enabling systemd user linger...${NC}"
# Linger ensures systemd --user services remain active when the interactive session closes
loginctl enable-linger "$(id -u)" 2>/dev/null || loginctl enable-linger "$(whoami)" 2>/dev/null || true
echo -e "${GREEN}✓ User lingering enabled.${NC}"

echo -e "\n${BOLD}[5/5] Activating service...${NC}"
systemctl --user daemon-reload
systemctl --user enable xrdp-session-keeper.service
systemctl --user restart xrdp-session-keeper.service

sleep 1
if systemctl --user is-active --quiet xrdp-session-keeper.service; then
    echo -e "${BOLD}${GREEN}=================================================================${NC}"
    echo -e "${BOLD}${GREEN}  ✓ Session Keeper is ACTIVE and successfully armed!             ${NC}"
    echo -e "${BOLD}${GREEN}=================================================================${NC}"
    echo -e "\n${BOLD}What this protects you from:${NC}"
    echo -e "  • ${CYAN}Tier 1 Defeat:${NC} Xorg local 900s (15m) idle/disconnect killswitch disengaged."
    echo -e "  • ${CYAN}Cloud Continuity:${NC} Cloud broker session state kept active across disconnections."
    echo -e "  • ${CYAN}Idle Defeat:${NC} Screen blanking / idle disconnect prevented while connected."
    echo -e "  • ${CYAN}Input Safety:${NC} Automatic pointer grab release and window manager sanity across reconnects."
    echo -e "\n${BOLD}How to verify:${NC}"
    echo -e "  1. Leave your apps (terminals, code, builds) running."
    echo -e "  2. Disconnect your RDP client / browser for 20+ minutes (exceeding the 15-minute limit)."
    echo -e "  3. Reconnect — your desktop session and all applications will be right where you left them!"
    echo -e "\n${BOLD}Check status anytime:${NC}"
    echo -e "  systemctl --user status xrdp-session-keeper"
    echo -e "  tail -f ~/.local/state/session-keeper.log\n"
else
    echo -e "${RED}Warning: Service failed to start immediately. Check logs with:${NC}"
    echo -e "  journalctl --user -u xrdp-session-keeper -n 30\n"
    exit 1
fi
