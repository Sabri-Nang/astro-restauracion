# AstroRestore AI

Aplicación en desarrollo para la restauración y el análisis de imágenes astronómicas mediante modelos de difusión e inteligencia artificial.

Proyecto académico correspondiente al **Trabajo Integrador N.º 2** de la materia **Procesamiento Digital de Imágenes e Introducción a Visión por Computadora**, de la **Tecnicatura Superior en Ciencia de Datos e Inteligencia Artificial**.

- **Sub-tarea seleccionada:** B — Eliminación de ruido y desenfoque (*denoising/deblurring*).
- **Foco exclusivo del MVP:** reducción de ruido (*denoising*). La corrección de desenfoque queda fuera del alcance inicial.
- **Estado actual:** configuración inicial del paquete Python y comando de consola de prueba. Las funciones de restauración, evaluación e interfaz descritas en este documento están **planificadas**, salvo indicación expresa.
- **Autora:** Sabrina Sanches, según los metadatos del proyecto.
- **Repositorio central:** [astro-restauracion en GitHub](https://github.com/Sabri-Nang/astro-restauracion).

## 1. Problema que busca resolver

Las fotografías astronómicas pueden conservar ruido asociado al sensor, la temperatura y las condiciones de adquisición incluso después de la alineación y el apilamiento. Los filtros agresivos pueden eliminar estrellas tenues y estructuras difusas de nebulosas o galaxias junto con el ruido.

Las herramientas generativas plantean otro problema: pueden introducir detalles plausibles que no correspondan a la observación original. Una imagen visualmente más atractiva no constituye, por sí sola, una observación científicamente más confiable.

AstroRestore AI propone explorar la reducción de ruido y ofrecer herramientas para examinar los cambios introducidos por la IA, especialmente antes de utilizar las imágenes con fines educativos o de divulgación.

## 2. Objetivos generales y específicos

### Objetivo general

Desarrollar una aplicación que permita reducir el ruido de imágenes astronómicas mediante un modelo de difusión preentrenado de Hugging Face, incorporando herramientas de comparación y análisis para evaluar las modificaciones introducidas por el procesamiento.

El proyecto busca estudiar hasta qué punto las transformaciones conservan la información astronómica original, además de explorar la mejora de la apariencia visual.

### Objetivos específicos

- Evaluar un modelo preentrenado para reducción de ruido sin entrenar un modelo desde cero.
- Permitir la carga de imágenes PNG o TIFF y el ajuste de la intensidad de restauración.
- Facilitar la comparación entre imagen original y procesada mediante vistas antes/después, un deslizador y mapas de diferencias.
- Calcular PSNR y SSIM cuando exista una referencia confiable.
- Comparar el modelo con un filtro bilateral de OpenCV como línea base clásica.
- Incorporar un modelo de visión que analice ambas imágenes y describa modificaciones y posibles artefactos.
- Comunicar las limitaciones del procesamiento generativo y favorecer experimentos reproducibles.

Estos objetivos no representan funcionalidades ya implementadas ni garantías de conservación de información.

## 3. Diseño Centrado en el Usuario — Persona Julia

### Perfil y contexto tecnológico

**Julia tiene 34 años**, es profesora de Física en una escuela secundaria, aficionada a la astrofotografía y participante activa en talleres de divulgación científica.

Posee conocimientos tecnológicos intermedios-avanzados: utiliza Siril, DeepSkyStacker y Photoshop, puede ejecutar scripts básicos de Python y usar aplicaciones web. No cuenta con conocimientos especializados sobre arquitecturas de aprendizaje profundo ni modelos de difusión.

### Problema y solución actual

Julia dedica varias horas a capturar y procesar fotografías del cielo nocturno. Utiliza Siril o DeepSkyStacker para alinear y apilar sus tomas y luego aplica filtros de reducción de ruido, ajustes de contraste y modificaciones del histograma.

El proceso requiere tiempo y ajustes manuales para decidir cuánto ruido eliminar sin perder información relevante. Le preocupa borrar estrellas tenues o estructuras difusas, y también presentar detalles generados artificialmente como si fueran observaciones verificadas en sus clases y talleres.

### Frustraciones

- Pérdida de detalles astronómicos al aplicar filtros agresivos.
- Falta de transparencia de las herramientas generativas.
- Tiempo excesivo dedicado al procesamiento manual.
- Dificultad para distinguir estructuras reales de posibles artefactos.
- Incertidumbre sobre la confiabilidad de las imágenes empleadas en divulgación científica.

### Objetivos de Julia

- Reducir el ruido y preservar, en la medida de lo posible, estrellas y estructuras originales.
- Reducir el tiempo de procesamiento.
- Comparar visualmente la imagen original con la restaurada.
- Identificar regiones modificadas por la IA.
- Comprender las limitaciones del resultado antes de utilizarlo con fines educativos.

### Contexto de uso previsto

Desde su computadora personal, después de una sesión de observación o mientras prepara material educativo, Julia cargaría una imagen previamente procesada y apilada, seleccionaría la intensidad y ejecutaría la restauración. Luego compararía ambas imágenes, consultaría el mapa de diferencias y revisaría el análisis visual y sus advertencias antes de decidir si comparte el resultado.

Este recorrido describe la experiencia propuesta; todavía no está disponible en el código.

## 4. Solución propuesta

Se propone una aplicación web desarrollada en Gradio que integre carga de imágenes, restauración mediante difusión, comparación, evaluación y descarga del resultado.

El candidato inicial es `stable-diffusion-v1-5/stable-diffusion-v1-5`, que se evaluaría mediante un pipeline de imagen a imagen (*image-to-image*) con intensidad baja. **No es un modelo especializado en restauración astronómica** y su utilidad para este problema debe demostrarse experimentalmente. Una intensidad baja no garantiza la conservación de las estructuras originales.

La selección definitiva dependerá de la disponibilidad, licencia, compatibilidad con el entorno y resultados de evaluación. También está pendiente seleccionar el modelo de visión para el análisis comparativo.

El análisis visual tendrá carácter descriptivo y exploratorio. Sus observaciones no equivaldrán a una verificación científica de las estructuras restauradas.

## 5. Funcionalidades previstas del MVP

Todas las siguientes funcionalidades están **pendientes de implementación**:

- Cargar imágenes astronómicas PNG o TIFF.
- Aplicar un modelo de difusión preentrenado de Hugging Face para reducción de ruido.
- Ajustar la intensidad de restauración.
- Visualizar las imágenes original y restaurada.
- Compararlas mediante un deslizador antes/después.
- Generar mapas de diferencias.
- Calcular métricas de calidad cuando exista una imagen de referencia confiable.
- Analizar las modificaciones mediante un modelo de visión con acceso a ambas imágenes.
- Mostrar advertencias sobre posibles artefactos generativos.
- Descargar la imagen procesada.

## 6. Arquitectura general del sistema

El siguiente diagrama representa el **flujo previsto**, no una arquitectura ya implementada:

```mermaid
flowchart LR
    A[Imagen de entrada] --> B[Preprocesamiento]
    B --> C[Modelo de difusión]
    C --> D[Imagen restaurada]
    D --> E[Evaluación y análisis visual]
    A -->|Original para comparación| E
    R[Referencia confiable si existe] -.->|PSNR y SSIM| E
    E --> F[Presentación en Gradio]
```

Se prevé separar las responsabilidades de carga y preprocesamiento, inferencia, evaluación, análisis visual e interfaz para reutilizar el código localmente y en Google Colab. Los módulos concretos todavía no existen.

El preprocesamiento deberá definir cómo manejar dimensiones, canales, profundidad de bits y normalización. Los mapas de diferencias requerirán imágenes comparables; PSNR y SSIM se calcularán contra una referencia confiable, no simplemente contra la entrada ruidosa. El modelo de visión recibirá la imagen original y la restaurada para describir cambios.

### Estructura real del repositorio

```text
astro-restauracion/
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
├── uv.lock
└── src/
    └── astro_restauracion/
        └── __init__.py
```

Existe además un entorno local `.venv/`, excluido del control de versiones. El único archivo Python del proyecto es `src/astro_restauracion/__init__.py`, cuya función `main()` imprime un saludo.

## 7. Tecnologías utilizadas y previstas

### Configuración existente

- **Python:** `.python-version` selecciona `3.12`; `pyproject.toml` declara `requires-python = ">=3.12"`.
- **uv:** gestión del entorno y las dependencias, con versiones resueltas en `uv.lock`.
- **Empaquetado:** backend `uv_build>=0.12.3,<0.13.0`.
- **Paquete:** `astro-restauracion`, versión `0.1.0`, importable como `astro_restauracion`.
- **Control de versiones:** Git y remoto de GitHub configurado.

Las dependencias directas declaradas actualmente son:

- `accelerate>=1.15.0`
- `diffusers>=0.42.1`
- `gradio>=6.31.0`
- `numpy>=2.5.4`
- `pillow>=12.3.0`
- `transformers>=5.22.2`

Estas declaraciones preparan el entorno; el código actual todavía no utiliza esas bibliotecas para procesar imágenes. **PyTorch (`torch`) está incluido en `uv.lock` como dependencia transitiva de Accelerate**, pero no está declarado como dependencia directa.

### Uso previsto

- **PyTorch y Hugging Face Diffusers:** inferencia del modelo de difusión.
- **Hugging Face Transformers:** integración del modelo de visión por seleccionar.
- **OpenCV:** procesamiento y filtro bilateral de referencia; pendiente de incorporación a las dependencias.
- **Pillow y NumPy:** lectura y manipulación de imágenes y arreglos.
- **scikit-image:** cálculo de métricas; pendiente de incorporación a las dependencias.
- **Gradio:** interfaz web y presentación de comparaciones.
- **Google Colab:** experimentos que requieran una GPU compatible.
- **Visual Studio Code:** entorno principal de desarrollo.

La configuración de Python y uv se conserva sin cambios. La declaración directa de PyTorch y la incorporación de las bibliotecas faltantes deberán resolverse durante la implementación.

## 8. Dataset y estrategia de evaluación

Se prevé utilizar imágenes astronómicas reales de datasets públicos. **Todavía no se seleccionó ni incorporó un dataset al repositorio**. Quedan pendientes su procedencia, licencia, criterios de selección, formatos y condiciones de uso.

### Evaluación controlada

1. Seleccionar imágenes astronómicas de buena calidad como referencias.
2. Agregar ruido artificial controlado, documentando su tipo, intensidad y semilla.
3. Procesar las versiones ruidosas mediante difusión y mediante el filtro bilateral.
4. Comparar los resultados con la referencia utilizando PSNR (*Peak Signal-to-Noise Ratio*), SSIM (*Structural Similarity Index*), mapas de diferencias e inspección visual de estrellas y estructuras difusas.

El ruido artificial se utilizará exclusivamente para evaluar la restauración; no implica generar imágenes astronómicas nuevas. Se deberá registrar la escala de valores empleada en las métricas y mantener condiciones comparables entre métodos. La evaluación controlada no garantiza que el comportamiento se generalice a todo ruido de adquisición real.

### Evaluación con imágenes ruidosas reales

Se procesarán imágenes que ya contengan ruido y se compararán visualmente los resultados, los mapas de diferencias y las observaciones del modelo de visión para identificar posibles artefactos.

Sin una referencia confiable, no se reportarán PSNR o SSIM como evidencia de recuperación de la señal original ni se podrá verificar de manera concluyente la autenticidad de todos los detalles restaurados. Un mapa de diferencias muestra dónde cambió la imagen, pero no determina si esos cambios son correctos.

### Línea base clásica y reproducibilidad

Se implementará un **filtro bilateral de OpenCV** para comparar un método tradicional con el modelo de difusión, sin asumir que la difusión ofrecerá mejores resultados.

Se prevé registrar imágenes de origen, degradaciones sintéticas, parámetros del filtro, identificador y revisión del modelo, intensidad de restauración, semillas, versiones y entorno de ejecución. Esto complementará el archivo de dependencias `uv.lock`.

**No hay experimentos, métricas ni resultados de restauración disponibles en el repositorio actual.**

## 9. Hardware y entorno de ejecución

Equipo disponible, según la información del proyecto:

- **Sistema operativo:** Windows.
- **GPU:** AMD Radeon RX 580 2048SP.
- **VRAM dedicada:** 8 GB.
- **RAM:** 16 GB.
- **Python de desarrollo:** 3.12.
- **IDE:** Visual Studio Code.
- **Gestor de dependencias:** uv.

### Limitaciones de ejecución local

La GPU AMD no permite utilizar directamente una distribución de PyTorch destinada a GPU NVIDIA mediante CUDA. El soporte de aceleración AMD depende de la combinación de GPU, sistema operativo y versiones del entorno. La RX 580 no figura en la [matriz de compatibilidad de Radeon para PyTorch en Windows con ROCm 7.2.1](https://rocmdocs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html); esta referencia no garantiza compatibilidad con otras versiones.

El proyecto no incluye una configuración validada de aceleración para este equipo. Los 8 GB de VRAM no garantizan que un pipeline sea compatible o pueda ejecutarse con cualquier resolución. La inferencia en CPU queda pendiente de validación y podría resultar lenta; no hay tiempos de ejecución medidos.

El desarrollo principal se realizará localmente en VS Code, con GitHub como repositorio central. Para experimentos que requieran GPU se contempla Google Colab, sujeto a disponibilidad de recursos y compatibilidad de las versiones. Todavía no hay notebooks ni un procedimiento de ejecución en Colab incorporados al repositorio.

## 10. Instalación y ejecución

### Requisitos

- Python 3.12 para reproducir la versión seleccionada en `.python-version`.
- uv disponible en la terminal.
- Una copia del repositorio y acceso a las dependencias, mediante red o caché local.

Desde la raíz del repositorio, sincronizar el entorno respetando el archivo de bloqueo:

```powershell
uv sync --locked
```

Ejecutar el punto de entrada definido en `pyproject.toml`:

```powershell
uv run --locked astro-restauracion
```

Salida actual esperada:

```text
Hello from astro-restauracion!
```

Este comando ejecuta únicamente la función inicial de prueba: todavía no inicia una interfaz Gradio ni carga modelos.

### Verificación realizada

En el entorno local existente, con uv `0.12.3`, se verificaron satisfactoriamente los siguientes comandos utilizando la caché disponible:

```powershell
uv sync --locked --offline
uv run --locked --offline astro-restauracion
```

La sincronización respetó `uv.lock` y la ejecución produjo el saludo mostrado. La opción `--offline` requiere las dependencias en caché; esta comprobación no equivale a validar una instalación desde cero, la descarga de modelos ni la inferencia en GPU.

## 11. Alcance y limitaciones

### Incluido en el alcance previsto del MVP

- Reducción de ruido en imágenes astronómicas PNG o TIFF.
- Uso de un modelo de difusión preentrenado de Hugging Face.
- Modelo de visión para análisis comparativo.
- Comparación antes/después y mapas de diferencias.
- Métricas de evaluación con referencia confiable.
- Interfaz Gradio y descarga del resultado.
- Documentación y reproducibilidad experimental.

### Fuera del alcance inicial

- Entrenamiento de modelos desde cero.
- Superresolución.
- Reconstrucción de regiones faltantes.
- Procesamiento de archivos FITS.
- Corrección de desenfoque.
- Verificación astrométrica automática.
- Garantía de autenticidad científica de las estructuras restauradas.

### Interpretación de los resultados futuros

La restauración visual y la verificación científica son tareas distintas. El procesamiento generativo puede alterar o inventar estructuras; ni la inspección visual, ni un modelo de visión, ni una mejora en PSNR o SSIM prueban por sí solos la autenticidad astronómica de cada detalle. La imagen original deberá conservarse como referencia para la comparación.

## 12. Estado actual del desarrollo

### Implementado o configurado

- Estructura inicial de paquete bajo `src/astro_restauracion/`.
- Metadatos de versión y autoría en `pyproject.toml`.
- Selección local de Python 3.12 y requisito de Python `>=3.12`.
- Gestión con uv, backend `uv_build` y archivo `uv.lock`.
- Dependencias directas enumeradas en la sección de tecnologías.
- Comando `astro-restauracion`, que imprime un saludo.
- Exclusión del entorno virtual y archivos generados mediante `.gitignore`.
- Remoto GitHub configurado.

### Pendiente de implementación o validación

- Todas las funcionalidades del MVP, incluidos carga de imágenes, preprocesamiento, inferencia, comparación, análisis, métricas e interfaz.
- Selección de datasets y modelos definitivos.
- Filtro bilateral y protocolo experimental reproducible.
- Incorporación de OpenCV y scikit-image y revisión de la declaración de PyTorch.
- Compatibilidad de ejecución local, uso de GPU y reutilización en Colab.
- Pruebas del procesamiento y resultados experimentales.

### Observaciones de consistencia

El README previo estaba vacío y no contenía información técnica que conservar. Se mantuvieron los nombres reales del paquete y del comando, los metadatos existentes y la configuración de Python y uv.

El nombre público **AstroRestore AI** convive con el nombre técnico `astro-restauracion` sin renombrar el paquete. La descripción de `pyproject.toml` conserva el texto inicial `Add your description here`, por lo que aún no refleja el objetivo documentado. Esta actualización solo modifica el README.

## 13. Próximas etapas

1. Seleccionar datasets públicos y documentar procedencia, licencias y criterios de evaluación.
2. Definir el tratamiento de PNG y TIFF, incluidos profundidad de bits, canales, normalización y dimensiones.
3. Validar el entorno de inferencia y decidir la ejecución local o en Colab; revisar las dependencias necesarias.
4. Evaluar el modelo candidato y seleccionar el modelo de difusión y el modelo de visión según licencia, compatibilidad y resultados.
5. Implementar componentes modulares de carga, preprocesamiento, restauración y línea base bilateral.
6. Implementar mapas de diferencias, PSNR y SSIM para el protocolo con referencia y registrar parámetros y semillas.
7. Integrar el análisis visual comparativo y las advertencias sobre artefactos generativos.
8. Construir la interfaz Gradio con intensidad ajustable, comparación y descarga.
9. Ejecutar los experimentos controlados y con ruido real, documentar resultados verificables y actualizar las instrucciones de uso.
