# Music: text to song with ACE-Step 1.5

Prompt and lyrics in, songs out. `scripts/music.py` drives ACE-Step 1.5's REST API on the Mac (default) or on the Art PC, and saves each take with a `.json` of what the planner chose (seed, BPM, key, lyrics).

```bash
python3 scripts/music.py "warm indie folk, fingerpicked acoustic guitar, gentle female vocal" --lyrics-file song.txt --seconds 60
python3 scripts/music.py "cinematic orchestral build, strings and horns" --instrumental --seconds 45 --takes 2
python3 scripts/music.py "..." --instrumental --host artpc --free-gpu --model acestep-v15-xl-turbo
```

Lyrics use section tags such as `[Verse]`, `[Chorus]`, `[Bridge]`; `--instrumental` sends `[Instrumental]`. Output is 48 kHz stereo in `music-out/`.

`--jobs cues.json` runs a list of cues in one server session, so the Art PC pauses llama-server once for the whole list. Each entry sets any of `name`, `prompt`, `lyrics`, `lyrics_file`, `instrumental`, `seconds`, `takes`, `seed`, `bpm`, `key`, `lang`; the command line fills in the rest. In a batch of takes only the first uses `--seed`; the others get random seeds, which the file names and `.json` record.

| Flag | Default | |
|---|---|---|
| `--seconds` | 30 | 10 to 600 |
| `--takes` | 1 | Variations in one batch, up to 8 |
| `--seed` | random | Same seed and settings give the same song |
| `--bpm`, `--key` | planner decides | e.g. `--bpm 90 --key "G major"` |
| `--lang` | en | Lyrics language |
| `--model` | `acestep-v15-turbo` | `acestep-v15-xl-turbo` on the Art PC |
| `--no-plan` | off | Skip the 1.7B planner: faster, flatter |
| `--format` | mp3 | `wav`, `flac` |
| `--host` | mac | `artpc` needs `--free-gpu` |
| `--keep` | off | Leave the server running (Mac only) |

## Why this model

ACE-Step 1.5 (from the ACE-Step team with StepFun, MIT license) is a 2B diffusion model guided by a 1.7B language model that plans the song (structure, tempo, key, an expanded caption) before the audio is rendered. Its model card states the training data was licensed, royalty-free or synthetic and that output may be used commercially. Its README also lists covers, section repaint, stem separation, vocal-to-accompaniment and LoRA training; `music.py` covers text to song only.

It is weak at sound effects; use [`sfx.md`](sfx.md) for those.

## Where it runs

| | Mac Studio | Art PC |
|---|---|---|
| Install | `~/ACE-Step-1.5` | `G:\AI\ACE-Step-1.5` |
| Models | `acestep-v15-turbo` (2B), `acestep-5Hz-lm-1.7B`, Qwen3 embedding, VAE (9.4 GB) | same, plus `acestep-v15-xl-turbo` (4B, 20 GB on disk) |
| Server | started by `music.py` on `127.0.0.1:8001`, stopped afterwards | `start-music-server.ps1` on `127.0.0.1:8001`, reached through an SSH tunnel |
| Planner backend | MLX | PyTorch (vLLM does not run on Windows) |

On the Mac, `music.py` launches `.venv/bin/acestep-api` with the same settings as ACE-Step's `start_api_server_macos.sh`, minus its git update check. Log: `~/.local/state/acestep/api.log`.

On the Art PC, `--free-gpu` is required. `start-music-server.ps1`:

1. Pauses llama-server through the `llama-hold` flag file (or `schtasks /end` without the watcher), the same way as [`higgs.md`](higgs.md).
2. Passes the free memory from nvidia-smi as `MAX_CUDA_VRAM`. ACE-Step otherwise sizes itself from the card's total of 24 GB.
3. Loads the models at startup (`ACESTEP_NO_INIT=false`) and waits up to 10 minutes for the API.

`stop-music-server.ps1` stops the server and resumes llama-server. `music.py` calls it in a `finally`, so it also runs when generation fails.

A `finally` on the Mac does not help when the client itself dies. On 2026-10-12 a killed `music.py` left llama-server paused for about 80 minutes. Now `start-music-server.ps1` writes the pause marker with a session token and starts a detached `music-guard.ps1` with a lease (`music.py` sizes it at 15 minutes plus 2 per minute of requested audio). If the marker still carries that token when the lease runs out, the guard runs `stop-music-server.ps1` itself. Tested with a 1-minute lease and the client killed after 20 seconds: the guard stopped ACE-Step and removed the hold flag at 1 minute.

Deploy the PC scripts with `scp scripts/artpc/*-music-server.ps1 scripts/artpc/music-guard.ps1 mvyho@100.114.149.53:G:/AI/music/`. Set `MUSIC_HOST` to reach the PC another way, such as `mvyho@192.168.100.2` over the direct cable.

## Measured (2026-10-12)

30-second song with lyrics, fingerpicked folk prompt, planner on:

| | Model load | Generate | Whole run |
|---|---|---|---|
| Mac, turbo | 52 s (first request) | 21 s warm | 51 s for a 20 s instrumental, cold start to stop |
| Art PC 3090, turbo | 190 s (cold, from the G: USB disk) | 27 s (planner 11 s) | 224 s including the llama-server pause and resume |
| Art PC 3090, XL turbo | 40 s (file cache still warm from the copy) | 19 s (planner 6 s) | 68 s, plus the llama-server reload below |

Turbo and XL got the same prompt, lyrics and seed; both sang the lyrics. Which sounds better is for the ear: the planner picked C major for one and G major for the other, so the takes differ in more than the model. For turbo the 3090 is no faster than the Mac, because the planner runs on plain PyTorch on Windows. The PC is the place for XL.

## Gotchas

- After XL, llama-server took over 4 minutes to come back instead of about 10 seconds. Loading 20 GB of XL pushed the day model's 16 GB GGUF out of the Windows file cache, and `start-llama.bat` loads it through mmap without `--no-mmap`, which reads the G: disk at a few MB/s. Reading the file once (`cmd /c copy /b G:\models\gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf NUL`, 140 s) refilled the cache and it was up 45 s later. The lasting fix is `--no-mmap` in `start-llama.bat`.

- Next to llama-server only about 2 GB of VRAM is free, and ACE-Step runs out of memory even in its smallest mode. `start-music-server.ps1` refuses below 8 GB.
- ACE-Step reads the card's total memory, not the free memory, to choose its tier. Without `MAX_CUDA_VRAM` it would pick the top tier next to llama-server and overcommit the card.
- With lazy loading, the first request loads the models from the G: USB disk inside the request and the server answers nothing for over a minute. The PC launcher loads them at startup instead.
- ACE-Step's own launch scripts check GitHub for updates and may run `uv sync`; `music.py` and the PC launcher start the venv's `acestep-api` directly so the install does not change under us.
