# Qwen3-TTS

Local text-to-speech on both machines. Apache 2.0, 10 languages including English, Russian and French.

| Variant | What it does |
|---|---|
| `1.7B-CustomVoice` | Nine preset voices (`Ryan`, `Vivian`, ...) plus an optional style instruction ("calm", "excited"). Used for agent replies. |
| `1.7B-Base` | Voice cloning from a 3+ second reference clip and its transcript. |

## Mac Studio (MLX)

| | |
|---|---|
| Install | `scripts/mac/install.sh` |
| Path | `~/models/qwen3-tts/` (venv + models, outside the Hugging Face cache) |
| Package | `mlx-audio[server]==0.5.8` |
| Models | `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit` (3.1 GB), `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit` (3.1 GB) |
| Server | launch agent `com.weeeha.qwen3-tts`, `127.0.0.1:8890`, OpenAI-compatible `POST /v1/audio/speech` |
| Start / stop | `tts-up` (starts and preloads the model) / `tts-down` |
| Log | `~/.local/state/qwen3-tts/server.log` |

The server is on demand, with `RunAtLoad` and `KeepAlive` off. While loaded it holds about 4.8 GB (7.5 GB peak), and the Mac already runs close to its 64 GB at night.

Measured 2026-10-08: cold request 14.5 s, warm request 2-5 s, generation about 2.4x faster than real time. English and Russian output transcribed back word for word with Parakeet.

One-off generation without the server:

```bash
cd ~/models/qwen3-tts
.venv/bin/mlx_audio.tts.generate --model ./Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit \
  --text "Hello" --voice Ryan --output_path samples --file_prefix hello
```

Gotchas:

- launchd's default `PATH` has no `/opt/homebrew/bin`, so MP3 and Opus encoding fail with "ffmpeg not found" after the HTTP 200 has already gone out. The client then sees a cut-off stream (OpenClaw reports `openai: terminated`). The plist sets `PATH` for this reason. WAV needs no ffmpeg.
- A cold start after `launchctl bootstrap` can take over 30 s, so `tts-up` waits up to 90 s.
- `hf download` can stall on a large file. Kill it and run it again; it resumes.

## OpenClaw

`config/openclaw/speaker-tts.json5` points only the `speaker` agent at the local server:

```bash
openclaw config patch --file config/openclaw/speaker-tts.json5 --dry-run
openclaw config patch --file config/openclaw/speaker-tts.json5
```

Replace `$HOME` in the file with the real path first, since `config patch` does not expand it. The global `tts.provider` stays `elevenlabs`. OpenClaw tries the agent's provider first and falls back to the other configured providers, so Speaker uses ElevenLabs whenever the local server is down.

## Art PC (CUDA)

See `scripts/artpc/`.
