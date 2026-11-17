"""
title: Métrica
description: Cuenta las sílabas métricas de cada verso en español (sinalefas y acento final) y saca la rima y el esquema. Úsala siempre antes de opinar sobre métrica o rima.
version: 1.0
"""

import re
import unicodedata

FUERTES = set("aeoáéíóú")  # í y ú con tilde rompen el diptongo: cuentan como fuertes
VOCALES = FUERTES | set("iuü")
TILDES = set("áéíóú")
NOMBRES = {5: "pentasílabo", 6: "hexasílabo", 7: "heptasílabo", 8: "octosílabo", 9: "eneasílabo", 10: "decasílabo",
           11: "endecasílabo", 12: "dodecasílabo", 13: "tridecasílabo", 14: "alejandrino"}


def _limpia(p: str) -> str:
    p = p.lower()
    p = re.sub(r"(?<=[qg])u(?=[eiéí])", "", p)  # u muda: que, guiso (la ü de pingüino sí suena)
    p = re.sub(r"y$", "i", p) if re.search(r"[aeiouáéíóú]y$", p) or p == "y" else p  # hoy, rey, la conjunción y
    return p.replace("h", "")  # la h no suena ni separa vocales


def _nucleos(p: str):
    """Lista de núcleos silábicos: cada uno es la cadena de vocales que suena junta (diptongos y triptongos)."""
    out, previa = [], False
    for c in p:
        if c not in VOCALES:
            previa = False
            continue
        if previa and not (out[-1][-1] in FUERTES and c in FUERTES):  # dos fuertes = hiato; si no, diptongo
            out[-1] += c
        else:
            out.append(c)
        previa = True
    return out


def _tonica(p: str, nucleos) -> int:
    """Índice del núcleo tónico."""
    for i, n in enumerate(nucleos):
        if set(n) & TILDES:
            return i
    if len(nucleos) == 1:
        return 0
    return len(nucleos) - 2 if re.search(r"[aeiouns]$", p) else len(nucleos) - 1


def _vocal_tonica(n: str) -> str:
    return next((c for c in n if c in TILDES), None) or next((c for c in n if c in "aeo"), n[-1])


