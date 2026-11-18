#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="${1:-$HOME/.openclaw/extensions/discord}"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$PLUGIN_DIR/openclaw.plugin.json" ]; then
  echo "Discord plugin not found at: $PLUGIN_DIR" >&2
  echo "Usage: $0 [path-to-discord-plugin]" >&2
  exit 1
fi

echo "Patching: $PLUGIN_DIR"
for file in \
  "dist/index.js" \
  "dist/.setup/voice-runtime-DDymtIw8.mjs" \
  "dist/.setup/provider-YP8gN9_o.mjs" \
  "openclaw.plugin.json"; do
  if [ -f "$PLUGIN_DIR/$file" ] && [ ! -f "$PLUGIN_DIR/$file.bak-$STAMP" ]; then
    cp -a "$PLUGIN_DIR/$file" "$PLUGIN_DIR/$file.bak-$STAMP"
  fi
done

cd "$PLUGIN_DIR"
for patch_file in index manifest voice-runtime provider; do
  echo "Applying patches/$patch_file.patch"
  patch -p1 < "$ROOT/patches/$patch_file.patch"
done

cp "$ROOT/plugin/voice-say-tool.js" "$PLUGIN_DIR/dist/"
cp "$ROOT/plugin/voice-agentic-tool.js" "$PLUGIN_DIR/dist/"

mkdir -p "$PLUGIN_DIR/assets"
cp "$ROOT/assets/agentic-wake.mp3" "$ROOT/assets/agentic-done.mp3" "$PLUGIN_DIR/assets/"

mkdir -p "$HOME/.openclaw/workspace/scripts"
cp "$ROOT/scripts/stt.sh" "$ROOT/scripts/vosk_stt.py" "$HOME/.openclaw/workspace/scripts/"
chmod +x "$HOME/.openclaw/workspace/scripts/stt.sh"

echo
echo "Installed."
echo "Next: merge config/openclaw.example.json5 into ~/.openclaw/openclaw.json,"
echo "then run: openclaw plugins reload discord --wait"
