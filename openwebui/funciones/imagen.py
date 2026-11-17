"""
title: Imagen
description: Escribe lo que quieres ver y genera una imagen con stable-diffusion.cpp (local, vía llama-swap).
version: 1.0
"""

import base64
import io
import json
import os
import re
import time

import aiohttp
from PIL import Image
from pydantic import BaseModel, Field

E = os.path.expanduser("~/Proyectos/c_srfrijol")
# id en llama-swap -> (nombre, ¿prompt en inglés? (False, True o "tags"), segundos aproximados)
MODELOS = {
    "flux2-klein": ("FLUX.2 klein", False, 30),
    "illustrious": ("Illustrious XL (anime)", "tags", 75),
    "sdxl": ("SDXL", True, 80),
    "flux1-schnell": ("FLUX.1 schnell", True, 150),
}
# sd-server lee parámetros extra dentro del prompt
NEGATIVO_ANIME = ("nsfw, lowres, worst quality, low quality, bad anatomy, bad hands, extra fingers, missing fingers, "
                  "blurry, jpeg artifacts, watermark, signature, text")


def anime(tags: str) -> str:
    """Prompt de Illustrious: calidad delante y negativo dentro (sd-server lee <sd_cpp_extra_args>). Tiende a dibujar
    chicas aunque pidas «1boy»: «male focus» y «1girl» en el negativo lo corrigen."""
    neg = NEGATIVO_ANIME
    if re.search(r"\b\d?boys?\b", tags) and not re.search(r"\b\d?girls?\b", tags):
        tags, neg = tags + ", male focus", "1girl, female, " + neg
    return ("masterpiece, best quality, very aesthetic, absurdres, " + tags +
            '<sd_cpp_extra_args>{"negative_prompt": "' + neg + '"}</sd_cpp_extra_args>')
# palabras del texto -> tamaño (múltiplos de 64, ~1 megapíxel)
FORMATOS = [(r"\b(vertical|retrato|m[oó]vil|historia)\b", (768, 1344)),
            (r"\b(horizontal|panor[aá]mic|paisaje|16:9|fondo de pantalla|wallpaper)", (1344, 768))]


class Pipe:
    class Valves(BaseModel):
        SWAP: str = Field(default="http://127.0.0.1:8090/v1")
        OLLAMA: str = Field(default="http://127.0.0.1:11434")
        TRADUCTOR: str = Field(default="gemma4:e4b")

    def __init__(self):
        self.type = "manifold"
        self.valves = self.Valves()

    def pipes(self):
        return [{"id": k, "name": f"Imagen · {v[0]}"} for k, v in MODELOS.items()]

    async def _ingles(self, s, texto, tags=False):
        q = ("Convierte esta petición en un prompt en inglés para un generador de imágenes: una o dos frases "
             "descriptivas (sujeto, estilo, luz, composición), sin comillas ni explicación.\n\nPetición: " + texto)
        if tags:  # Illustrious se entrenó con etiquetas de danbooru: las sigue mucho mejor que frases
            q = ("Convierte esta petición en etiquetas de danbooru en inglés separadas por comas (personajes como 1girl/1boy, "
                 "pelo, ojos, ropa, la ACCIÓN que hace (reading, running…), pose, lugar, luz, encuadre), sin explicación.\n\nPetición: " + texto)
        body = {"model": self.valves.TRADUCTOR, "prompt": q, "stream": False, "think": False, "keep_alive": 0}
        async with s.post(f"{self.valves.OLLAMA}/api/generate", json=body, timeout=120) as r:
            return (await r.json())["response"].strip().strip('"')

    async def pipe(self, body: dict, __event_emitter__=None):
        modelo = body.get("model", "").split(".")[-1]
        nombre, en_ingles, calc = MODELOS.get(modelo, MODELOS["flux2-klein"])
        msgs = [m for m in body.get("messages", []) if m.get("role") == "user"]
        texto = msgs[-1]["content"] if msgs else ""
        if isinstance(texto, list):
            texto = " ".join(p.get("text", "") for p in texto if p.get("type") == "text")
        if not texto.strip():
            return "Escribe qué quieres ver en la imagen."
        if body.get("metadata", {}).get("task"):  # título/etiquetas de Open WebUI: no generar
            return texto[:40]

        async def estado(t, fin=False):
            if __event_emitter__:
                await __event_emitter__({"type": "status", "data": {"description": t, "done": fin}})

        w, h = 1024, 1024
        for patron, tam in FORMATOS:
            if re.search(patron, texto, re.I):
                w, h = tam
                break

        async with aiohttp.ClientSession() as s:
            prompt = texto
            if en_ingles:
                await estado("Preparando la descripción…")
                try:
                    prompt = await self._ingles(s, texto, en_ingles == "tags")
                except Exception:
                    pass
            await estado(f"Generando con {nombre} ({w}×{h}), unos {calc} s…")
            t0 = time.time()
            try:
                async with s.post(f"{self.valves.SWAP}/images/generations", timeout=900,
                                  json={"model": modelo, "size": f"{w}x{h}", "n": 1,
                                        "response_format": "b64_json",
                                        "prompt": anime(prompt) if en_ingles == "tags" else prompt}) as r:
                    d = await r.json(content_type=None)
                png = base64.b64decode(d["data"][0]["b64_json"])
            except Exception as e:
                await estado("Falló la generación", True)
                return f"No se pudo generar la imagen ({e})."

        os.makedirs(f"{E}/salidas/imagenes", exist_ok=True)
        ruta = f"{E}/salidas/imagenes/{time.strftime('%Y%m%d-%H%M%S')}-{modelo}.png"
        open(ruta, "wb").write(png)
        # en el chat va en JPEG: el PNG pesa ~2 MB y se guardaría entero en cada mensaje
        buf = io.BytesIO()
        Image.open(io.BytesIO(png)).convert("RGB").save(buf, "JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode()
        await estado(f"Listo en {int(time.time() - t0)} s", True)
        extra = f"\n\n*{prompt}*" if prompt != texto else ""
        return f"![imagen](data:image/jpeg;base64,{b64}){extra}\n\nArchivo: `{ruta}`"


if __name__ == "__main__":
    a = anime("1boy, black hair, glasses, reading")
    assert "male focus" in a and '"negative_prompt": "1girl' in a, a
    b = anime("1girl, 1boy, park")
    assert "male focus" not in b and '"negative_prompt": "nsfw' in b, b
    print("OK")
