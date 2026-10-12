"""say.py: generate speech with Qwen3-TTS on the Art PC.

Preset voice (CustomVoice model):
    say.py --text "Hello" --voice Ryan --out hello.wav
Voice clone (Base model), from a 3+ second clip and its transcript:
    say.py --text "Hello" --ref-audio me.wav --ref-text "What I said in the clip." --out hello.wav

The day llama-server keeps ~21 of the 3090's 24 GB, so --device auto uses the GPU only when
enough VRAM is free and otherwise runs on the CPU. For GPU speed, pause llama-server through the
llama-hold watcher (it relaunches the server seconds after a plain schtasks /end):
    create C:\\Users\\mvyho\\llama-hold.manual  ...  delete it afterwards
"""

import argparse
import subprocess
import time
from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

MODELS = Path(__file__).resolve().parent / "models"
CUSTOM_VOICE = MODELS / "Qwen3-TTS-12Hz-1.7B-CustomVoice"
BASE = MODELS / "Qwen3-TTS-12Hz-1.7B-Base"
# 1.7B in bf16 is ~3.4 GB of weights; leave headroom for activations and the speech tokenizer.
MIN_FREE_VRAM_GB = 6.0


def free_vram_gb() -> float | None:
    """Free VRAM on GPU 0 in GB, or None without a CUDA GPU.

    Takes the lower of CUDA's reading and nvidia-smi's, which counts every process on the card.
    On 2026-10-11 the CUDA reading alone sent a run to the GPU while nvidia-smi showed about
    3.3 GB free, and it generated at 0.14x real time.
    """
    if not torch.cuda.is_available():
        return None
    readings = [torch.cuda.mem_get_info(0)[0] / 1024**3]
    try:
        out = subprocess.run(
            ["nvidia-smi", "-i", "0", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        readings.append(float(out.stdout.strip()) / 1024)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return min(readings)


def pick_device(requested: str) -> tuple[str, str]:
    """Return the device and a short reason, so the output line says why it ran where it did."""
    if requested != "auto":
        return requested, "requested"
    free = free_vram_gb()
    if free is None:
        return "cpu", "no CUDA GPU"
    if free >= MIN_FREE_VRAM_GB:
        return "cuda:0", f"{free:.1f} GB VRAM free"
    print(
        f"Only {free:.1f} GB of VRAM free (needs {MIN_FREE_VRAM_GB:.0f}), running on the CPU. "
        "For GPU speed, pause llama-server: create C:\\Users\\mvyho\\llama-hold.manual, delete it after."
    )
    return "cpu", f"{free:.1f} GB VRAM free"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--text", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--voice", default="Ryan", help="CustomVoice speaker, e.g. Ryan, Vivian, Serena, Aiden")
    p.add_argument("--instruct", default=None, help="Style instruction for CustomVoice, e.g. 'calm and slow'")
    p.add_argument("--lang", default="Auto", help="Auto, English, Russian, French, ...")
    p.add_argument("--ref-audio", default=None, help="Reference clip; switches to the Base model (voice clone)")
    p.add_argument("--ref-text", default=None, help="Transcript of --ref-audio")
    p.add_argument("--device", default="auto", help="auto, cuda:0 or cpu")
    a = p.parse_args()

    device, why = pick_device(a.device)
    dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
    model_dir = BASE if a.ref_audio else CUSTOM_VOICE

    t0 = time.time()
    model = Qwen3TTSModel.from_pretrained(str(model_dir), device_map=device, dtype=dtype)
    t1 = time.time()
    if a.ref_audio:
        wavs, sr = model.generate_voice_clone(
            text=a.text, language=a.lang, ref_audio=a.ref_audio, ref_text=a.ref_text
        )
    else:
        wavs, sr = model.generate_custom_voice(
            text=a.text, language=a.lang, speaker=a.voice, instruct=a.instruct
        )
    t2 = time.time()

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sf.write(a.out, wavs[0], sr)
    seconds = len(wavs[0]) / sr
    print(
        f"{a.out}: {seconds:.1f}s audio on {device} ({why}) | load {t1 - t0:.1f}s, "
        f"generate {t2 - t1:.1f}s ({seconds / (t2 - t1):.2f}x real time)"
    )


if __name__ == "__main__":
    main()