def _sin_tilde(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def verso(linea: str) -> dict:
    palabras = [_limpia(p) for p in re.findall(r"[a-záéíóúüñ]+", linea.lower())]
    palabras = [p for p in palabras if _nucleos(p)]
    if not palabras:
        return {}
    total = sum(len(_nucleos(p)) for p in palabras)
    sinalefas, unida = 0, False
    for a, b, orig_b in zip(palabras, palabras[1:], re.findall(r"[a-záéíóúüñ]+", linea.lower())[1:] + [""]):
        # vocal final + vocal inicial (la h no cuenta), salvo hie-/hue- (suenan a consonante) y sin encadenar
        # tres: «rosa y azucena» une «sa y», no «sa y a»
        junta = (a[-1] in VOCALES and b[0] in VOCALES and not re.match(r"h[iu][aeo]", orig_b)
                 and not (unida and len(a) == 1))
        sinalefas += junta
        unida = junta
    ultima = palabras[-1]
    nuc = _nucleos(ultima)
    t = _tonica(ultima, nuc)
    desde_final = len(nuc) - 1 - t  # 0 aguda, 1 llana, 2+ esdrújula
    ajuste = {0: 1, 1: 0}.get(desde_final, -1)
    tipo = {0: "aguda (+1)", 1: "llana"}.get(desde_final, "esdrújula (−1)")
    # rima desde la vocal tónica: consonante = todos los sonidos, asonante = tónica + última vocal
    inicio = sum(len(n) for n in nuc[:t])  # posición aproximada en las vocales; se busca en el texto
    resto = ultima[[i for i, c in enumerate(ultima) if c in VOCALES][inicio]:]
    vt = _vocal_tonica(nuc[t])
    resto = resto[resto.index(vt):] if vt in resto else resto
    consonante = _sin_tilde(resto).replace("v", "b")
    asonante = _sin_tilde(vt + ("" if desde_final == 0 else _vocal_tonica(nuc[-1]) if len(nuc[-1]) > 1 else nuc[-1][-1]))
    medida = total - sinalefas + ajuste
    return {"medida": medida, "silabas": total, "sinalefas": sinalefas, "final": tipo,
            "consonante": consonante, "asonante": asonante}


def esquema(versos) -> str:
    letras, vistas = [], {}
    for v in versos:
        if not v:
            letras.append("-")
            continue
        clave = next((k for k in vistas if k[0] == v["consonante"]), None) or \
            next((k for k in vistas if k[1] == v["asonante"]), None)
        if clave is None:
            clave = (v["consonante"], v["asonante"])
            vistas[clave] = chr(ord("A") + len(vistas))
        letras.append(vistas[clave])
    return "".join(letras)


class Tools:
    def medir(self, texto: str) -> str:
        """
        Cuenta las sílabas métricas de cada verso (sílabas, menos sinalefas, más el ajuste del final agudo/llano/esdrújulo) y da su rima consonante y asonante y el esquema de rima. Úsala SIEMPRE antes de hablar de métrica o rima: no cuentes de cabeza.
        :param texto: el poema o la letra, un verso por línea.
        """
        lineas = [l.strip() for l in (texto or "").splitlines() if l.strip()]
        if not lineas:
            return "No hay versos que medir."
        vs = [verso(l) for l in lineas]
        out = []
        for i, (l, v) in enumerate(zip(lineas, vs), 1):
            if not v:
                out.append(f"{i}. «{l}»: sin sílabas")
                continue
            out.append(f"{i}. «{l}» → {v['medida']} ({NOMBRES.get(v['medida'], 'verso')}): {v['silabas']} sílabas, "
                       f"{v['sinalefas']} sinalefas, final {v['final']}; rima -{v['consonante']} (asonante {v['asonante']})")
        medidas = {v["medida"] for v in vs if v}
        out.append(f"Esquema de rima: {esquema(vs)}. " + ("Medida regular." if len(medidas) == 1 else
                   f"Medidas distintas: {', '.join(map(str, sorted(medidas)))}."))
        out.append("Recuento automático por reglas (sinalefa siempre que se puede): si el poeta hace hiato, dialefa, "
                   "diéresis o sinéresis a propósito, puede variar en una sílaba.")
        return "\n".join(out)


if __name__ == "__main__":
    m = lambda s: verso(s)["medida"]
    assert [m(v) for v in ["Camino por la playa sola", "buscando tu figura", "pero solo encuentro la marea",
                           "y el viento que me nombra."]] == [9, 7, 10, 7]
    assert m("Volverán las oscuras golondrinas") == 11 and m("en tu balcón sus nidos a colgar") == 11
    assert m("En tanto que de rosa y azucena") == 11  # Garcilaso: «sa y» une, no «sa y a»
    assert m("se muestra la color en vuestro gesto") == 11
    assert m("la luna mira el mar") == 7 and m("el agua del cántaro") == 6  # aguda +1, esdrújula −1
    assert m("Que por mayo era, por mayo") == 8  # «yo e» sinalefa
    assert m("hoy") == 2 and m("país") == 3 and m("ciudad") == 3 and m("río") == 2 and m("guerra") == 2
    assert verso("buscando tu figura")["asonante"] == "ua" and verso("en tu balcón sus nidos a colgar")["asonante"] == "a"
    assert verso("y el viento que me nombra")["consonante"] == "ombra"
    r = Tools().medir("Volverán las oscuras golondrinas\nen tu balcón sus nidos a colgar,\ny otra vez con el ala a sus cristales\njugando llamarán.")
    assert "Esquema de rima: ABCB" in r, r
    assert m("jugando llamarán") == 7
    print(r)
    print("OK")
