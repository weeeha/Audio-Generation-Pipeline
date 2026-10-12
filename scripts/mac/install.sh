#!/bin/zsh
# install.sh: set up Qwen3-TTS on an Apple Silicon Mac (mlx-audio, on-demand server on 127.0.0.1:8890).
# Idempotent: re-running skips what is already there. Needs uv (https://docs.astral.sh/uv/).
set -euo pipefail

HERE="${0:A:h}"
ROOT="$HOME/models/qwen3-tts"
MODELS=(Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit Qwen3-TTS-12Hz-1.7B-Base-8bit)
LABEL="com.weeeha.qwen3-tts"

mkdir -p "$ROOT" "$HOME/.local/state/qwen3-tts" "$HOME/.local/bin"
cd "$ROOT"

if [ ! -x .venv/bin/mlx_audio.server ]; then
  uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python "mlx-audio[server]==0.5.8" "huggingface_hub[cli]"
fi

# hf resumes partial files, so a stalled download can simply be re-run.
for m in $MODELS; do
  .venv/bin/hf download "mlx-community/$m" --local-dir "./$m"
done

cp "$HERE/tts-up" "$HERE/tts-down" "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/tts-up" "$HOME/.local/bin/tts-down"

cp "$HERE/$LABEL.plist" "$HOME/Library/LaunchAgents/"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/$LABEL.plist"

echo "Installed. Start with: tts-up"
