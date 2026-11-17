<p align="center"><img alt="Open Web UI - C_SrFrijol — Local · Privado · Creativo" src="assets/brand/logo.png" width="760"></p>

# Open Web UI - C_SrFrijol

IA local en este equipo (Ryzen 5 5600G, 46 GB de RAM, Radeon RX 6600 XT de 8 GB), con **Open WebUI** como
interfaz. Open WebUI se abre a la red de casa con cuenta; lo demás (llama-swap, ComfyUI) escucha solo en
`127.0.0.1`. Nada arranca solo al iniciar sesión.

```
./srfrijol arrancar     # Open WebUI en http://127.0.0.1:3000 y desde casa en http://<equipo>.local:3000
./srfrijol abrir        # arranca si hace falta y abre el navegador (lanzador «Open Web UI - C_SrFrijol» del menú)
./srfrijol estado       # qué está en marcha y qué modelo ocupa la gráfica
./srfrijol video        # ComfyUI en http://127.0.0.1:8188 (libera antes la gráfica)
./srfrijol parar        # todo
./srfrijol logs
scripts/descargar.sh   # vuelve a bajar lo que falte (reanuda)
```

En el menú de aplicaciones: **Open Web UI - C_SrFrijol** (abre) y **Apagar Open Web UI - C_SrFrijol** (`~/.local/share/applications/`).
Logo e icono en `assets/brand/`.

## Cómo está montado

```
Open WebUI :3000 ──► Ollama :11434          gemma4:e4b (el de Helpert) · qwen3.5:9b
                 └─► llama-swap :8090 ──┬─► llama-server (llama.cpp, Vulkan)  Qwen3.6-35B-A3B
                                        ├─► sd-server (stable-diffusion.cpp, Vulkan)  flux2-klein · sdxl · flux1-schnell
                                        ├─► Kokoro-FastAPI (CPU)  voz
                                        └─► whisper-server (CPU)  voz a texto
ComfyUI (ROCm) :8188 ── vídeo con Wan 2.2 TI2V 5B (aparte, ver abajo)
```

**llama-swap** arranca cada servidor cuando se le pide y lo apaga tras un rato sin uso (`ttl`). Los de la gráfica
(grupo `gpu`) van de uno en uno: el escritorio ya usa ~4 GB de los 8 (Chrome, Hyprland, el fondo animado…).
Antes de cargar uno, `scripts/liberar-vram.sh` descarga lo que Ollama tenga en memoria (Helpert lo recarga solo).

| Qué | Modelo | Dónde |
|---|---|---|
| Texto rápido | gemma4:e4b | Ollama (compartido con Helpert) |
| Texto, buena calidad | qwen3.5:9b | Ollama |
| Texto, el más capaz | Qwen3.6-35B-A3B UD-IQ4_XS (MoE) | `models/llm`, llama.cpp con `--fit` |
| Imagen | FLUX.2 klein 4B Q4 (por defecto), SDXL 1.0, FLUX.1 schnell Q4 | `models/image` |
| Voz | Kokoro, voz `ef_dora` (español) | `kokoro/` |
| Voz a texto | whisper.cpp small (el de HyprFrijol) | `~/.local/share/hyprfrijol/whisper` |
| Vídeo | Wan 2.2 TI2V 5B Q4 + umt5 Q4 + VAE | `models/video/wan22`, en ComfyUI |

## Open WebUI

- Con cuenta y abierto a la red de casa (`0.0.0.0:3000`). Usuario y contraseña del admin en `config/webui-cuenta`
  (solo legible por ti, fuera de git; `scripts/instalar-modos.py` entra con ella). Registro cerrado: las cuentas
  nuevas las crea el admin en Administración › Usuarios.
- `./srfrijol arrancar` pone `CORS_ALLOW_ORIGIN` con localhost, `<equipo>.local` y la IP actual: solo la propia
  interfaz puede usar la API, no otras webs abiertas en el navegador. Si cambia la IP, `./srfrijol parar` y arrancar.
- Para entrar desde el móvil u otro equipo, el cortafuegos debe dejar pasar el puerto 3000 desde la red local:
  `sudo ufw allow from 192.168.18.0/24 to any port 3000 proto tcp`.
- `config/openwebui.env` solo vale para el **primer** arranque: luego todo se cambia en Ajustes › Administración.
- Tras cada respuesta Open WebUI solo genera el título del chat: las etiquetas y las sugerencias de seguimiento
  están apagadas (Administración › Interfaz) porque ocupaban la gráfica 4–9 s más por mensaje.
