#!/usr/bin/env python3
"""Instala (o actualiza) en Open WebUI los modos de openwebui/modos/*.md y las herramientas de openwebui/herramientas/*.py.
Cada modo lleva su avatar (assets/modos/<id>.png, de scripts/avatares-modos.py) y su carpeta en el lateral, con el modo
como modelo por defecto: los chats de cada modo quedan separados. «grupo:» mete la carpeta dentro de otra.

Cada modo es un «modelo» de Open WebUI: un modelo base + su prompt de sistema (+ herramientas). Vuelve a ejecutarlo
tras editar un .md o un .py: sobrescribe lo instalado. Uso: scripts/instalar-modos.py (con ./srfrijol arrancar hecho).
"""
import base64
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

E = pathlib.Path(__file__).resolve().parent.parent
API = "http://127.0.0.1:3000/api/v1"


def pedir(ruta, datos=None, token=None):
    req = urllib.request.Request(API + ruta, method="POST" if datos is not None else "GET",
                                 data=None if datos is None else json.dumps(datos).encode(),
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 404) and datos is None:
            return None
        sys.exit(f"Open WebUI respondió {e.code} en {ruta}: {e.read().decode()[:300]}")


def leer_modo(p):
    m = re.match(r"---\n(.*?)\n---\n(.*)", p.read_text(), re.S)
    if not m:
        sys.exit(f"{p.name}: falta la cabecera --- … ---")
    cab = dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)
    cab = {k.strip(): v.strip() for k, v in cab.items()}
    for k in ("id", "nombre", "base"):
        if not cab.get(k):
            sys.exit(f"{p.name}: falta «{k}» en la cabecera")
    params = {"system": m.group(2).strip()}
    if cab.get("temperatura"):
        params["temperature"] = float(cab["temperatura"])
    if cab.get("contexto"):
        params["num_ctx"] = int(cab["contexto"])  # Ollama usa 4096 si no: no caben prompt + resultados de herramientas
    if cab.get("pensar") == "no":
        # los Qwen/gemma piensan por defecto: «think» para Ollama, chat_template_kwargs para llama.cpp (llama-swap)
        params["think"] = False
        params["custom_params"] = {"chat_template_kwargs": {"enable_thinking": False}}
    meta = {"description": cab.get("descripcion", ""),
            "toolIds": [t.strip() for t in cab.get("herramientas", "").split(",") if t.strip()],
            # sin las herramientas integradas de Open WebUI (memoria, notas, chats…): con tantas, el 9B se inventa
            # los nombres de los parámetros de las nuestras
            "capabilities": {"vision": True, "file_upload": True, "web_search": True, "image_generation": True,
                             "code_interpreter": True, "citations": True, "status_updates": True,
                             "builtin_tools": False},
            "suggestion_prompts":[{"content": s.strip()} for s in cab.get("sugerencias", "").split("|") if s.strip()],
            "tags": [{"name": cab.get("grupo", "Modos").split(" ", 1)[-1]}]}
    png = E / "assets/modos" / f"{cab['id']}.png"
    if png.exists():
        meta["profile_image_url"] = "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()
    return {"id": cab["id"], "base_model_id": cab["base"], "name": cab["nombre"], "meta": meta, "params": params,
            "grupo": cab.get("grupo", "")}


def carpeta(nombre, token, padre=None, modelo=None):
    """Crea (o actualiza) la carpeta «<emoji> Nombre» del lateral; con modelo, los chats nuevos en ella usan ese modo."""
    icono, _, texto = nombre.partition(" ")
    existe = next((f for f in pedir("/folders/", token=token) or []
                   if f["name"] == texto and f.get("parent_id") == padre), None)
    if not existe:
        existe = pedir("/folders/", {"name": texto, "parent_id": padre, "meta": {"icon": icono}}, token)
    datos = (pedir(f"/folders/{existe['id']}", token=token) or {}).get("data") or {}  # conserva lo que haya puesto el usuario
    if modelo:
        datos["model_ids"] = [modelo]
    pedir(f"/folders/{existe['id']}/update", {"meta": {"icon": icono}, "data": datos}, token)
    return existe["id"]


def main():
    try:
        cuenta = E / "config/webui-cuenta"  # «email\ncontraseña» del admin; sin el archivo, Open WebUI sin cuentas
        email, clave = (cuenta.read_text().split("\n")[:2] if cuenta.exists() else ("", ""))
        token = pedir("/auths/signin", {"email": email, "password": clave})["token"]
    except urllib.error.URLError:
        sys.exit("Open WebUI no responde en :3000. Arráncalo con ./srfrijol arrancar")

    for p in sorted((E / "openwebui/herramientas").glob("*.py")):
        codigo = p.read_text()
        titulo = re.search(r"^title:\s*(.+)$", codigo, re.M)
        desc = re.search(r"^description:\s*(.+)$", codigo, re.M)
        forma = {"id": p.stem, "name": titulo.group(1) if titulo else p.stem, "content": codigo,
                 "meta": {"description": desc.group(1) if desc else "", "manifest": {}}}
        existe = pedir(f"/tools/id/{p.stem}", token=token)
        pedir(f"/tools/id/{p.stem}/update" if existe else "/tools/create", forma, token)
        print(f"herramienta {p.stem}: {'actualizada' if existe else 'creada'}")

    # filtro global que reactiva las herramientas del modo en cada mensaje (si no, solo van en el primero)
    p = E / "openwebui/funciones/herramientas_modo.py"
    forma = {"id": p.stem, "name": "Herramientas del modo", "content": p.read_text(),
             "meta": {"description": "Activa en cada mensaje las herramientas del modo", "manifest": {}}}
    f = pedir(f"/functions/id/{p.stem}", token=token)
    f = pedir(f"/functions/id/{p.stem}/update" if f else "/functions/create", forma, token)
    if not f.get("is_active"):
        f = pedir(f"/functions/id/{p.stem}/toggle", {}, token)
    if not f.get("is_global"):
        pedir(f"/functions/id/{p.stem}/toggle/global", {}, token)
    print(f"filtro {p.stem}: activo y global")

    modos = [leer_modo(p) for p in sorted((E / "openwebui/modos").glob("*.md"))]
    grupos = {m.pop("grupo") for m in modos} - {""}
    if modos:
        pedir("/models/import", {"models": modos}, token)
    padres = {g: carpeta(g, token) for g in sorted(grupos)}
    for m, p in zip(modos, sorted((E / "openwebui/modos").glob("*.md"))):
        grupo = re.search(r"^grupo:\s*(.+)$", p.read_text().split("\n---", 1)[0], re.M)
        carpeta(m["name"], token, padres.get(grupo.group(1).strip()) if grupo else None, m["id"])
        print(f"modo {m['name']} ({m['base_model_id']}): instalado, con su carpeta"
              + (f" dentro de «{grupo.group(1).strip()}»" if grupo else ""))


if __name__ == "__main__":
    main()
