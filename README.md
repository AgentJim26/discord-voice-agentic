# Discord Voice Agentic Module

An OpenClaw Discord voice extension that adds:

- `/vc say` — speak arbitrary text in the current voice channel via TTS.
- `/vc agentic on|off|status` — wake-word voice mode.
- `discord_voice_say` and `discord_voice_agentic` agent tools.
- Wake-word flow: say **“hey Jim”** or **“hi Jim”**, hear a wake chime, speak, hear a done chime, then get a spoken answer.
- A short follow-up window after each answer, so you can continue without repeating the wake word.
- Local speech-to-text with Vosk and local text-to-speech with `edge-tts`.

This is a patch module for the installed `@openclaw/discord` plugin. It is version-specific; read the patch notes before applying it to a different plugin release.

## Requirements

- OpenClaw `2026.10.x`
- `@openclaw/discord` plugin `2026.10.4` (installed under `~/.openclaw/extensions/discord`)
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

### 2. Copy the helper scripts and chimes

```bash
cp scripts/stt.sh scripts/vosk_stt.py /home/jim/.openclaw/workspace/scripts/
chmod +x /home/jim/.openclaw/workspace/scripts/stt.sh
mkdir -p /home/jim/.openclaw/extensions/discord/assets
cp assets/agentic-wake.mp3 assets/agentic-done.mp3 /home/jim/.openclaw/extensions/discord/assets/
```

### 3. Apply the plugin patches

Back up the installed plugin first:

```bash
cd /home/jim/.openclaw/extensions/discord
cp -a dist/index.js dist/index.js.bak-voice-agentic
cp -a dist/.setup/voice-runtime-DDymtIw8.mjs dist/.setup/voice-runtime-DDymtIw8.mjs.bak-voice-agentic
cp -a dist/.setup/provider-YP8gN9_o.mjs dist/.setup/provider-YP8gN9_o.mjs.bak-voice-agentic
cp -a openclaw.plugin.json openclaw.plugin.json.bak-voice-agentic
```

Then apply the patches from the repository root:

```bash
cd /home/jim/.openclaw/extensions/discord
patch -p1 < /path/to/discord-voice-agentic/patches/index.patch
patch -p1 < /path/to/discord-voice-agentic/patches/manifest.patch
patch -p1 < /path/to/discord-voice-agentic/patches/voice-runtime.patch
patch -p1 < /path/to/discord-voice-agentic/patches/provider.patch
cp /path/to/discord-voice-agentic/plugin/voice-say-tool.js dist/
cp /path/to/discord-voice-agentic/plugin/voice-agentic-tool.js dist/
```

`install.sh` automates the backup, patch, and copy steps.

### 4. Configure OpenClaw

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
        captureSilenceGraceMs: 800,
        allowedChannels: [
          { guildId: "YOUR_GUILD_ID", channelId: "YOUR_VOICE_CHANNEL_ID" }
        ],
        tts: { provider: "tts-local-cli" }
      }
    }
  }
}
```

### 5. Reload

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

## How it works

1. The Discord plugin captures a speaker segment with `@discordjs/voice`.
2. Vosk transcribes the WAV through the `tools.media.models` CLI entry.
3. In agentic mode, the transcript must start with `hey Jim` or `hi Jim`.
4. The wake chime plays, the command runs through the OpenClaw agent, and the reply is synthesized with `edge-tts`.
5. The done chime plays before the reply, and a follow-up window stays open after playback.

## Known limitations

- The patches target the installed `@openclaw/discord` `2026.10.4` bundle. A different plugin version will need its file names and surrounding code updated.
- `voice-runtime.patch` includes the earcon and wake-word logic; the `params.runtime` argument passed to `runCommandFromIngress` is required in the tested build.
- The wake-word gate is regex-based on the STT transcript. Unusual pronunciations can miss the wake word.
- The follow-up window is 12 seconds. Closing phrases (`thanks`, `that's all`, `stop`, `bye`) close it early.
- This module was built and tested on Linux arm64 with a local Vosk model. Provider and audio-device behavior can differ on other hosts.

## License

MIT. See `LICENSE`.
