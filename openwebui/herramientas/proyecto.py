"""
title: Proyecto
description: Crea y trabaja en apps dentro de salidas/proyectos/ (leer, escribir, editar archivos y ejecutar comandos) y lee las skills de Claude instaladas para seguirlas.
version: 1.0
"""

import glob
import json
import os
import re
import shutil
import signal
import subprocess
import unicodedata

E = os.path.expanduser("~/Proyectos/c_srfrijol")
C = os.path.expanduser("~/.claude")
MAX = 16000  # caracteres por lectura (~4,5k tokens): el modelo tiene 32k de contexto en total
SALIDA = 4000  # caracteres de salida de un comando
IGNORAR = {".git", "node_modules", "dist", "build", "target", ".venv", "venv", "__pycache__", ".next", ".cache"}


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


def _dentro(base: str, ruta: str) -> str:
    p = os.path.realpath(os.path.join(base, (ruta or "").lstrip("/")))
    if p != base and not p.startswith(base + os.sep):
        raise ValueError(f"«{ruta}» queda fuera del proyecto.")
    return p


def _descripcion(md: str) -> str:
    m = re.search(r"^description:[ \t]*(.*)$", md, re.M)
    if not m:
        return ""
    d = m.group(1).strip()
    if d in ("|", ">", "|-", ">-", ""):  # descripción en varias líneas indentadas
        d = " ".join(re.findall(r"^[ \t]+(\S.*)$", md[m.end():].split("\n---")[0].split("\n\n")[0], re.M))
    return d.strip("'\"")


