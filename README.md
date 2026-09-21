# JioPC Session Keeper: Persistent Background Sessions

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20JioPC-blue.svg)]()
[![Permissions](https://img.shields.io/badge/Root-Not%20Required%20(100%25%20User--Space)-success.svg)]()

> **Maintain persistent desktop sessions across disconnections on JioPC.** Keep your graphical desktop, background compilations, dev servers, terminals, and IDEs running uninterrupted without requiring root/sudo.

---

## The Problem: Disconnect & Idle Session Teardown

On JioPC remote cloud desktops, closing your browser tab, disconnecting your RDP client, or experiencing a temporary network drop triggers an automatic 15-minute timeout that terminates your graphical session and resets your environment:

- **Local Display Teardown**: The remote display server terminates after 900 seconds of an empty connection socket.
- **Cloud Orchestrator Reclamation**: The cloud broker reclaims the compute node if the session remains in a disconnected state for 15 minutes.
- **Why Basic Workarounds Failed**: Standard user-space tricks like `loginctl enable-linger` or mouse-jiggler scripts only affect client-side idle timeouts while actively connected; they cannot stop the teardown sequence once the network connection drops.

---

## The Solution: Autonomous Session Keeper Daemon

The **Session Keeper** is a lightweight, non-root background daemon running under `systemd --user` that provides complete session continuity:

1. **Session Continuity Across Disconnections**:
   The moment an external client disconnects, the daemon immediately attaches a local loopback handler to maintain the display socket state, resetting the local 15-minute countdown.
2. **Session State Synchronization**:
   It emits session continuity heartbeats to keep the remote orchestrator informed that background tasks are active, preventing cloud-side node reclamation.
3. **Seamless Handover on Reconnect**:
   When you reconnect from your client, the daemon immediately yields priority, smoothly handing over the display to your incoming session.
4. **Pointer & Window Manager Sanitization**:
   On disconnect and reconnect, the daemon automatically refreshes window manager grabs and clears any trapped pointer states, ensuring mouse clicks, right-clicks, and scrolling always work immediately.
5. **Idle Screen Lockout Prevention**:
   While actively connected, the daemon sends periodic keep-alives to prevent unnecessary screen blanking.

---

## Step 0: Getting a Working Terminal via Chrome & ttyd (No Hotkeys Needed)

Stock JioPC does not provide terminal icons in the start menu, has no graphical terminal emulators (`gnome-terminal`, `xterm`) pre-installed, and keyboard shortcuts (`Ctrl + Alt + T`, `Alt + F2`) are typically intercepted by your local client OS. *(Note: Previous Flatpak-based methods like PuTTY `pterm` no longer work due to sandbox portal restrictions).*

Instead, you can use **`ttyd`**—a standalone, single-file web terminal that runs a full interactive Linux bash shell inside your pre-installed **Google Chrome** browser (`http://localhost:7681`). No root/sudo permissions are required.

### Part 1: Download `ttyd` via Chrome
1. In JioPC, open **Google Chrome** (click the desktop icon or find it in the start menu).
2. Copy and paste this download link into the Chrome address bar, then press **Enter**:
   ```text
   https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64
   ```
3. Chrome will download `ttyd.x86_64` into your **Downloads** folder (`~/Downloads`).
   > *Tip: If Chrome shows a warning prompt saying "This file may harm your computer", click **Keep**.*

### Part 2: Create the One-Click "Web Terminal" Action in File Manager
1. Open **File Manager** (double-click the **Downloads** or **Computer** folder on your desktop).
2. In the top menu bar, click: **`Edit` → `Configure custom actions...`**.
3. Click the **`+`** (Add) button on the right side.
4. In the **Basic** tab:
   - **Name**: `Open Web Terminal`
   - **Description**: `Launch bash terminal in Google Chrome`
   - **Command**: Copy and paste this exact command into the box:
     ```bash
     bash -c "ls ~/Downloads/ttyd* >/dev/null 2>&1 || curl -sL https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64 -o ~/Downloads/ttyd.x86_64; chmod +x ~/Downloads/ttyd*; pgrep -f ttyd >/dev/null || nohup ~/Downloads/ttyd* -W -p 7681 bash >/dev/null 2>&1 & sleep 1; google-chrome http://localhost:7681"
     ```
5. In the **Appearance Conditions** tab:
   - Check **Directories** (or leave all checked).
6. Click **OK**, then click **Close**.

### Part 3: Launch Your Terminal!
1. **Right-click** anywhere in the empty space inside **File Manager**.
2. Click **`Open Web Terminal`**.
3. 👉 **Google Chrome will open a new tab at `http://localhost:7681` with your active bash terminal!**

> **Note**: For all future sessions, simply right-click in File Manager and select `Open Web Terminal`, or open Chrome and navigate to `http://localhost:7681`.

---

## Quick Installation (Zero Root Required)

Once in your terminal inside JioPC, run:

```bash
git clone https://github.com/sys-dissect/jiopc-session-keeper.git
cd jiopc-session-keeper && ./install.sh
```

The installer will:
1. Create a lightweight user-space Python environment with `grpcio`.
2. Install the daemon binary into `~/bin/xrdp-session-keeper.py`.
3. Enable `systemd` user lingering (`loginctl enable-linger`) so background services survive disconnections.
4. Enable and start `xrdp-session-keeper.service`.

---

## Testing & Verification Guide

To test that your session survives beyond the 15-minute limit:

1. **Open your tools**:
   Leave a terminal open running a task (or a document open in your text editor).
2. **Disconnect**:
   Close your RDP client (FreeRDP, Windows Remote Desktop, or browser tab).
3. **Wait at least 18 to 20 minutes**:
   Set a timer on your phone for **20 minutes** (the default killswitch activates strictly at 15 minutes).
4. **Reconnect**:
   Log back into your JioPC session.
5. **Verify**:
   - Your open windows, editor, and terminals should remain exactly as you left them.
   - Verify the daemon log:
     ```bash
     tail -n 30 ~/.local/state/session-keeper.log
     ```
   - Verify uptime:
     ```bash
     uptime
     ```

---

## Checking Daemon Status

```bash
# Check service status
systemctl --user status xrdp-session-keeper.service

# Follow live daemon logs
tail -f ~/.local/state/session-keeper.log

# Check recent journal logs
journalctl --user -u xrdp-session-keeper -n 50 --no-pager
```

---

## Uninstallation

To completely remove the Session Keeper:

```bash
cd jiopc-session-keeper && ./uninstall.sh
```

---

## Contributing & Feedback

We welcome feedback, issues, and test reports from the community!
- If you test this on different JioPC subscription tiers or client types (Windows, Mac, Linux, Mobile, Web Browser), please report your results under [Issues](https://github.com/sys-dissect/jiopc-session-keeper/issues) or [Discussions](https://github.com/sys-dissect/jiopc-session-keeper/discussions).
- Tested on: **JioPC Enterprise / 8-vCPU Intel Xeon Platinum 8370C / Ubuntu 22.04 LTS**.

---

## License

[MIT License](LICENSE) © 2026 sys-dissect
