"""
title: Ilustrar
description: Ilustra un libro con FLUX.2 klein usando el arte de referencia de sus personajes (arte/ del libro) y guarda ahí el resultado.
version: 1.0
"""

import base64
import io
import os
import re
import time
import unicodedata

import aiohttp
from PIL import Image
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
    print("OK")