- Imagen: en el chat, el botón de imagen usa `flux2-klein`; se cambia a `sdxl` o `flux1-schnell` en
  Administración › Imágenes.

## Imagen desde el chat

Elige **Imagen · FLUX.2 klein** (26–30 s, el recomendado), **Imagen · SDXL** (~80 s) o **Imagen · FLUX.1 schnell**
(~150 s) y escribe lo que quieres. "vertical"/"retrato"/"móvil" da 768×1344; "horizontal"/"paisaje"/"fondo de
pantalla" da 1344×768; si no, 1024×1024. Para SDXL y schnell, gemma4 traduce antes al inglés. Cada imagen se guarda
también en `salidas/imagenes/` en PNG (`openwebui/funciones/imagen.py`).

## Modos (asistentes especializados)

Cada modo es un modelo de Open WebUI (modelo base + prompt de sistema + herramientas) definido en
`openwebui/modos/<id>.md`: cabecera `--- … ---` (`id`, `nombre`, `base`, `descripcion`, `herramientas`, `temperatura`,
`contexto`, `pensar: no`, `sugerencias` separadas por `|`, `color: #rrggbb` y opcional `grupo`) y debajo el prompt. Las herramientas (código Python que el
modelo llama) están en `openwebui/herramientas/`. Tras editar cualquiera de los dos, con Open WebUI en marcha:

```
openwebui/.venv/bin/python scripts/avatares-modos.py   # avatar de cada modo (assets/modos/<id>.png), si cambia
scripts/instalar-modos.py      # crea o sobrescribe modos, herramientas y carpetas
```

Cada modo tiene **su carpeta en el lateral** (con su emoji; los críticos juntos en «Críticos»): un chat nuevo dentro
de la carpeta empieza ya con ese modo y se guarda ahí, así no se mezclan los chats de un modo con los de otro.

Los modos no cargan las herramientas integradas de Open WebUI (memoria, notas…), para que el modelo solo vea las
suyas. El filtro global `openwebui/funciones/herramientas_modo.py` (lo instala el mismo script) vuelve a activar las
herramientas del modo en cada mensaje: la interfaz solo las manda en el primero del chat.

| Modo | Base | Qué hace |
|---|---|---|
| 🎸 Compositor | Qwen3.6 35B-A3B, sin pensar | Acordes, progresiones, rasgueos, escalas, círculo de quintas, letras; guitarra, piano, ukelele, bajo |
| ✍️ Escritor | Qwen3.6 35B-A3B, sin pensar | Novela y relato: estructura, fichas de personajes, mundo, capítulos, revisión; guarda cada libro |
| 🌻 Crítico optimista | Qwen3.6 35B-A3B, sin pensar | Lo mejor de tu obra y cómo crecer, en positivo |
| ⚖️ Crítico constructivo | Qwen3.6 35B-A3B, sin pensar | Aciertos, problemas, cambios por orden de impacto y nota de 1 a 10 |
| 🥀 Crítico implacable (Ego) | Qwen3.6 35B-A3B, sin pensar | Duro y exigente, al estilo de Anton Ego, pero cada defecto con lo que haría falta para arreglarlo |

**Compositor.** Las notas y digitaciones salen de la herramienta *Teoría musical*
(`openwebui/herramientas/teoria_musical.py`, autocomprobación: `python3 -I openwebui/herramientas/teoria_musical.py`):
escalas, acordes (inversiones de piano, formas abiertas y de cejilla de guitarra y ukelele, desglose cuerda a
cuerda), acordes de una tonalidad con progresiones, círculo de quintas, transposición/capo y mapa del mástil.
Medido con el 35B sin pensar: 1–2 min por respuesta con herramientas (+25 s la primera vez, al cargarlo), digitaciones
y diagramas copiados bien. En una prueba anterior (antes de afinar la herramienta) qwen3.5:9b sin pensar copiaba mal
las digitaciones; con `pensar: si` acertaba más pero tardaba lo mismo. Para cambiarlo, `base:` en `compositor.md`.
Límites: el dedo que va en cada traste y el razonamiento armónico (qué escala va sobre qué) son del modelo, no de la
herramienta, y pueden fallar.

