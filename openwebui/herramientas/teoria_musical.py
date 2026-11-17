"""
title: Teoría musical
description: Escalas, acordes, armonía de una tonalidad, círculo de quintas, transposición y mapas del mástil (guitarra, ukelele, bajo) y del piano. Cálculo exacto: úsala en vez de recordar notas o digitaciones.
version: 1.0
"""

import re

LETRAS = "CDEFGAB"
NAT = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LATINO = {"C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}
ES = {"do": "C", "re": "D", "mi": "E", "fa": "F", "sol": "G", "la": "A", "si": "B"}
ALT = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}

# (semitonos, grados de letra) desde la tónica: así F mayor sale con Bb y no con A#
ESCALAS = {
    "mayor": [(0, 0), (2, 1), (4, 2), (5, 3), (7, 4), (9, 5), (11, 6)],
    "menor": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (8, 5), (10, 6)],
    "menor armonica": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (8, 5), (11, 6)],
    "menor melodica": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (9, 5), (11, 6)],
    "dorica": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (9, 5), (10, 6)],
    "frigia": [(0, 0), (1, 1), (3, 2), (5, 3), (7, 4), (8, 5), (10, 6)],
    "lidia": [(0, 0), (2, 1), (4, 2), (6, 3), (7, 4), (9, 5), (11, 6)],
    "mixolidia": [(0, 0), (2, 1), (4, 2), (5, 3), (7, 4), (9, 5), (10, 6)],
    "locria": [(0, 0), (1, 1), (3, 2), (5, 3), (6, 4), (8, 5), (10, 6)],
    "frigia dominante": [(0, 0), (1, 1), (4, 2), (5, 3), (7, 4), (8, 5), (10, 6)],
    "pentatonica mayor": [(0, 0), (2, 1), (4, 2), (7, 4), (9, 5)],
    "pentatonica menor": [(0, 0), (3, 2), (5, 3), (7, 4), (10, 6)],
    "blues": [(0, 0), (3, 2), (5, 3), (6, 4), (7, 4), (10, 6)],
}
ALIAS_ESCALA = {"jonica": "mayor", "eolica": "menor", "menor natural": "menor", "pentatonica": "pentatonica mayor",
                "flamenca": "frigia dominante", "menor pentatonica": "pentatonica menor",
                "mayor pentatonica": "pentatonica mayor", "andaluza": "frigia dominante", "major": "mayor", "minor": "menor"}

ACORDES = {  # calidad -> [(semitonos, grados)]
    "": [(0, 0), (4, 2), (7, 4)], "m": [(0, 0), (3, 2), (7, 4)], "dim": [(0, 0), (3, 2), (6, 4)],
    "aug": [(0, 0), (4, 2), (8, 4)], "sus2": [(0, 0), (2, 1), (7, 4)], "sus4": [(0, 0), (5, 3), (7, 4)],
    "5": [(0, 0), (7, 4)], "6": [(0, 0), (4, 2), (7, 4), (9, 5)], "m6": [(0, 0), (3, 2), (7, 4), (9, 5)],
    "7": [(0, 0), (4, 2), (7, 4), (10, 6)], "maj7": [(0, 0), (4, 2), (7, 4), (11, 6)],
    "m7": [(0, 0), (3, 2), (7, 4), (10, 6)], "m7b5": [(0, 0), (3, 2), (6, 4), (10, 6)],
    "dim7": [(0, 0), (3, 2), (6, 4), (9, 6)], "mmaj7": [(0, 0), (3, 2), (7, 4), (11, 6)],
    "7sus4": [(0, 0), (5, 3), (7, 4), (10, 6)], "add9": [(0, 0), (4, 2), (7, 4), (2, 1)],
    "madd9": [(0, 0), (3, 2), (7, 4), (2, 1)], "9": [(0, 0), (4, 2), (7, 4), (10, 6), (2, 1)],
    "maj9": [(0, 0), (4, 2), (7, 4), (11, 6), (2, 1)], "m9": [(0, 0), (3, 2), (7, 4), (10, 6), (2, 1)],
}
ALIAS_ACORDE = {"M": "", "maj": "", "mayor": "", "min": "m", "-": "m", "menor": "m", "°": "dim", "o": "dim",
                "+": "aug", "M7": "maj7", "7M": "maj7", "Δ": "maj7", "Δ7": "maj7", "ø": "m7b5", "ø7": "m7b5",
                "m7(b5)": "m7b5", "-7": "m7", "°7": "dim7", "o7": "dim7", "sus": "sus4", "m(maj7)": "mmaj7",
                "mM7": "mmaj7", "add2": "add9", "2": "sus2", "4": "sus4"}
