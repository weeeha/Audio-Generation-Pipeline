# Audio-Generation-Pipeline

Local audio generation on the Art PC (RTX 3090).

- [`docs/models.md`](docs/models.md): which models are installed, where, and how to re-download them.
- [`docs/sfx.md`](docs/sfx.md): text-to-sound-effect with Stable Audio 3 small-sfx, driven from the Mac.
- [`scripts/artpc/`](scripts/artpc/): scripts that run on the Art PC.

## What is here

- **Text to SFX.** `scripts/sfx.py` sends a prompt to a second ComfyUI instance on the Art PC (`127.0.0.1:8189`, reached through an SSH tunnel) and saves one WAV per take.
- **Higgs Audio v2.** The 3B base model and its tokenizer are downloaded to `G:\models\higgs-audio-v2\` on the Art PC. This repo holds the download scripts and notes; there is no generation script for it yet.

## Run

Needs Python 3 (standard library only), SSH access to the Art PC over Tailscale, and the model files described in `docs/sfx.md`.

```bash
python3 scripts/sfx.py "heavy metal door slam in a concrete hallway" --seconds 3 --takes 4
```

Flags: `--seconds` (default 3), `--takes` (default 3), `--steps` (default 8), `--seed`, `--raw` (send the prompt unchanged), `--out` (default `sfx-out/`). `SFX_HOST` overrides the SSH target.

## Layout

```
docs/models.md       installed models, paths, licences
docs/sfx.md          SFX setup, measurements, operating the server
scripts/sfx.py       prompt in, WAVs out
scripts/artpc/       PowerShell and Python files that run on the Art PC
                     (SFX server start/stop, ComfyUI launcher, Higgs download)
```
