"""say.py: generate speech with Qwen3-TTS on the Art PC.

Preset voice (CustomVoice model):
    say.py --text "Hello" --voice Ryan --out hello.wav
Voice clone (Base model), from a 3+ second clip and its transcript:
    say.py --text "Hello" --ref-audio me.wav --ref-text "What I said in the clip." --out hello.wav

The day llama-server keeps ~21.7 of the 3090's 24 GB, so --device auto uses the GPU only when
enough VRAM is free and otherwise runs on the CPU. Stop the server first for GPU speed:
    schtasks /end /tn llama-server    ...    schtasks /run /tn llama-server
"""

import argparse
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


def pick_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if not torch.cuda.is_available():
        return "cpu"
    free, _ = torch.cuda.mem_get_info()
    return "cuda:0" if free / 1024**3 >= MIN_FREE_VRAM_GB else "cpu"


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

    device = pick_device(a.device)
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
        f"{a.out}: {seconds:.1f}s audio on {device} | load {t1 - t0:.1f}s, "
        f"generate {t2 - t1:.1f}s ({seconds / (t2 - t1):.2f}x real time)"
    )


if __name__ == "__main__":
    main()
