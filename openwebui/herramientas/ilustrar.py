"""
title: Ilustrar
description: Ilustra un libro con FLUX.2 klein usando el arte de referencia de sus personajes (arte/ del libro) y anima sus ilustraciones con Wan 2.2 14B; lo guarda todo en arte/.
version: 1.1
"""

import asyncio
import base64
import io
import json
import os
import random
import re
import time
import unicodedata

import aiohttp
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

E = os.path.expanduser("~/Proyectos/c_srfrijol")
CARPETAS = ("personajes", "escenarios", "objetos")
# ~1 MP: con --flash-attn on y referencias ≤768 px, 832x1216 + una referencia tarda ~48 s (704x1024: ~31 s, con
# menos detalle en ojos y pelo). Antes de esos dos cambios tardaba 12 min.
FORMATOS = {"vertical": "832x1216", "horizontal": "1216x832", "cuadrado": "1024x1024"}
REF_MAX = 768  # lado mayor de cada referencia: más grande solo añade tokens (y minutos) a la atención
IMG = (".jpg", ".jpeg", ".png", ".webp")
# estilo de la casa, sacado del arte de referencia del autor: va en todas las imágenes para que no deriven
ESTILO = ("Polished anime / manga illustration, clean confident lineart, cel shading with soft painterly light, "
          "expressive detailed eyes, dramatic composition, limited palette with one strong accent color, "
          "subtle grain and ink splatter.")
# solo si la escena trae criaturas: en el estilo fijo metía monstruos en escenas sin ellos
HORROR = "Creatures: dark grotesque horror, many teeth, sinewy forms."
# Wan 2.2 14B imagen a vídeo (Q3_K_M + LoRA Lightning de 4 pasos), 33 fotogramas a 16 fps = 2 s. Medido el 2026-11-17:
# 8,8 min a 480x832 (la mitad del modelo va en la RAM: solo quedan ~3 GB de VRAM con el escritorio)
ANIM = {"vertical": (480, 832), "horizontal": (832, 480)}
ANIM_ESTILO = "Keep the exact art style, character design and colors of the image."


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


