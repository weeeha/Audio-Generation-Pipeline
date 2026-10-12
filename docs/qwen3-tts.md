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
- The server loads whatever the request's `model` field names. Send the local folder path, as `tts-up` and the OpenClaw config do. A Hugging Face repo id such as `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit` makes it download a second copy into `~/.cache/huggingface/hub` inside the request, and the request hangs (seen 2026-10-11).
- A hung download also blocks `tts-down`: the port closes but the process waits on the download, so `tts-up` then times out. `launchctl kickstart -k gui/$(id -u)/com.weeeha.qwen3-tts` kills and relaunches it.

## OpenClaw

`config/openclaw/speaker-tts.json5` points only the `speaker` agent at the local server:

```bash
openclaw config patch --file config/openclaw/speaker-tts.json5 --dry-run
openclaw config patch --file config/openclaw/speaker-tts.json5
```

Replace `$HOME` in the file with the real path first, since `config patch` does not expand it. The global `tts.provider` stays `elevenlabs`. OpenClaw tries the agent's provider first and falls back to the other configured providers, so Speaker uses ElevenLabs whenever the local server is down.

## Art PC (CUDA)

| | |
|---|---|
| Install | `scripts/artpc/install.ps1` |
| Path | `G:\AI\Qwen3-TTS\` (venv, models, `say.py`). G: is a USB hard drive and must be mounted. |
| Packages | `qwen-tts==0.1.1`, `torch 2.11.0+cu128` |
| Models | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` (4.2 GB), `Qwen/Qwen3-TTS-12Hz-1.7B-Base` (4.2 GB), official bf16 |
| Run | `G:\AI\Qwen3-TTS\.venv\Scripts\python.exe G:\AI\Qwen3-TTS\say.py --text "..." --out out.wav` |

No server on the PC yet. `say.py` loads the model per call (2.9 s from G:) and writes one WAV. Add `--ref-audio clip.wav --ref-text "..."` to clone a voice with the Base model, `--instruct "..."` for style, and `--lang Russian` to force a language.

The day `llama-server` (Gemma 26B on `:8080`) holds about 21 GB of the 3090. `--device auto` uses the GPU only with at least 6 GB of VRAM free and otherwise runs on the CPU. It takes the lower of CUDA's and nvidia-smi's free-memory readings: on 2026-10-12, with llama-server loaded, torch reported 22.4 GB free and nvidia-smi 3.5 GB. llama-server runs as SYSTEM, and CUDA's reading in our process does not count its memory, so the old CUDA-only check sent runs onto a full GPU.

To guarantee the GPU, pause llama-server: create `C:\Users\mvyho\llama-hold.manual`, run `say.py`, then delete the file. The `llama-hold` watcher stops every llama-server while the file exists and relaunches the day server 15 seconds after it is gone. `schtasks /end /tn llama-server` alone does not work while the watcher runs: it relaunched the server 5 seconds later (2026-10-12). OpenClaw's primary model runs on that server.

Measured 2026-10-08 on `cuda:0` while other jobs shared the GPU: 5.1 s of audio in 12.7 s (0.40x real time), slower than the Mac. The reference `qwen-tts` code runs one sample with no flash attention, so treat this as a floor. Output transcribed back correctly.

Measured 2026-10-12 with warm file caches, CustomVoice `Ryan`:

| Where it ran | Audio | Load | Generate |
|---|---|---|---|
| GPU, llama-server paused | 6.8 s | 7.3 s | 26.3 s (0.26x real time) |
| CPU, llama-server loaded (what `auto` now picks) | 3.3 s | 2.1 s | 22.1 s (0.15x real time) |
| GPU, llama-server loaded (what the old check picked, 2026-10-11) | 2.2 s | 105.7 s | 16.1 s (0.14x real time) |

The GPU take ran long, with sound after the words, and transcribed correctly. A cold load from G: while another job reads the drive took 143 s. Every Art PC option is far slower than the Mac server (about 2.4x real time), so use the Mac for speech and the PC as a fallback.

Gotchas:

- Xet downloads stalled at 244 MB on this machine. `install.ps1` sets `HF_HUB_DISABLE_XET=1`.
- uv's cache is also on G:, so installs and downloads compete with anything else writing to that drive. With a second 12 GB download running alongside, the install took about 70 minutes.
