# Experimentos, métricas y evidencias técnicas

Este documento conserva los comandos y resultados experimentales trasladados del README. No es el recorrido de la interfaz de Julia. Los ensayos describen versiones y sesiones concretas; los archivos de outputs/ son locales y no se descargan al clonar. La evidencia pública está en assets/ejemplos/etapa3_tile/. Ninguno de los ensayos registrados demostró una restauración mejor que conservar la entrada ruidosa.

## Preparación y ensayos reproducibles

### Paso 2 de etapa 3: ensayo gaussiano

Se conserva el par de referencia y ruido para comparar variantes de difusión sobre los mismos datos. La siguiente variante preparada incorpora ControlNet Tile.

### Imágenes gaussianas conservadas y metadata

Las imágenes del ensayo se guardan en **`assets/ruido_gaussiano/`**, fuera de `outputs/`. Esta carpeta no está ignorada por Git y permite conservar los PNG con el proyecto cuando se publiquen los cambios. Las cuatro intensidades del primer barrido comparten una única copia ruidosa, por lo que no se duplican los mismos datos.

El conjunto ya incluye los seis ejemplos con sigma 0,03, semilla 123 y lado máximo 256: [catálogo y conversiones](../assets/ruido_gaussiano/README.md). Cada carpeta conserva referencia, entrada ruidosa y registros verificables. Las cinco nuevas entradas están preparadas para probar; todavía no tienen una restauración evaluada. Para subirlas a la app se utiliza `entrada_ruidosa.png`. El TIFF de `heic1702a` necesitó una copia RGB de 8 bits previa, con pérdida de precisión tonal documentada y sin modificar el original.

| Imagen conservada | Referencia y preparación | Dimensiones | Media y sigma añadidas | Semilla y generador | Metadata de reproducción |
| --- | --- | --- | --- | --- | --- |
| [Referencia preparada](../assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256/referencia_preparada.png) | `potw1803a.tif`, RGB de 8 bits, LANCZOS; lado máximo 256, lados múltiplos de 8, sin recorte ni ampliación | 256 × 192 | Sin ruido artificial añadido | No corresponde | [Experimento](../assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256/experimento.json) |
| [Entrada con ruido gaussiano](../assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256/entrada_ruidosa.png) | La referencia de la fila anterior; ruido agregado después del redimensionamiento | 256 × 192, RGB de 8 bits | Media 0; sigma 0,03 en [0, 1], equivalente a 7,65 niveles antes del recorte | 123; NumPy `Generator(PCG64(123))`, independiente por píxel y canal | [Todos los parámetros y hashes](../assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256/reproduccion.json) |

