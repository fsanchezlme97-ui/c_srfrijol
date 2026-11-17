"""
title: Libro
description: Guarda y lee la biblia de cada libro (personajes, capítulos, notas de mundo y trama) en salidas/libros/. Úsala para no olvidar nada entre chats.
version: 1.2
"""

import glob
import os
import re
import time
import unicodedata

from pydantic import BaseModel, Field

E = os.path.expanduser("~/Proyectos/c_srfrijol")
TIPOS = {"personaje": "personajes", "capitulo": "capitulos", "nota": "notas"}
# libros externos (se configuran en las Valves): cada tipo se busca en las carpetas de esta lista que existan.
# Sus archivos nuevos conservan el nombre que da el autor («A1 - La isla/C4 - Título»), no un slug.
CANDIDATAS = {
    "personajes": ["personajes", "compendio/personajes"],
    "capitulos": ["capitulos", "temporadas"],  # en externos, también subcarpetas: temporadas/<arco>/<capítulo>.md
    "notas": ["notas", "compendio", "compendio/sistemas", "extras"],
}
MAX = 12000  # caracteres por lectura: el modelo tiene 16k tokens de contexto en total


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


def _tipo(t: str) -> str:
    t = _slug(t).rstrip("s").replace("-", "")
    t = {"mundo": "nota", "trama": "nota"}.get(t, t)
    if t not in TIPOS:
        raise ValueError(f"Tipo «{t}» no válido: usa personaje, capitulo o nota.")
    return TIPOS[t]


def _limpio(nombre: str) -> str:
    # nombre de archivo legible para libros externos; sin «..», rutas absolutas ni caracteres que NTFS no admite
    partes = [re.sub(r'[:*?"<>|\x00-\x1f]', "", p).strip() for p in re.split(r"[\\/]", nombre or "")]
    if not partes or any(not p or p.startswith(".") for p in partes):
        raise ValueError("Nombre no válido.")
    return os.path.join(*partes)