class Tools:
    def __init__(self):
        self.raiz = f"{E}/salidas/proyectos"
        self.claude = C

    def _skills(self) -> dict:
        """nombre -> carpeta. Las de ~/.claude/skills primero; luego las de los plugins instalados."""
        dirs = sorted(glob.glob(f"{self.claude}/skills/*/SKILL.md"))
        try:
            with open(f"{self.claude}/plugins/installed_plugins.json") as fh:
                plugins = json.load(fh).get("plugins", {})
            for entradas in plugins.values():
                for e in entradas:
                    dirs += sorted(glob.glob(f"{e.get('installPath', '')}/skills/*/SKILL.md"))
        except (OSError, ValueError):
            pass
        out = {}
        for f in dirs:
            out.setdefault(os.path.basename(os.path.dirname(f)), os.path.dirname(f))  # shortcut: con nombres repetidos gana la primera; si chocan skills distintas, usar «plugin:skill»
        return out

    def _base(self, proyecto: str) -> str:
        if not _slug(proyecto):
            raise ValueError("Falta el nombre del proyecto.")
        return os.path.join(os.path.realpath(self.raiz), _slug(proyecto))

    def _crear(self, base: str) -> None:
        if not os.path.isdir(base):  # .gitignore desde el principio: si no, el primer commit se lleva node_modules
            os.makedirs(base)
            with open(f"{base}/.gitignore", "w") as fh:
                fh.write("\n".join(sorted(IGNORAR - {".git"})) + "\n")

    def buscar_skills(self, buscar: str = "") -> str:
        """
        Busca entre las skills de Claude instaladas (guías de cómo hacer bien una tarea: diseño frontend, tests, depuración…). Sin texto lista todos los nombres.
        :param buscar: palabras clave en inglés, p. ej. "frontend design", "test", "debug", "electron".
        """
        sk = self._skills()
        if not buscar.strip():
            return f"{len(sk)} skills: " + ", ".join(sorted(sk))
        palabras = [w for w in re.split(r"\W+", buscar.lower()) if w]
        res = []
        for nombre, d in sk.items():
            with open(f"{d}/SKILL.md", errors="replace") as fh:
                desc = _descripcion(fh.read(3000))
            texto = f"{nombre} {desc}".lower()
            puntos = sum(3 * (w in nombre) + (w in texto) for w in palabras)  # cuenta palabras distintas, no repeticiones
            if puntos:
                res.append((-puntos, nombre, desc[:160]))
        res.sort()
        return "\n".join(f"- {n}: {d}" for _, n, d in res[:12]) or f"Ninguna skill con «{buscar}». Prueba otras palabras en inglés."

    def leer_skill(self, nombre: str, archivo: str = "") -> str:
        """
        Lee una skill de Claude para seguir sus instrucciones. Léela ANTES de hacer la tarea que cubre.
        :param nombre: nombre exacto de la skill, p. ej. "frontend-design".
        :param archivo: vacío para SKILL.md, o un archivo de referencia que mencione la skill, p. ej. "references/palette.md".
        """
        d = self._skills().get(nombre.strip())
        if not d:
            return f"No hay ninguna skill «{nombre}». Usa buscar_skills."
        d = os.path.realpath(d)
        try:
            ruta = _dentro(d, archivo or "SKILL.md")
        except ValueError as e:
            return str(e)
        if not os.path.isfile(ruta):
            return f"La skill «{nombre}» no tiene «{archivo}»."
        with open(ruta, errors="replace") as fh:
            texto = fh.read()
        extra = sorted(os.path.relpath(os.path.join(r, f), d) for r, _, fs in os.walk(d) for f in fs if f != "SKILL.md")
        pie = f"\n\n[Otros archivos de la skill: {', '.join(extra[:30])}]" if extra and not archivo else ""
        return (texto if len(texto) <= MAX else texto[:MAX] + "\n[…recortado]") + pie

    def archivos(self, proyecto: str = "") -> str:
        """
        Sin proyecto: lista los proyectos. Con proyecto: lista sus archivos (sin node_modules, .git, dist…). Llámala al retomar un proyecto.
        :param proyecto: nombre del proyecto (vacío para ver todos).
        """
        if not proyecto:
            ps = sorted(os.listdir(self.raiz)) if os.path.isdir(self.raiz) else []
            return "Proyectos: " + ", ".join(ps) if ps else "Aún no hay proyectos."
        try:
            base = self._base(proyecto)
        except ValueError as e:
            return str(e)
        if not os.path.isdir(base):
            return f"El proyecto «{_slug(proyecto)}» no existe; se crea al escribir su primer archivo."
        out = []
        for r, ds, fs in os.walk(base):
            ds[:] = sorted(x for x in ds if x not in IGNORAR)
            out += [f"{os.path.relpath(os.path.join(r, f), base)} ({os.path.getsize(os.path.join(r, f))} B)" for f in sorted(fs)]
        return f"# {_slug(proyecto)}\n" + ("\n".join(out[:200]) or "(vacío)") + ("\n[…más de 200]" if len(out) > 200 else "")

    def leer(self, proyecto: str, ruta: str) -> str:
        """
        Lee un archivo del proyecto. Léelo antes de editarlo.
        :param proyecto: nombre del proyecto.
        :param ruta: ruta dentro del proyecto, p. ej. "src/main.js".
        """
        try:
            p = _dentro(self._base(proyecto), ruta)
        except ValueError as e:
            return str(e)
        if not os.path.isfile(p):
            return f"No existe «{ruta}». Mira archivos(proyecto)."
        with open(p, errors="replace") as fh:
            texto = fh.read()
        return texto if len(texto) <= MAX else texto[:MAX] + f"\n[…recortado: el archivo tiene {len(texto)} caracteres; divídelo en archivos más pequeños]"

    def escribir(self, proyecto: str, ruta: str, texto: str) -> str:
        """
        Crea o reemplaza un archivo del proyecto con el contenido COMPLETO. Para cambiar unas líneas de un archivo existente usa editar.
        :param proyecto: nombre del proyecto.
        :param ruta: ruta dentro del proyecto, p. ej. "index.html" o "src/app.js".
        :param texto: contenido completo del archivo.
        """
        try:
            p = _dentro(self._base(proyecto), ruta)
        except ValueError as e:
            return str(e)
        if os.path.isdir(p):
            return f"«{ruta}» es una carpeta."
        self._crear(self._base(proyecto))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(texto if texto.endswith("\n") else texto + "\n")
        return f"Escrito «{ruta}» en «{_slug(proyecto)}»: {texto.count(chr(10)) + 1} líneas."

    def editar(self, proyecto: str, ruta: str, buscar: str, reemplazar: str) -> str:
        """
        Cambia un trozo de un archivo: sustituye el texto exacto «buscar» (debe aparecer una sola vez, con sus espacios) por «reemplazar».
        :param proyecto: nombre del proyecto.
        :param ruta: ruta dentro del proyecto.
        :param buscar: texto exacto que hay ahora, copiado de leer (unas líneas, las justas para que sea único).
        :param reemplazar: texto nuevo.
        """
        try:
            p = _dentro(self._base(proyecto), ruta)
        except ValueError as e:
            return str(e)
        if not os.path.isfile(p):
            return f"No existe «{ruta}»."
        with open(p) as fh:
            texto = fh.read()
        n = texto.count(buscar) if buscar else 0
        if n != 1:
            return f"«buscar» aparece {n} veces en «{ruta}»: tiene que aparecer exactamente una. Vuelve a leer el archivo y copia el trozo tal cual."
        with open(p, "w") as fh:
            fh.write(texto.replace(buscar, reemplazar))
        return f"Editado «{ruta}»."

    def ejecutar(self, proyecto: str, comando: str, segundos: int = 120) -> str:
        """
        Ejecuta un comando de terminal dentro de la carpeta del proyecto (npm install, npm test, python -m pytest, git init…) y devuelve su salida. No arranques servidores que no terminan: usa build o tests.
        :param proyecto: nombre del proyecto.
        :param comando: comando de bash, p. ej. "npm install" o "python -m pytest -q".
        :param segundos: tiempo máximo (por defecto 120, máximo 600).
        """
        try:
            base = self._base(proyecto)
        except ValueError as e:
            return str(e)
        self._crear(base)
        # shortcut: sin aislamiento, el comando corre con tus permisos (solo se fija la carpeta); si el modo se abre a otros usuarios, meterlo en bubblewrap/contenedor
        pr = subprocess.Popen(comando, shell=True, cwd=base, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, text=True, errors="replace", start_new_session=True)
        try:
            out, _ = pr.communicate(timeout=max(1, min(int(segundos or 120), 600)))
            fin = f"código de salida {pr.returncode}"
        except subprocess.TimeoutExpired:
            os.killpg(pr.pid, signal.SIGKILL)  # mata también los hijos (npm → node), si no se quedan colgados
            out, _ = pr.communicate()
            fin = f"cortado a los {segundos} s (¿un servidor que no termina?)"
        out = out or ""
        return f"$ {comando}\n" + (out if len(out) <= SALIDA else "[…]\n" + out[-SALIDA:]) + f"\n[{fin}]"

    def copiar_skill(self, proyecto: str, nombre: str) -> str:
        """
        Copia una skill de Claude a .claude/skills/ del proyecto, para que Claude Code la use al continuar el proyecto. Úsala con las skills que hayas seguido.
        :param proyecto: nombre del proyecto.
        :param nombre: nombre exacto de la skill.
        """
        d = self._skills().get(nombre.strip())
        if not d:
            return f"No hay ninguna skill «{nombre}». Usa buscar_skills."
        try:
            destino = _dentro(self._base(proyecto), f".claude/skills/{os.path.basename(d)}")
        except ValueError as e:
            return str(e)
        shutil.copytree(d, destino, dirs_exist_ok=True)
        return f"Copiada la skill «{nombre}» a .claude/skills/ de «{_slug(proyecto)}»."