| Parámetro común necesario para reproducir el ruido | Valor |
| --- | --- |
| Fuente y original | [ESA/Hubble potw1803a](https://esahubble.org/images/potw1803a/), `potw1803a.tif`, TIFF RGB de 933 × 700 |
| Crédito y licencia | NASA, ESA, and J. Comerford (University of Colorado-Boulder); [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) según [ESA/Hubble](https://esahubble.org/copyright/) |
| Orientación y conversión | `ImageOps.exif_transpose` y `convert('RGB')` |
| Escala y tamaño | `escala=min(1,256/max(ancho,alto))`; cada lado `int(lado_original*escala)//8*8`; LANCZOS |
| Arreglo y color | Alto × ancho × RGB, orden C; `float64 / 255`, sin linealización ni normalización por imagen |
| Distribución y muestreo | Normal aditiva N(0; 0,03²); `rng.normal(0.0, 0.03, size=(192,256,3))`; semilla 123, PCG64 |
| Recorte y cuantización | `np.rint(np.clip(referencia_normalizada+ruido,0,1)*255).astype(np.uint8)`; empate al par |
| Recorte inferior / superior observado | 0,13201904296875 / 0,000047471788194444445 de las muestras RGB |
| Versiones | Python 3.12.10, NumPy 2.5.4, Pillow 12.3.0; zlib 1.3.1 en la verificación local |
| Archivo final | PNG, compresión 6, `optimize=False`, sin metadata PNG adicional |
| SHA-256 del original | `9bc563fef8171c749cc455ad9b0b140652cd26c28187eff4983686bf74f147a2` |
| SHA-256 del PNG de referencia | `71482fdf9473d832f5e2effb3873c8987e441874798df65e9f48f7ef5ad5818e` |
| SHA-256 del PNG ruidoso | `cc4ee54d8e6247933e2c9c9afd8310e27820fbcd534a9a821b4b691018b92c58` |
| SHA-256 de píxeles RGB del ruido | `3139866480700bd5dd0e67055636173dc0a689063700993683b1e116a6496434` |

El [catálogo detallado](../assets/ruido_gaussiano/README.md) incluye también el hash de píxeles de la referencia, atribución y algoritmo completo. Para reproducir el ruido no se necesita difusión ni el TIFF: se utiliza la referencia preparada conservada. Se verificó reproducción idéntica tanto en píxeles como en bytes PNG en el entorno local. En otro codificador, los píxeles pueden coincidir aunque cambien los bytes PNG.

```powershell
uv run --locked python -m src.noise_assets reproduce --metadata assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256/reproduccion.json --output outputs/reproduccion_gaussiana/nueva_entrada_ruidosa.png
```

La salida debe ser nueva. El original y los activos no se sobrescriben. Intensidad, pasos y semilla del modelo no intervienen en la generación del ruido y se registran por separado en cada restauración.

### SD 1.5 + ControlNet Tile — ejecutado y evaluado en un caso

El primer barrido evaluó **SD 1.5 img2img sin ControlNet**. Posteriormente se ejecutó la variante Tile en Colab y la autora compartió `ensayo_controlnet_tile.zip`. La revisión confirmó los hashes de entrada y salida, recalculó las métricas y comparó con el ensayo anterior. El ZIP registra código de la revisión `e4c6ba6121feafa362d9d8ab9a98e247e9177ab8`; los hashes de ocho archivos de código y dependencias coinciden con esa revisión. La variante está implementada en `src/diffusion.py` y conectada con `src.experiment restore` y `sweep`.

Se mantienen sigma 0,03, semilla de ruido 123, referencia de 256 × 192, 30 pasos configurados, semilla del modelo 42, DDIM, guidance 1 e intensidades **0,10 / 0,15 / 0,20 / 0,25**. ControlNet usa fuerza **1,0**, inicio **0**, fin **1** y `guess_mode=False`. La condición es la misma imagen ruidosa, sin prefiltrado ni redimensionamiento adicional; la referencia se usa exclusivamente para evaluar. No se realiza superresolución ni entrenamiento. Estos valores son un punto inicial para comparar, sin eficacia validada.

**Resultados verificados de Tile**, calculados contra la misma referencia sintética:

- Entrada ruidosa: PSNR **31,2381 dB**, SSIM **0,637538**.
- Tile 0,10: PSNR **28,4258 dB**, SSIM **0,552753**. Frente a SD sin Tile a 0,10: **+0,3356 dB** y **+0,008634** de SSIM. Frente a la entrada ruidosa: **−2,8123 dB** y **−0,084784** de SSIM.
- Tile 0,15: PSNR **27,6885 dB**, SSIM **0,533936**. Frente a SD sin Tile a 0,15: **+0,4586 dB** y **+0,011346** de SSIM. Frente a la entrada ruidosa: **−3,5495 dB** y **−0,103602** de SSIM.
- Tile 0,20 y 0,25: salidas bloqueadas por el filtro de seguridad; sin imágenes válidas ni métricas. Sin Tile, solo 0,25 había quedado bloqueada en este barrido.

**Interpretación:** Tile 0,10 es la más cercana a la referencia entre las salidas de difusión probadas, pero su MSE sigue siendo **1,91 veces** el de la entrada ruidosa. Tile mejora ligeramente las dos métricas frente a SD sin Tile también en los cuatro recortes, pero sigue por debajo de la entrada ruidosa en todos ellos. La inspección muestra cambios de textura de fondo, contorno y brillo en las galaxias y alargamiento de la fuente puntual. No se acredita reducción de ruido con conservación de señal en estas condiciones ni se atribuye autenticidad científica a las estructuras. La comparación abarca una imagen, una fuerza de control y unas semillas; no constituye una validación general ni una comparación estadística de modelos.

Las métricas recalculadas coinciden con las del ZIP dentro de una tolerancia absoluta de 1e−12; los PNG de entrada coinciden con los activos y sus píxeles con los del ensayo sin Tile. El ZIP registra CUDA y `torch.float16`; no incluye el nombre concreto de la GPU, por lo que no se atribuye un hardware idéntico entre sesiones. Los estados históricos «evaluación pendiente» de los registros originales se preservan y la revisión se guarda por separado.

Evidencias locales: [revisión y diferencias de métricas](../outputs/etapa3/controlnet_tile_colab_20261115T033837Z/revision_local/comparacion.json) y [recortes comparativos SD/Tile](../outputs/etapa3/controlnet_tile_colab_20261115T033837Z/revision_local/comparacion_sd_tile_regiones.png). La carpeta conserva el ZIP original y sus archivos extraídos, sin ejecutar contenido del archivo adjunto. SHA-256 del ZIP: `61b7be1b422a5add57821de5d57d6d515b2d6e4df55de0459b8f2bd325102697`.

En una sesión CUDA con los archivos del proyecto:

```powershell
uv run --locked python -m src.experiment sweep --experiment-dir assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256 --output-dir outputs/etapa3/controlnet_tile --controlnet-tile --controlnet-scale 1.0 --device cuda
uv run --locked python -m src.evaluation --sweep-dir outputs/etapa3/controlnet_tile --output-dir outputs/etapa3/controlnet_tile/evaluacion --regions-potw1803a
```

El barrido verifica los hashes y copia las mismas entradas a una carpeta nueva. Guarda cada salida y sus parámetros por separado, con identificador y revisión del modelo base y de Tile, hash de la condición, fuerza y período de control. Si el filtro de seguridad bloquea una salida, registra ese caso y continúa con las otras intensidades sin asignarle métricas. Un error distinto —por ejemplo falta de memoria— interrumpe el barrido y conserva el registro parcial. No se cambia automáticamente de CUDA a CPU.

**Ejecución en Colab desde el navegador, con el proyecto publicado en GitHub:**

1. Abrir el [notebook de ControlNet Tile en Colab](https://colab.research.google.com/github/Sabri-Nang/astro-restauracion/blob/main/colab/experimento_controlnet_tile.ipynb).
2. Seleccionar GPU T4 si está disponible e interrumpir otros servidores antes de utilizar la GPU.
3. Ejecutar las celdas en orden dejando `ORIGEN = 'github'`. El notebook clona `main` en una carpeta nueva, comprueba los archivos necesarios, registra la revisión Git y hashes del código y los activos, instala uv y Python 3.12 con el bloqueo y exige CUDA. Los PNG gaussianos se obtienen del repositorio; no hace falta subir el TIFF ni un ZIP.
4. Revisar referencia y ruido; ejecutar el barrido Tile. Solo esa celda carga y descarga los modelos. La primera carga puede ser lenta y requiere más memoria y descarga que SD sin ControlNet.
5. Ejecutar la evaluación y revisar los recortes. El notebook muestra también la evaluación previa cuando está incluida y verifica que usa la misma referencia y entrada. Descargar el ZIP final antes de cerrar Colab.

**Alternativa para cambios aún no publicados:** desde la raíz, ejecutar `uv run --locked python colab/preparar_controlnet.py`. Genera `outputs/controlnet_tile_colab.zip` y actualiza el hash esperado del notebook. El paquete incluye solo código, dependencias bloqueadas, activos gaussianos públicos y, si está disponible localmente, la evaluación previa de SD 1.5; no incluye tokens, entornos ni pesos. Subir a Colab la copia local del notebook, cambiar a `ORIGEN = 'paquete_local'` y subir el ZIP cuando lo solicite. Se verifica su SHA-256 y el de cada archivo. El selector `google.colab.files.upload()` de esta alternativa está dirigido al navegador de Colab.

La preparación local comprueba la sintaxis de todas las celdas; no sustituye una ejecución completa con GPU. La aplicación actual de `app.py` integra SD 1.5 + Tile. El laboratorio técnico conserva su recorrido independiente; los comandos de esta sección permiten repetir el ensayo por consola o notebook.

### Controles de sigma cero y VAE — ejecutados y revisados

**Estado:** cinco controles reales ejecutados en Colab y revisados localmente; resultados y límites registrados a continuación.

El VAE codifica la imagen en una representación latente comprimida y la decodifica de nuevo. En SD img2img, la codificación habitual muestrea el posterior; por eso se comparan tanto un control determinista con su moda como uno con muestreo y semilla 42. Se utilizan la misma revisión, precisión y preprocesamiento del pipeline, con su escalado latente y filtro de seguridad. El pipeline completo se carga para reutilizar componentes, pero los controles VAE no ejecutan UNet, scheduler ni ControlNet. [Documentación de AutoencoderKL](https://huggingface.co/docs/diffusers/en/api/models/autoencoderkl).

Controles ejecutados sobre el par conservado:

1. Referencia contra sí misma y entrada gaussiana contra la referencia: puntos de partida sin procesamiento IA.
2. Referencia → VAE usando la moda del posterior, sin muestreo.
3. Referencia → VAE usando muestreo posterior con semilla 42.
4. Entrada gaussiana de sigma 0,03 → VAE usando muestreo posterior con semilla 42.
5. Referencia sin ruido añadido → SD 1.5 sin Tile, intensidad 0,10, 30 pasos configurados y semilla 42.
6. Misma entrada sigma cero → SD 1.5 + Tile, con los mismos parámetros y fuerza de control 1,0.

**Sigma cero no significa fotografía sin ruido real ni intensidad cero:** la referencia publicada puede tener ruido propio y procesamiento previo. En ambos controles de difusión se conserva `strength=0.1`, equivalente a tres pasos efectivos de DDIM con 30 pasos configurados. En Tile sigma cero, la referencia preparada es explícitamente la propia entrada y condición; el registro lo identifica para no confundirlo con restaurar la copia ruidosa usando una guía limpia externa.

```powershell
uv run --locked python -m src.diagnostics --asset-dir assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256 --output-dir outputs/etapa3/controles_sigma0_vae --device cuda
```

La carpeta debe ser nueva. Se verifican hashes, se conserva cada entrada y se guardan salidas, PSNR, SSIM y recortes contra la referencia y, cuando corresponde, también métricas contra la propia entrada del control. Los bloqueos se registran sin imagen ni métricas; otros errores conservan el registro parcial. La identidad tiene PSNR infinito, representado en JSON mediante `psnr_db=null` y `psnr_infinito=true`.

Para ejecutar en Colab, abrir el [notebook de controles VAE y sigma cero](https://colab.research.google.com/github/Sabri-Nang/astro-restauracion/blob/main/colab/controles_sigma0_vae.ipynb), seleccionar GPU T4 si está disponible e interrumpir otros servidores. Ejecutar las celdas en orden y descargar `controles_sigma0_vae.zip` al terminar. Se clona el código publicado y se registra la revisión Git y hashes; si existe una caché del ensayo Tile en esa misma sesión, se reutiliza sin copiar ni versionar pesos. CUDA es explícita y no se cambia automáticamente a CPU.

**Resultados sobre la referencia sin ruido artificial añadido**, siempre comparados contra esa referencia:

- Identidad: MSE **0**, PSNR infinito y SSIM **1**.
- VAE con moda: PSNR **32,2794 dB**, SSIM **0,773996**.
- VAE con muestreo y semilla 42: PSNR **32,2792 dB**, SSIM **0,774010**.
- SD sin Tile, intensidad 0,10: PSNR **29,9498 dB**, SSIM **0,727774**.
- SD + Tile, intensidad 0,10: PSNR **30,3092 dB**, SSIM **0,733375**.

El VAE altera la representación aun sin ejecutar difusión. Moda y muestreo son casi iguales en este caso y semilla, sin probar que ocurra en otros casos. SD y Tile aplicados a sigma cero quedan más lejos de la referencia que la reconstrucción VAE sola, según ambas métricas.

**Comparación sobre la misma entrada ruidosa de sigma 0,03**, con métricas contra la referencia preparada:

- Conservar la entrada ruidosa: PSNR **31,2381 dB**, SSIM **0,637538**.
- VAE con muestreo, sin difusión: PSNR **30,0305 dB**, SSIM **0,595138**.
- SD sin Tile, intensidad 0,10, ensayo anterior: PSNR **28,0902 dB**, SSIM **0,544119**.
- SD + Tile, intensidad 0,10, ensayo anterior: PSNR **28,4258 dB**, SSIM **0,552753**.

El MSE de VAE sobre la entrada ruidosa es **1,32 veces** el de conservar la entrada. Por lo tanto, parte del deterioro ya se observa en codificación/decodificación VAE, antes de la UNet. Las salidas completas de difusión quedan aún más alejadas de la referencia en los ensayos observados. No se debe interpretar el PSNR de VAE sobre sigma cero como una mejora de denoising frente a una entrada distinta con sigma 0,03.

**Inspección y límites:** las ampliaciones muestran suavizado y modificación de estructuras finas en VAE y cambios adicionales de contorno, brillo y textura al ejecutar difusión. Los errores de estos procesos no lineales no son aditivos: no se pueden restar sus MSE ni asignar porcentajes causales exactos al VAE o a la difusión. Tampoco se demuestra que toda configuración o modelo basado en VAE falle en restauración. Este diagnóstico corresponde a una imagen de 256 × 192, unas semillas y una precisión concretas; la referencia publicada puede tener ruido propio y no verifica autenticidad científica. Estos controles son complementarios al cierre obligatorio de etapa 3 con análisis visual e informe para Julia.

Evidencias locales: [revisión recalculada](../outputs/etapa3/controles_sigma0_vae_colab_20261115T041012Z/revision_local/revision.json), [recortes de VAE](../outputs/etapa3/controles_sigma0_vae_colab_20261115T041012Z/revision_local/comparacion_vae_regiones.png) y [recortes de difusión con sigma cero](../outputs/etapa3/controles_sigma0_vae_colab_20261115T041012Z/revision_local/comparacion_sigma0_regiones.png). Se preserva el ZIP original y los registros históricos de interpretación pendiente. SHA-256 del ZIP: `9d45e3b43fa8e4bcf6451c683ca46370dd57b9924c876e8b43fc687b41ddc692`.

### Preparación inicial del ensayo gaussiano

Abrir el [notebook de ruido gaussiano](../colab/experimento_ruido_gaussiano.ipynb). Mantiene dos fases separadas: primero genera y muestra la referencia y la entrada ruidosa sin IA; después permite ejecutar difusión expresamente. El notebook inicial conserva su recorrido fijo; para otras imágenes y control interactivo se agregó el laboratorio separado descrito a continuación. La preparación y las pruebas son livianas; la inferencia se reserva para Colab con CUDA.

Para preparar el mismo ensayo desde la raíz, sin descargar ni cargar modelos:

```powershell
uv run --locked python -m src.experiment prepare --input assets/ejemplos/originales/potw1803a.tif --output-dir outputs/etapa3/gaussiano_sigma0.03_seed123_size256 --sigma 0.03 --noise-seed 123 --size 256
```

La carpeta debe ser nueva: no se sobrescriben ensayos. Se guardan `referencia_preparada.png`, `entrada_ruidosa.png`, `comparacion_referencia_ruido.png`, `diferencias_referencia_ruido.png` y `experimento.json`. Este último identifica fuente, hashes, dimensiones, versiones, generador y recorte. `--provenance ruta.json` permite registrar fuente, crédito y licencia declarados; el notebook ya los incluye para `potw1803a.tif`.

Se suma una muestra gaussiana independiente por píxel y canal en RGB normalizado a [0, 1], con media 0 y sigma 0,03 (7,65 niveles en 8 bits antes del recorte). Se usa PCG64 con semilla de ruido 123. El ruido se agrega después de preparar el tamaño, se recorta a [0, 1] y se redondea a 8 bits. Se registran por separado las fracciones de muestras RGB recortadas por debajo de cero y por encima de uno. Cerca de negro y blanco, esa operación altera la distribución y puede introducir sesgo. La simulación se aplica sobre RGB publicado, sin linealización ni calibración física de electrones o ADC. La [documentación de NumPy](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.normal.html) define `scale` como la desviación estándar.

Inspeccionar primero el grano del fondo, estrellas tenues y estructuras difusas. Para ensayar otro nivel, cambiar solo sigma y la carpeta de salida, manteniendo semilla y tamaño. La referencia solo define el objetivo de esta degradación; no se supone libre de ruido original.

Después de inspeccionar, el comando de restauración para una sesión CUDA es:

```powershell
uv run --locked python -m src.experiment restore --experiment-dir outputs/etapa3/gaussiano_sigma0.03_seed123_size256 --output-dir outputs/etapa3/gaussiano_sigma0.03_seed123_size256/difusion_strength0.2_steps30_seed42 --strength 0.2 --steps 30 --model-seed 42 --device cuda
```

En el notebook, la celda de difusión está desactivada por defecto mediante `EJECUTAR_DIFUSION = False`; activarla solo después de inspeccionar el ruido. Verifica CUDA y utiliza intensidad 0,2, 30 pasos configurados y semilla del modelo 42, independiente de la semilla del ruido: seis pasos efectivos con nuestro DDIM. Son parámetros iniciales de exploración, sin eficacia validada. Antes de inferir se verifican hashes de referencia y ruido; la entrada preparada por el pipeline debe coincidir píxel a píxel con la ruidosa guardada.

La restauración guarda `salida.png`, `comparacion_triple.png`, dos mapas y `resultado.json` con el registro original y los parámetros del modelo. El mapa **ruido–salida** muestra modificaciones del modelo; **referencia–salida** muestra diferencias frente al objetivo sintético. Ninguno determina autenticidad. No se calculan métricas automáticamente.

**Verificación realizada:** se generó localmente el par de `potw1803a.tif` a 256 × 192 y se inspeccionó su comparación. Posteriormente se probaron cuatro intensidades por la API del laboratorio de Colab, con tres salidas válidas y una bloqueada, como se detalla a continuación. El original y sus créditos se conservan; las nuevas derivadas se documentan en el [registro de ejemplos](../assets/ejemplos/README.md). Las pruebas automatizadas cubren reproducibilidad, sigma cero, estadística en una imagen sintética uniforme, recorte, preservación del original y rechazo de entradas modificadas, además de una restauración simulada. Esas pruebas automatizadas no son resultados de denoising.

### Barrido inicial de intensidades — ejecutado y evaluado en un caso

Se probaron intensidades **0,10 / 0,15 / 0,20 / 0,25** sobre `potw1803a.tif` mediante una sesión independiente de la API del laboratorio Gradio alojado en Colab. Se mantuvieron fijos sigma 0,03, semilla de ruido 123, referencia RGB de 256 × 192 (lado máximo 256), semilla del modelo 42, 30 pasos configurados, scheduler DDIM, `guidance_scale=1` y el prompt `astronomical photograph, stars and galaxies`. Se usó la revisión de SD 1.5 fijada en `src/diffusion.py`. No se entrenó el modelo.

- **0,10:** salida válida, 3 pasos efectivos, 0,308 s de inferencia registrados.
- **0,15:** salida válida, 4 pasos efectivos, 0,355 s de inferencia registrados.
- **0,20:** salida válida, 6 pasos efectivos, 0,440 s de inferencia registrados.
- **0,25:** el pipeline informó «El filtro de seguridad bloqueó la salida; no se guardó como prueba válida». No hay salida descargada ni tiempo de inferencia registrado para ese caso; se preveían 7 pasos efectivos.

Las tres salidas válidas registran `cuda:0`, `torch.float16`, Python 3.12.3, PyTorch 2.15.0, Diffusers 0.42.1 y Transformers 5.22.2. Los tiempos son los informados por esa ejecución y no incluyen toda la transferencia de archivos; no son un benchmark general. La API no expone la revisión Git del servidor y no se le atribuye la revisión local.

Antes de inferir se verificó que referencia y ruido remotos coinciden píxel a píxel con la preparación local. Las tres inferencias válidas registran el mismo SHA-256 de entrada del modelo y sus archivos descargados se verificaron contra los hashes de salida. El bloqueo de 0,25 proviene del clasificador de contenido del pipeline; el registro no expone conceptos ni puntuaciones, por lo que no permite determinar su causa visual ni confirmar un falso positivo. No se modificó el filtro ni las condiciones acordadas.

Evidencias locales, excluidas de Git: [registro del barrido](../outputs/etapa3/barrido_potw1803a_20261115T023534122516Z/barrido.json), [comparación de las cinco vistas disponibles](../outputs/etapa3/barrido_potw1803a_20261115T023534122516Z/comparacion_cinco_vistas.png) y [ZIP de los ensayos](../outputs/etapa3/barrido_potw1803a_20261115T023534122516Z/ensayos_completos.zip). Cada carpeta de intensidad válida conserva comparación triple, mapas absolutos, imágenes y JSON. La preparación local y la remota pueden diferir en la codificación del PNG y sus hashes de archivo aunque sus píxeles coincidan; se conservan ambos registros.

**Alcance:** se fijaron condiciones y se exploraron las cuatro intensidades. Posteriormente se calcularon PSNR y SSIM contra la referencia y se revisaron cuatro recortes comunes. Ninguna salida válida supera la entrada ruidosa en esas métricas; 0,10 es la mejor de las salidas SD, sin acreditar una mejora de restauración. Método y resultados: **Métricas de Calidad**. Los controles posteriores de VAE y sigma cero ya se ejecutaron y revisaron; las pruebas a 50 pasos y la selección generalizable de parámetros quedan pendientes.

### Laboratorio Gradio independiente de la app de Julia

El [notebook del laboratorio](../colab/laboratorio_ruido.ipynb) inicia una interfaz separada definida en `laboratorio.py`. No modifica el recorrido ni los controles de `app.py` y no requiere una imagen ni un SHA-256 de ejemplo fijo.

Para abrirlo localmente desde la raíz:

```powershell
uv run --locked python laboratorio.py
```

Generar y examinar el ruido es liviano; se recomienda Colab con GPU para difusión. En Colab, ejecutar las celdas del notebook de laboratorio y abrir su enlace público temporal. La celda del servidor debe permanecer activa. El clon necesita los módulos publicados; en una sesión previa, interrumpir el servidor, actualizar con `git pull --ff-only origin main` y volver a iniciarlo. No se publican cambios automáticamente.

1. Subir un PNG o TIFF de 8 bits propio. El panel de original y procedencia muestra la imagen en RGB sin reducir y permite indicar fuente, crédito y licencia declarados. Estos campos son opcionales para ejecutar el ensayo; si no se completan, se guardan vacíos sin atribuir una licencia. Antes de compartir resultados hay que verificar y completar la procedencia. Las mismas restricciones de profundidad y tamaño mínimo de `prepare_image` se mantienen.
2. Ajustar sigma (0–0,2), semilla del ruido y lado máximo (256 o 512). El ruido se actualiza con el control, sin ejecutar difusión. Se muestran la referencia preparada y su copia ruidosa; cualquier salida anterior se descarta al cambiar imagen, sigma, semilla o tamaño.
3. Pulsar **Aplicar difusión a la copia ruidosa** para cargar y ejecutar el modelo. Se procesa la misma copia mostrada, verificada antes de inferir. CUDA es explícita y no cambia silenciosamente a CPU. Durante inferencia conviene esperar antes de mover controles; la cola serializa las operaciones para conservar la correspondencia entre vistas.
4. Comparar **referencia preparada → ruido → salida**. El comparador muestra referencia/ruido antes de inferir y ruido/salida después. Los parámetros de la última ejecución quedan registrados.
5. Elegir el par del mapa: referencia/ruido, ruido/salida o referencia/salida. Se presentan el mapa absoluto de escala fija y una vista multiplicada por una ganancia entre 1 y 64, con recorte a 255. La ganancia modifica solo la presentación; no regenera ruido, no ejecuta difusión y no cambia las imágenes ni el mapa absoluto. Se muestran mínimo, máximo, media y fracciones de píxeles no nulos y recortados. Son estadísticas descriptivas del mapa redondeado, no métricas de calidad de restauración.
6. Descargar el ZIP después de inferir. Incluye referencia, ruido, salida, mapas absolutos y los registros. Las carpetas únicas de cada ejecución quedan en `outputs/laboratorio/`; no se sobrescriben ensayos ni se publica la procedencia declarada automáticamente.

**Verificación:** 24 pruebas automatizadas aprobadas, incluyendo cambios de sigma, limpieza de resultados anteriores, protección frente a una entrada desactualizada, ganancia visual y ZIP, con difusión simulada. También se comprobó el servidor real por HTTP con subida de imagen sintética, sigma cero, cambio de ganancia y limpieza de vistas. No se ejecutó inferencia real para verificar estos cambios ni se realizó todavía una revisión visual del laboratorio en el navegador de Colab.

### Ensayos posteriores solicitados — todavía no implementados

1. **Poisson:** definir escala de conteos antes de muestrear. Para señal normalizada `I` y escala `c`, una opción sintética es `Poisson(c * I) / c`; no equivale directamente a conteos físicos sobre RGB ya procesado. Mantener el resto de condiciones del ensayo.
2. **Impulsivo blanco (salt):** reemplazar píxeles RGB completos por blanco con probabilidad inicialmente entre 0,001 y 0,005. Conservar la máscara de píxeles alterados para examinar si el modelo los elimina, mantiene o convierte en estructuras parecidas a estrellas. Las “estrellas fantasma” son una hipótesis a contrastar, no una causa o resultado demostrado. No confundir salt con salt-and-pepper.
3. **Desenfoque por convolución:** especificar sigma espacial, núcleo y tratamiento de bordes; examinar ensanchamiento y cambios de geometría. Es una degradación espacial distinta de sumar ruido. Se reserva como ampliación experimental fuera del MVP de reducción de ruido, manteniendo las dimensiones; no implica superresolución. No se afirma que un núcleo gaussiano reproduzca todo el seeing atmosférico.

Primero se cerrará la inspección del ensayo gaussiano; no se mezclarán degradaciones inicialmente. Se documentarán los resultados desfavorables con el mismo cuidado que cualquier mejora aparente.

## Métricas de Calidad (opcional)

Se calcularon PSNR y SSIM para la entrada ruidosa y las tres salidas válidas del barrido de `potw1803a.tif`. LPIPS no está implementado. PSNR compara errores de píxeles y SSIM compara aspectos de estructura; ambos requieren una referencia confiable para el experimento y una escala de datos documentada. Una fotografía ruidosa real sin referencia limpia no permite usarlos como evidencia de recuperación de señal.

En el experimento gaussiano, la referencia es la imagen preparada anterior a agregar ruido artificial. Esa referencia solo define el objetivo del ensayo sintético: las imágenes publicadas ya están procesadas y no son observaciones perfectas libres de ruido. Las métricas no prueban autenticidad y siguen siendo opcionales.

**Método reproducible:** `src/evaluation.py` verifica hashes de la referencia, entrada y salidas y exige correspondencia píxel a píxel de las copias usadas por cada ensayo. Opera en RGB publicado sin linealizar, convertido a float64 en [0, 1], con `data_range=1`. SSIM usa los tres canales (`channel_axis=-1`), ventana gaussiana de 11 × 11, sigma 1,5, covarianza poblacional (`use_sample_covariance=False`), K1=0,01 y K2=0,03. No alinea imágenes ni ajusta su contraste. La configuración queda registrada en JSON. [Documentación de las métricas de scikit-image](https://scikit-image.org/docs/stable/api/skimage.metrics.html).

Resultados globales, todos contra la misma referencia; valores mayores de PSNR y SSIM indican mayor similitud:

- **Entrada ruidosa:** PSNR **31,24 dB**, SSIM **0,6375**.
- **SD intensidad 0,10:** PSNR **28,09 dB**, SSIM **0,5441**.
- **SD intensidad 0,15:** PSNR **27,23 dB**, SSIM **0,5226**.
- **SD intensidad 0,20:** PSNR **25,33 dB**, SSIM **0,4683**.
- **Intensidad 0,25:** sin métricas, porque la salida fue bloqueada y no se conservó como imagen válida.

**Interpretación:** 0,10 es la más cercana de las tres salidas SD, pero empeora 3,15 dB de PSNR y 0,0934 de SSIM respecto de la entrada ruidosa. Su error cuadrático medio global pasa de 0,00075196 a 0,00155232, aproximadamente 2,06 veces el inicial. Este resultado no avala llamar «mejor limpieza» a la salida. Las intensidades mayores empeoran ambos indicadores en este caso. No se concluye que todo modelo de difusión falle en restauración ni que estas condiciones sean representativas de otras imágenes.

Se inspeccionaron cuatro recortes fijos de 64 × 64 píxeles: fondo, galaxia superior, galaxia inferior y una región puntual. Se ampliaron ×3 con vecino más cercano solo para visualizarlos, sin modificar los datos de cálculo. Se observa textura añadida en el fondo, cambios de contorno y brillo en las galaxias y una forma más alargada de la fuente puntual, especialmente a 0,20. En los cuatro recortes, las tres salidas SD también tienen PSNR y SSIM inferiores a los de la entrada ruidosa. Son observaciones relativas a la referencia publicada, sin clasificación científica de cada estructura. Los recortes sirven de diagnóstico y no constituyen un conjunto independiente de validación.

Para repetir la evaluación, conservando una carpeta de salida nueva:

```powershell
uv run --locked python -m src.evaluation --sweep-dir outputs/etapa3/barrido_potw1803a_20261115T023534122516Z --output-dir outputs/etapa3/barrido_potw1803a_20261115T023534122516Z/evaluacion_nueva --regions-potw1803a
```

Los archivos del barrido deben existir localmente; no se descargan al clonar. La evaluación no descarga pesos ni ejecuta inferencia. Artefactos locales: [métricas y método en JSON](../outputs/etapa3/barrido_potw1803a_20261115T023534122516Z/evaluacion/evaluacion.json), [CSV](../outputs/etapa3/barrido_potw1803a_20261115T023534122516Z/evaluacion/metricas.csv) y [recortes ampliados](../outputs/etapa3/barrido_potw1803a_20261115T023534122516Z/evaluacion/regiones_ampliadas.png). Los registros originales de las inferencias se conservan intactos y su campo histórico de evaluación pendiente no se reescribe; esta evaluación se registra por separado.

## Evidencias técnicas y evaluación

### Revisión de resultados guardados en Colab

Se revisó el [ensayo compartido](https://colab.research.google.com/drive/1iuKBK8DO_-ZDcP_MiUfW5TyaFHTRQOr9#scrollTo=difusion-gaussiano). El notebook guardado usa la revisión `d049aa3`, sigma 0,03, semilla de ruido 123 y referencia de 256 × 192. La celda de difusión conserva `EJECUTAR_DIFUSION = False` y su salida registra **Difusión omitida**. Por lo tanto, esas salidas no permiten evaluar eficacia de restauración ni comportamiento del modelo.

En la comparación guardada se aprecia más grano, especialmente en el fondo. El mapa referencia–ruido es oscuro, pero no está vacío: mínimo 0, máximo 18, media 5,42155 y 49.067 de 49.152 píxeles del mapa con valores no nulos. Estas cantidades corresponden a la media RGB absoluta redondeada a 8 bits. Su baja intensidad en escala 0–255 explica el aspecto casi negro; no indica que las imágenes sean iguales. Las fracciones de muestras RGB recortadas por el generador fueron aproximadamente 13,20 % por debajo de cero y 0,00475 % por encima de uno.

Se produjo una vista del mapa con ganancia ×16, sin cambiar sus valores originales; aproximadamente 0,0651 % de sus píxeles se recorta a blanco en esa presentación. El laboratorio permite cambiar la ganancia y mantiene la vista absoluta al lado. Artefactos locales, excluidos de Git: `outputs/revision_colab_gaussiano/` con notebook recuperado, imágenes, vista amplificada y registro descriptivo. Procedencia y modificaciones: [registro de ejemplos](../assets/ejemplos/README.md).

### Dataset y estrategia de evaluación

Se seleccionaron seis imágenes de observaciones publicadas por ESA/Hubble. Sus archivos se conservan localmente y su procedencia, licencias y créditos se registran en el [README de ejemplos](../assets/ejemplos/README.md). Son imágenes de divulgación ya procesadas, no datos crudos ni referencias científicas libres de ruido. Todavía falta definir y ejecutar el protocolo de evaluación sobre este conjunto.

#### Evaluación controlada

1. Seleccionar imágenes astronómicas de buena calidad como referencias.
2. Agregar ruido artificial controlado, documentando su tipo, intensidad y semilla.
3. Procesar las versiones ruidosas mediante difusión; opcionalmente, incorporar el filtro bilateral como línea base.
4. Mostrar juntas la referencia preparada, la versión con ruido y la salida del modelo. Comenzar con inspección visual de estrellas y estructuras difusas y mapas de diferencias; opcionalmente calcular PSNR (*Peak Signal-to-Noise Ratio*) y SSIM (*Structural Similarity Index*).

El ruido artificial se utilizará exclusivamente para evaluar la restauración; no implica generar imágenes astronómicas nuevas. Se deberá registrar la escala de valores empleada en las métricas y mantener condiciones comparables entre métodos. La evaluación controlada no garantiza que el comportamiento se generalice a todo ruido de adquisición real.

#### Evaluación con imágenes ruidosas reales

Se procesarán imágenes que ya contengan ruido y se compararán visualmente los resultados, los mapas de diferencias y las observaciones del modelo de visión para identificar posibles artefactos.

Sin una referencia confiable, no se reportarán PSNR o SSIM como evidencia de recuperación de la señal original ni se podrá verificar de manera concluyente la autenticidad de todos los detalles restaurados. Un mapa de diferencias muestra dónde cambió la imagen, pero no determina si esos cambios son correctos.

#### Línea base clásica y reproducibilidad

Como mejora opcional, se podrá implementar un **filtro bilateral de OpenCV** para comparar un método tradicional con el modelo de difusión, sin asumir que la difusión ofrecerá mejores resultados.

Se prevé registrar imágenes de origen, degradaciones sintéticas, parámetros del filtro, identificador y revisión del modelo, intensidad de restauración, semillas, versiones y entorno de ejecución. Esto complementará el archivo de dependencias `uv.lock`.

**Ya existe una evaluación inicial del ensayo gaussiano**, descrita en **Métricas de Calidad**: las tres salidas válidas del barrido empeoran PSNR y SSIM respecto de la entrada ruidosa. La evaluación del conjunto y la generalización siguen pendientes. La prueba técnica de etapa 2 verifica integración e inferencia y no debe presentarse como un resultado de restauración validado.

### Prueba técnica por consola

Después de descargar `potw1803a.tif` según las instrucciones de ejemplos:

```powershell
uv run --locked python -m src.diffusion --input assets/ejemplos/originales/potw1803a.tif --output-dir outputs/prueba_diffusion --device cpu --steps 4 --strength 0.5 --size 256
```

Este comando solicita dos pasos efectivos con DDIM y guarda `entrada_preparada.png`, `salida.png` y `parametros.json`. Este último registra modelo, revisión, licencia, semilla, parámetros, dimensiones, SHA-256 de la entrada, versiones y tiempos medidos. Los archivos quedan excluidos de Git. La semilla facilita repetir el experimento en un entorno equivalente, sin garantizar igualdad bit a bit entre hardware o versiones distintas.

La prueba usa una imagen publicada sin agregarle ruido artificial: verifica integración e inferencia. La evaluación de denoising será un experimento posterior. `--device auto` selecciona CUDA cuando está disponible y CPU en caso contrario; también se puede solicitar `--device cuda` en un entorno compatible.

### Verificación realizada

En el entorno local existente, con uv `0.12.3`, se verificaron satisfactoriamente los siguientes comandos utilizando la caché disponible:

```powershell
uv sync --locked --offline
uv run --locked --offline python -c "from app import create_app; print(type(create_app()).__name__)"
```

La sincronización respeta `uv.lock`; el segundo comando comprueba la construcción de la interfaz sin iniciar un servidor. La opción `--offline` requiere las dependencias en caché; esta comprobación no equivale a validar una instalación desde cero ni la inferencia en GPU.

El **11 de noviembre de 2026** se verificó además el comando de prueba técnica con `potw1803a.tif`, semilla 42, intensidad 0,5 y cuatro pasos configurados (dos efectivos). Se cargó la revisión fijada de Stable Diffusion 1.5 y se generó una salida de 256 × 192 píxeles sin bloqueo del filtro de seguridad. La ejecución utilizó Windows 11, Python 3.12.10, PyTorch 2.15.0 en CPU, Diffusers 0.42.1, Transformers 5.22.2 y Pillow 12.3.0.

Los artefactos locales son [entrada preparada](../outputs/prueba_diffusion/entrada_preparada.png), [salida de prueba](../outputs/prueba_diffusion/salida.png) y [registro de parámetros](../outputs/prueba_diffusion/parametros.json). No se publican en Git; esos enlaces solo funcionan después de ejecutar la prueba localmente. La entrada tiene SHA-256 `9bc563fef8171c749cc455ad9b0b140652cd26c28187eff4983686bf74f147a2`. La prueba usa una derivada de la imagen acreditada a **NASA, ESA, and J. Comerford (University of Colorado-Boulder)**; la conversión, el redimensionamiento y la salida generativa son modificaciones del proyecto. No se agregó ruido sintético ni se midió eficacia de restauración.

### Validación de cinco imágenes — etapa 2

Con los cinco TIFF de 8 bits descargados según el [registro de ejemplos](../assets/ejemplos/README.md), ejecutar:

```powershell
uv run --locked python -m src.validation --device auto
```

La validación procesa `potw1803a.tif`, `potw1428a.tif`, `heic0503a.tif`, `heic1520a.tif` y `potw1408a.tif`, con semilla 42, cuatro pasos configurados, intensidad 0,5 y tamaño máximo 256. Excluye `heic1702a.tif` porque es de 16 bits por canal. Puede solicitarse `--device cuda` si existe una GPU compatible o `--device cpu` para ejecutarla localmente; esta última opción puede tardar varios minutos por imagen.

Se reutiliza el modelo en memoria y se crea una carpeta por imagen en `outputs/etapa2/`, con entrada preparada, salida, parámetros y `comparacion.png` (entrada a la izquierda y salida a la derecha). `resumen.json` se actualiza después de cada caso y solo marca la ejecución completa cuando hay cinco resultados correctos con hashes de entrada diferentes. Se registran errores individuales sin declararlos como pruebas exitosas. Los resultados permanecen locales, excluidos de Git.

Esta comprobación acredita el procesamiento técnico de cinco imágenes distintas. No mide reducción de ruido ni demuestra autenticidad científica; las comparaciones deben revisarse visualmente.

### Resultados registrados de la etapa 2

El 11 de noviembre de 2026 se completaron cinco ejecuciones en CPU con PyTorch 2.15.0, precisión bfloat16, Python 3.12.10, Diffusers 0.42.1, semilla 42, intensidad 0,5 y dos pasos efectivos de DDIM. Cada caso tiene una entrada distinta, original intacto y salida no uniforme. Se generaron y revisaron las comparaciones contra la entrada preparada, no contra el TIFF a resolución completa.

- **potw1803a.tif:** 256 × 192 píxeles; 161.042 s de inferencia. Cambios notorios en las formas, colores y brillos de las galaxias; no acredita limpieza de ruido.
- **potw1428a.tif:** 256 × 248 píxeles; 222.833 s de inferencia. Aparecen patrones curvos y brillos alargados que no se aprecian en la referencia preparada; cambia la apariencia del cúmulo.
- **heic0503a.tif:** 248 × 248 píxeles; 223.288 s de inferencia. Se alteran las estructuras del polvo y la distribución de colores y brillos alrededor de V838 Mon.
- **heic1520a.tif:** 256 × 168 píxeles; 137.070 s de inferencia. Se modifican y engrosan filamentos; aparecen trazos curvos distintos de los de la referencia preparada.
- **potw1408a.tif:** 256 × 120 píxeles; 102.478 s de inferencia. Cambian numerosos brillos puntuales y las formas y colores de la nebulosidad; no se puede afirmar conservación de detalles.

Los tiempos pertenecen a estas ejecuciones locales; no describen el rendimiento de Colab ni son un benchmark general. La prueba de T4 documentada en la alternativa Colab se realizó por separado sobre una imagen.

**Resultado técnico:** cinco casos correctos, cinco hashes de entrada diferentes y comparaciones visuales disponibles. **Resultado visual:** se observaron alteraciones importantes en todos los casos; estas salidas no demuestran mejora de denoising ni fidelidad científica. La intensidad 0,5 se utilizó para una prueba técnica corta, no como parámetro recomendado de restauración. Estos ejemplos se conservan como material de fallos para la etapa 3.

Artefactos locales: [resumen de resultados](../outputs/etapa2/resumen.json) y [comparaciones de los cinco casos](../outputs/etapa2/comparaciones.png). Cada subcarpeta contiene `entrada_preparada.png`, `salida.png`, `comparacion.png` y `parametros.json`. Están excluidos de Git; los enlaces funcionan después de ejecutar la validación. Los créditos, fuentes y condiciones de las imágenes se conservan en el [registro de ejemplos](../assets/ejemplos/README.md).

### Evidencia versionada del cierre de etapa 3

[Comparación real y análisis CLIP](../assets/ejemplos/etapa3_tile/README.md), con imágenes, registro original, frases, afinidades y hashes. [Detalle de implementación y límites](analisis_visual.md). Se distingue completar el recorrido técnico de demostrar reducción de ruido.

### Etapa 4: interfaz y preparación de demo

Se retomó la revisión centrada en Julia y una [base de diseño compartida](diseno_interfaz.md). Para iniciar localmente: `uv run --locked python app.py`. **Procesar y comparar** inicia la inferencia sobre la foto propia. Por pedido de la autora, se retiraron los ejemplos y el acceso a ensayos guardados de la vista principal; la evidencia histórica permanece en el repositorio.

Para probar los commits locales en Colab: `uv run --locked python colab/preparar_app.py`, subir [app_integrada.ipynb](../colab/app_integrada.ipynb) a Colab y cargar el ZIP generado en `outputs/astrorestore_app_colab.zip`. El notebook también admite GitHub después de publicar. [Guía de comprobación, capturas y guion de cinco minutos](entrega_etapa4.md). La ejecución completa en Colab, revisión visual, video, reflexión y licencia del código permanecen pendientes.

Comprobación de etapa 4: instalación en copia nueva, HTTP 200 y descarga del ensayo guardado correctos. [Registro y límites](verificacion_etapa4.md). La herramienta de navegador no estuvo disponible; no se da por realizada la revisión visual ni se fabricaron capturas.

[Volver al README principal](../README.md).
