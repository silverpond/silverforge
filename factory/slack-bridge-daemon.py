#!/usr/bin/env python3
"""
Persistent Slack -> agent bridge daemon.

Runs on the worker machine. Uses Slack Socket Mode (websocket) for instant
message delivery. Reads ~/factory/active-runs.json to route thread replies
to the correct tmux session.

Active runs file format:
  {
    "<thread_ts>": {
      "run_id": "abc123",
      "session": "factory-abc123"
    },
    ...
  }

Usage:
  slack-bridge-daemon.py start   -- start daemon in background
  slack-bridge-daemon.py stop    -- stop daemon
  slack-bridge-daemon.py status  -- check if running
  slack-bridge-daemon.py run     -- run in foreground (for debugging)
"""
import json
import os
import re
import signal
import subprocess
import sys
import time

FACTORY_DIR = os.path.expanduser("~/factory")
ACTIVE_RUNS_FILE = os.path.join(FACTORY_DIR, "active-runs.json")
PID_FILE = os.path.join(FACTORY_DIR, ".bridge-daemon.pid")
LOG_FILE = os.path.join(FACTORY_DIR, ".bridge-daemon.log")

SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "")

PYTHONPATH = "/nix/store/9dnf2b03cppfr26gplrz1p02ig82rx6c-python3.13-slack-sdk-3.38.0/lib/python3.13/site-packages"


def load_active_runs():
    try:
        with open(ACTIVE_RUNS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def send_to_session(session, text):
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{session}:0", text],
        timeout=5, capture_output=True,
    )
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{session}:0", "Enter"],
        timeout=5, capture_output=True,
    )


def run_daemon():
    sys.path.insert(0, PYTHONPATH)
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.request import SocketModeRequest
    from slack_sdk.socket_mode.response import SocketModeResponse
    from slack_sdk import WebClient

    web_client = WebClient(token=SLACK_BOT_TOKEN)
    bot_user_id = web_client.auth_test()["user_id"]
    print(f"[bridge-daemon] started, bot={bot_user_id}", flush=True)

    def handle(client: SocketModeClient, req: SocketModeRequest):
        client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

        if req.type != "events_api":
            return

        event = req.payload.get("event", {})
        if event.get("type") != "message":
            return
        if event.get("subtype"):  # edits, deletions, bot_message etc.
            return
        if event.get("user") == bot_user_id:
            return

        thread_ts = event.get("thread_ts")
        if not thread_ts:
            return  # not a thread reply

        channel = event.get("channel")
        if SLACK_CHANNEL_ID and channel != SLACK_CHANNEL_ID:
            return  # not our channel

        runs = load_active_runs()
        run = runs.get(thread_ts)
        if not run:
            return  # not a factory thread

        text = event.get("text", "").strip()
        if not text:
            return

        session = run["session"]
        run_id = run["run_id"]
        print(f"[bridge-daemon] run={run_id} -> {session}: {text[:80]}", flush=True)
        send_to_session(session, text)

    socket_client = SocketModeClient(
        app_token=SLACK_APP_TOKEN,
        web_client=web_client,
    )
    socket_client.socket_mode_request_listeners.append(handle)
    socket_client.connect()
    print("[bridge-daemon] connected to Slack Socket Mode", flush=True)

    # Keep alive
    while True:
        time.sleep(10)


# ── CLI commands ─────────────────────────────────────────────────────────────

def cmd_run():
    run_daemon()


def cmd_start():
    if _is_running():
        print("bridge-daemon is already running")
        return
    if not SLACK_APP_TOKEN or not SLACK_BOT_TOKEN:
        print("Error: SLACK_APP_TOKEN and SLACK_BOT_TOKEN must be set", file=sys.stderr)
        sys.exit(1)
    os.makedirs(FACTORY_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as log:
        proc = subprocess.Popen(
            [sys.executable, __file__, "run"],
            env={**os.environ, "PYTHONPATH": PYTHONPATH},
            stdout=log, stderr=log,
            start_new_session=True,
        )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    time.sleep(1)
    if _is_running():
        print(f"bridge-daemon started (pid={proc.pid})")
    else:
        print("bridge-daemon failed to start, check logs:", LOG_FILE, file=sys.stderr)
        sys.exit(1)


def cmd_stop():
    pid = _read_pid()
    if not pid:
        print("bridge-daemon is not running")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        os.unlink(PID_FILE)
    except FileNotFoundError:
        pass
    print("bridge-daemon stopped")


def cmd_status():
    if _is_running():
        print(f"bridge-daemon is running (pid={_read_pid()})")
    else:
        print("bridge-daemon is not running")


def _read_pid():
    try:
        return int(open(PID_FILE).read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_running():
    pid = _read_pid()
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"run": cmd_run, "start": cmd_start, "stop": cmd_stop, "status": cmd_status}.get(
        cmd, lambda: print(f"Unknown command: {cmd}", file=sys.stderr)
    )()
