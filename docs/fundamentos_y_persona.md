# Fundamentos, alcance y persona usuaria

Detalle trasladado del README principal. El resumen de presentación se mantiene en el README; aquí se conserva el contexto de Julia y los objetivos del proyecto.

## Objetivos del proyecto

### Objetivo general

Desarrollar una aplicación que permita reducir el ruido de imágenes astronómicas mediante un modelo de difusión preentrenado de Hugging Face, incorporando herramientas de comparación y análisis para evaluar las modificaciones introducidas por el procesamiento.

El proyecto busca estudiar hasta qué punto las transformaciones conservan la información astronómica original, además de explorar la mejora de la apariencia visual.

### Objetivos específicos

- Evaluar un modelo preentrenado para reducción de ruido sin entrenar un modelo desde cero.
- Permitir la carga de imágenes PNG o TIFF y el ajuste de la intensidad de restauración.
- Facilitar la comparación entre imagen original y procesada mediante vistas antes/después, un deslizador y mapas de diferencias.
- Como mejora opcional, calcular PSNR y SSIM cuando exista una referencia confiable.
- Como mejora opcional, comparar el modelo con un filtro bilateral de OpenCV como línea base clásica.
- Incorporar un modelo de visión que analice ambas imágenes y describa modificaciones y posibles artefactos.
- Comunicar las limitaciones del procesamiento generativo y favorecer experimentos reproducibles.

Estos objetivos no representan funcionalidades ya implementadas ni garantías de conservación de información.

## Persona Usuaria

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

La interfaz ofrece carga, difusión con Tile, comparación, análisis CLIP y descarga. El ensayo gaussiano controlado se mantiene separado en consola y notebook; no se inventa una referencia limpia para las imágenes del usuario.

### Evolución de la estructura

El nombre público **AstroRestore AI** convive con el nombre técnico del proyecto `astro-restauracion`. Se eliminó el antiguo paquete `src/astro_restauracion/` y su comando de saludo para adoptar la disposición solicitada. Se preservaron autoría, versión, selección de Python y dependencias directas; la descripción de `pyproject.toml` ahora refleja el objetivo del proyecto. El archivo `uv.lock` se actualizó para representar la aplicación sin empaquetado.

## Uso de Agentes de IA

**Herramienta utilizada en esta colaboración:** Codex. Se usa para inspeccionar el repositorio, proponer e implementar cambios, verificar código y apoyar la documentación. Las instrucciones del proyecto están en `AGENTS.md`.

**Decisiones expresadas o aceptadas por la autora:** caso astronómico y persona Julia, sub-tarea B con foco exclusivo en reducción de ruido, continuidad por etapas y commits pequeños. La autora aceptó el primer avance de comparación y autorizó sus commits y publicación. También confirmó el funcionamiento de la app desde el enlace de Colab.

**Propuestas e implementaciones del agente:** cálculo de diferencias con escala fija, centralización de advertencias, conexión con Gradio, pruebas sin inferencia y reorganización de este README. El agente propuso evaluar primero SD 1.5 con ruido controlado y considerar ControlNet Tile si las estructuras se alteran demasiado. El modelo inicial SD 1.5 estaba documentado como propuesta a evaluar; no se atribuye su elección original a una persona sin evidencia adicional.

**Revisión y límites:** se registraron cinco pruebas técnicas con observaciones visuales. La suite automatizada se amplió durante el desarrollo hasta las 62 pruebas del último registro de etapa 4; no se confunde con cinco nuevas inferencias. La aceptación de cambios no sustituye la revisión visual pendiente de la nueva interfaz. La autora debe poder explicar el código entregado y completar su reflexión personal.

**Opciones pospuestas:** cambio directo a SDXL y múltiples modelos. Las métricas se incorporaron posteriormente para evaluar el barrido autorizado por la autora. Los modelos alternativos no se presentan como probados ni descartados por resultados experimentales.

[Volver al README principal](../README.md).
