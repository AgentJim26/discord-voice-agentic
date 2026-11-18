# Discord Voice Agentic Module

An OpenClaw Discord voice extension for a wake-word voice assistant:

- `/vc say` — speak arbitrary text in the current voice channel via TTS.
- `/vc agentic on|off|status` — persistent wake-word voice mode.
- `discord_voice_say` and `discord_voice_agentic` agent tools.
- Wake phrases: **“Hey Jim”** or **“Hi Jim”** (the matcher also accepts Jimbo, Jimbot, Jym, and Gym).
- Paired start/stop chimes with a request window that ends after a short pause.
- Local Vosk speech-to-text and local `edge-tts` speech synthesis.
- No automatic follow-up: after a reply the microphone closes and another wake phrase is required.

This is a patch module for the installed `@openclaw/discord` plugin. It is version-specific; the patches target the installed `2026.10.4` bundle and may need rebasing for another release.

## Current voice behavior

A normal exchange is:

1. Say **“Hey Jim.”** A recognized wake plays the start chime.
2. Ask the request. The request window waits for about **3 seconds** of word-gap silence.
3. The stop chime plays, the microphone closes, and the request is transcribed.
4. The reply is generated and spoken through the Discord voice channel.
5. After the reply, another **“Hey Jim”** is required for the next request.

Additional rules in the current revision:

- A wake phrase and the request can arrive in the same transcript. The start and stop chimes are still paired around that request.
- The stop chime is only played after a matching start chime; there are no stop-only cues.
- Idle capture waits about **1 second** for a wake phrase. While listening to a request the worker is switched to about **3 seconds**, so short pauses inside a sentence do not cut the request off.
- Low-level noise without recognized words does not keep the request window open.
- A **30-second** safety timer is the fallback for a stuck turn; it is not the normal end-of-request path.
- A wake phrase can be split by a pause (**“Hey … Jim”**). The runtime briefly holds a lone `hey`/`hi`/`hello`/`hay` transcript and combines it with the next segment.
- One request is active at a time per voice call. A second speaker or a second wake while the assistant is busy is ignored rather than starting an overlapping turn.
- Agentic mode is stored per guild and survives plugin reloads/restarts.
- Each call gets its own voice session and short call context. The assistant does not carry the previous call's spoken conversation into a new call.
- Voice turns are deliberately audio-only: they use `modelRun: true` with no tools, shell, or agent loop. Ask in text chat for actions that require tools.

## How it works

### Runtime state machine

The main patch is `patches/voice-runtime.patch`. It adds an agentic state machine to the Discord voice runtime, with state kept per speaker:

- waiting for a wake phrase;
- listening for a request;
- processing one request;
- speaking the reply;
- back to waiting for the next wake.

The runtime sends the audio worker a `capture-grace` command:

- about **1000 ms** while idle, waiting for a wake;
- about **3000 ms** while listening for the request.

`patches/audio-worker.patch` teaches the worker to accept that command. This adaptive timeout is why the same `captureSilenceGraceMs` setting can stay short for wake detection while allowing normal pauses during a question.

The start and stop chimes are serialized through the playback queue and have a short timeout, so a stuck chime cannot indefinitely block the reply. The stop chime is only enqueued when the corresponding listening state is actually active.

### Speech recognition

`tools.media.models` invokes `scripts/stt.sh` for each captured WAV. The script converts the audio to 16 kHz mono and talks to a persistent local Vosk server:

- `scripts/vosk_server.py` loads the Vosk model once and exposes a Unix socket at `~/.cache/vosk-stt.sock`.
- `scripts/vosk_client.py` sends a WAV path and receives the transcript.
- If the server or socket is unavailable, `stt.sh` falls back to the one-shot `scripts/vosk_stt.py`.

Keeping the model loaded removes the repeated model-loading delay from every voice segment. The persistent server is started automatically by `stt.sh` and uses the small English Vosk model by default.

### Assistant turn and TTS

After a request transcript is accepted, the runtime:

