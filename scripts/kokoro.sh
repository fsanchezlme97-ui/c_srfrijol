#!/usr/bin/env bash
# Kokoro-FastAPI en la CPU: kokoro.sh <puerto>
cd "$(dirname "$(readlink -f "$0")")/../kokoro" || exit 1
export USE_GPU=false PYTHONPATH="$PWD:$PWD/api" MODEL_DIR=src/models VOICES_DIR=src/voices/v1_0 WEB_PLAYER_PATH="$PWD/web" ESPEAK_DATA_PATH=/usr/share/espeak-ng-data
exec .venv/bin/uvicorn api.src.main:app --host 127.0.0.1 --port "$1"
