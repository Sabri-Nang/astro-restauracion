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
   **Fullsize Original**, en formato TIFF, salvo `potw1849a`, para la que se usa
   **Publication TIFF 4K**. Sus dimensiones locales se distinguen en el registro.
3. Guardar cada archivo en `assets/ejemplos/originales/` con el nombre indicado.

Los enlaces locales de la tabla funcionarán después de descargar las imágenes;
en GitHub se deben utilizar los enlaces a las fichas de origen.

## Registro de imágenes

| Archivo | Descripción | Formato y dimensiones publicados | Fuente y publicación | Autoría y atribución requerida | Licencia o permiso | Modificaciones en el proyecto |
| --- | --- | --- | --- | --- | --- | --- |
| [potw1803a.tif](originales/potw1803a.tif) | Galaxias SDSS J1354+1327 (inferior) y SDSS J1354+1328 (superior). La publicación describe episodios de expulsión de gas asociados al agujero negro supermasivo de la galaxia inferior. La ficha incluye observaciones ópticas e infrarrojas de Hubble y rayos X de Chandra. | TIFF; 933 × 700 píxeles. | ESA/Hubble, `potw1803a`; 15 de enero de 2018. [Ficha de origen](https://esahubble.org/images/potw1803a/). [Descarga original](https://esahubble.org/media/archives/images/original/potw1803a.tif). | NASA, ESA, and J. Comerford (University of Colorado-Boulder). Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/potw1803a/parametros.json.  También se conserva la prueba inicial en outputs/prueba_diffusion/. |
| [heic1702a.tif](originales/heic1702a.tif) | Campo amplio centrado en el cuásar HE0435-1223. Una galaxia en primer plano actúa como lente gravitacional y produce cuatro imágenes aparentes del mismo cuásar; corresponden al fenómeno astronómico documentado, no a duplicaciones generadas por IA. La ficha incluye observaciones ópticas e infrarrojas de Hubble. | TIFF; 2020 × 2020 píxeles. | ESA/Hubble, `heic1702a`; 26 de enero de 2017. [Ficha de origen](https://esahubble.org/images/heic1702a/). | ESA/Hubble, NASA, Suyu et al. Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto; copia RGB de 8 bits desde el TIFF de 16 bits, reducción LANCZOS y ruido gaussiano en assets/ruido_gaussiano/heic1702a_sigma0.03_seed123_size256/. La conversión pierde precisión tonal y queda documentada en sus registros. |
| [potw1428a.tif](originales/potw1428a.tif) | Cúmulo globular NGC 121, perteneciente a la Pequeña Nube de Magallanes, en la constelación de Tucana. Imagen obtenida con la cámara ACS de Hubble, que permite distinguir estrellas individuales del cúmulo. | TIFF; 3222 × 3148 píxeles. | ESA/Hubble, `potw1428a`; 14 de julio de 2014. [Ficha de origen: The oldest cluster in its cloud](https://esahubble.org/images/potw1428a/). | ESA/Hubble & NASA. Acknowlegement: Stefano Campani. Conservar el crédito y el reconocimiento completos, con la grafía publicada por la fuente. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/potw1428a/parametros.json. |
| [heic0503a.tif](originales/heic0503a.tif) | Estrella V838 Monocerotis (V838 Mon) y las nubes de polvo circundantes, observadas con la cámara ACS de Hubble. La imagen muestra un eco de luz: la iluminación del polvo por el aumento de brillo de la estrella ocurrido en 2002 revela sus estructuras. | TIFF; 3400 × 3382 píxeles. | ESA/Hubble, `heic0503a`; 3 de febrero de 2005. [Ficha de origen: Light continues to echo three years after stellar outburst](https://esahubble.org/images/heic0503a/). | NASA, ESA, and The Hubble Heritage Team (AURA/STScI). Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/heic0503a/parametros.json. |
| [heic1520a.tif](originales/heic1520a.tif) | Sección de la nebulosa del Velo, un remanente de supernova, en la región NGC 6960, también conocida como nebulosa de la Escoba de la Bruja. Observación de Hubble con la cámara WFC3 que muestra estructuras filamentosas de gas. | TIFF; 10681 × 7121 píxeles. | ESA/Hubble, `heic1520a`; 24 de septiembre de 2015. [Ficha de origen: Revisiting the Veil Nebula](https://esahubble.org/images/heic1520a/). | NASA, ESA, Hubble Heritage Team. Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/heic1520a/parametros.json. |
| [potw1408a.tif](originales/potw1408a.tif) | Cúmulo estelar joven LH63, parcialmente inmerso en la nebulosa de emisión LHA 120-N 51 (N51), una región de formación estelar de la Gran Nube de Magallanes. Observación de Hubble con la cámara WFPC2 que muestra estrellas jóvenes, gas y polvo. | TIFF; 1502 × 739 píxeles. | ESA/Hubble, `potw1408a`; 24 de febrero de 2014. [Ficha de origen: Cloaked in red](https://esahubble.org/images/potw1408a/). | NASA, ESA, and D. Gouliermis (University of Heidelberg). Acknowledgement: Luca Limatola. Conservar el crédito y el reconocimiento completos. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | Original intacto. Derivadas de la validación técnica de etapa 2: preparación RGB de 8 bits, LANCZOS con lado máximo 256 y salida de Stable Diffusion 1.5 (intensidad 0,5, semilla 42, dos pasos efectivos). Sin ruido sintético añadido; se observaron alteraciones visuales y no se afirma restauración validada. Registro local: outputs/etapa2/potw1408a/parametros.json. |
| [potw1849a.tif](originales/potw1849a.tif) | Campo del cúmulo de galaxias de Coma, observado con ACS de Hubble en las bandas ópticas B (475 nm) e I (814 nm). La publicación describe cúmulos globulares entre las galaxias, ligados al cúmulo de Coma. | TIFF de publicación 4K local: 4000 × 2250 píxeles, RGB de 8 bits por canal. La ficha publica 18281 × 10283 píxeles para la versión de tamaño completo. | ESA/Hubble, `potw1849a`; 3 de diciembre de 2018. [Ficha de origen: Clusters within clusters](https://esahubble.org/images/potw1849a/). [Descarga Publication TIFF 4K](https://esahubble.org/media/archives/images/publicationtiff/potw1849a.tif). | NASA, ESA, J. Mack, and J. Madrid et al. Conservar este crédito completo. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), conforme a las [condiciones de ESA/Hubble](https://esahubble.org/copyright/). | TIFF local intacto; copia RGB de 8 bits, reducción LANCZOS a 256 × 144 y ruido gaussiano de media 0, sigma 0,03 y semilla 123, añadido después de reducir. Par conservado en assets/ruido_gaussiano/potw1849a_sigma0.03_seed123_size256/. Sin inferencia ni restauración evaluada. |

## Condiciones de uso y conservación

- Mantener el crédito completo de cada imagen, el enlace de origen y la licencia; indicar las modificaciones sin sugerir respaldo de ESA/Hubble al proyecto.
- Conservar los TIFF originales. Son imágenes de divulgación ya procesadas, no datos crudos ni referencias científicas perfectas libres de ruido.
- Guardar conversiones, reducciones, ruido y salidas generativas como copias. No presentar una reconstrucción IA como observación astronómica verificada.

## Derivadas conservadas

Los siete TIFF locales tienen una referencia preparada y una copia con ruido en
[ruido_gaussiano](../ruido_gaussiano/README.md). Se usaron LANCZOS, lado máximo
256, dimensiones múltiplos de ocho y ruido gaussiano de media 0, sigma 0,03 y
semilla 123, añadido después de reducir. Cada carpeta conserva imágenes, fuente,
crédito completo, licencia, modificaciones y hashes en `experimento.json` y
`reproduccion.json`. El par de `potw1803a` fue evaluado; las otras seis copias
todavía no tienen una restauración evaluada. `heic1702a` necesitó conversión
explícita de 16 a 8 bits. Los TIFF originales permanecen intactos.

El [ejemplo real de SD + Tile y CLIP](etapa3_tile/README.md) conserva entrada,
salida, comparación, diferencias e informe de `potw1803a`, con parámetros y
atribución. Incluye una copia resaltada para revisar cambios, sin otra inferencia.
Las salidas de difusión deben identificarse como reconstrucciones por IA.

Las cinco pruebas técnicas anteriores produjeron copias RGB reducidas, salidas
SD 1.5 y mapas absolutos de diferencias; los archivos locales están en
`outputs/etapa2/` y `outputs/etapa3/`, excluidos de Git. Esas pruebas no agregaron
ruido sintético ni acreditaron reducción de ruido. El detalle histórico queda
en los commits; las modificaciones de cada fuente se resumen en la tabla.

## Incorporar una imagen

Agregar al registro nombre, descripción, formato, dimensiones, fuente, crédito,
licencia o permiso y modificaciones. Antes de compartir una derivada, verificar
los derechos y acompañarla de esas atribuciones. La procedencia declarada en
el laboratorio se registra, pero no se valida automáticamente.
