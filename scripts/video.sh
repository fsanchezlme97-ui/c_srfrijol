#!/usr/bin/env bash
# Vídeo con Wan 2.2 TI2V 5B en ComfyUI (./srfrijol video antes). Mejor el texto en inglés.
#   scripts/video.sh "descripción" [pasos=20] [fotogramas=49]   → ruta del .webm en comfyui/output/srfrijol
set -euo pipefail
E="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
TXT=${1:?falta la descripción}; STEPS=${2:-20}; LEN=${3:-49}
body=$(jq -c --arg t "$TXT" --argjson s "$STEPS" --argjson l "$LEN" --argjson seed "$RANDOM" \
  '{prompt: (.["5"].inputs.text=$t | .["8"].inputs.steps=$s | .["8"].inputs.seed=$seed | .["7"].inputs.length=$l)}' \
  "$E/workflows/wan22-texto-a-video.json")
id=$(curl -sf http://127.0.0.1:8188/prompt -H 'Content-Type: application/json' -d "$body" | jq -r .prompt_id)
echo "En cola: $id" >&2
while :; do
  h=$(curl -sf "http://127.0.0.1:8188/history/$id" || echo '{}')
  st=$(jq -r --arg i "$id" '.[$i].status.status_str // empty' <<<"$h")
  [ "$st" = success ] && { jq -r --arg i "$id" '.[$i].outputs[][][]?|select(.filename?)|"'"$E"'/comfyui/output/\(.subfolder)/\(.filename)"' <<<"$h"; exit 0; }
  [ "$st" = error ] && { jq -r --arg i "$id" '.[$i].status.messages[-1][1].exception_message // .[$i].status.messages[-1]' <<<"$h" >&2; exit 1; }
  sleep 3
done
