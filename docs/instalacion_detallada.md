# Instalación detallada y ejecución en Colab

## Aplicación integrada actual

Para el recorrido de Julia, usar [app_integrada.ipynb](../colab/app_integrada.ipynb), en el navegador de Google Colab con GPU. El README principal resume los pasos. El notebook admite `ORIGEN = 'github'` para el código publicado o `ORIGEN = 'paquete_local'` para el ZIP generado con `uv run --locked python colab/preparar_app.py`. El selector de ZIP de esta ruta usa `google.colab.files.upload()` y está dirigido al navegador, no a VS Code.

La interfaz actual ofrece **Procesar y comparar**, intensidad, comparador, resaltado e informe; los parámetros completos están en la descarga. Si se cambió el proyecto, generar un nuevo ZIP antes de subirlo. Reiniciar el servidor para cargar la versión nueva y volver a descargar los resultados antes de cerrar Colab. El enlace local apunta a la máquina remota; abrir el enlace público `gradio.live` que muestra la celda. La celda permanece activa mientras sirve la app.

Para usar ruido sintético, subir un `entrada_ruidosa.png` del [catálogo gaussiano](../assets/ruido_gaussiano/README.md); conservar su `referencia_preparada.png` para evaluar fuera de la app. La app no calcula métricas contra una referencia inventada.

## Prueba inicial e historial de instalación

Las instrucciones siguientes conservan el notebook inicial, la solución al HTTP 403, el selector de archivos para VS Code y las mediciones CPU/T4. No sustituyen al notebook integrado recomendado arriba. Sus mediciones no incluyen el recorrido completo actual con Tile y CLIP.

## Instalación y Ejecución

### Requisitos

- Python 3.12 para reproducir la versión seleccionada en `.python-version`.
- uv disponible en la terminal.
- Para utilizar las imágenes de ejemplo, descargar los TIFF manualmente según la [documentación de ejemplos](../assets/ejemplos/README.md). No están incluidos en Git ni se requiere Git LFS.
- Una copia del repositorio y acceso a las dependencias, mediante red o caché local.

### Pasos

Clonar el repositorio y entrar en su carpeta:

```powershell
git clone https://github.com/Sabri-Nang/astro-restauracion.git
cd astro-restauracion
```

Desde la raíz del repositorio, sincronizar el entorno respetando el archivo de bloqueo:

```powershell
uv sync --locked
```

Ejecutar la aplicación desde la raíz:

```powershell
uv run app.py
```

Gradio muestra una dirección local en la terminal. Abrirla en el navegador, subir una copia PNG o TIFF compatible y pulsar **Procesar y comparar**. La primera prueba descarga varios GB de pesos; las siguientes reutilizan la caché. Se muestran el comparador, las zonas resaltadas y el informe; el mapa absoluto y los parámetros se guardan en el ZIP. Detener el servidor con `Ctrl+C`. También puede utilizarse `uv run --locked python app.py` para exigir el archivo de bloqueo actualizado. El comando exacto `uv run app.py` se verificó con HTTP 200, control de subida, botón de proceso y ambos paneles de comparación. El comando anterior `astro-restauracion` fue retirado al eliminar el paquete anidado.

### Alternativa: Google Colab