if __name__ == "__main__":
    import tempfile

    t = Tools()
    tmp = tempfile.mkdtemp()
    t.raiz, t.claude = f"{tmp}/proy", f"{tmp}/claude"
    os.makedirs(f"{tmp}/claude/skills/diseno-web/references")
    open(f"{tmp}/claude/skills/diseno-web/SKILL.md", "w").write("---\nname: diseno-web\ndescription: >\n  Frontend design\n  for web UIs\n---\nUsa buena tipografía.")
    open(f"{tmp}/claude/skills/diseno-web/references/a.md", "w").write("ref")
    os.makedirs(f"{tmp}/plug/skills/tdd")
    open(f"{tmp}/plug/skills/tdd/SKILL.md", "w").write("---\nname: tdd\ndescription: \"Write the test first\"\n---\nRojo, verde.")
    os.makedirs(f"{tmp}/claude/plugins")
    json.dump({"plugins": {"x@y": [{"installPath": f"{tmp}/plug"}]}}, open(f"{tmp}/claude/plugins/installed_plugins.json", "w"))
    assert t.buscar_skills() == "2 skills: diseno-web, tdd"
    assert t.buscar_skills("frontend").startswith("- diseno-web: Frontend design for web UIs"), t.buscar_skills("frontend")
    assert t.buscar_skills("test") == "- tdd: Write the test first"
    assert "Ninguna" in t.buscar_skills("cocina")
    s = t.leer_skill("diseno-web")
    assert "buena tipografía" in s and "references/a.md" in s, s
    assert t.leer_skill("diseno-web", "references/a.md") == "ref"
    assert "fuera" in t.leer_skill("diseno-web", "../../../plugins/installed_plugins.json")
    assert t.archivos() == "Aún no hay proyectos."
    assert "Escrito «src/app.js» en «mi-app»: 2 líneas." == t.escribir("Mi App", "src/app.js", "let a = 1;\nlet b = 2;")
    assert "fuera" in t.escribir("Mi App", "../x", "y") and "fuera" in t.leer("mi app", "/../../x")
    assert "Falta" in t.escribir("..", "x", "y")
    assert "aparece 0 veces" in t.editar("mi-app", "src/app.js", "let c", "x")
    assert t.editar("mi-app", "src/app.js", "let b = 2;", "let b = 3;") == "Editado «src/app.js»."
    assert t.leer("mi-app", "src/app.js") == "let a = 1;\nlet b = 3;\n"
    os.makedirs(f"{t.raiz}/mi-app/node_modules/z")
    assert "node_modules" in open(f"{t.raiz}/mi-app/.gitignore").read()
    assert "src/app.js" in t.archivos("mi-app") and "node_modules" not in t.archivos("mi-app")
    assert "código de salida 0" in t.ejecutar("mi-app", "ls src") and "app.js" in t.ejecutar("mi-app", "ls src")
    assert "código de salida 3" in t.ejecutar("mi-app", "exit 3")
    assert "cortado a los 1 s" in t.ejecutar("mi-app", "sleep 30 & sleep 30", 1)
    assert "Copiada" in t.copiar_skill("mi-app", "tdd") and os.path.isfile(f"{t.raiz}/mi-app/.claude/skills/tdd/SKILL.md")
    assert t.archivos() == "Proyectos: mi-app"
    real = Tools()._skills()
    print(len(real), "skills reales;", Tools().buscar_skills("frontend design").splitlines()[0], "\nOK")
