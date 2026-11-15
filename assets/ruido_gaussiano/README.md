# Imágenes con ruido gaussiano conservadas

Se conserva el par exacto usado para evaluar SD 1.5 sin ControlNet. Las cuatro
intensidades procesaron **una misma imagen ruidosa**, no cuatro degradaciones.
Las copias PNG de Colab pueden tener otra codificación y hash de archivo, pero
se verificó que sus píxeles RGB coinciden con los de este par.

## Catálogo

| Archivo | Función | Fuente | Dimensiones y modo | Ruido añadido | Registro |
| --- | --- | --- | --- | --- | --- |
| [referencia_preparada.png](potw1803a_sigma0.03_seed123_size256/referencia_preparada.png) | Referencia anterior al ruido artificial; puede contener ruido propio de la publicación | `potw1803a.tif`, ESA/Hubble | 256 × 192, RGB, 8 bits por canal | Ninguno en esta copia | [Experimento original](potw1803a_sigma0.03_seed123_size256/experimento.json) |
| [entrada_ruidosa.png](potw1803a_sigma0.03_seed123_size256/entrada_ruidosa.png) | Entrada común para comparar SD 1.5 y SD 1.5 + ControlNet Tile | Referencia conservada de `potw1803a.tif` | 256 × 192, RGB, 8 bits por canal | Gaussiano aditivo, media 0, sigma 0,03, semilla 123 | [Metadata completa de reproducción](potw1803a_sigma0.03_seed123_size256/reproduccion.json) |

## Parámetros de reproducción de la imagen ruidosa

| Parámetro | Valor |
| --- | --- |
| Original | `potw1803a.tif`, TIFF RGB, 933 × 700 |
| SHA-256 del TIFF | `9bc563fef8171c749cc455ad9b0b140652cd26c28187eff4983686bf74f147a2` |
| Fuente | https://esahubble.org/images/potw1803a/ |
| Descarga del original | https://esahubble.org/media/archives/images/original/potw1803a.tif |
| Crédito | NASA, ESA, and J. Comerford (University of Colorado-Boulder) |
| Licencia | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), según las [condiciones de ESA/Hubble](https://esahubble.org/copyright/) |
| Orientación y conversión | `ImageOps.exif_transpose`, seguido de `convert('RGB')` |
| Redimensionamiento | LANCZOS, lado máximo 256; sin recorte ni ampliación |
| Escala espacial | `min(1, 256 / max(ancho, alto))` |
| Ajuste de dimensiones | Cada lado: `int(lado_original * escala) // 8 * 8`; resultado 256 × 192 |
| Momento del ruido | Después de preparar y redimensionar la imagen |
| Espacio de trabajo | RGB publicado, sin linealizar ni calibrar el sensor |
| Tipo y normalización | `float64`, valores RGB divididos por 255; escala [0, 1] |
| Distribución | Normal aditiva, media teórica 0, sigma 0,03; varianza 0,0009 |
| Sigma en escala 0–255 | 7,65 niveles antes del recorte |
| Semilla del ruido | 123; independiente de la semilla del modelo de difusión |
| Generador | `np.random.Generator(np.random.PCG64(123))` |
| Muestreo | `rng.normal(loc=0.0, scale=0.03, size=(192, 256, 3))` |
| Independencia y orden | Una muestra por píxel y canal; arreglo alto × ancho × RGB, orden C |
| Suma y recorte | Sumar al RGB normalizado y aplicar `np.clip(suma, 0.0, 1.0)` |
| Cuantización | `np.rint(recorte * 255.0).astype(np.uint8)`; redondeo al entero más cercano, empate al par |
| Fracción de muestras RGB recortadas abajo | 0,13201904296875 |
| Fracción de muestras RGB recortadas arriba | 0,000047471788194444445 |
| Entorno de preparación y verificación local | Python 3.12.10, NumPy 2.5.4, Pillow 12.3.0; zlib 1.3.1 en la verificación |
| Codificación PNG | `compress_level=6`, `optimize=False`, sin metadata PNG adicional |
| SHA-256 PNG de referencia | `71482fdf9473d832f5e2effb3873c8987e441874798df65e9f48f7ef5ad5818e` |
| SHA-256 píxeles RGB de referencia | `b0d98f57e859779a4c9a04cda147729d1c19bd571e6bc2f716f0847ed09cb642` |
| SHA-256 PNG de entrada ruidosa | `cc4ee54d8e6247933e2c9c9afd8310e27820fbcd534a9a821b4b691018b92c58` |
| SHA-256 píxeles RGB de entrada ruidosa | `3139866480700bd5dd0e67055636173dc0a689063700993683b1e116a6496434` |
| Algoritmos y registro | `src/diffusion.py::prepare_image`, `src/noise.py::add_gaussian_noise`, `src/noise_assets.py`; hashes de código en `reproduccion.json` |

Los hashes de píxeles corresponden a `image.tobytes()` en RGB, sin cabeceras.
Para reproducirlos no hace falta descargar de nuevo el TIFF: basta con la
referencia preparada conservada, el registro y las versiones indicadas.
Los parámetros de SD —intensidad, pasos y semilla IA— no intervienen en la
creación de esta imagen ruidosa. Se registran por separado en cada restauración.

Desde la raíz, para regenerar y verificar sin sobrescribir el activo:

```powershell
uv run --locked python -m src.noise_assets reproduce --metadata assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256/reproduccion.json --output outputs/reproduccion_gaussiana/entrada_ruidosa.png
```

El comando exige el mismo hash de píxeles antes de guardar e informa si el PNG
también coincide byte a byte. Los bytes PNG pueden variar entre codificadores
o versiones de compresión sin que cambien los píxeles.

Para reconstruir la preparación desde el TIFF original, verificar su hash y
usar `src.experiment prepare` con sigma 0,03, semilla 123 y tamaño máximo 256
en una carpeta nueva. La procedencia debe acompañar a la nueva preparación.

## Límites y atribución

El recorte cerca de negro y blanco modifica la distribución gaussiana final.
Esta degradación sintética sobre RGB publicado no simula de forma calibrada
el ruido de adquisición de una cámara astronómica.

Al compartir estas imágenes, conservar el crédito, la fuente y la licencia,
e indicar conversión a RGB, reducción LANCZOS y adición de ruido en la copia.
Las salidas futuras de difusión deben identificarse además como generativas.
La referencia solo es un objetivo del ensayo; no garantiza autenticidad científica.
