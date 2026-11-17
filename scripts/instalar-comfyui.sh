#!/usr/bin/env bash
# ComfyUI con PyTorch ROCm 6.3 (RX 6600 XT = gfx1032, sin soporte oficial: HSA_OVERRIDE_GFX_VERSION=10.3.0 al arrancar)
set -euo pipefail
E="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
[ -d "$E/comfyui/.git" ] || git clone -q --depth 1 --branch v0.45.0 https://github.com/comfyanonymous/ComfyUI.git "$E/comfyui"
cd "$E/comfyui"
[ -d .venv ] || uv venv -q --python 3.12 .venv
export VIRTUAL_ENV="$PWD/.venv"
uv pip install torch==2.9.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.3
uv pip install -r requirements.txt
[ -d custom_nodes/ComfyUI-GGUF ] || git clone -q --depth 1 https://github.com/city96/ComfyUI-GGUF custom_nodes/ComfyUI-GGUF
uv pip install -r custom_nodes/ComfyUI-GGUF/requirements.txt
# modelos de vídeo (los baja descargar.sh) en las carpetas de ComfyUI
ln -sfn "$E/models/video/wan22/Wan2.2-TI2V-5B-Q4_K_M.gguf" models/unet/Wan2.2-TI2V-5B-Q4_K_M.gguf
ln -sfn "$E/models/video/wan22/umt5-xxl-encoder-Q4_K_M.gguf" models/text_encoders/umt5-xxl-encoder-Q4_K_M.gguf
ln -sfn "$E/models/video/wan22/wan2.2_vae.safetensors" models/vae/wan2.2_vae.safetensors
HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv/bin/python -c "import torch; print('torch', torch.__version__, 'gpu', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-')"
echo "COMFYUI INSTALADO"
