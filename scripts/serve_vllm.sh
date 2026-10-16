#!/bin/bash
# Thesis vLLM server. Uses /home/workbench/thesis-env only, not finalrouter.
set -euo pipefail
VENV=/home/workbench/thesis-env
if [[ ! -x "$VENV/bin/vllm" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -U pip
  "$VENV/bin/pip" install -r "$(dirname "$0")/../requirements-wsl.txt"
fi
exec "$VENV/bin/vllm" serve "Qwen/Qwen3-8B-FP8" \
  --host 127.0.0.1 \
  --port 8011 \
  --served-model-name "Qwen/Qwen3-8B-FP8" \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.55 \
  --enforce-eager