1. Stops listening and plays the stop chime.
2. Calls the OpenClaw Gateway as a direct voice model turn: `agent` followed by `agent.wait`, with `modelRun: true`, no tools, and a short per-call history.
3. Synthesizes the returned text with the configured local TTS provider.
4. Plays the TTS audio and releases the voice state when the player reports idle.

The external Gateway CLI is the primary path so a stale in-process turn cannot leave the voice loop blocked. The runtime falls back to in-process Gateway RPC, then the legacy voice path, if the external call fails. TTS has a 20-second safety timeout.

The voice system prompt keeps replies short and spoken, and tells the model not to call tools or produce markdown/code formatting.

## Repository layout

```text
assets/                         Wake and done MP3 chimes
config/openclaw.example.json5   Example OpenClaw configuration
install.sh                      Backup, patch, and copy helper
patches/
  index.patch                   Register the two voice tools
  manifest.patch                Declare the tools in the plugin manifest
  voice-runtime.patch           Agentic loop, cues, STT/TTS integration
  audio-worker.patch            Dynamic capture-grace support
  provider.patch                TTS provider/runtime integration
plugin/                         `discord_voice_say` and `discord_voice_agentic`
scripts/
  stt.sh                        Media CLI STT entrypoint
  vosk_server.py                Persistent Vosk Unix-socket server
  vosk_client.py                Client used by stt.sh
  vosk_stt.py                   One-shot fallback transcriber
```

## Requirements

- OpenClaw `2026.10.x`
- `@openclaw/discord` plugin `2026.10.4` installed under `~/.openclaw/extensions/discord`
- `ffmpeg` and `ffprobe`
- Python 3 with `venv`
- A Discord bot with `Connect`, `Speak`, `Send Messages`, and `Read Message History` in the voice channel
- The `GuildVoiceStates` gateway intent enabled for the bot

## Install

### 1. Install the local speech engines

```bash
python3 -m venv /home/jim/.local/venvs/tts
/home/jim/.local/venvs/tts/bin/pip install edge-tts

python3 -m venv /home/jim/.local/venvs/stt
/home/jim/.local/venvs/stt/bin/pip install vosk

mkdir -p /home/jim/.local/share/vosk
cd /home/jim/.local/share/vosk
curl -L -o /tmp/vosk-model.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
python3 -c "import zipfile; zipfile.ZipFile('/tmp/vosk-model.zip').extractall('/home/jim/.local/share/vosk')"
```

### 2. Apply the plugin patches and helper files

The quickest path is:

```bash
cd /home/jim/.openclaw/workspace/discord-voice-agentic
./install.sh
```

`install.sh` backs up the installed files, applies the patches, copies the two tool modules and chimes, and installs the STT scripts (including the persistent server and client).

For a manual install, back up all patched files first:

```bash
cd /home/jim/.openclaw/extensions/discord
for f in \
  dist/index.js \
  dist/.setup/voice-runtime-DDymtIw8.mjs \
  dist/.setup/provider-YP8gN9_o.mjs \
  dist/src/voice/audio-worker.runtime.js \
  openclaw.plugin.json; do
  cp -a "$f" "$f.bak-voice-agentic"
done
```

Then apply the patches from the repository root:

```bash
cd /home/jim/.openclaw/extensions/discord
patch -p1 < /path/to/discord-voice-agentic/patches/index.patch
patch -p1 < /path/to/discord-voice-agentic/patches/manifest.patch
patch -p1 < /path/to/discord-voice-agentic/patches/voice-runtime.patch
patch -p1 < /path/to/discord-voice-agentic/patches/audio-worker.patch
patch -p1 < /path/to/discord-voice-agentic/patches/provider.patch

cp /path/to/discord-voice-agentic/plugin/voice-say-tool.js dist/
cp /path/to/discord-voice-agentic/plugin/voice-agentic-tool.js dist/

mkdir -p assets
cp /path/to/discord-voice-agentic/assets/agentic-wake.mp3 assets/
cp /path/to/discord-voice-agentic/assets/agentic-done.mp3 assets/

mkdir -p /home/jim/.openclaw/workspace/scripts
cp /path/to/discord-voice-agentic/scripts/stt.sh \
   /path/to/discord-voice-agentic/scripts/vosk_stt.py \
   /path/to/discord-voice-agentic/scripts/vosk_server.py \
   /path/to/discord-voice-agentic/scripts/vosk_client.py \
   /home/jim/.openclaw/workspace/scripts/
chmod +x /home/jim/.openclaw/workspace/scripts/stt.sh \
  /home/jim/.openclaw/workspace/scripts/vosk_stt.py \
  /home/jim/.openclaw/workspace/scripts/vosk_server.py \
  /home/jim/.openclaw/workspace/scripts/vosk_client.py
```

