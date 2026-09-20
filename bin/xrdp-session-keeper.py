#!/usr/bin/env python3
"""
JioPC Session Keeper Daemon
---------------------------
Maintains graphical desktop session continuity and background persistence on JioPC.

Operational Logic:
1. When a real user is connected via RDP/browser:
   - The keeper remains in passive STANDBY to never displace or interfere with the user.
   - Pokes the idle timeout socket periodically to suppress screen blanking.
2. When the user disconnects:
   - The keeper detects disconnect within 1 second and attaches to the local display socket.
   - Completes the 26-byte XR_MSG_VERSION + XR_MSG_INVALIDATE handshake, resetting local disconnect timers.
   - Emits session state synchronization to ensure background tasks remain uninterrupted.
3. When the user reconnects:
   - Yields priority immediately to the incoming client.
   - Refreshes window manager grabs so mouse clicks and scrolling work smoothly.
"""

import os
import sys
import time
import socket
import select
import struct
import subprocess
import glob
import logging

USER_ID = os.getuid()


def find_display_num():
    """Detect display number dynamically from environment or /var/run/xrdp socket."""
    disp_env = os.environ.get("DISPLAY")
    if disp_env and disp_env.startswith(":"):
        try:
            return int(disp_env.lstrip(":").split(".")[0])
        except ValueError:
            pass
    socks = glob.glob(f"/var/run/xrdp/{USER_ID}/xrdp_display_*")
    for s in socks:
        base = os.path.basename(s)
        num_str = base.replace("xrdp_display_", "")
        if num_str.isdigit():
            return int(num_str)
    return 10


DISPLAY_NUM = find_display_num()
SOCK_PATH = f"/var/run/xrdp/{USER_ID}/xrdp_display_{DISPLAY_NUM}"
LOG_DIR = os.path.expanduser("~/.local/state")
LOG_FILE = os.path.join(LOG_DIR, "session-keeper.log")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [session-keeper] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("session-keeper")

def find_session_ipc_socket():
    """Locate local broker session IPC socket in system runtime paths."""
    env_sock = os.environ.get("SESSION_IPC_SOCK")
    if env_sock and os.path.exists(env_sock):
        return env_sock
    for p in glob.glob("/run/**/grpc.sock", recursive=True):
        if os.path.exists(p) and not p.startswith("/run/user/"):
            return p
    return None


def spoof_session_connect(state=1):
    """
    Sends session state notification to local broker socket.
    States:
        0: Connect
        1: Reconnect
        2: Disconnect
    Sending Reconnect (1) maintains background session continuity across disconnects.
    """
    sock_path = find_session_ipc_socket()
    if not sock_path or not os.path.exists(sock_path):
        logger.debug("Session IPC socket does not exist or was not detected.")
        return False

    try:
        import grpc
        import pwd

        try:
            username = pwd.getpwuid(USER_ID).pw_name
        except Exception:
            username = str(USER_ID)

        def encode_varint(val):
            res = bytearray()
            while val > 0x7F:
                res.append((val & 0x7F) | 0x80)
                val >>= 7
            res.append(val & 0x7F)
            return bytes(res)

        ubytes = username.encode("utf-8")
        req_bytes = (
            bytes([1 << 3 | 2]) + encode_varint(len(ubytes)) + ubytes +
            bytes([2 << 3 | 0]) + encode_varint(DISPLAY_NUM) +
            bytes([3 << 3 | 0]) + encode_varint(os.getpid()) +
            bytes([4 << 3 | 0]) + encode_varint(state)
        )

        options = [("grpc.default_authority", "localhost")]
        with grpc.insecure_channel(f"unix:{sock_path}", options=options) as channel:
            call_fn = channel.unary_unary(
                "/XrdpEvent.XrdpEventService/SendSessionChange",
                request_serializer=lambda x: x,
                response_deserializer=lambda x: x,
            )
            call_fn(req_bytes, timeout=3.0)

        state_name = "Reconnect" if state == 1 else ("Connect" if state == 0 else f"State({state})")
        logger.info(f"Synchronized session state: {state_name} (Session continuity active).")
        return True
    except Exception as e:
        logger.warning(f"Session IPC notification: {e}")
        return False