1. Abrir [Google Colab](https://colab.research.google.com/) y seleccionar **Archivo → Subir notebook** para cargar la copia local de `colab/ejecutar_en_colab.ipynb`. Esta opción permite usar el notebook actualizado aunque aún no esté publicado en GitHub.
2. En **Entorno de ejecución → Cambiar tipo de entorno de ejecución**, seleccionar GPU (por ejemplo T4, si está disponible) y conectar. Los recursos dependen de la disponibilidad de Colab.
3. Ejecutar la preparación: se comprueba `nvidia-smi`, se clona el código publicado en GitHub, se registra su revisión y se instala uv `0.12.3`. `uv sync --locked --python 3.12` crea el entorno del proyecto; el kernel del notebook y ese entorno son independientes.
4. Ejecutar primero la celda auxiliar `ejecutar_con_salida`, que transmite los mensajes de los subprocesos a la salida del notebook, y después la comprobación de PyTorch. Debe mostrar Python 3.12, GPU y VRAM. Si CUDA no está disponible, el notebook se detiene para evitar ejecutar la prueba involuntariamente en CPU.
5. Ejecutar la celda del selector **Subir TIFF**, seleccionar el archivo local `assets/ejemplos/originales/potw1803a.tif` y esperar a que termine la transferencia. Después, ejecutar la celda de prueba. El selector usa `ipywidgets.FileUpload`, alternativa recomendada para [Colab desde VS Code](https://github.com/googlecolab/colab-vscode/wiki/Known-Issues-and-Workarounds#filesupload-and-filesupload_file), donde `google.colab.files.upload()` no está soportado. La preparación instala ipywidgets 8.1.7 en el kernel del notebook, separado del entorno uv de la aplicación. Se verifica el SHA-256 y se reutiliza el archivo si ya está disponible en la sesión. La descarga directa desde ESA/Hubble puede responder **HTTP 403**; queda como opción mediante `ORIGEN_IMAGEN = 'descargar'`, utilizando el archivo del selector si falla la conexión. Se emplean la misma semilla 42, cuatro pasos configurados, intensidad 0,5 y tamaño máximo 256 que en CPU. Se muestran la entrada preparada, la salida y los tiempos reales; no se presupone una mejora de rendimiento ni de calidad.
6. Descargar el ZIP de resultados mediante la celda correspondiente antes de finalizar la sesión. Incluye las imágenes y el registro con revisión del proyecto y hardware GPU.
7. Opcionalmente, ejecutar la última celda para abrir Gradio mediante un enlace público temporal y subir imágenes propias. **La celda permanece ejecutándose mientras el servidor está activo**; esperar el enlace `https://...gradio.live` en su salida y abrirlo en el navegador. El modelo se vuelve a cargar en el proceso de la interfaz, reutilizando los pesos descargados. Interrumpir la celda al terminar; el auxiliar detiene también los procesos secundarios en Colab.

El notebook clona el código que ya está publicado en GitHub; los cambios locales de la aplicación deberán publicarse para que estén disponibles en Colab. Los TIFF locales no se transfieren automáticamente al entorno remoto. La prueba solicita únicamente la imagen indicada y rechaza un archivo cuyo SHA-256 no coincida.

El [nivel gratuito de Colab](https://research.google.com/colaboratory/faq.html) puede finalizar sesiones cuyo uso principal sea una interfaz web externa; se prioriza la prueba interactiva dentro del notebook. Los resultados temporales se pierden al eliminarse el entorno. La descarga automática falló con HTTP 403 y se incorporó la subida mediante ipywidgets. No se realizó ninguna publicación automática.

**Prueba GPU registrada por la autora el 11 de noviembre de 2026:** las salidas conservadas del notebook muestran una Tesla T4, Python 3.12.3, dispositivo `cuda:0` y precisión `float16`. Con la misma entrada y parámetros de la prueba CPU, se registraron **45,825 segundos de carga** y **2,294 segundos de inferencia**, y se mostraron las dos imágenes. La ejecución local en CPU había medido 174,832 segundos de inferencia. Estos valores corresponden a dos ejecuciones en entornos y precisiones distintos; no constituyen un benchmark general ni una evaluación de denoising. La autora confirmó posteriormente el acceso y funcionamiento de la interfaz desde su enlace público. La salida en vivo de subprocesos se añadió después para que los registros y el enlace sean visibles desde VS Code.
**Actualizar una sesión ya iniciada:** la preparación solo clona el repositorio si la carpeta no existe. Si se publicaron cambios después de iniciar la sesión, interrumpir Gradio y ejecutar esta celda antes de volver a lanzarlo:

```python
ejecutar_con_salida(
    ["git", "pull", "--ff-only", "origin", "main"],
    cwd=proyecto,
)
```

Si Git informa conflictos o cambios locales, revisar el mensaje antes de continuar; no descartar archivos automáticamente. Al reiniciar Gradio puede cambiar el enlace público.

[Volver al README principal](../README.md).
