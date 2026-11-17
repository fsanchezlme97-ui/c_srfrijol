#!/usr/bin/env -S openwebui/.venv/bin/python
"""Dibuja el avatar de cada modo (assets/modos/<id>.png): su emoji sobre un cuadrado redondeado de su color.

Lee «nombre» (el emoji es lo primero) y «color» de la cabecera de openwebui/modos/*.md. Vuélvelo a ejecutar al
añadir un modo o cambiar su color, y luego scripts/instalar-modos.py. Uso (necesita Pillow, que trae Open WebUI):
    openwebui/.venv/bin/python scripts/avatares-modos.py
"""
import pathlib
import re
import sys

from PIL import Image, ImageDraw, ImageFont

E = pathlib.Path(__file__).resolve().parent.parent
EMOJI = "/usr/share/fonts/noto/NotoColorEmoji.ttf"  # fuente de mapa de bits: solo se dibuja a 109 px
LADO = 256


def avatar(emoji: str, color: str) -> Image.Image:
    rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    claro = tuple(min(255, c + 55) for c in rgb)
    # degradado diagonal del tono claro al color, como el logo
    fondo = Image.new("RGB", (LADO, LADO))
    for y in range(LADO):
        for x in range(0, LADO, 4):
            t = (x + y) / (2 * LADO)
            fondo.paste(tuple(round(claro[i] + (rgb[i] - claro[i]) * t) for i in range(3)), (x, y, x + 4, y + 1))
    mascara = Image.new("L", (LADO, LADO))
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, LADO - 1, LADO - 1), radius=LADO // 4, fill=255)
    img = Image.new("RGBA", (LADO, LADO))
    img.paste(fondo, mask=mascara)
    glifo = Image.new("RGBA", (160, 160))
    ImageDraw.Draw(glifo).text((80, 80), emoji, font=ImageFont.truetype(EMOJI, 109), embedded_color=True, anchor="mm")
    glifo = glifo.crop(glifo.getbbox()) if glifo.getbbox() else glifo
    glifo.thumbnail((int(LADO * 0.58),) * 2, Image.LANCZOS)
    img.alpha_composite(glifo, ((LADO - glifo.width) // 2, (LADO - glifo.height) // 2))
    return img


def main():
    salida = E / "assets/modos"
    salida.mkdir(parents=True, exist_ok=True)
    for p in sorted((E / "openwebui/modos").glob("*.md")):
        cab = dict(re.findall(r"^(\w+):\s*(.+)$", p.read_text().split("\n---", 1)[0], re.M))
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", cab.get("color", "")):
            print(f"{p.name}: sin «color: #rrggbb» en la cabecera, me lo salto", file=sys.stderr)
            continue
        emoji = cab["nombre"].split()[0]
        avatar(emoji, cab["color"]).save(salida / f"{cab['id']}.png", optimize=True)
        print(f"{cab['id']}: {emoji} {cab['color']}")


if __name__ == "__main__":
    main()