class Tools:
    class Valves(BaseModel):
        CARPETA_LIBROS: str = Field(default=f"{E}/salidas/libros", description="Dónde se crean los libros nuevos.")
        LIBROS_EXTERNOS: str = Field(
            default="",
            description="Carpetas de libros que ya tienes en otro sitio, separadas por «;». El libro se llama como su carpeta.")

    def __init__(self):
        self.valves = self.Valves()

    @property
    def raiz(self):
        return os.path.expanduser(self.valves.CARPETA_LIBROS)

    @property
    def externos(self):
        rutas = [os.path.expanduser(r.strip()).rstrip("/") for r in self.valves.LIBROS_EXTERNOS.split(";") if r.strip()]
        return {_slug(os.path.basename(r)): r for r in rutas if _slug(os.path.basename(r))}

    def _base(self, libro):
        if not _slug(libro):
            raise ValueError("Falta el nombre del libro o del elemento.")
        if _slug(libro) in self.externos:
            return self.externos[_slug(libro)]
        return os.path.join(self.raiz, _slug(libro))  # el slug solo deja a-z0-9-: no sale de salidas/libros

    def _carpetas(self, libro, carpeta):
        base = self._base(libro)
        if _slug(libro) not in self.externos:
            return [os.path.join(base, carpeta)]
        return [os.path.join(base, c) for c in
                ([c for c in CANDIDATAS[carpeta] if os.path.isdir(os.path.join(base, c))] or [carpeta])]

    def _archivos(self, libro, carpeta):
        """[(nombre visible, ruta)] de un tipo; los capítulos de libros externos se buscan también en subcarpetas."""
        out = []
        for d in self._carpetas(libro, carpeta):
            patron = "**/*.md" if carpeta == "capitulos" and _slug(libro) in self.externos else "*.md"
            for f in sorted(glob.glob(os.path.join(glob.escape(d), patron), recursive=True)):
                out.append((os.path.relpath(f, d)[:-3], f))
        return out

    def _ruta(self, libro, tipo, nombre):
        if not _slug(nombre):
            raise ValueError("Falta el nombre del libro o del elemento.")
        carpeta = _tipo(tipo)
        for visible, f in self._archivos(libro, carpeta):
            if _slug(visible) == _slug(nombre):
                return f
        if _slug(libro) in self.externos:
            return os.path.join(self._carpetas(libro, carpeta)[0], _limpio(nombre) + ".md")
        return os.path.join(self._base(libro), carpeta, _slug(nombre) + ".md")

    def indice(self, libro: str = "") -> str:
        """
        Sin libro: lista los libros guardados. Con libro: lista sus personajes, capítulos y notas con su primera línea. Llámala al empezar a trabajar en un libro.
        :param libro: título del libro (vacío para ver todos).
        """
        try:
            if not libro:
                libros = sorted(set(os.listdir(self.raiz) if os.path.isdir(self.raiz) else []) | set(self.externos))
                return "Libros: " + ", ".join(libros) if libros else "Aún no hay libros guardados."
            base = self._base(libro)
        except ValueError as e:
            return str(e)
        if not os.path.isdir(base):
            if _slug(libro) in self.externos:
                return f"El libro «{_slug(libro)}» está en {base} y ese disco no está montado ahora."
            return f"El libro «{_slug(libro)}» aún no existe; se crea al guardar algo en él."
        out = [f"# {_slug(libro)}"]
        for tipo, carpeta in TIPOS.items():
            for visible, f in self._archivos(libro, carpeta):
                with open(f, encoding="utf-8", errors="replace") as fh:
                    texto = fh.read()
                linea = next((l.strip("#* ").strip() for l in texto.splitlines() if l.strip()), "")[:100]
                out.append(f"- {tipo} `{visible}` ({len(texto.split())} palabras): {linea}")
        return "\n".join(out) if len(out) > 1 else out[0] + "\n(vacío)"

    def leer(self, libro: str, tipo: str, nombre: str) -> str:
        """
        Lee una ficha de personaje, un capítulo o una nota del libro. Léela antes de escribir sobre ese personaje o de continuar ese capítulo.
        :param libro: título del libro.
        :param tipo: personaje, capitulo o nota.
        :param nombre: nombre tal como sale en el índice, p. ej. "lucia" o "03-la-tormenta".
        """
        try:
            ruta = self._ruta(libro, tipo, nombre)
        except ValueError as e:
            return str(e)
        if not os.path.isfile(ruta):
            return f"No existe {_tipo(tipo)[:-1]} «{nombre}» en «{_slug(libro)}». Mira el índice."
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
        # shortcut: solo el final de textos largos; si hacen falta capítulos enteros más largos, leer por trozos
        return texto if len(texto) <= MAX else f"[…solo los últimos {MAX} caracteres. Para seguirlo, guarda SOLO lo nuevo con anadir=true…]\n" + texto[-MAX:]

    def guardar(self, libro: str, tipo: str, nombre: str, texto: str, anadir: bool = False) -> str:
        """
        Guarda una ficha de personaje, un capítulo o una nota. Con anadir=false reemplaza: manda el texto COMPLETO (la versión anterior se aparta en .anteriores/). Con anadir=true pega el texto al final: úsalo para cada parte nueva de un capítulo.
        :param libro: título del libro.
        :param tipo: personaje, capitulo o nota (mundo, trama, estilo, cronología…).
        :param nombre: nombre corto, p. ej. "lucia", "03-la-tormenta", "mundo". Para capítulos empieza por el número.
        :param texto: contenido en Markdown: completo si reemplazas, solo lo nuevo si añades.
        :param anadir: true para añadir al final en vez de reemplazar.
        """
        try:
            ruta = self._ruta(libro, tipo, nombre)
        except ValueError as e:
            return str(e)
        if not (texto or "").strip():
            return "No guardo un texto vacío."
        if not os.path.isdir(self._base(libro)) and _slug(libro) in self.externos:
            return f"El disco de «{_slug(libro)}» no está montado: no guardo nada."
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        aviso = ""
        if anadir and os.path.isfile(ruta):
            with open(ruta, "a", encoding="utf-8") as fh:
                fh.write("\n" + texto.strip() + "\n")
            with open(ruta, encoding="utf-8") as fh:
                total = len(fh.read().split())
            return f"Añadidas {len(texto.split())} palabras a {_tipo(tipo)[:-1]} «{_slug(nombre)}» ({total} en total)."
        if os.path.isfile(ruta):
            if os.path.getsize(ruta) > MAX:  # no ha podido leerlo entero: reemplazar lo recortaría
                return (f"«{_slug(nombre)}» es más largo de lo que puedes leer de una vez: no lo reemplazo. "
                        "Usa anadir=true para seguirlo, o guarda la versión nueva con otro nombre.")
            antes = os.path.join(os.path.dirname(ruta), ".anteriores")
            os.makedirs(antes, exist_ok=True)
            os.replace(ruta, os.path.join(antes, f"{os.path.basename(ruta)[:-3]}-{time.strftime('%Y%m%d-%H%M%S')}.md"))
            aviso = " (versión anterior en .anteriores/)"
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write(texto.strip() + "\n")
        return f"Guardado {_tipo(tipo)[:-1]} «{_slug(nombre)}» en «{_slug(libro)}»: {len(texto.split())} palabras{aviso}."


