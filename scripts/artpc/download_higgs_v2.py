import os, time
from huggingface_hub import snapshot_download
root = r"G:\models\higgs-audio-v2"
for repo, sub in [("bosonai/higgs-audio-v2-tokenizer", "higgs-audio-v2-tokenizer"),
                  ("bosonai/higgs-tts-2-3b-base", "higgs-tts-2-3b-base")]:
    t = time.time()
    print(f"START {repo}", flush=True)
    # Long pulls drop mid-file (IncompleteRead); each retry resumes from the .incomplete file.
    for attempt in range(1, 11):
        try:
            snapshot_download(repo, local_dir=os.path.join(root, sub), max_workers=4)
            break
        except Exception as e:
            print(f"RETRY {attempt} {repo}: {type(e).__name__}: {e}", flush=True)
            time.sleep(15)
    else:
        raise SystemExit(f"FAILED {repo} after 10 attempts")
    print(f"DONE {repo} in {time.time()-t:.0f}s", flush=True)
print("ALL DONE", flush=True)
