# Higgs Audio v2 (Higgs TTS 2)

Text to speech and voice cloning on the Art PC with Boson AI's 3B base model. The model files are in `G:\models\higgs-audio-v2\` (download: [`models.md`](models.md)); the code and venv are in `G:\AI\higgs-tts\`.

```powershell
G:\AI\higgs-tts\.venv\Scripts\python.exe G:\AI\higgs-tts\higgs.py --text "Hello there." --out hello.wav --free-gpu
```

Clone a voice from a short clip and its exact transcript:

```powershell
... higgs.py --text "Hello there." --ref-audio me.wav --ref-text "What I said in the clip." --out hello.wav --free-gpu
```

| Flag | Default | |
|---|---|---|
| `--scene` | "Audio is recorded from a quiet room." | Recording environment, rendered as the scene description |
| `--temperature` | 0.3 | Boson's recommended value. `--greedy` for deterministic output |
| `--seed` | random | Same seed and settings give the same take |
| `--max-new-tokens` | 1200 | 25 tokens per second of audio, so about 48 s |
| `--device` | auto | `cuda:0` or `cpu`. The CPU path runs in float32 (about 23 GB of RAM) and is untested |
| `--free-gpu` | off | Stop llama-server for the run and start it again afterwards |

Output is a 24 kHz mono WAV.

## GPU

The model is 5.8B parameters in bf16 (11.5 GB of weights) plus a 0.8 GB audio tokenizer, so it needs about 14 GB of VRAM. The day llama-server (Gemma 26B on `:8080`) holds about 21 of the 3090's 24 GB, which leaves too little.

Without `--free-gpu`, `higgs.py` stops with a message when there is not enough VRAM. With it, the script pauses llama-server, waits for the memory to come free, generates, resumes llama-server and waits for `:8080/health`. OpenClaw's primary model is down for those minutes and OpenClaw uses its fallback chain.

How it pauses depends on the `llama-hold` watcher (`C:\Users\mvyho\llama-hold.ps1`, a logon task):

- **`llama-hold` running:** `schtasks /end /tn llama-server` does not work, because the watcher relaunches llama-server within 5 seconds (seen 2026-10-12). The script creates the watcher's manual flag `C:\Users\mvyho\llama-hold.manual` instead, which makes it stop every llama-server and keep them down. It deletes the flag afterwards, even when generation fails, and the watcher relaunches the day server 15 seconds later. The hold also stops the CPU night server on `:8081`; the watcher relaunches that one only before 07:00.
- **`llama-hold` not running:** the script ends the `llama-server` task and runs it again afterwards, if it was running before.

## How it loads

The Hugging Face repos were converted to the Transformers-native format in April 2026 (`HiggsAudioV2ForConditionalGeneration`, transformers 5.3.0 or newer). Boson's older `boson_multimodal` package from github.com/boson-ai/higgs-audio cannot load them: it expects a `model.pth` tokenizer file that the repo no longer has.

`processor_config.json` names the audio tokenizer by its Hub id (`bosonai/higgs-audio-v2-tokenizer`), so `AutoProcessor.from_pretrained` would fetch it from the Hub and ignore the local copy. `higgs.py` builds the processor from the local folders instead and sets `HF_HUB_OFFLINE=1`, so it never downloads anything.

## Verified

2026-10-12 on the Art PC's 3090, both runs with `--free-gpu` while llama-server was loaded:

| | Audio | Load | Generate |
|---|---|---|---|
| Plain, seed 1234 | 4.4 s | 185.2 s (cold, 11.5 GB from the G: USB disk) | 4.9 s (0.90x real time) |
| Clone from a 2.2 s clip, seed 1234 | 3.5 s | 8.9 s (warm cache) | 3.7 s (0.94x real time) |

Both transcribed back correctly with Whisper. Pausing through `llama-hold` freed the GPU within about 2 seconds, and llama-server answered `/health` again about 25 seconds after the flag was removed (15 s grace plus a 10 s load from cache). The flag was gone afterwards and one llama-server was running.

Also run on the Mac Studio's GPU (MPS) with the model folders pointed at a local copy: plain 3.7 s of audio in 19.5 s and clone 4.0 s in 8.3 s, peak memory 14.3 GB.

## Install

From the Mac:

```bash
scp scripts/artpc/higgs.py scripts/artpc/install-higgs.ps1 mvyho@100.114.149.53:
ssh mvyho@100.114.149.53 "powershell -NoProfile -ExecutionPolicy Bypass -File install-higgs.ps1"
```

`install-higgs.ps1` creates the venv with the same torch build as `G:\AI\Qwen3-TTS` (2.11.0, CUDA 12.8), so uv reuses its cached wheels, then adds torchaudio, `transformers==5.17.0`, `accelerate`, `soundfile` and `librosa`, all pinned to the versions tested on 2026-10-12.

## Gotchas

- `torchaudio` is required even though nothing here decodes audio with it: `HiggsAudioV2TokenizerModel` refuses to load without it.
- Passing `load_audio_backend` to `apply_chat_template` breaks voice cloning in transformers 5.17.0. The kwarg reaches `DacFeatureExtractor.__call__`, which raises `TypeError`. `higgs.py` loads the reference clip with librosa itself and passes the samples.
- The context is 2048 positions for the prompt, the reference clip (25 per second) and the output together. Keep reference clips under about 15 seconds.
- License: Boson Higgs Audio 2 Community License, based on the Llama 3 community license. Read it before commercial use.
