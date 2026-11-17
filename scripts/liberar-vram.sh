#!/usr/bin/env bash
# Antes de cargar un modelo pesado en la gráfica: descarga los modelos que Ollama tenga en memoria (los de Helpert
# vuelven solos la próxima vez que se usen, ~3 s) y ejecuta la orden que recibe.
#   liberar-vram.sh <orden> [argumentos…]
for m in $(curl -s --max-time 3 http://127.0.0.1:11434/api/ps | jq -r '.models[]?.name' 2>/dev/null); do
  curl -s --max-time 10 http://127.0.0.1:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null
done
exec "$@"
