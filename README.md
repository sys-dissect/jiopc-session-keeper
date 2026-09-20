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

## Step 0: Getting a Working Terminal on Stock JioPC (No Hotkeys)

Stock JioPC does not provide terminal icons in the start menu, and client-side operating systems (like Fedora/GNOME or macOS) often intercept keyboard shortcuts like `Alt + F2`. 

However, **PuTTY** is pre-installed as a system Flatpak (`uk.org.greenend.chiark.sgtatham.putty`), which includes **`pterm`**—a pure-GTK, standalone X11 terminal. You can launch a host terminal using **100% mouse clicks**:

1. Open **File Manager** (double-click "Computer" or "Downloads" on the desktop).
2. In the top menu bar, click: **`Edit` → `Configure custom actions...`**.
3. Click the **`+`** (Add) button on the right.
4. In the **Basic** tab:
   - **Name**: `Terminal`
   - **Command**:
     ```bash
     flatpak run --command=pterm uk.org.greenend.chiark.sgtatham.putty -e flatpak-spawn --host bash
     ```
5. In the **Appearance Conditions** tab:
   - Check **Directories** (or leave all checked).
6. Click **OK**, then **Close**.

👉 **Right-click anywhere inside File Manager and click `Terminal`** to launch a native host bash shell!

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
