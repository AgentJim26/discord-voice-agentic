#!/bin/bash
set -e
in="$1"
tmp="$(mktemp --suffix=.wav)"
trap 'rm -f "$tmp"' EXIT
ffmpeg -y -v error -i "$in" -ar 16000 -ac 1 -c:a pcm_s16le "$tmp"
PY=/home/jim/.local/venvs/stt/bin/python
SERVER=/home/jim/.openclaw/workspace/scripts/vosk_server.py
CLIENT=/home/jim/.openclaw/workspace/scripts/vosk_client.py
SOCK="$HOME/.cache/vosk-stt.sock"
if [ ! -S "$SOCK" ] || ! pgrep -f "$SERVER" >/dev/null 2>&1; then
  rm -f "$SOCK"
  nohup "$PY" "$SERVER" >/tmp/vosk-server.log 2>&1 &
  for _ in $(seq 1 50); do
    [ -S "$SOCK" ] && break
    sleep 0.1
  done
fi
if [ -S "$SOCK" ] && "$PY" "$CLIENT" "$SOCK" "$tmp" 2>/dev/null; then
  exit 0
fi
# Fallback if the persistent server cannot be reached.
exec "$PY" /home/jim/.openclaw/workspace/scripts/vosk_stt.py "$tmp"
