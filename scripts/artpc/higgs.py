"""higgs.py: generate speech with Higgs Audio v2 (Higgs TTS 2, 3B base) on the Art PC.

Plain text to speech:
    higgs.py --text "Hello there." --out hello.wav
Voice clone, from a short clip and its transcript:
    higgs.py --text "Hello there." --ref-audio me.wav --ref-text "What I said in the clip." --out hello.wav
Dialogue, one [SPEAKERn] tag per line, voices described with --speaker:
    higgs.py --text-file scene.txt --speaker "SPEAKER0: feminine" --speaker "SPEAKER1: masculine" --out scene.wav

The model needs about 14 GB of VRAM, and the day llama-server keeps about 21 of the 3090's 24 GB.
--free-gpu pauses llama-server for the run and resumes it afterwards (OpenClaw's primary model is
down for those minutes). Without it, the script stops with a message instead of crawling on the CPU.

Runs offline from the local folders in G:\\models\\higgs-audio-v2 and never downloads anything.
"""

import os

# The model folder's processor_config.json names the Hub repo of the audio tokenizer. Offline mode
# turns any attempt to fetch it (or anything else) into an error instead of a silent download.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

import librosa
import soundfile as sf
import torch
from transformers import (
    AutoTokenizer,
    DacFeatureExtractor,
    HiggsAudioV2ForConditionalGeneration,
    HiggsAudioV2Processor,
    HiggsAudioV2TokenizerModel,
    set_seed,
)

ROOT = Path(r"G:\models\higgs-audio-v2")
MODEL_DIR = ROOT / "higgs-tts-2-3b-base"
TOKENIZER_DIR = ROOT / "higgs-audio-v2-tokenizer"
SAMPLE_RATE = 24000
# 11.5 GB of bf16 weights, 0.8 GB audio tokenizer, plus KV cache and activations.
MIN_FREE_VRAM_GB = 14.0
LLAMA_TASK = "llama-server"
LLAMA_HEALTH = "http://127.0.0.1:8080/health"
# The llama-hold watcher relaunches llama-server seconds after a plain stop. While this flag file
# exists it stops every llama-server and keeps them down, and it relaunches the day server 15 s
# after the file is gone. Note that the hold also stops the CPU night server on :8081.
HOLD_TASK = "llama-hold"
HOLD_FLAG = Path(r"C:\Users\mvyho\llama-hold.manual")
SYSTEM_PROMPT = "Generate audio following instruction."
# Boson's model card uses this system message for [SPEAKER*]-tagged dialogue.
DIALOGUE_SYSTEM_PROMPT = (
    "You are an AI assistant designed to convert text into speech.\n"
    "If the user's message includes a [SPEAKER*] tag, do not read out the tag and generate speech for the "
    "following text, using the specified voice.\n"
    "If no speaker tag is present, select a suitable voice on your own."
)


def free_vram_gb() -> float | None:
    """Free VRAM on GPU 0 in GB (lower of CUDA's and nvidia-smi's reading), or None without CUDA."""
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


def llama_up() -> bool:
    try:
        with urllib.request.urlopen(LLAMA_HEALTH, timeout=3) as r:
            return r.status == 200
    except OSError:
        return False


def hold_running() -> bool:
    out = subprocess.run(["schtasks", "/query", "/tn", HOLD_TASK, "/fo", "csv", "/nh"],
                         capture_output=True, text=True)
    return out.returncode == 0 and '"Running"' in out.stdout


def pause_llama() -> str:
    """Stop llama-server and return how, so resume_llama() undoes it the same way."""
    if hold_running():
        print(f"Pausing llama-server through llama-hold ({HOLD_FLAG})...", flush=True)
        HOLD_FLAG.touch()
        return "hold"
    print("Stopping the llama-server task...", flush=True)
    subprocess.run(["schtasks", "/end", "/tn", LLAMA_TASK], capture_output=True, text=True)
    return "task"


def wait_for_free_vram() -> None:
    for _ in range(60):
        free = free_vram_gb() or 0.0
        if free >= MIN_FREE_VRAM_GB:
            print(f"  {free:.1f} GB VRAM free", flush=True)
            return
        time.sleep(1)
    raise SystemExit(
        f"llama-server paused but only {free_vram_gb() or 0:.1f} GB of VRAM is free; "
        "something else holds the GPU (check nvidia-smi)."
    )


def resume_llama(how: str) -> None:
    print("Resuming llama-server...", flush=True)
    if how == "hold":
        HOLD_FLAG.unlink(missing_ok=True)
    else:
        subprocess.run(["schtasks", "/run", "/tn", LLAMA_TASK], capture_output=True, text=True)
    # llama-hold waits 15 s, then the model loads from the G: USB disk (seconds when cached).
    for _ in range(100):
        time.sleep(3)
        if llama_up():
            print("  llama-server is back on :8080", flush=True)
            return
    print("  llama-server is not answering after 5 minutes. Check C:\\Users\\mvyho\\llama-hold.log", flush=True)


