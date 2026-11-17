"""
title: Vídeo (Wan 2.2)
description: Escribe lo que quieres ver y genera un vídeo corto con Wan 2.2 en ComfyUI (local).
version: 1.0
"""

import asyncio
import json
import os
import random
import time
import urllib.parse

import aiohttp
from pydantic import BaseModel, Field

E = os.path.expanduser("~/Proyectos/c_srfrijol")


class Pipe:
    class Valves(BaseModel):
        COMFY: str = Field(default="http://127.0.0.1:8188")
        OLLAMA: str = Field(default="http://127.0.0.1:11434")
        TRADUCTOR: str = Field(default="gemma4:e4b", description="modelo de Ollama que pasa el texto a un prompt en inglés")
        PASOS: int = Field(default=20, description="más pasos, más calidad y más tiempo (~10 s cada uno)")
        SEGUNDOS: int = Field(default=2, description="duración por defecto; se puede pedir en el texto (\"de 4 segundos\")")

    def __init__(self):
        self.valves = self.Valves()

    async def _estado(self, emit, texto, fin=False):
        if emit:
            await emit({"type": "status", "data": {"description": texto, "done": fin}})

    async def _prompt_ingles(self, s, texto):
        """Traduce y enriquece la petición; devuelve (prompt en inglés, segundos)."""
        q = (
            "Convierte esta petición de vídeo en un prompt en inglés para un modelo de texto a vídeo: una sola frase "
            "descriptiva (sujeto, acción, entorno, luz, cámara), sin comillas. Si la petición dice una duración en "
            f"segundos, ponla; si no, usa {self.valves.SEGUNDOS}. Responde solo JSON: "
            '{"prompt": "...", "segundos": N}\n\nPetición: ' + texto
        )
        body = {"model": self.valves.TRADUCTOR, "prompt": q, "stream": False, "format": "json",
                "think": False, "keep_alive": 0}  # keep_alive 0: que no se quede en la gráfica
        async with s.post(f"{self.valves.OLLAMA}/api/generate", json=body, timeout=120) as r:
            d = json.loads((await r.json())["response"])
        seg = max(1, min(int(d.get("segundos") or self.valves.SEGUNDOS), 5))
        return d["prompt"].strip(), seg

    async def pipe(self, body: dict, __event_emitter__=None):
        msgs = [m for m in body.get("messages", []) if m.get("role") == "user"]
        texto = msgs[-1]["content"] if msgs else ""
        if isinstance(texto, list):
            texto = " ".join(p.get("text", "") for p in texto if p.get("type") == "text")
        if not texto.strip():
            return "Escribe qué quieres ver en el vídeo."
        if body.get("metadata", {}).get("task"):  # título/etiquetas que pide Open WebUI: no generar nada
            return texto[:40]

        emit = __event_emitter__
        async with aiohttp.ClientSession() as s:
            await self._estado(emit, "Preparando la descripción…")
            try:
                prompt, seg = await self._prompt_ingles(s, texto)
            except Exception:
                prompt, seg = texto, self.valves.SEGUNDOS  # sin traductor: tal cual

            # libera la gráfica (llama-swap y Ollama) y arranca ComfyUI si no está
            await self._estado(emit, "Liberando la gráfica y arrancando ComfyUI…")
            p = await asyncio.create_subprocess_exec(
                f"{E}/srfrijol", "video", env={**os.environ, "SRFRIJOL_SIN_NAVEGADOR": "1"},
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await p.wait()

            wf = json.load(open(f"{E}/workflows/wan22-texto-a-video.json"))
            wf["5"]["inputs"]["text"] = prompt
            wf["7"]["inputs"]["length"] = seg * 24 + 1  # 24 fps; Wan pide 4n+1 fotogramas
            wf["8"]["inputs"]["steps"] = self.valves.PASOS
            wf["8"]["inputs"]["seed"] = random.randint(0, 2**31)
            try:
                async with s.post(f"{self.valves.COMFY}/prompt", json={"prompt": wf}, timeout=30) as r:
                    pid = (await r.json())["prompt_id"]
            except Exception as e:
                await self._estado(emit, "No se pudo hablar con ComfyUI", True)
                return f"No pude enviar el vídeo a ComfyUI ({e}). Prueba `./srfrijol video` en la terminal."

            t0 = time.time()
            calc = self.valves.PASOS * 10 * seg / 2 + 60
            while True:
                await asyncio.sleep(5)
                async with s.get(f"{self.valves.COMFY}/history/{pid}", timeout=30) as r:
                    h = (await r.json()).get(pid)
                st = (h or {}).get("status", {}).get("status_str")
                if st == "success":
                    break
                if st == "error":
                    msg = h["status"]["messages"][-1][1].get("exception_message", "error").split("\n")[0]
                    await self._estado(emit, "Falló la generación", True)
                    return f"ComfyUI falló: {msg}"
                t = int(time.time() - t0)
                await self._estado(emit, f"Generando vídeo de {seg} s… {t // 60}:{t % 60:02d} (unos {int(calc // 60)} min)")

            out = [f for o in h["outputs"].values() for v in o.values() if isinstance(v, list)
                   for f in v if isinstance(f, dict) and f.get("filename")][0]
            url = f"{self.valves.COMFY}/view?" + urllib.parse.urlencode(
                {"filename": out["filename"], "subfolder": out.get("subfolder", ""), "type": "output"})
            t = int(time.time() - t0)
            await self._estado(emit, f"Listo en {t // 60}:{t % 60:02d}", True)
            ruta = f"{E}/comfyui/output/{out.get('subfolder', '')}/{out['filename']}"
            return f"<video>{url}</video>\n\n*{prompt}*\n\nArchivo: `{ruta}`"