INTERVALO = {0: "1", 1: "b2", 2: "2", 3: "b3", 4: "3", 5: "4", 6: "b5", 7: "5", 8: "#5", 9: "6", 10: "b7", 11: "7"}

# afinaciones (grave -> aguda), en clases de altura; el ukelele es re-entrante (G4 C4 E4 A4)
INSTRUMENTOS = {"guitarra": ("E A D G B E", [4, 9, 2, 7, 11, 4]), "bajo": ("E A D G", [4, 9, 2, 7]),
                "bajo5": ("B E A D G", [11, 4, 9, 2, 7]), "ukelele": ("G C E A", [7, 0, 4, 9])}

# digitaciones abiertas comprobadas (grave -> aguda, x = no suena); se validan contra las notas del acorde abajo
ABIERTOS = {
    "guitarra": {"C": "x32010", "A": "x02220", "G": "320003", "E": "022100", "D": "xx0232", "F": "133211",
                 "Am": "x02210", "Em": "022000", "Dm": "xx0231", "Bm": "x24432", "C7": "x32310", "A7": "x02020",
                 "G7": "320001", "E7": "020100", "D7": "xx0212", "B7": "x21202", "Am7": "x02010", "Em7": "022030",
                 "Dm7": "xx0211", "Cmaj7": "x32000", "Fmaj7": "xx3210", "Gmaj7": "320002", "Amaj7": "x02120",
                 "Dmaj7": "xx0222", "Asus2": "x02200", "Asus4": "x02230", "Dsus2": "xx0230", "Dsus4": "xx0233",
                 "Esus4": "022200", "Cadd9": "x32033"},
    "ukelele": {"C": "0003", "G": "0232", "F": "2010", "D": "2220", "A": "2100", "E": "1402", "Am": "2000",
                "Em": "0432", "Dm": "2210", "Bm": "4222", "Bb": "3211", "C7": "0001", "G7": "0212", "A7": "0100",
                "D7": "2223", "E7": "1202", "Am7": "0000", "Dm7": "2213", "Cmaj7": "0002", "Fmaj7": "2413",
                "Gm": "0231", "Csus4": "0013", "Gsus4": "0233", "Dsus4": "0230"},
}
# formas móviles: (nombre, desplazamiento de la tónica respecto al traste 0, calidad -> forma relativa)
MOVILES = {
    "guitarra": [("cejilla forma de E (tónica en la 6ª)", 4, {"": "022100", "m": "022000", "7": "020100",
                  "m7": "020000", "sus4": "022200", "maj7": "0x110x"}),
                 ("cejilla forma de A (tónica en la 5ª)", 9, {"": "x02220", "m": "x02210", "7": "x02020",
                  "m7": "x02010", "maj7": "x02120", "sus2": "x02200", "sus4": "x02230", "m7b5": "x0101x",
                  "dim7": "x01212", "dim": "x0121x"})],
    "ukelele": [("forma de Bb (cejilla)", 10, {"": "3211", "m": "3111", "7": "1211", "m7": "1111",
                                                       "dim": "3101"})],
}


def _nota(s):
    """'Sol#', 'mib', 'Bb', 'f' -> (índice de letra, clase de altura, resto del texto)."""
    s = s.strip()
    m = re.match(r"(sol|do|re|mi|fa|la|si)(?!dd|ug)", s, re.I)  # «Fadd9», «Faug» son F, no Fa
    if m:
        letra, resto = ES[m.group(1).lower()], s[m.end():]
    elif s and s[0].upper() in NAT:
        letra, resto = s[0].upper(), s[1:]
    else:
        raise ValueError(f"No reconozco la nota «{s}» (usa C D E F G A B o Do Re Mi…)")
    a = re.match(r"[#♯b♭]*", resto).group(0)
    alt = a.count("#") + a.count("♯") - a.count("b") - a.count("♭")
    return LETRAS.index(letra), (NAT[letra] + alt) % 12, resto[len(a):]


