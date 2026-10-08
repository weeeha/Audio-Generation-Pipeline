# Models

Where each model lives, how it got there, and what to watch for.

## Higgs Audio v2 (Boson AI)

| | |
|---|---|
| Machine | Art PC (`artstation`, RTX 3090 24 GB) |
| Path | `G:\models\higgs-audio-v2\` |
| Downloaded | 2026-10-08 |
| License | "other" on Hugging Face (Boson Higgs Audio 2 Community License). Read the terms before commercial use. |

Two repos, both needed:

| Folder | Hugging Face repo | Size |
|---|---|---|
| `higgs-tts-2-3b-base\` | [`bosonai/higgs-tts-2-3b-base`](https://huggingface.co/bosonai/higgs-tts-2-3b-base) | 11.6 GB (`model.safetensors` 11.54 GB) |
| `higgs-audio-v2-tokenizer\` | [`bosonai/higgs-audio-v2-tokenizer`](https://huggingface.co/bosonai/higgs-audio-v2-tokenizer) | 0.8 GB |

**Repo was renamed.** The old name `boson-ai/higgs-audio-v2-generation-3B-base` (still in older docs and code samples) returns HTTP 401, which looks like an auth problem but means the repo is gone. `bosonai/higgs-audio-v2-generation-3B-base` 307-redirects to `bosonai/higgs-tts-2-3b-base`. Use the new name.

**G: is a USB external drive**, not internal. Fine for storage; loads are slower than from the `C:` NVMe. Copy to `C:` if it becomes a daily hot path.

### Re-download

From the Mac:

```bash
scp scripts/artpc/download_higgs_v2.py scripts/artpc/start-download.ps1 mvyho@100.114.149.53:
ssh mvyho@100.114.149.53 "powershell -NoProfile -ExecutionPolicy Bypass -File start-download.ps1"
```

`snapshot_download` resumes, so rerunning after an interruption only fetches what is missing. Progress: `G:\models\higgs-audio-v2\download.log`. Throughput on 2026-10-08 was about 2-3 MB/s, so a full pull takes about an hour.