### 3. Configure OpenClaw

Merge `config/openclaw.example.json5` into `~/.openclaw/openclaw.json`. The important parts:

```json5
{
  tts: {
    auto: "off",
    provider: "tts-local-cli",
    providers: {
      "tts-local-cli": {
        command: "/home/jim/.local/venvs/tts/bin/edge-tts",
        args: ["--text", "{{Text}}", "--write-media", "{{OutputPath}}", "--no-progress"],
        outputFormat: "mp3",
        timeoutMs: 120000
      }
    }
  },
  tools: {
    media: {
      audio: { enabled: true },
      models: [{
        type: "cli",
        command: "/bin/bash",
        args: ["/home/jim/.openclaw/workspace/scripts/stt.sh", "{{AttachmentPath}}"],
        capabilities: ["audio"],
        timeoutSeconds: 120
      }]
    }
  },
  channels: {
    discord: {
      intents: { voiceStates: true },
      voice: {
        enabled: true,
        mode: "stt-tts",
        captureSilenceGraceMs: 1000,
        allowedChannels: [
          { guildId: "YOUR_GUILD_ID", channelId: "YOUR_VOICE_CHANNEL_ID" }
        ],
        tts: { provider: "tts-local-cli" }
      }
    }
  }
}
```

`captureSilenceGraceMs` is the idle/default grace. The runtime raises it to 3000 ms while listening through the `capture-grace` worker command.

### 4. Reload

```bash
openclaw config validate
openclaw plugins reload discord --wait
```

Then join the voice channel with `/vc join channel:<id>` or the `discord_voice_say` tool.

## Usage

- `/vc join channel:<voice-channel-id>`
- `/vc say text:Hello from Jim`
- `/vc agentic on`
- `/vc agentic off`
- `/vc agentic status`
- `/vc leave`

Agent tools:

- `discord_voice_say({ text, guildId?, channelId? })`
- `discord_voice_agentic({ enabled, guildId? })`

Agentic mode is persisted in `~/.openclaw/state/discord-voice-agentic.json` per guild. If you move the installation to a different account or host, update the absolute paths in the patches, scripts, and config example.

## Known limitations

- The patches target the installed `@openclaw/discord` `2026.10.4` bundle. A different plugin version will need its file names and surrounding code updated.
- Wake recognition is regex-based on the Vosk transcript. Accents, background noise, and unusual pronunciations can miss the wake phrase.
- The idle wait is about 1 second. A very long pause between “Hey” and “Jim” can still miss the wake; the split-prefix buffer covers gaps up to about 3 seconds.
- The request endpointer is about 3 seconds. A pause longer than that inside a request can end the capture early.
- Replies are not streamed token-by-token. Latency still depends on the local Vosk transcription, the Gateway/model turn, and TTS synthesis/playback.
- Voice turns have no tools. Actions such as shell commands or file operations must be requested in text chat.
- Only one request can be active per voice call. Other speakers are not queued.
- The first request after the Vosk server starts is slower while the model loads. Later requests reuse the resident model.
- TTS playback has a 20-second safety cutoff so a stuck player cannot block the voice state indefinitely.
- Paths under `/home/jim` are deployment-specific. Update the runtime sound paths, scripts, and config if your home directory differs.

## License

MIT. See `LICENSE`.