**Escritor.** La herramienta *Libro* (`openwebui/herramientas/libro.py`, autocomprobación:
`python3 -I openwebui/herramientas/libro.py`) guarda cada libro en `salidas/libros/<libro>/` como Markdown:
`personajes/`, `capitulos/` y `notas/` (mundo, trama, estilo…). Así se sigue el libro en otro chat: el modo lee el
índice y las fichas antes de escribir y guarda lo que apruebes. Al reemplazar algo, la versión anterior queda en
`.anteriores/` de esa carpeta; los capítulos se guardan por partes (cada parte se añade al final). Medido: 15–50 s
por respuesta (escena de 300 palabras leyendo índice y ficha). Límites: lee como mucho los últimos 12.000 caracteres
de un texto (el contexto es de 16k tokens), así que no reemplaza un capítulo más largo (solo lo continúa); para
reescribirlo, guárdalo con otro nombre. El contenido de las fichas lo escribe el modelo y puede equivocarse (revísalas).

**Críticos.** Los tres critican textos, ideas y descripciones de obras citando frases concretas; pueden leer
(nunca guardar) los libros del Escritor con la herramienta *Libro* («lee el capítulo 1 de mi libro X»). Medido: 30–60 s
por crítica. Límites: no ven imágenes (el 35B no tiene visión; descríbela con palabras) y al hablar de rima y métrica
aún se equivocan a veces (p. ej. llaman consonante a una rima asonante).

## Vídeo desde el chat

En Open WebUI, elige el modelo **Vídeo (Wan 2.2)** y escribe lo que quieres ver, en español ("un perro corriendo
por la playa al atardecer, de 3 segundos"; máximo 5). La función (`openwebui/funciones/video.py`, instalada en
Administración › Funciones) pasa el texto a un prompt en inglés con gemma4, libera la gráfica, arranca ComfyUI si
hace falta y deja el vídeo en el chat. Unos 5 minutos por cada 2 s de vídeo. Pasos y duración por defecto, en los
ajustes (válvulas) de la función.

## ComfyUI (vídeo)

`./srfrijol video` descarga lo que ocupe la gráfica (llama-swap y Ollama) y arranca ComfyUI con `--lowvram --disable-smart-memory` (sin eso el VAE no cabe al decodificar). La plantilla
`workflows/wan22-texto-a-video.json` (Wan 2.2 TI2V 5B, 640×352, 49 fotogramas ≈ 2 s a 24 fps) se carga en ComfyUI
arrastrándola, o desde la terminal:

```
scripts/video.sh "a paper boat on a calm lake at sunset" [pasos=20] [fotogramas=49]
```

La RX 6600 XT (gfx1032) no tiene soporte oficial de ROCm; va con `HSA_OVERRIDE_GFX_VERSION=10.3.0` y PyTorch con
ROCm 6.3 (con 6.4.3 y posteriores hay casos de cuelgues en esta tarjeta). Mientras ComfyUI tenga un vídeo en la
gráfica, no pidas imágenes ni el 35B en Open WebUI: no caben a la vez.

## Medido en este equipo (escritorio abierto, ~4 GB de VRAM ocupados por él)

| Modelo | Resultado |
|---|---|
| gemma4:e4b | 88 t/s generando |
| qwen3.5:9b | 32,6 t/s generando, 156 t/s leyendo |
| Qwen3.6-35B-A3B | 16–18 t/s generando, ~310 t/s leyendo (lote 2048); 6–11 s de carga si está en la caché de disco, ~25 s si no; se queda cargado 30 min |
| FLUX.2 klein 1024² 4 pasos | 26 s (35 s pedida desde Open WebUI con la carga) |
| FLUX.2 klein 704×1024 + 1 referencia (modo Compositor de imágenes) | 30–32 s con `--flash-attn on` (36 s sin él; 53 s sin `--offload-to-cpu`) |
| SDXL 1024² 25 pasos q8_0 | 76 s con `--flash-attn on` (82 s sin él) |
| FLUX.1 schnell 1024² 4 pasos | 57 s con `--flash-attn on` y el escritorio ligero (147 s antes, con ~4 GB de VRAM ocupados) |
| Kokoro | 4,5 s de voz en 1,3 s |
| whisper small (CPU) | 3,7 s para 4,5 s de audio, con arranque |
| Wan 2.2 TI2V 5B, 640×352, 49 fotogramas (2 s), 20 pasos | 4,6 min (10 s por paso) |

## Carpetas

`bin/` binarios (llama.cpp b12428 Vulkan, stable-diffusion.cpp master-1104 Vulkan, llama-swap v273) ·
`config/` · `models/` · `openwebui/` (entorno y datos) · `kokoro/` · `comfyui/` · `scripts/` · `logs/`
