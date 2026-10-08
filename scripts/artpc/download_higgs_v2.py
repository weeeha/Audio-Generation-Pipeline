import os, time
from huggingface_hub import snapshot_download
root = r"G:\models\higgs-audio-v2"
for repo, sub in [("bosonai/higgs-audio-v2-tokenizer", "higgs-audio-v2-tokenizer"),
                  ("bosonai/higgs-tts-2-3b-base", "higgs-tts-2-3b-base")]:
    t = time.time()
    print(f"START {repo}", flush=True)
    snapshot_download(repo, local_dir=os.path.join(root, sub), max_workers=4)
    print(f"DONE {repo} in {time.time()-t:.0f}s", flush=True)
print("ALL DONE", flush=True)