def load_processor(device: str) -> HiggsAudioV2Processor:
    """Build the processor from the local folders.

    AutoProcessor.from_pretrained(MODEL_DIR) would load the audio tokenizer from the Hub id written in
    processor_config.json and ignore the local copy, so the parts are assembled here instead.
    """
    config = json.loads((MODEL_DIR / "processor_config.json").read_text(encoding="utf-8"))
    feature_extractor = DacFeatureExtractor.from_dict(config["feature_extractor"])
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    audio_tokenizer = HiggsAudioV2TokenizerModel.from_pretrained(TOKENIZER_DIR, device_map=device)
    chat_template = (MODEL_DIR / "chat_template.jinja").read_text(encoding="utf-8")
    return HiggsAudioV2Processor(feature_extractor, tokenizer, audio_tokenizer, chat_template=chat_template)


def build_conversation(text: str, scene: str, ref_audio: str | None, ref_text: str | None,
                       speakers: list[str] | None = None) -> list[dict]:
    system = DIALOGUE_SYSTEM_PROMPT if "[SPEAKER" in text else SYSTEM_PROMPT
    # Each speaker description is its own scene item ("SPEAKER0: feminine"), as in the model card.
    scene_items = [scene, *(speakers or [])]
    conversation = [
        {"role": "system", "content": [{"type": "text", "text": system}]},
        {"role": "scene", "content": [{"type": "text", "text": item} for item in scene_items]},
    ]
    if ref_audio:
        # Cloning is a one-turn example: the clip's transcript, then the clip as the model's reply.
        # Loaded here as 24 kHz mono samples, so transformers never picks an audio decoding backend.
        clip, _ = librosa.load(ref_audio, sr=SAMPLE_RATE, mono=True)
        conversation += [
            {"role": "user", "content": [{"type": "text", "text": ref_text}]},
            {"role": "assistant", "content": [{"type": "audio", "audio": clip}]},
        ]
    conversation.append({"role": "user", "content": [{"type": "text", "text": text}]})
    return conversation


def generate(a: argparse.Namespace, device: str) -> tuple[torch.Tensor, float, float]:
    dtype = torch.float32 if device == "cpu" else torch.bfloat16
    t0 = time.time()
    processor = load_processor(device)
    model = HiggsAudioV2ForConditionalGeneration.from_pretrained(MODEL_DIR, device_map=device, dtype=dtype)
    load_s = time.time() - t0

    conversation = build_conversation(a.text, a.scene, a.ref_audio, a.ref_text, a.speaker)
    inputs = processor.apply_chat_template(
        conversation, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
    ).to(model.device)

    if a.seed is not None:
        set_seed(a.seed)
    if a.greedy:
        sampling = {"do_sample": False}
    else:
        sampling = {"do_sample": True, "temperature": a.temperature, "top_p": 0.95, "top_k": 50}

    t1 = time.time()
    with torch.inference_mode():
        codes = model.generate(**inputs, max_new_tokens=a.max_new_tokens, **sampling)
        wav = processor.batch_decode(codes)[0]
    return wav, load_s, time.time() - t1


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--text")
    src.add_argument("--text-file", help="UTF-8 text file, e.g. a dialogue with [SPEAKER0] / [SPEAKER1] lines")
    p.add_argument("--out", required=True)
    p.add_argument("--scene", default="Audio is recorded from a quiet room.", help="Recording environment")
    p.add_argument("--speaker", action="append", help='Voice for a dialogue tag, e.g. "SPEAKER0: feminine"; repeat per speaker')
    p.add_argument("--ref-audio", default=None, help="Reference clip to clone the voice from")
    p.add_argument("--ref-text", default=None, help="Transcript of --ref-audio (required with it)")
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--greedy", action="store_true", help="Deterministic decoding instead of sampling")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--max-new-tokens", type=int, default=1200, help="25 tokens per second of audio")
    p.add_argument("--device", default="auto", help="auto, cuda:0 or cpu (cpu is very slow)")
    p.add_argument("--free-gpu", action="store_true", help="Stop llama-server for the run, restart it after")
    a = p.parse_args()
    if a.text_file:
        a.text = Path(a.text_file).read_text(encoding="utf-8").strip()
    if a.ref_audio and not a.ref_text:
        p.error("--ref-audio needs --ref-text, the transcript of the clip")

    paused, was_up = None, False
    device = a.device
    # Everything after llama-server may have been paused sits in this try, so it always comes back.
    try:
        if device == "auto":
            free = free_vram_gb()
            if free is None:
                raise SystemExit("No CUDA GPU. Pass --device cpu to run on the CPU anyway (very slow).")
            if free < MIN_FREE_VRAM_GB:
                if not a.free_gpu:
                    raise SystemExit(
                        f"Only {free:.1f} GB of VRAM free; Higgs needs about {MIN_FREE_VRAM_GB:.0f}. "
                        "Rerun with --free-gpu to pause llama-server for this run."
                    )
                was_up = llama_up()
                paused = pause_llama()
                wait_for_free_vram()
            device = "cuda:0"
        wav, load_s, gen_s = generate(a, device)
    finally:
        # Always remove a hold flag this run created; restart a plain task only if it was running.
        if paused == "hold" or (paused == "task" and was_up):
            resume_llama(paused)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sf.write(a.out, wav.float().numpy(), SAMPLE_RATE)
    seconds = len(wav) / SAMPLE_RATE
    print(
        f"{a.out}: {seconds:.1f}s audio on {device} | load {load_s:.1f}s, "
        f"generate {gen_s:.1f}s ({seconds / gen_s:.2f}x real time)"
    )


if __name__ == "__main__":
    main()