def _deletrear(li, pc, semis, grados):
    letra = LETRAS[(li + grados) % 7]
    d = ((pc + semis) - NAT[letra]) % 12
    return letra + ALT[d - 12 if d > 6 else d]


def _pc(nombre):
    return _nota(nombre)[1]


def _con_latino(n):
    return f"{n} ({LATINO[n[0]]}{n[1:]})"


def _acorde(simbolo):
    """'Lam7/G' -> (raíz, calidad, [notas], bajo o None)."""
    simbolo = simbolo.strip()
    bajo = None
    if "/" in simbolo:
        simbolo, b = simbolo.rsplit("/", 1)
        li, pc, _ = _nota(b)
        bajo = _deletrear(li, pc, 0, 0)
    li, pc, q = _nota(simbolo)
    q = q.strip()
    q = ALIAS_ACORDE.get(q, q)
    if q not in ACORDES:
        raise ValueError(f"No conozco el tipo de acorde «{q}». Conozco: " + ", ".join(k or "mayor" for k in ACORDES))
    return _deletrear(li, pc, 0, 0), q, [_deletrear(li, pc, s, g) for s, g in ACORDES[q]], bajo


def _escala(tonica, tipo):
    t = re.sub(r"[áéíóú]", lambda m: "aeiou"["áéíóú".index(m.group())], tipo.lower().strip())
    t = ALIAS_ESCALA.get(t, t)
    if t not in ESCALAS:
        raise ValueError(f"No conozco la escala «{tipo}». Conozco: " + ", ".join(ESCALAS))
    li, pc, _ = _nota(tonica)
    return t, [(_deletrear(li, pc, s, g), s) for s, g in ESCALAS[t]]


def _tonalidad(texto):
    """'Sol mayor', 'Em', 'F# menor' -> (tónica, 'mayor'|'menor')."""
    li, pc, resto = _nota(texto)
    r = resto.strip().lower()
    menor = r.startswith(("m", "-")) and not r.startswith(("maj", "mayor", "major"))
    return _deletrear(li, pc, 0, 0), "menor" if menor else "mayor"


def _calidad(notas_pc):
    r = notas_pc[0]
    iv = tuple((p - r) % 12 for p in notas_pc[1:])
    return {(4, 7): "", (3, 7): "m", (3, 6): "dim", (4, 8): "aug", (4, 7, 11): "maj7", (4, 7, 10): "7",
            (3, 7, 10): "m7", (3, 6, 10): "m7b5", (3, 7, 11): "mmaj7", (4, 8, 11): "maj7#5", (3, 6, 9): "dim7"}[iv]


def _romano(grado, q):
    r = ["I", "II", "III", "IV", "V", "VI", "VII"][grado]
    if q.startswith("m") and not q.startswith("maj") or q.startswith("dim"):
        r = r.lower()
    return r + {"": "", "m": "", "dim": "°", "aug": "+", "m7b5": "ø7", "dim7": "°7", "m7": "7"}.get(q, q)


def _mastil(pcs, nombres, raiz, instrumento, trastes=12):
    cuerdas, afin = INSTRUMENTOS[instrumento]
    lineas = ["    " + "".join(f"{f:^5}" for f in range(trastes + 1))]
    for nombre_cuerda, abierta in reversed(list(zip(cuerdas.split(), afin))):
        celdas = []
        for f in range(trastes + 1):
            p = (abierta + f) % 12
            n = nombres.get(p, "")
            celdas.append(f"{('[' + n + ']') if p == raiz else n:^5}" if p in pcs else f"{'·':^5}")
        lineas.append(f"{nombre_cuerda:>2} |" + "".join(celdas))
    return "```\n" + "\n".join(lineas) + "\n```\n(arriba la cuerda más aguda; [ ] = tónica; trastes 3, 5, 7, 9 y 12 son los marcados)"