if __name__ == "__main__":
    import tempfile

    t = Tools()
    t.valves = t.Valves(CARPETA_LIBROS=tempfile.mkdtemp(), LIBROS_EXTERNOS="")
    assert t.indice() == "Aún no hay libros guardados."
    assert "no existe" in t.indice("El Faro")
    assert "Guardado personaje «lucia» en «el-faro»" in t.guardar("El Faro", "Personajes", "Lucía", "# Lucía\nFarera, 40 años.")
    assert "anteriores" in t.guardar("El Faro", "personaje", "lucia", "# Lucía\nFarera, 41 años.")
    assert t.leer("el faro", "personaje", "LUCÍA") == "# Lucía\nFarera, 41 años.\n"
    assert len(os.listdir(f"{t.raiz}/el-faro/personajes/.anteriores")) == 1
    t.guardar("El Faro", "capítulo", "01 La llegada", "# 1. La llegada\n" + "ola " * 5000)
    t.guardar("El Faro", "mundo", "isla", "La isla tiene un solo muelle.")
    i = t.indice("El Faro")
    assert "personaje `lucia` (5 palabras): Lucía" in i and "capitulo `01-la-llegada` (5004 palabras)" in i, i
    assert "nota `isla`" in i and ".anteriores" not in i
    assert t.leer("El Faro", "capitulo", "01-la-llegada").startswith("[…solo los últimos")
    assert "no lo reemplazo" in t.guardar("El Faro", "capitulo", "01-la-llegada", "corto")
    assert "Añadidas 2 palabras" in t.guardar("El Faro", "capitulo", "01-la-llegada", "Fin. Ya.", True)
    assert t.leer("El Faro", "capitulo", "01-la-llegada").endswith("ola\n\nFin. Ya.\n")
    assert "Guardado nota «x»" in t.guardar("El Faro", "nota", "x", "nuevo", True)  # añadir a algo que no existe = crear
    assert "no válido" in t.guardar("El Faro", "receta", "x", "y")
    assert "Falta" in t.guardar("../..", "nota", "x", "y") and "Falta" in t.leer("El Faro", "nota", "..")
    assert "vacío" in t.guardar("El Faro", "nota", "x", "  ")
    ext = os.path.join(tempfile.mkdtemp(), "Saga")
    t.valves.LIBROS_EXTERNOS = f" {ext}/ ; "
    os.makedirs(f"{ext}/temporadas/A1 - La isla")
    os.makedirs(f"{ext}/compendio/personajes")
    open(f"{ext}/temporadas/A1 - La isla/C3 - La tormenta.md", "w").write("# C3 — La tormenta\nEl faro se apagó…")
    open(f"{ext}/compendio/personajes/tomas_vidal.md", "w").write("# Tomás\n")
    i2 = t.indice("Saga")
    assert "capitulo `A1 - La isla/C3 - La tormenta`" in i2 and "personaje `tomas_vidal`" in i2, i2
    assert t.leer("saga", "capitulo", "A1 - La isla/C3 - La tormenta").startswith("# C3")
    assert t.leer("saga", "capitulo", "a1-la-isla-c3-la-tormenta").startswith("# C3")  # también por slug
    assert "Guardado" in t.guardar("saga", "capitulo", "A1 - La isla/C4 - El juicio", "# C4")
    assert os.path.isfile(f"{ext}/temporadas/A1 - La isla/C4 - El juicio.md")
    assert "anteriores" in t.guardar("saga", "personaje", "Tomás Vidal", "# Tomás\n17 años.")
    assert open(f"{ext}/compendio/personajes/tomas_vidal.md").read() == "# Tomás\n17 años.\n"
    assert "no válido" in t.guardar("saga", "nota", "../fuera", "x") and "no válido" in t.guardar("saga", "nota", "/etc/x", "x")
    assert "nota `generalidades`" not in t.indice("saga") and "Guardado" in t.guardar("saga", "nota", "generalidades", "g")
    assert os.path.isfile(f"{ext}/compendio/generalidades.md")
    t.valves.LIBROS_EXTERNOS = "/no/montado/saga"
    assert "no está montado" in t.indice("saga") and "no está montado" in t.guardar("saga", "nota", "x", "y")
    assert t.indice() == "Libros: el-faro, saga"
    print(i, "\nOK")
