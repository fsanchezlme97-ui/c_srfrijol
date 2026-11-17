#!/usr/bin/env bash
# Kokoro-FastAPI en CPU: dependencias del uv.lock (torch de CPU) y el modelo v1.0
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/../kokoro"
uv sync --frozen --extra cpu
PYTHONPATH=$PWD:$PWD/api uv run --no-sync python docker/scripts/download_model.py --output api/src/models/v1_0
echo "KOKORO INSTALADO"
