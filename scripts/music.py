#!/usr/bin/env python3
"""Text to music with ACE-Step 1.5, on the Mac or the Art PC.

    python3 scripts/music.py "warm indie folk, acoustic guitar, gentle female vocal" --lyrics-file song.txt --seconds 60
    python3 scripts/music.py "cinematic orchestral build" --instrumental --seconds 45 --takes 2
    python3 scripts/music.py "..." --instrumental --host artpc --free-gpu --model acestep-v15-xl-turbo
    python3 scripts/music.py --jobs cues.json --host artpc --free-gpu   # several cues, one server session

The Mac (default) runs ACE-Step's API server from ~/ACE-Step-1.5 on 127.0.0.1:8001. It starts the
server when needed and stops it afterwards, unless it was already running or --keep is given.

--host artpc starts the same server on the Art PC over SSH and reaches it through a tunnel. It needs
--free-gpu, which pauses llama-server for the run: next to it only about 2 GB of VRAM is free, and
ACE-Step runs out of memory even in its smallest mode. The PC launcher tells ACE-Step how much memory
nvidia-smi reports as free, because ACE-Step otherwise sizes itself from the card's total.

--jobs takes a JSON list of cues; each entry sets any of name, prompt, lyrics, lyrics_file,
instrumental, seconds, takes, seed, bpm, key, lang, and the command line fills in the rest. All cues
run in one server session, so the Art PC pauses llama-server once.

Stdlib only. Files land in ./music-out/ with a .json next to each one (seed, BPM, key, lyrics).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ACE_DIR = Path.home() / "ACE-Step-1.5"
PORT = 8001
TUNNEL_PORT = 18001
PC_HOST = os.environ.get("MUSIC_HOST", "mvyho@100.114.149.53")  # Art PC over Tailscale
PC_DIR = r"G:\AI\music"
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "LogLevel=ERROR"]
LM_MODEL = "acestep-5Hz-lm-1.7B"
LOG = Path.home() / ".local" / "state" / "acestep" / "api.log"


def api(base: str, path: str, payload=None, timeout: float = 600):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ACE-Step {e.code} on {path}:\n{e.read().decode(errors='replace')}")
    return json.loads(body) if body[:1] in (b"{", b"[") else body


def server_up(base: str) -> bool:
    try:
        with urllib.request.urlopen(base + "/v1/models", timeout=3):
            return True
    except OSError:
        return False


def wait_up(base: str, seconds: int) -> None:
    for _ in range(seconds):
        if server_up(base):
            return
        time.sleep(1)
    sys.exit(f"ACE-Step API never answered on {base}")


def start_mac_server(model: str) -> subprocess.Popen:
    """Same settings as ACE-Step's start_api_server_macos.sh, minus its git update check."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "ACESTEP_LM_BACKEND": "mlx", "TOKENIZERS_PARALLELISM": "false",
           "ACESTEP_INIT_LLM": "auto", "ACESTEP_LM_MODEL_PATH": LM_MODEL, "ACESTEP_CONFIG_PATH": model}
    print(f"Starting ACE-Step on the Mac (log: {LOG})", flush=True)
    with open(LOG, "ab") as log:
        proc = subprocess.Popen([str(ACE_DIR / ".venv" / "bin" / "acestep-api"), "--host", "127.0.0.1",
                                 "--port", str(PORT)], cwd=ACE_DIR, env=env, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
    wait_up(f"http://127.0.0.1:{PORT}", 120)
    return proc


def pc(script: str, *args: str) -> None:
    cmd = rf"powershell -NoProfile -ExecutionPolicy Bypass -File {PC_DIR}\{script} " + " ".join(args)
    out = subprocess.run(["ssh", *SSH_OPTS, PC_HOST, cmd], capture_output=True, text=True)
    print(out.stdout.strip(), flush=True)
    if out.returncode != 0:
        sys.exit(f"{script} failed:\n{out.stderr.strip()}")


def open_tunnel() -> subprocess.Popen:
    tunnel = subprocess.Popen(["ssh", *SSH_OPTS, "-N", "-L", f"{TUNNEL_PORT}:127.0.0.1:{PORT}", PC_HOST])
    for _ in range(40):
        if server_up(f"http://127.0.0.1:{TUNNEL_PORT}"):
            return tunnel
        time.sleep(0.25)
    tunnel.terminate()
    sys.exit(f"tunnel to the Art PC's :{PORT} never answered")


def build_job(a: argparse.Namespace) -> dict:
    if a.instrumental:
        lyrics = "[Instrumental]"
    elif a.lyrics_file:
        lyrics = Path(a.lyrics_file).read_text(encoding="utf-8")
    else:
        lyrics = a.lyrics or ""
    job = {
        "prompt": a.prompt,
        "lyrics": lyrics,
        "audio_duration": a.seconds,
        "batch_size": a.takes,
        "thinking": not a.no_plan,  # the 1.7B LM plans structure, BPM and key before the DiT renders
        "audio_format": a.format,
        "inference_steps": a.steps,
        "vocal_language": a.lang,
        "model": a.model,
    }
    if a.seed is not None:
        job.update(use_random_seed=False, seed=a.seed)
    if a.bpm:
        job["bpm"] = a.bpm
    if a.key:
        job["key_scale"] = a.key
    return job


def generate(base: str, a: argparse.Namespace) -> None:
    t0 = time.time()
    task_id = api(base, "/release_task", build_job(a))["data"]["task_id"]
    while True:
        item = api(base, "/query_result", {"task_id_list": [task_id]})["data"][0]
        if item.get("status") in (1, 2):
            break
        if time.time() - t0 > 1800:
            sys.exit(f"task {task_id} still running after 30 minutes")
        time.sleep(2)
    if item["status"] == 2:
        sys.exit(f"ACE-Step failed:\n{json.dumps(item, indent=2)[:2000]}")

    slug = re.sub(r"[^a-z0-9]+", "-", (a.name or a.prompt).lower()).strip("-")[:40]
    a.out.mkdir(parents=True, exist_ok=True)
    for i, take in enumerate(json.loads(item["result"])):
        if not take.get("file"):
            continue
        with urllib.request.urlopen(base + take["file"], timeout=300) as r:
            data = r.read()
        # seed_value lists the whole batch ("70,2050038755"): take i used entry i. Only the first is
        # the --seed you passed; the others are random, and the .json keeps them for a re-run.
        seeds = str(take.get("seed_value", "")).split(",")
        seed = seeds[i] if i < len(seeds) and seeds[i] else str(i)
        dest = a.out / f"{slug}_{take.get('dit_model', a.model)}_s{seed}_{i}.{a.format}"
        dest.write_bytes(data)
        meta = {k: take.get(k) for k in ("metas", "seed_value", "lm_model", "dit_model")}
        dest.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        m = take.get("metas") or {}
        print(f"{dest}  ({m.get('bpm')} BPM, {m.get('keyscale')}, {take.get('dit_model')}, "
              f"LM {take.get('lm_model') or 'off'}, {time.time() - t0:.0f}s)", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prompt", nargs="?", help="Style, instruments, mood, vocal type")
    p.add_argument("--jobs", type=Path, help="JSON list of cues to run in one server session")
    p.add_argument("--name", help="File name prefix instead of the prompt")
    lyr = p.add_mutually_exclusive_group()
    lyr.add_argument("--lyrics", help="Lyrics with [Verse] / [Chorus] tags")
    lyr.add_argument("--lyrics-file")
    lyr.add_argument("--instrumental", action="store_true")
    p.add_argument("--seconds", type=float, default=30, help="10 to 600")
    p.add_argument("--takes", type=int, default=1, help="Variations in one batch, up to 8")
    p.add_argument("--seed", type=int)
    p.add_argument("--bpm", type=int)
    p.add_argument("--key", help='e.g. "G major"')
    p.add_argument("--lang", default="en", help="Lyrics language")
    p.add_argument("--model", default="acestep-v15-turbo", help="DiT model, e.g. acestep-v15-xl-turbo")
    p.add_argument("--steps", type=int, default=8, help="8 for turbo models")
    p.add_argument("--no-plan", action="store_true", help="Skip the 1.7B LM planner (faster, flatter)")
    p.add_argument("--format", default="mp3", choices=["mp3", "wav", "flac"])
    p.add_argument("--host", default="mac", choices=["mac", "artpc"])
    p.add_argument("--free-gpu", action="store_true", help="Art PC: pause llama-server for the run (required)")
    p.add_argument("--keep", action="store_true", help="Leave the ACE-Step server running afterwards")
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "music-out")
    a = p.parse_args()
    jobs = [a]
    if a.jobs:
        jobs = [argparse.Namespace(**{**vars(a), **cue}) for cue in json.loads(a.jobs.read_text(encoding="utf-8"))]
    for job in jobs:
        if not job.prompt:
            p.error("a prompt is required (positional, or 'prompt' in each --jobs entry)")
        if not 1 <= job.takes <= 8:
            p.error("--takes must be 1 to 8")

    if a.host == "mac":
        base = f"http://127.0.0.1:{PORT}"
        proc = None if server_up(base) else start_mac_server(a.model)
        try:
            for job in jobs:
                generate(base, job)
        finally:
            if proc and not a.keep:
                proc.terminate()
                proc.wait(timeout=60)
        return

    if not a.free_gpu:
        p.error("--host artpc needs --free-gpu: ACE-Step does not fit next to llama-server (about 2 GB free)")
    if a.keep:
        print("--keep ignored with --free-gpu: llama-server must come back.", flush=True)
        a.keep = False
    # The PC resumes llama-server by itself after this long, in case this client dies mid-run.
    audio_min = sum(job.seconds * job.takes for job in jobs) / 60
    lease = 15 + int(2 * audio_min + 0.999)
    start_args = ["-Model", a.model, "-LeaseMinutes", str(lease)] + (["-FreeGpu"] if a.free_gpu else [])
    try:
        pc("start-music-server.ps1", *start_args)
        tunnel = open_tunnel()
        try:
            for job in jobs:
                generate(f"http://127.0.0.1:{TUNNEL_PORT}", job)
        finally:
            tunnel.terminate()
    finally:
        # Also runs when the start failed halfway, so a paused llama-server always resumes.
        if not a.keep:
            pc("stop-music-server.ps1")


if __name__ == "__main__":
    main()