def _suena(forma, afin, base=0):
    return {(a + int(c) + base) % 12 for a, c in zip(afin, forma) if c != "x"}


def _digitaciones(raiz, q, notas, instrumento):
    afin = INSTRUMENTOS[instrumento][1]
    pcs, rpc = {_pc(n) for n in notas}, _pc(raiz)
    out = []
    abierto, moviles = None, []
    for k, f in ABIERTOS[instrumento].items():
        r, qq, _, _ = _acorde(k)
        if _pc(r) == rpc and qq == q:
            abierto = f
    if abierto:
        out.append(f"abierto: `{abierto}`")
    for nombre, desde, formas in MOVILES[instrumento]:
        if q in formas:
            t = (rpc - desde) % 12
            base = min(int(c) for c in formas[q] if c != "x")
            if t + base >= 12 and t - 12 + base >= 0:  # bajar una octava si la forma cabe más abajo
                t -= 12
            forma = "".join("x" if c == "x" else str(int(c) + t) if int(c) + t < 10 else f"({int(c) + t})"
                            for c in formas[q])
            if forma != abierto:
                moviles.append((t + base, f"{nombre}, cejilla en el traste {t + base}: `{forma}`"))
    out += [txt for _, txt in sorted(moviles)]
    return out or [f"sin forma guardada para este tipo; mira el mapa del mástil (notas {', '.join(notas)})"]


def _cuerdas(forma, instrumento):
    """`x32010` -> 'A traste 3, D traste 2, G al aire, B traste 1, E al aire (E grave sin tocar)'."""
    nombres = INSTRUMENTOS[instrumento][0].split()
    trastes = re.findall(r"x|\(\d+\)|\d", forma)
    partes = [f"{n} " + ("sin tocar" if t == "x" else "al aire" if t == "0" else f"traste {t.strip('()')}")
              for n, t in zip(nombres, trastes)]
    return ", ".join(partes)


