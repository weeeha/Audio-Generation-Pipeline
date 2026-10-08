# SFX: text prompt to sound effect

Text prompt in, sound effect WAVs out. Runs **Stable Audio 3 small-sfx** in ComfyUI on the Art PC (`artstation`, RTX 3090), driven from the Mac.

```bash
python3 scripts/sfx.py "heavy metal door slam in a concrete hallway" --seconds 3 --takes 4
```

WAVs (24-bit, 44.1 kHz stereo) land in `sfx-out/`, one per take, each with its own seed so you can pick the best. `--raw` sends your prompt unchanged; otherwise `shape_prompt()` in `scripts/sfx.py` appends "isolated sound effect, no music, no voice".

## Why this model

Picked 2026-10-08. Stable Audio 3 (Stability AI, May 2026) ships a dedicated SFX checkpoint (`small-sfx`, 2.3 GB) that is distilled to 8 steps, plus ComfyUI support since v0.3x. ACE-Step (already on the PC at `G:\AI\ACE-Step-1.5`) is a music model and is weak at SFX. Stable Audio Open 1.0 is the older generation. ElevenLabs Sound Effects is the cloud alternative if quality beats local.

License: Stable Audio Community License (free for personal use and businesses under USD 1M annual revenue) plus the Gemma terms for the T5Gemma text encoder.

## Layout on the Art PC

| Path | What |
|---|---|
| `G:\models\stable-audio-3\checkpoints\stable_audio_3_small_sfx.safetensors` | model, from `Comfy-Org/stable-audio-3` |
| `G:\models\stable-audio-3\text_encoders\t5gemma_b_b_ul2.safetensors` | text encoder |
| `G:\AI\sfx\` | `run_comfy.py`, `start-sfx-server.ps1`, `extra_model_paths.yaml`, `output\`, `user\`, `server.log` |

The server is a **second ComfyUI instance on `127.0.0.1:8189`** that reuses the Krita-managed install (`G:\Krita AI\ComfyUI`, v0.33.3, the only install with SA3 support) read-only. Krita's own models, settings and `extra_model_paths.yaml` are untouched. `sfx.py` starts it on demand over SSH and reaches it through an SSH tunnel; it is never exposed on the network.

`run_comfy.py` exists because the Krita venv's uv launcher can't resolve the `cpython-3.12` junction from an SSH session ("uv trampoline failed to spawn Python child process"). It runs the real `cpython-3.12.9` interpreter and adds the venv's site-packages instead.

## Operate

- Start: `ssh mvyho@100.114.149.53 powershell -File G:\AI\sfx\start-sfx-server.ps1` (`sfx.py` does this for you)
- Stop: kill the python process whose command line has `--port 8189`
- Browser UI: `ssh -L 18189:127.0.0.1:8189 mvyho@100.114.149.53`, then open http://localhost:18189
- VRAM: `llama-server` (gemma-4-26B on `:8080`) holds about 21 GB of the 3090's 24 GB. The SFX model loads in what's left.

Deploy the server files with `scp scripts/artpc/run_comfy.py scripts/artpc/start-sfx-server.ps1 mvyho@100.114.149.53:G:/AI/sfx/`. Set `SFX_HOST` to point `sfx.py` at another machine.