class Tools:
    class Valves(BaseModel):  # mismas carpetas que en la herramienta «Libro»: si cambias una, cambia la otra
        CARPETA_LIBROS: str = Field(default=f"{E}/salidas/libros", description="Dónde están los libros de srfrijol.")
        LIBROS_EXTERNOS: str = Field(
            default="",
            description="Carpetas de libros que tienes en otro sitio, separadas por «;». Su arte va en <carpeta>/arte.")
        SWAP: str = Field(default="http://127.0.0.1:8090/v1")
        COMFY: str = Field(default="http://127.0.0.1:8188")

    def __init__(self):
        self.valves = self.Valves()

    @property
    def externos(self):
        rutas = [os.path.expanduser(r.strip()).rstrip("/") for r in self.valves.LIBROS_EXTERNOS.split(";") if r.strip()]
        return {_slug(os.path.basename(r)): r for r in rutas if _slug(os.path.basename(r))}

    def _arte(self, libro):
        if not _slug(libro):
            raise ValueError("Falta el nombre del libro.")
        base = self.externos.get(_slug(libro)) or os.path.join(os.path.expanduser(self.valves.CARPETA_LIBROS), _slug(libro))
        if not os.path.isdir(base):
            raise ValueError(f"No encuentro el libro «{_slug(libro)}» en {base} (¿disco sin montar?).")
        return os.path.join(base, "arte")

    def _imagenes(self, arte):
        return [(c, f) for c in CARPETAS if os.path.isdir(os.path.join(arte, c))
                for f in sorted(os.listdir(os.path.join(arte, c))) if f.lower().endswith(IMG)]

    def referencias(self, libro: str, personaje: str = "") -> str:
        """
        Lista el arte de referencia del libro (archivos de arte/personajes, escenarios y objetos). Con personaje, solo los que llevan su nombre. Llámala antes de ilustrar a alguien.
        :param libro: título del libro, p. ej. "el-faro".
        :param personaje: nombre o parte del nombre (p. ej. "lucia"); vacío para ver todo.
        """
        try:
            arte = self._arte(libro)
        except ValueError as e:
            return str(e)
        clave = _slug(personaje).split("-")[0] if personaje else ""
        fs = [f"{c}/{f}" for c, f in self._imagenes(arte) if clave in _slug(f)]
        if not fs:
            return f"No hay arte de «{personaje}». Ilustra solo con texto (sin referencias)." if personaje else "El libro no tiene arte todavía."
        return f"{len(fs)} imágenes (el nombre del archivo dice la forma o etapa):\n" + "\n".join(fs)

    async def ilustrar(self, libro: str, escena: str, nombre: str, referencias: str = "",
                       carpeta: str = "personajes", formato: str = "vertical", __event_emitter__=None) -> str:
        """
        Genera una ilustración (1–3 minutos) y la guarda en arte/<carpeta>/ del libro. El estilo de la casa se añade solo.
        :param libro: título del libro.
        :param escena: descripción en INGLÉS: quién (rasgos de la ficha), qué hace, dónde, luz y encuadre. Con referencias, nombra «the character from image 1», etc.
        :param nombre: nombre base del archivo, p. ej. "lucia_transformada" (se le añade un número).
        :param referencias: hasta 3 archivos de referencias(), separados por comas, p. ej. "personajes/lucia_005.jpg". Vacío = solo texto.
        :param carpeta: personajes, escenarios u objetos.
        :param formato: vertical, horizontal o cuadrado.
        """
        async def estado(t, fin=False):
            if __event_emitter__:
                await __event_emitter__({"type": "status", "data": {"description": t, "done": fin}})

        try:
            arte = self._arte(libro)
            if carpeta not in CARPETAS:
                raise ValueError(f"Carpeta «{carpeta}» no válida: usa {', '.join(CARPETAS)}.")
            if not _slug(nombre) or not (escena or "").strip():
                raise ValueError("Faltan la escena o el nombre del archivo.")
            disponibles = {f"{c}/{f}": os.path.join(arte, c, f) for c, f in self._imagenes(arte)}
            refs = [r.strip() for r in (referencias or "").split(",") if r.strip()]
            if len(refs) > 3:
                raise ValueError("Como mucho 3 referencias: más confunden al modelo y lo hacen muy lento.")
            # solo nombres de la lista: ni rutas libres ni «..»
            falta = [r for r in refs if r not in disponibles]
            if falta:
                raise ValueError(f"No existen {', '.join(falta)}: copia los nombres tal cual de referencias().")
            # con referencia, un pelo u ojos descritos en el texto pisan a la imagen (probado: sale otra persona)
            if refs and re.search(r"\b(hair|haired|eyes?|eyed|ponytail|bangs|braids?)\b", escena, re.I):
                raise ValueError("Con referencias no describas pelo ni ojos (el texto pisa a la imagen y sale otra "
                                 "persona). Reescribe la escena sin ellos y vuelve a llamar a ilustrar.")
        except ValueError as e:
            return str(e)

        horror = f" {HORROR}" if re.search(r"creature|monster|beast", escena, re.I) else ""
        # el 35B suele inventar pelo/ropa y el texto pesa más que la imagen: la identidad manda la referencia
        fiel = ("Keep each referenced character's exact face, hair color and length, eye color and outfit from "
                "their reference image; ignore any conflicting description of them.\n") if refs else ""
        prompt = f"{fiel}{escena.strip()}\n\nStyle: {ESTILO}{horror}"
        size = FORMATOS.get(formato, FORMATOS["vertical"])
        await estado(f"Ilustrando con {len(refs)} referencias ({size}), 1–3 min…")
        t0 = time.time()
        try:
            async with aiohttp.ClientSession() as s:
                if refs:
                    form = aiohttp.FormData()
                    for k, v in {"model": "flux2-klein", "prompt": prompt, "size": size, "n": "1",
                                 "response_format": "b64_json"}.items():
                        form.add_field(k, v)
                    for r in refs:
                        im = Image.open(disponibles[r]).convert("RGB")
                        im.thumbnail((REF_MAX, REF_MAX))
                        buf = io.BytesIO()
                        im.save(buf, "PNG")
                        form.add_field("image[]", buf.getvalue(), filename=f"ref{len(buf.getvalue())}.png")
                    req = s.post(f"{self.valves.SWAP}/images/edits", data=form, timeout=900)
                else:
                    req = s.post(f"{self.valves.SWAP}/images/generations", timeout=900,
                                 json={"model": "flux2-klein", "prompt": prompt, "size": size, "n": 1,
                                       "response_format": "b64_json"})
                async with req as r:
                    d = await r.json(content_type=None)
            png = base64.b64decode(d["data"][0]["b64_json"])
        except Exception as e:
            await estado("Falló la ilustración", True)
            return f"No se pudo generar la imagen ({e}). Dile al autor el error; no lo reintentes solo."

        destino = os.path.join(arte, carpeta)
        os.makedirs(destino, exist_ok=True)
        n = 1
        while os.path.exists(ruta := os.path.join(destino, f"{_slug(nombre).replace('-', '_')}_ia_{n:03d}.png")):
            n += 1
        with open(ruta, "wb") as fh:
            fh.write(png)
        if __event_emitter__:  # al chat en JPEG: el PNG pesa ~2 MB y se guardaría en cada mensaje
            buf = io.BytesIO()
            Image.open(io.BytesIO(png)).convert("RGB").save(buf, "JPEG", quality=88)
            b64 = base64.b64encode(buf.getvalue()).decode()
            await __event_emitter__({"type": "message", "data": {"content": f"![{nombre}](data:image/jpeg;base64,{b64})\n\n"}})
        await estado(f"Lista en {int(time.time() - t0)} s", True)
        return (f"Imagen generada y ya mostrada al autor. Guardada en `arte/{carpeta}/{os.path.basename(ruta)}` (copia esta ruta tal cual). "
                "No la describas (no la ves): pregunta si le gusta o qué cambiar.")

    async def animar(self, libro: str, imagen: str, movimiento: str, __event_emitter__=None) -> str:
        """
        Anima una ilustración del libro (vídeo de 2 s, tarda 8–10 minutos y ocupa la gráfica entera) y guarda el vídeo junto a ella. Una sola vez por petición del autor.
        :param libro: título del libro.
        :param imagen: un archivo de referencias(), p. ej. "personajes/lucia_ia_001.png".
        :param movimiento: en INGLÉS, qué se mueve y cómo: acción del personaje, pelo/ropa, cámara (p. ej. "she raises her sword, hair blowing in the wind, slow camera push in").
        """
        async def estado(t, fin=False):
            if __event_emitter__:
                await __event_emitter__({"type": "status", "data": {"description": t, "done": fin}})

        try:
            arte = self._arte(libro)
            disponibles = {f"{c}/{f}": os.path.join(arte, c, f) for c, f in self._imagenes(arte)}
            if imagen not in disponibles:  # solo nombres de la lista: ni rutas libres ni «..»
                raise ValueError(f"No existe «{imagen}»: copia el nombre tal cual de referencias().")
            if not (movimiento or "").strip():
                raise ValueError("Falta el movimiento (en inglés).")
        except ValueError as e:
            return str(e)

        im = Image.open(disponibles[imagen]).convert("RGB")
        w, h = ANIM["vertical" if im.height >= im.width else "horizontal"]
        buf = io.BytesIO()
        ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.35)).save(buf, "PNG")  # 0,35: no cortar la cabeza
        wf = json.load(open(f"{E}/workflows/wan22-14b-imagen-a-video.json"))
        wf["9"]["inputs"]["text"] = f"{movimiento.strip()} {ANIM_ESTILO}"
        wf["12"]["inputs"].update(width=w, height=h)
        wf["13"]["inputs"]["noise_seed"] = wf["14"]["inputs"]["noise_seed"] = random.randint(0, 2**31)

        await estado("Liberando la gráfica y arrancando ComfyUI…")
        p = await asyncio.create_subprocess_exec(f"{E}/srfrijol", "video", env={**os.environ, "SRFRIJOL_SIN_NAVEGADOR": "1"},
                                                 stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p.wait()
        t0 = time.time()
        try:
            async with aiohttp.ClientSession() as s:
                form = aiohttp.FormData()
                form.add_field("image", buf.getvalue(), filename="srfrijol-animar.png", content_type="image/png")
                form.add_field("overwrite", "true")
                async with s.post(f"{self.valves.COMFY}/upload/image", data=form, timeout=60) as r:
                    wf["11"]["inputs"]["image"] = (await r.json())["name"]
                async with s.post(f"{self.valves.COMFY}/prompt", json={"prompt": wf}, timeout=30) as r:
                    pid = (await r.json())["prompt_id"]
                while True:
                    await asyncio.sleep(10)
                    async with s.get(f"{self.valves.COMFY}/history/{pid}", timeout=30) as r:
                        hist = (await r.json()).get(pid) or {}
                    st = hist.get("status", {}).get("status_str")
                    if st == "error":
                        raise RuntimeError(hist["status"]["messages"][-1][1].get("exception_message", "error").split("\n")[0])
                    if st == "success":
                        break
                    t = int(time.time() - t0)
                    await estado(f"Animando {imagen} ({w}×{h}, 2 s)… {t // 60}:{t % 60:02d} de unos 9 min")
                out = [f for o in hist["outputs"].values() for v in o.values() if isinstance(v, list)
                       for f in v if isinstance(f, dict) and f.get("filename")][0]
                # que el 35B vuelva a caber en la gráfica al seguir la conversación
                await s.post(f"{self.valves.COMFY}/free", json={"unload_models": True, "free_memory": True}, timeout=30)
        except Exception as e:
            await estado("Falló la animación", True)
            return f"No se pudo animar la imagen ({e}). Dile al autor el error; no lo reintentes solo."

        carpeta, archivo = imagen.split("/", 1)
        base = re.sub(r"_ia_\d+$", "", os.path.splitext(archivo)[0])
        n = 1
        while os.path.exists(ruta := os.path.join(arte, carpeta, f"{base}_anim_{n:03d}.webm")):
            n += 1
        with open(os.path.join(E, "comfyui/output", out.get("subfolder", ""), out["filename"]), "rb") as fh, open(ruta, "wb") as dst:
            dst.write(fh.read())
        if __event_emitter__:
            url = f"{self.valves.COMFY}/view?filename={out['filename']}&subfolder={out.get('subfolder', '')}&type=output"
            await __event_emitter__({"type": "message", "data": {"content": f"<video>{url}</video>\n\n"}})
        t = int(time.time() - t0)
        await estado(f"Animada en {t // 60}:{t % 60:02d}", True)
        return (f"Vídeo generado y ya mostrado al autor. Guardado en `arte/{carpeta}/{os.path.basename(ruta)}` (copia esta ruta tal cual). "
                "No lo describas (no lo ves): pregunta si le gusta o qué movimiento cambiar.")


if __name__ == "__main__":
    import asyncio
    import tempfile

    t = Tools()
    raiz = tempfile.mkdtemp()
    t.valves = t.Valves(CARPETA_LIBROS=raiz, LIBROS_EXTERNOS=f"{raiz}/fuera/Otra Saga")
    os.makedirs(f"{raiz}/saga/arte/personajes")
    os.makedirs(f"{raiz}/fuera/Otra Saga/arte/escenarios")
    Image.new("RGB", (8, 8)).save(f"{raiz}/saga/arte/personajes/Lucia_Farera_001.jpg")
    Image.new("RGB", (8, 8)).save(f"{raiz}/fuera/Otra Saga/arte/escenarios/torre.png")
    open(f"{raiz}/saga/arte/personajes/notas.txt", "w").write("x")
    assert "escenarios/torre.png" in t.referencias("otra-saga")
    assert "personajes/Lucia_Farera_001.jpg" in t.referencias("Saga", "Lucía Farera")
    assert "notas.txt" not in t.referencias("saga") and "No hay arte" in t.referencias("saga", "tomas")
    assert "No encuentro" in t.referencias("otro")
    run = lambda **k: asyncio.run(t.ilustrar("saga", **k))
    assert "No existen" in run(escena="x", nombre="a", referencias="../../../etc/passwd")
    assert "No existen" in run(escena="x", nombre="a", referencias="personajes/../notas.txt")
    assert "Como mucho 3" in run(escena="x", nombre="a", referencias="a,b,c,d")
    assert "no válida" in run(escena="x", nombre="a", carpeta="..")
    assert "Faltan" in run(escena=" ", nombre="a")
    assert "no describas pelo" in run(escena="She has long white hair", nombre="a", referencias="personajes/Lucia_Farera_001.jpg")
    anima = lambda **k: asyncio.run(t.animar("saga", **k))
    assert "No existe" in anima(imagen="../../../etc/passwd", movimiento="x")
    assert "No existe" in anima(imagen="personajes/notas.txt", movimiento="x")
    assert "Falta el movimiento" in anima(imagen="personajes/Lucia_Farera_001.jpg", movimiento=" ")
    print("OK")