def get_screen_resolution():
    """Detect current screen resolution from xrandr or fallback to standard."""
    try:
        out = subprocess.check_output(
            ["xrandr"], env=dict(os.environ, DISPLAY=f":{DISPLAY_NUM}"), stderr=subprocess.DEVNULL
        ).decode()
        for line in out.splitlines():
            if "*" in line:
                parts = line.strip().split()[0].split("x")
                return int(parts[0]), int(parts[1])
    except Exception:
        pass
    w = int(os.environ.get("XRDP_START_WIDTH", 1806))
    h = int(os.environ.get("XRDP_START_HEIGHT", 1054))
    return w, h


def is_external_client_connected():
    """
    Check /proc/net/unix to see if an ESTABLISHED socket is active on SOCK_PATH.
    Returns True if another client is connected, False if idle/listening only.
    """
    if not os.path.exists("/proc/net/unix"):
        return False

    try:
        with open("/proc/net/unix", "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 8 and parts[7] == SOCK_PATH:
                    # parts[5] is State: '01' is LISTENING, '03' is ESTABLISHED
                    if parts[5] == "03":
                        return True
    except Exception as e:
        logger.warning(f"Error reading /proc/net/unix: {e}")

    return False


def build_version_message():
    """
    Construct 26-byte XR_MSG_VERSION packet:
    Length: 26 (uint32)
    Type: 103 (uint16)
    Msg: 301 (uint16)
    Params: 0, 0, 0, 1 (4 x uint32)
    Pad: 0 (uint16)
    """
    return struct.pack("<IHHIIIIH", 26, 103, 301, 0, 0, 0, 1, 0)


def build_invalidate_message(width, height):
    """
    Construct 26-byte XR_MSG_INVALIDATE packet:
    Length: 26 (uint32)
    Type: 103 (uint16)
    Msg: 200 (uint16)
    Param1: 0 (uint32)
    Param2: (width << 16) | (height & 0xffff) (uint32)
    Params: 0, 0 (2 x uint32)
    Pad: 0 (uint16)
    """
    param2 = ((width & 0xFFFF) << 16) | (height & 0xFFFF)
    return struct.pack("<IHHIIIIH", 26, 103, 200, 0, param2, 0, 0, 0)


def poke_idle_timeout():
    """Send sound_playing to xrdp_idle_timeout_data_flow socket to prevent idle screen blanking/lockout."""
    idle_socks = glob.glob(f"/var/run/xrdp/{USER_ID}/xrdp_idle_timeout_data_flow_*")
    for s_path in idle_socks:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(s_path)
                s.sendall(b"sound_playing")
        except Exception:
            pass


def sanitize_pointer_state():
    """Ensure no mouse buttons remain stuck in pressed/grab state across disconnects."""
    try:
        # 1. Clear any stuck XTest buttons
        subprocess.run(
            ["xdotool", "mouseup", "1", "mouseup", "2", "mouseup", "3"],
            env=dict(os.environ, DISPLAY=f":{DISPLAY_NUM}"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        # 2. Reset xfwm4 cleanly to unfreeze any active pointer grabs (state 6)
        # and destroy orphaned full-screen InputOnly popup/grab windows.
        subprocess.Popen(
            ["xfwm4", "--replace"],
            env=dict(os.environ, DISPLAY=f":{DISPLAY_NUM}"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("Sanitized pointer state and refreshed window manager grabs.")
    except Exception as e:
        logger.warning(f"Error sanitizing pointer state: {e}")


def ensure_window_manager():
    """Ensure the xfwm4 window manager is running on the active display."""
    try:
        res = subprocess.run(
            ["pgrep", "-u", str(USER_ID), "-x", "xfwm4"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if res.returncode != 0:
            logger.warning("xfwm4 is not running! Reviving window manager...")
            subprocess.Popen(
                ["xfwm4", "--replace"],
                env=dict(os.environ, DISPLAY=f":{DISPLAY_NUM}"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info("Revived xfwm4 window manager.")
    except Exception as e:
        logger.warning(f"Error ensuring window manager: {e}")


def hold_session():
    """
    Connect to xrdp_display_10 to disengage the disconnect timer and hold the session.
    Stays connected until the real user connects (at which point Xorg closes this socket).
    """
    if not os.path.exists(SOCK_PATH):
        logger.debug(f"Socket {SOCK_PATH} does not exist yet. Waiting...")
        time.sleep(2)
        return

    logger.info("Real client disconnected. Attaching loopback session keeper to disengage 900s kill timer...")

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCK_PATH)
        sock.setblocking(False)

        w, h = get_screen_resolution()
        version_pkt = build_version_message()
        invalidate_pkt = build_invalidate_message(w, h)

        sock.sendall(version_pkt)
        time.sleep(0.05)
        sock.sendall(invalidate_pkt)

        logger.info(f"Connected to Xorg :10 successfully. Handshake sent (screen {w}x{h}). Local disconnect timer neutralized.")

        # Sanitize pointer grab state
        sanitize_pointer_state()

        # Neutralize Tier 2 Cloud Controller 15-minute disconnect timer
        spoof_session_connect(state=1)
        time.sleep(1.0)
        spoof_session_connect(state=1)
        last_cloud_heartbeat = time.time()

        # Keep draining socket until server closes it (when real user connects)
        buf = bytearray(65536)
        while True:
            r, _, _ = select.select([sock], [], [], 2.0)
            if r:
                try:
                    nbytes = sock.recv_into(buf)
                    if nbytes == 0:
                        logger.info("Real user connection detected (Xorg closed keeper socket). Yielding session...")
                        sanitize_pointer_state()
                        break
                except (BlockingIOError, InterruptedError):
                    continue
                except Exception as e:
                    logger.info(f"Socket closed ({e}). Yielding session...")
                    sanitize_pointer_state()
                    break

            # Periodic Tier 2 Cloud Controller Heartbeat (every 60s)
            now = time.time()
            if now - last_cloud_heartbeat >= 60.0:
                spoof_session_connect(state=1)
                last_cloud_heartbeat = now

            # Check if user linger or Xorg is still healthy
            if not os.path.exists(SOCK_PATH):
                logger.warning("Xorg socket disappeared!")
                break

    except ConnectionRefusedError:
        logger.warning(f"Connection to {SOCK_PATH} refused. Xorg may be restarting.")
        time.sleep(2)
    except Exception as e:
        logger.error(f"Error in hold_session: {e}")
        time.sleep(2)
    finally:
        try:
            sock.close()
        except Exception:
            pass


def main():
    logger.info(f"XRDP Session Keeper started for UID {USER_ID} on {SOCK_PATH}")

    # Ensure systemd linger is active
    try:
        subprocess.run(["loginctl", "enable-linger", str(USER_ID)], check=False)
    except Exception:
        pass

    last_idle_poke = 0.0
    last_connected_sync = 0.0
    while True:
        try:
            ensure_window_manager()
            if is_external_client_connected():
                # Real user is currently connected. Reset idle timer every 30s.
                now = time.time()
                if now - last_idle_poke >= 30.0:
                    poke_idle_timeout()
                    last_idle_poke = now
                # Synchronize session state with cloud broker every 60s while connected
                # to neutralize any stale cloud-side disconnect timers from transient drops.
                if now - last_connected_sync >= 60.0:
                    spoof_session_connect(state=1)
                    last_connected_sync = now
                logger.debug("Real user active. Standing by...")
                time.sleep(2)
            else:
                # Reset connected sync timestamp so reconnect is immediately signaled on return
                last_connected_sync = 0.0
                # No active client connected. Engage session hold.
                hold_session()
                # Short grace sleep after yielding before re-checking
                time.sleep(2)
        except KeyboardInterrupt:
            logger.info("Session keeper stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected loop exception: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
