# Audio-Generation-Pipeline

Local audio generation on the Mac Studio and the Art PC (RTX 3090).

- [`docs/models.md`](docs/models.md): which models are installed, where, and how to re-download them.
- [`docs/sfx.md`](docs/sfx.md): text-to-sound-effect with Stable Audio 3 small-sfx, driven from the Mac.
- [`docs/qwen3-tts.md`](docs/qwen3-tts.md): Qwen3-TTS text-to-speech on both machines, and how OpenClaw's Speaker agent uses it.
- [`docs/higgs.md`](docs/higgs.md): Higgs Audio v2 text-to-speech and voice cloning on the Art PC.
- [`docs/music.md`](docs/music.md): text-to-song with ACE-Step 1.5, on the Mac or the Art PC.
- [`scripts/mac/`](scripts/mac/): install script, launch agent and `tts-up` / `tts-down` for the Mac.
- [`scripts/artpc/`](scripts/artpc/): scripts that run on the Art PC.
- [`config/openclaw/`](config/openclaw/): OpenClaw config patches.

## What is here

- **Text to SFX.** `scripts/sfx.py` sends a prompt to a second ComfyUI instance on the Art PC (`127.0.0.1:8189`, reached through an SSH tunnel) and saves one WAV per take.
- **Text to speech.** Qwen3-TTS runs on the Mac as an on-demand OpenAI-compatible server (`127.0.0.1:8890`) and on the Art PC as a one-shot script (`say.py`).
- **Higgs Audio v2.** Boson AI's 3B base model, for expressive speech and voice cloning from a short clip. `higgs.py` runs it on the Art PC from `G:\models\higgs-audio-v2\`, and needs the GPU to itself, so it can pause llama-server for the run.

- **Music.** `scripts/music.py` turns a style prompt and lyrics into songs with ACE-Step 1.5, on the Mac by default or on the Art PC with llama-server paused.

## Run

SFX needs Python 3 (standard library only), SSH access to the Art PC over Tailscale, and the model files described in `docs/sfx.md`.

```bash
python3 scripts/sfx.py "heavy metal door slam in a concrete hallway" --seconds 3 --takes 4
```

Flags: `--seconds` (default 3), `--takes` (default 3), `--steps` (default 8), `--seed`, `--raw` (send the prompt unchanged), `--out` (default `sfx-out/`). `SFX_HOST` overrides the SSH target.

Speech on the Mac, after `scripts/mac/install.sh`:

```bash
tts-up
curl -s http://127.0.0.1:8890/v1/audio/speech -H 'Content-Type: application/json' \
  -d '{"model":"'"$HOME"'/models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit","input":"Hello","voice":"Ryan","response_format":"wav"}' \
  -o hello.wav
tts-down
```

## Layout

```
docs/models.md             installed models, paths, licences
docs/sfx.md                SFX setup, measurements, operating the server
docs/qwen3-tts.md          Qwen3-TTS on both machines, OpenClaw wiring
docs/higgs.md              Higgs Audio v2 on the Art PC
docs/music.md              ACE-Step 1.5 music on the Mac and the Art PC
scripts/sfx.py             prompt in, WAVs out
scripts/music.py           prompt and lyrics in, songs out
scripts/mac/               Qwen3-TTS install, launch agent, tts-up / tts-down
scripts/artpc/             PowerShell and Python files that run on the Art PC
                           (SFX server start/stop, ComfyUI launcher, Higgs download,
                           install and higgs.py, Qwen3-TTS install and say.py,
                           music server start/stop)
config/openclaw/           OpenClaw config patch for the Speaker agent
```

<!-- BEGIN:generation-family -->
## Related repos

Generated film falls apart when a face, a jacket or a voice changes between shots. Each of these six repos handles one part of keeping it consistent.

| Repo | What it does |
|---|---|
| [Film Design System](https://github.com/weeeha/Image-Generation-Pipeline-) | Keeps characters, props and settings consistent across image generations |
| 3D Models (private) | Generates 3D models from text, with a viewer and gallery |
| [Scene Builder 3D](https://github.com/weeeha/scene-builder-3d) | Blocks out shots in 3D before anything is generated |
| [Video Generation Pipeline](https://github.com/weeeha/Video-Generation-Pipeline) | Seedance and Runway video generation with reusable reference packs |
| [Audio Generation Pipeline](https://github.com/weeeha/Audio-Generation-Pipeline) | Local speech, voice cloning and sound effects |
| Continuity Lab (private, in progress) | Finds and repairs inconsistencies between generated video shots |
<!-- END:generation-family -->