class Tools:
    def escala(self, tonica: str, tipo: str = "mayor") -> str:
        """
        Notas exactas de una escala, con sus grados y nombres latinos.
        :param tonica: nota de partida, p. ej. "Sol", "F#", "Mib".
        :param tipo: mayor, menor, menor armonica, menor melodica, dorica, frigia, lidia, mixolidia, locria, frigia dominante (flamenca), pentatonica mayor, pentatonica menor, blues.
        """
        try:
            t, notas = _escala(tonica, tipo)
        except ValueError as e:
            return str(e)
        return (f"Escala {notas[0][0]} {t}: " + " – ".join(_con_latino(n) for n, _ in notas) +
                "\nGrados: " + " ".join(INTERVALO[s] for _, s in notas))

    def acorde(self, simbolo: str) -> str:
        """
        Notas, intervalos, inversiones en piano y digitaciones de guitarra y ukelele de un acorde.
        :param simbolo: cifrado del acorde, p. ej. "Am7", "Fmaj7", "D/F#", "Sol7", "Bbsus4", "Lam".
        """
        try:
            raiz, q, notas, bajo = _acorde(simbolo)
        except ValueError as e:
            return str(e)
        inv = [notas[i:] + notas[:i] for i in range(min(len(notas), 4))]
        r = [f"{simbolo}: " + " – ".join(_con_latino(n) for n in notas) +
             ("" if not bajo else f", con {bajo} en el bajo"),
             "Intervalos: " + " ".join("9" if g == 1 and q != "sus2" else INTERVALO[s] for s, g in ACORDES[q]),
             "Piano (mano derecha, de grave a agudo): " + " | ".join(
                 ("fundamental: " if i == 0 else f"{i}ª inversión: ") + " ".join(v) for i, v in enumerate(inv)),
             *(f"{nombre}: " + "; ".join(d) + ("" if "`" not in d[0] else
               f"\n  cuerda a cuerda (de grave a aguda), la primera: {_cuerdas(d[0].split('`')[1], inst)}")
               for nombre, inst, d in (("Guitarra (6ª→1ª)", "guitarra", _digitaciones(raiz, q, notas, "guitarra")),
                                       ("Ukelele (G C E A)", "ukelele", _digitaciones(raiz, q, notas, "ukelele")))),
             f"Bajo: tónica {raiz}" + (f" (toca {bajo})" if bajo else "") + f", quinta {notas[2] if len(notas) > 2 and q != '5' else notas[-1]}"]
        return "\n".join(r)

    def armonia(self, tonalidad: str) -> str:
        """
        Acordes de una tonalidad (tríadas y cuatriadas con números romanos) y progresiones típicas ya escritas en esa tonalidad.
        :param tonalidad: p. ej. "Sol mayor", "Em", "La menor", "Bb".
        """
        try:
            ton, modo = _tonalidad(tonalidad)
            _, esc = _escala(ton, modo)
        except ValueError as e:
            return str(e)
        nombres = [n for n, _ in esc]
        filas, triadas = [], []
        for i in range(7):
            t = [nombres[(i + k) % 7] for k in (0, 2, 4)]
            c = t + [nombres[(i + 6) % 7]]
            qt, qc = _calidad([_pc(n) for n in t]), _calidad([_pc(n) for n in c])
            triadas.append(nombres[i] + qt)
            g, u = (_digitaciones(nombres[i], qt, t, x)[0].split("`")[1::2] or ["—"] for x in ("guitarra", "ukelele"))
            filas.append(f"| {_romano(i, qt)} | {nombres[i] + qt} | {nombres[i] + qc} | {' '.join(t)} | `{g[0]}` | `{u[0]}` |")
        triadas.append(nombres[4])  # índice 7: V mayor (dominante de la menor armónica)
        if modo == "menor":
            v = _acorde(nombres[4])[2]
            g, u = (_digitaciones(nombres[4], "", v, x)[0].split("`")[1::2] or ["—"] for x in ("guitarra", "ukelele"))
            filas.append(f"| V (prestado) | {nombres[4]} | {nombres[4]}7 | {' '.join(v)} | `{g[0]}` | `{u[0]}` |")
        if modo == "mayor":
            prog = {"pop (I–V–vi–IV)": [0, 4, 5, 3], "años 50 (I–vi–IV–V)": [0, 5, 3, 4],
                    "balada (vi–IV–I–V)": [5, 3, 0, 4], "jazz (ii–V–I)": [1, 4, 0], "canon (I–V–vi–iii–IV–I–IV–V)": [0, 4, 5, 2, 3, 0, 3, 4],
                    "blues 12 compases": [0, 0, 0, 0, 3, 3, 0, 0, 4, 3, 0, 4]}
        else:
            prog = {"épica (i–VI–III–VII)": [0, 5, 2, 6], "andaluza (i–VII–VI–V)": [0, 6, 5, 7],
                    "melancólica (i–iv–V)": [0, 3, 7], "pop menor (i–VI–VII)": [0, 5, 6]}
        p = [f"- {k}: " + " – ".join(triadas[g] for g in v) for k, v in prog.items()]
        extra = ""
        if modo == "menor":
            li, pc, _ = _nota(nombres[4])
            v7 = _deletrear(li, pc, 0, 0)
            extra = (f"\nEn menor es muy común usar el V mayor de la menor armónica: {v7} o {v7}7 "
                     f"(la sensible {_deletrear(*_nota(ton)[:2], 11, 6)} empuja a volver a {ton}m); "
                     f"por eso las progresiones de arriba ya lo usan.")
        return (f"Tonalidad de {ton} {modo} (escala: {' '.join(nombres)})\n\n| Grado | Tríada | Cuatriada | Notas de la tríada | Guitarra (tríada) | Ukelele (tríada) |\n|---|---|---|---|---|---|\n"
                + "\n".join(filas) + "\n\nProgresiones:\n" + "\n".join(p) + extra)

    def circulo_de_quintas(self, tonalidad: str = "") -> str:
        """
        El círculo de quintas (tonalidades mayores, relativas menores y armaduras). Con una tonalidad, dice sus vecinas para modular o pedir acordes prestados.
        :param tonalidad: opcional, p. ej. "Re mayor" o "Bm".
        """
        mayores = ["C", "G", "D", "A", "E", "B", "F#", "Db", "Ab", "Eb", "Bb", "F"]
        arm = ["sin alteraciones", "1#", "2#", "3#", "4#", "5#", "6# (o Gb: 6b)", "5b", "4b", "3b", "2b", "1b"]
        rel = [_deletrear(*_nota(m)[:2], 9, 5) + "m" for m in mayores]
        txt = "Círculo de quintas (sentido horario = una quinta arriba):\n" + "\n".join(
            f"- {m} mayor / {r} — {a}" for m, r, a in zip(mayores, rel, arm))
        if tonalidad:
            try:
                ton, modo = _tonalidad(tonalidad)
            except ValueError as e:
                return str(e)
            pc = _pc(ton) if modo == "mayor" else (_pc(ton) + 3) % 12
            i = next(k for k, m in enumerate(mayores) if _pc(m) == pc)
            iz, de = (i - 1) % 12, (i + 1) % 12
            txt += (f"\n\n{ton} {modo}: está en la posición de {mayores[i]} mayor / {rel[i]} ({arm[i]}). "
                    f"Vecinas (comparten 6 de 7 notas, ideales para modular): {mayores[iz]} / {rel[iz]} y "
                    f"{mayores[de]} / {rel[de]}. Su relativa: {rel[i] if modo == 'mayor' else mayores[i]}.")
        return txt

    def transponer(self, acordes: str, semitonos: int) -> str:
        """
        Sube o baja una progresión de acordes un número de semitonos (p. ej. para cambiar de tono o usar cejilla/capo).
        :param acordes: acordes separados por espacios, comas o guiones, p. ej. "C G Am F".
        :param semitonos: cuántos semitonos subir (negativo para bajar). Con capo en el traste N, usa -N para saber qué formas tocar.
        """
        nombres = {0: "C", 1: "Db", 2: "D", 3: "Eb", 4: "E", 5: "F", 6: "F#", 7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B"}

        def mover(simbolo):
            partes = simbolo.split("/")
            out = []
            for p in partes:
                _, pc, resto = _nota(p)
                out.append(nombres[(pc + semitonos) % 12] + resto)
            return "/".join(out)

        try:
            res = [mover(a) for a in re.split(r"[\s,–\-|]+", acordes.strip()) if a]
        except ValueError as e:
            return str(e)
        return f"{acordes}  →  {' '.join(res)}  ({semitonos:+d} semitonos)"

    def mastil(self, acorde_o_escala: str, instrumento: str = "guitarra") -> str:
        """
        Mapa del mástil con todas las posiciones de las notas de un acorde o una escala, trastes 0 a 12.
        :param acorde_o_escala: un acorde ("Am7") o una escala con su tipo ("A pentatonica menor", "Sol mayor").
        :param instrumento: guitarra, bajo, bajo5 (5 cuerdas) o ukelele.
        """
        inst = instrumento.lower().replace("ukulele", "ukelele").replace("ukele", "ukelele").replace("ukelelele", "ukelele")
        if inst not in INSTRUMENTOS:
            return "Instrumentos: " + ", ".join(INSTRUMENTOS)
        try:
            partes = acorde_o_escala.split(maxsplit=1)
            if len(partes) == 2 and not partes[1].startswith("/"):
                raiz, notas = partes[0], [n for n, _ in _escala(partes[0], partes[1])[1]]
                raiz = notas[0]
            else:
                raiz, _, notas, _ = _acorde(acorde_o_escala)
        except ValueError as e:
            return str(e)
        nombres = {_pc(n): n for n in notas}
        return f"{acorde_o_escala} en {inst} ({INSTRUMENTOS[inst][0]}): {' '.join(notas)}\n" + _mastil(
            set(nombres), nombres, _pc(raiz), inst)


if __name__ == "__main__":  # autocomprobación: python3 teoria_musical.py
    assert [n for n, _ in _escala("F", "mayor")[1]] == ["F", "G", "A", "Bb", "C", "D", "E"]
    assert [n for n, _ in _escala("Mib", "mayor")[1]] == ["Eb", "F", "G", "Ab", "Bb", "C", "D"]
    assert [n for n, _ in _escala("F#", "menor")[1]] == ["F#", "G#", "A", "B", "C#", "D", "E"]
    assert "A C D E G" in Tools().mastil("A menor pentatonica")
    assert [n for n, _ in _escala("A", "blues")[1]] == ["A", "C", "D", "Eb", "E", "G"]
    assert [n for n, _ in _escala("E", "flamenca")[1]] == ["E", "F", "G#", "A", "B", "C", "D"]
    assert _acorde("Fadd9")[2] == ["F", "A", "C", "G"] and _acorde("Faug")[2] == ["F", "A", "C#"]
    assert _acorde("Fam")[2] == ["F", "Ab", "C"] and _acorde("Ddim")[2] == ["D", "F", "Ab"]
    assert _tonalidad("Re menor armónica") == ("D", "menor") and _tonalidad("Do mayor") == ("C", "mayor")
    assert _acorde("Bdim7")[2] == ["B", "D", "F", "Ab"]
    assert _acorde("Lam7/G")[2] == ["A", "C", "E", "G"] and _acorde("Lam7/G")[3] == "G"
    assert _acorde("Ebmaj7")[2] == ["Eb", "G", "Bb", "D"]
    assert _tonalidad("Sol mayor") == ("G", "mayor") and _tonalidad("Em") == ("E", "menor")
    # toda forma guardada suena solo notas del acorde, e incluye tónica y tercera (o la 2ª/4ª en sus)
    for inst, tabla in ABIERTOS.items():
        afin = INSTRUMENTOS[inst][1]
        for k, f in tabla.items():
            r, q, notas, _ = _acorde(k)
            pcs, suena = {_pc(n) for n in notas}, _suena(f, afin)
            assert suena <= pcs and {_pc(notas[0]), _pc(notas[1])} <= suena, (inst, k, f)
    for inst, moviles in MOVILES.items():
        afin = INSTRUMENTOS[inst][1]
        for _, desde, formas in moviles:
            for q, f in formas.items():
                notas = _acorde({4: "E", 9: "A", 10: "Bb"}[desde] + q)[2]
                pcs, suena = {_pc(n) for n in notas}, _suena(f, afin)
                assert suena <= pcs and _pc(notas[0]) in suena, (inst, q, f)
    t = Tools()
    assert "Bm" in t.armonia("D") and "F#m" in t.armonia("D") and "C#dim" in t.armonia("D")
    assert "| IV | Bb | Bbmaj7 | Bb D F | `x13331` | `3211` |" in t.armonia("Fa mayor") and "Edim | Em7b5 | E G Bb | `x7898x` | `9767` |" in t.armonia("Fa mayor"), t.armonia("Fa mayor")
    assert "| ii | Gm | Gm7 | G Bb D | `355333` | `0231` |" in t.armonia("Fa mayor")
    assert "G7" in t.armonia("Do mayor") and "Bm7b5" in t.armonia("Do mayor")
    assert "Am – G – F – E\n" in t.armonia("Am")
    assert "| V (prestado) | A | A7 | A C# E | `x02220` | `2100` |" in t.armonia("Re menor")
    assert t.transponer("C G Am F", 2).endswith("D A Bm G  (+2 semitonos)")
    assert "`133211`" in t.acorde("F") and "traste 5: `577555`" in t.acorde("Am") and "traste 8: `x8(10)(10)(10)8`" in t.acorde("F")
    assert "C traste 2, E traste 3, A traste 1" in t.acorde("Gm") and "A traste 3, D traste 2, G al aire" in t.acorde("C")
    assert "(14)" not in t.acorde("Am") and "traste 2: `4322`" in t.acorde("B")
    print(t.acorde("Bm7"), t.armonia("Em"), t.circulo_de_quintas("Re mayor"), t.mastil("A pentatonica menor"),
          t.mastil("G", "ukelele"), sep="\n\n")
    print("\nOK")
