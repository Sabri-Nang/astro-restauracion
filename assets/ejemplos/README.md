# Imágenes de ejemplo

Esta carpeta contiene imágenes astronómicas de ejemplo y documenta su
procedencia, condiciones de uso y modificaciones realizadas en el proyecto.

Los TIFF originales se conservan localmente y están excluidos del control de
versiones mediante `.gitignore`. No se suben a GitHub ni se gestionan con Git LFS.
Después de clonar el repositorio:

1. Crear la carpeta de destino desde la raíz:

   ```powershell
   New-Item -ItemType Directory -Path assets/ejemplos/originales -Force
   ```

2. Abrir la ficha de origen de cada imagen incluida en la tabla y descargar
   **Fullsize Original**, en formato TIFF.
3. Guardar cada archivo en `assets/ejemplos/originales/` con el nombre indicado.

Los enlaces locales de la tabla funcionarán después de descargar las imágenes;
en GitHub se deben utilizar los enlaces a las fichas de origen.

## Registro de imágenes

| Archivo | Descripción | Formato y dimensiones publicados | Fuente y publicación | Autoría y atribución requerida | Licencia o permiso | Modificaciones en el proyecto |
| --- | --- | --- | --- | --- | --- | --- |
| [potw1803a.tif](originales/potw1803a.tif) | Galaxias SDSS J1354+1327 (inferior) y SDSS J1354+1328 (superior). La publicación describe episodios de expulsión de gas asociados al agujero negro supermasivo de la galaxia inferior. La ficha incluye observaciones ópticas e infrarrojas de Hubble y rayos X de Chandra. | TIFF; 933 × 700 píxeles. | ESA/Hubble, `potw1803a`; 15 de enero de 2018. [Ficha de origen](https://esahubble.org/images/potw1803a/). [Descarga original](https://esahubble.org/media/archives/images/original/potw1803a.tif). | NASA, ESA, and J. Comerford (University of Colorado-Boulder). Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/potw1803a/parametros.json.  También se conserva la prueba inicial en outputs/prueba_diffusion/. |
| [heic1702a.tif](originales/heic1702a.tif) | Campo amplio centrado en el cuásar HE0435-1223. Una galaxia en primer plano actúa como lente gravitacional y produce cuatro imágenes aparentes del mismo cuásar; corresponden al fenómeno astronómico documentado, no a duplicaciones generadas por IA. La ficha incluye observaciones ópticas e infrarrojas de Hubble. | TIFF; 2020 × 2020 píxeles. | ESA/Hubble, `heic1702a`; 26 de enero de 2017. [Ficha de origen](https://esahubble.org/images/heic1702a/). | ESA/Hubble, NASA, Suyu et al. Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | No se registran transformaciones; incorporada como original descargado. |
| [potw1428a.tif](originales/potw1428a.tif) | Cúmulo globular NGC 121, perteneciente a la Pequeña Nube de Magallanes, en la constelación de Tucana. Imagen obtenida con la cámara ACS de Hubble, que permite distinguir estrellas individuales del cúmulo. | TIFF; 3222 × 3148 píxeles. | ESA/Hubble, `potw1428a`; 14 de julio de 2014. [Ficha de origen: The oldest cluster in its cloud](https://esahubble.org/images/potw1428a/). | ESA/Hubble & NASA. Acknowlegement: Stefano Campani. Conservar el crédito y el reconocimiento completos, con la grafía publicada por la fuente. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/potw1428a/parametros.json. |
| [heic0503a.tif](originales/heic0503a.tif) | Estrella V838 Monocerotis (V838 Mon) y las nubes de polvo circundantes, observadas con la cámara ACS de Hubble. La imagen muestra un eco de luz: la iluminación del polvo por el aumento de brillo de la estrella ocurrido en 2002 revela sus estructuras. | TIFF; 3400 × 3382 píxeles. | ESA/Hubble, `heic0503a`; 3 de febrero de 2005. [Ficha de origen: Light continues to echo three years after stellar outburst](https://esahubble.org/images/heic0503a/). | NASA, ESA, and The Hubble Heritage Team (AURA/STScI). Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/heic0503a/parametros.json. |
| [heic1520a.tif](originales/heic1520a.tif) | Sección de la nebulosa del Velo, un remanente de supernova, en la región NGC 6960, también conocida como nebulosa de la Escoba de la Bruja. Observación de Hubble con la cámara WFC3 que muestra estructuras filamentosas de gas. | TIFF; 10681 × 7121 píxeles. | ESA/Hubble, `heic1520a`; 24 de septiembre de 2015. [Ficha de origen: Revisiting the Veil Nebula](https://esahubble.org/images/heic1520a/). | NASA, ESA, Hubble Heritage Team. Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/heic1520a/parametros.json. |
| [potw1408a.tif](originales/potw1408a.tif) | Cúmulo estelar joven LH63, parcialmente inmerso en la nebulosa de emisión LHA 120-N 51 (N51), una región de formación estelar de la Gran Nube de Magallanes. Observación de Hubble con la cámara WFPC2 que muestra estrellas jóvenes, gas y polvo. | TIFF; 1502 × 739 píxeles. | ESA/Hubble, `potw1408a`; 24 de febrero de 2014. [Ficha de origen: Cloaked in red](https://esahubble.org/images/potw1408a/). | NASA, ESA, and D. Gouliermis (University of Heidelberg). Acknowledgement: Luca Limatola. Conservar el crédito y el reconocimiento completos. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/potw1408a/parametros.json. |

## Condiciones comunes de uso y conservación

### Derivadas de comparación de la etapa 3

Se generaron mapas de diferencias para las cinco imágenes de la validación
técnica de etapa 2, sin ejecutar nuevas inferencias ni alterar los originales.
Se guardan localmente en `outputs/etapa3/comparacion/<identificador>_diferencias.png`,
conservando el identificador que vincula cada mapa con su fuente, licencia y
atribución en el registro anterior. Cada mapa representa la media RGB de la
diferencia absoluta entre `entrada_preparada.png` y `salida.png`, redondeada a
8 bits y con escala fija de 0 a 255. Al compartirlo, indicar esta transformación
y acompañarlo del crédito y los enlaces de la imagen correspondiente. Estos
mapas muestran cambios, no resultados de reducción de ruido ni autenticidad.

- Presentar el crédito completo de cada imagen de forma visible y asociado a
  ella; al publicarlo en línea, incluir el enlace a la fuente y a la licencia.
- Indicar las modificaciones al generar versiones derivadas, sin sugerir
  respaldo de ESA/Hubble al proyecto.
- Conservar los originales descargados. Guardar los futuros recortes,
  conversiones, adiciones de ruido o restauraciones como copias y documentar
  sus modificaciones por separado.
- Estas imágenes de divulgación ya están procesadas: no son datos científicos
  crudos ni referencias garantizadas libres de ruido.
- No presentar imágenes generadas como observaciones astronómicas reales.

## Ensayo gaussiano de etapa 3

Se preparó una derivada de `potw1803a.tif` en
`outputs/etapa3/gaussiano_sigma0.03_seed123_size256/`: referencia RGB de 8 bits,
LANCZOS a 256 × 192, copia con ruido gaussiano aditivo de media cero y sigma
0,03 en escala [0, 1], semilla 123 y generador PCG64. El ruido se agrega después
de reducir la imagen, de forma independiente por píxel y canal. Se recorta a
[0, 1] y se redondea a 8 bits. Se guardan la comparación etiquetada, el mapa de
diferencias de escala fija y `experimento.json` con hashes y parámetros.
No se modificó el TIFF ni se ejecutó difusión para generar esta derivada.

Crédito: **NASA, ESA, and J. Comerford (University of Colorado-Boulder)**.
[Fuente](https://esahubble.org/images/potw1803a/) ·
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), según las
[condiciones de ESA/Hubble](https://esahubble.org/copyright/). Al compartir las
copias, mantener este crédito e identificar el redimensionamiento y el ruido
como modificaciones del proyecto. La imagen publicada ya está procesada;
su uso como referencia del ensayo no supone ausencia de ruido ni autenticidad
científica de una futura salida generativa.

## Incorporación de nuevas imágenes

### Revisión del ensayo guardado en Colab

Se revisaron las vistas guardadas en el
[notebook compartido](https://colab.research.google.com/drive/1iuKBK8DO_-ZDcP_MiUfW5TyaFHTRQOr9).
La comparación y el mapa corresponden a `potw1803a.tif` con los mismos créditos
y condiciones indicados en el ensayo anterior. Se conservaron localmente en
`outputs/revision_colab_gaussiano/`; `diferencias_x16.png` es una derivada del mapa
absoluto multiplicada por 16 y recortada a 255, únicamente para visualizarla.
No se amplificaron la referencia ni la imagen con ruido. El notebook guardado
indica que se omitió difusión; estas vistas no representan una restauración.

### Nuevas imágenes del laboratorio

Agregar una fila por imagen con nombre y ubicación del archivo, descripción,
formato y dimensiones, fuente y enlace de origen, autoría y atribución completa,
licencia o permiso y modificaciones realizadas, si corresponde.

El laboratorio permite cargar archivos propios sin un hash de ejemplo fijo.
Solicita fuente, crédito y licencia o permiso declarados y los guarda en el
registro de la ejecución; no los valida automáticamente. Comprobar esa información
antes de compartir imágenes o ZIP. Los archivos de ensayo quedan en `outputs/`,
excluidos de Git.
