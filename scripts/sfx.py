#!/usr/bin/env python3
"""Text-to-SFX on the Art PC (Stable Audio 3 small-sfx in ComfyUI), driven from the Mac.

    python3 scripts/sfx.py "heavy metal door slam in a concrete hallway" --seconds 3 --takes 4

Opens an SSH tunnel to artstation, makes sure the SFX ComfyUI instance on :8189 is up,
queues one generation per take (different seeds), and saves WAVs to ./sfx-out/.
Stdlib only.
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HOST = os.environ.get("SFX_HOST", "mvyho@100.114.149.53")  # Art PC over Tailscale
REMOTE_PORT = 8189
LOCAL_PORT = 18189
CKPT = "stable_audio_3_small_sfx.safetensors"
TEXT_ENCODER = "t5gemma_b_b_ul2.safetensors"
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "LogLevel=ERROR"]


def shape_prompt(text: str, seconds: float) -> str:
    """Turn a short idea into the prompt Stable Audio sees.

    SA3 small-sfx was trained on descriptive SFX captions; it rewards concrete nouns,
    materials, space and envelope ("short, dry, close-mic'd") over adjectives like
    "epic". This default only nudges toward a clean, isolated one-shot.
    """
    text = text.strip().rstrip(".")
    if seconds <= 4:
        return f"{text}. Single isolated sound effect, clean, no music, no voice."
    return f"{text}. Sound effect, clean recording, no music, no voice."


def build_graph(prompt: str, seconds: float, seed: int, steps: int, prefix: str) -> dict:
    # Same graph as Comfy-Org's audio_stable_audio_3_medium template, minus the
    # optional Qwen prompt-rewrite branch (4 GB extra VRAM).
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": TEXT_ENCODER, "type": "stable_audio", "device": "default"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
        "5": {"class_type": "EmptyLatentAudio", "inputs": {"seconds": seconds, "batch_size": 1}},
        "6": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "lcm",
                         "scheduler": "simple", "denoise": 1.0, "model": ["1", 0],
                         "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0]}},
        "7": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveAudio", "inputs": {"audio": ["7", 0], "filename_prefix": prefix}},
    }


def api(path: str, payload=None):
    url = f"http://127.0.0.1:{LOCAL_PORT}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    return json.loads(body) if body[:1] in (b"{", b"[") else body


def ensure_server():
    ps = r"powershell -NoProfile -ExecutionPolicy Bypass -File G:\AI\sfx\start-sfx-server.ps1"
    out = subprocess.run(["ssh", *SSH_OPTS, HOST, ps], capture_output=True, text=True)
    print(out.stdout.strip())
    if out.returncode != 0:
        sys.exit(f"server did not start:\n{out.stderr}")


def open_tunnel() -> subprocess.Popen:
    tunnel = subprocess.Popen(["ssh", *SSH_OPTS, "-N", "-L",
                               f"{LOCAL_PORT}:127.0.0.1:{REMOTE_PORT}", HOST])
    for _ in range(40):
        try:
            api("/system_stats")
            return tunnel
        except OSError:
            time.sleep(0.25)
    tunnel.terminate()
    sys.exit("tunnel to :8189 never answered")


def to_wav(src: Path) -> Path:
    dst = src.with_suffix(".wav")
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI24", str(src), str(dst)], check=True)
    src.unlink()
    return dst


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prompt")
    p.add_argument("--seconds", type=float, default=3.0)
    p.add_argument("--takes", type=int, default=3, help="variations, one seed each")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--seed", type=int, help="first seed (default random)")
    p.add_argument("--raw", action="store_true", help="send the prompt as-is, skip shape_prompt")
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "sfx-out")
    a = p.parse_args()

    prompt = a.prompt if a.raw else shape_prompt(a.prompt, a.seconds)
    slug = re.sub(r"[^a-z0-9]+", "-", a.prompt.lower()).strip("-")[:40]
    seed0 = a.seed if a.seed is not None else random.randrange(2**32)
    a.out.mkdir(parents=True, exist_ok=True)

    ensure_server()
    tunnel = open_tunnel()
    try:
        print(f"prompt: {prompt}")
        jobs = []
        for i in range(a.takes):
            seed = seed0 + i
            graph = build_graph(prompt, a.seconds, seed, a.steps, f"sfx/{slug}_s{seed}")
            jobs.append((seed, api("/prompt", {"prompt": graph})["prompt_id"]))
        t0 = time.time()
        for seed, pid in jobs:
            while True:
                hist = api(f"/history/{pid}")
                if pid in hist:
                    break
                time.sleep(0.5)
            entry = hist[pid]
            if entry.get("status", {}).get("status_str") == "error":
                sys.exit(json.dumps(entry["status"], indent=2))
            for node in entry["outputs"].values():
                for f in node.get("audio", []):
                    q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f["subfolder"], "type": f["type"]})
                    local = a.out / f["filename"]
                    local.write_bytes(api(f"/view?{q}"))
                    print(f"seed {seed}: {to_wav(local)}  ({time.time() - t0:.1f}s)")
    finally:
        tunnel.terminate()


if __name__ == "__main__":
    main()
