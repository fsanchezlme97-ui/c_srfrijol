#!/usr/bin/env bash
# Descargas de c_srfrijol, una tras otra y reanudables (curl -C -). Vuelve a lanzarlo si se corta: sigue donde iba.
set -uo pipefail
E="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
HF=https://huggingface.co
get() {   # get <url> <destino>
  local url=$1 out=$2
  [ -f "$out.ok" ] && { echo "ya está: ${out#$E/}"; return 0; }
  mkdir -p "$(dirname "$out")"
  echo "$(date +%T) bajando ${out#$E/}"
  for i in 1 2 3 4 5; do
    curl -fL -C - --retry 5 --retry-delay 5 -sS -o "$out" "$url" && { touch "$out.ok"; echo "$(date +%T) ok ${out#$E/} $(du -h "$out" | cut -f1)"; return 0; }
    echo "reintento $i: ${out#$E/}"; sleep 10
  done
  echo "FALLO: $url" ; return 1
}
# Binarios (Vulkan)
get https://github.com/ggml-org/llama.cpp/releases/download/b12428/llama-b12428-bin-ubuntu-vulkan-x64.tar.gz "$E/bin/llama.tar.gz"
get https://github.com/leejet/stable-diffusion.cpp/releases/download/master-1104-5dcfa79/sd-master-5dcfa79-bin-Linux-Ubuntu-26.04-x86_64-vulkan.zip "$E/bin/sd.zip"
get https://github.com/mostlygeek/llama-swap/releases/download/v273/llama-swap_273_linux_amd64.tar.gz "$E/bin/llama-swap.tar.gz"
# Imagen: FLUX.2 klein 4B
get $HF/leejet/FLUX.2-klein-4B-GGUF/resolve/main/flux-2-klein-4b-Q4_0.gguf "$E/models/image/flux2-klein/flux-2-klein-4b-Q4_0.gguf"
get $HF/unsloth/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf "$E/models/image/flux2-klein/Qwen3-4B-Q4_K_M.gguf"
get $HF/Comfy-Org/Flux-2-Klein-4B/resolve/main/split_files/vae/flux2-vae.safetensors "$E/models/image/flux2-klein/flux2-vae.safetensors"
# Imagen: SDXL
get $HF/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors "$E/models/image/sdxl/sd_xl_base_1.0.safetensors"
get $HF/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors "$E/models/image/sdxl/sdxl_vae_fp16_fix.safetensors"
# Imagen: FLUX.1 schnell (GGUF de leejet para sd.cpp; codificadores y VAE de second-state, sin registro)
get $HF/leejet/FLUX.1-schnell-gguf/resolve/main/flux1-schnell-q4_k.gguf "$E/models/image/flux1-schnell/flux1-schnell-q4_k.gguf"
get $HF/second-state/FLUX.1-schnell-GGUF/resolve/main/t5xxl-Q4_K.gguf "$E/models/image/flux1-schnell/t5xxl-Q4_K.gguf"
get $HF/second-state/FLUX.1-schnell-GGUF/resolve/main/clip_l.safetensors "$E/models/image/flux1-schnell/clip_l.safetensors"
get $HF/second-state/FLUX.1-schnell-GGUF/resolve/main/ae.safetensors "$E/models/image/flux1-schnell/ae.safetensors"
# Texto: Qwen3.6-35B-A3B (MoE)
get $HF/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf "$E/models/llm/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf"
# Vídeo: Wan 2.2 TI2V 5B
get $HF/QuantStack/Wan2.2-TI2V-5B-GGUF/resolve/main/Wan2.2-TI2V-5B-Q4_K_M.gguf "$E/models/video/wan22/Wan2.2-TI2V-5B-Q4_K_M.gguf"
get $HF/city96/umt5-xxl-encoder-gguf/resolve/main/umt5-xxl-encoder-Q4_K_M.gguf "$E/models/video/wan22/umt5-xxl-encoder-Q4_K_M.gguf"
get $HF/Comfy-Org/Wan-2.2/resolve/main/split_files/vae/wan2.2_vae.safetensors "$E/models/video/wan22/wan2.2_vae.safetensors"
echo "$(date +%T) DESCARGAS TERMINADAS"
