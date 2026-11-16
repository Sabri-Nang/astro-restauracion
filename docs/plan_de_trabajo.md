# Plan de trabajo por etapas

Seguimiento del cronograma del docente. Las fechas previstas se distinguen de las ejecuciones registradas. El recorrido vigente de Julia está en el README; los controles técnicos adicionales corresponden al laboratorio. La interfaz expone únicamente intensidad, con 30 pasos, semilla 42 y lado máximo 256 fijos. Las seis imágenes gaussianas ya están preparadas; queda ampliar la evaluación de restauración.

## Alcance del MVP

El alcance comprende las funcionalidades siguientes. La app permite cargar PNG/TIFF compatibles, ajustar la intensidad, ejecutar difusión y CLIP, comparar entrada y salida, revisar zonas amarillas y descargar un ZIP con diferencias y parámetros. Los otros controles técnicos permanecen en el laboratorio. La eficacia de reducción de ruido sigue sin demostrarse:

- Cargar imágenes astronómicas PNG o TIFF.
- Aplicar un modelo de difusión preentrenado de Hugging Face para reducción de ruido.
- Ajustar la intensidad de restauración.
- Visualizar las imágenes original y restaurada.
- Compararlas mediante un deslizador antes/después.
- Generar mapas de diferencias.
- Como mejora opcional, calcular métricas de calidad cuando exista una imagen de referencia confiable.
- Analizar las modificaciones mediante un modelo de visión con acceso a ambas imágenes.
- Mostrar advertencias sobre posibles artefactos generativos.
- Descargar la imagen procesada.

## Plan según las etapas del docente

Las fechas siguientes corresponden al cronograma propuesto por el docente. Las pruebas técnicas de etapa 2 se registraron el 11 de noviembre de 2026; el primer avance de comparación de etapa 3 se verificó posteriormente. No se atribuyen retrospectivamente a las fechas previstas.

#### Etapa 1 — Fundamentos (4–5 de noviembre) — completada

- [x] Persona Julia definida y documentada.
- [x] Proyecto, problema y alcance declarados: sub-tarea B, con denoising como foco del MVP.
- [x] Repositorio creado, estructurado y publicado con historial de commits.
- [x] Entorno Python 3.12 y uv funcionando.
- [x] Hardware y limitaciones documentados; modelo cargado e imagen de prueba generada en CPU y en una T4 de Colab.

**Evidencia:** registros locales de la prueba CPU y salidas de la prueba T4 conservadas en el notebook. El modelo tiene revisión y licencia identificadas. No se entrenó un modelo desde cero.

#### Etapa 2 — Prototipo básico (6–9 de noviembre) — completada el 11 de noviembre de 2026

- [x] Interfaz Gradio con carga de PNG/TIFF de 8 bits.
- [x] Procesamiento real con Stable Diffusion 1.5.
- [x] Entrada preparada y salida en la misma pantalla, sin modificar el archivo de origen.
- [x] Arranque con el comando exacto `uv run app.py`, verificado por HTTP.
- [x] Aplicación accesible en Colab desde el enlace público, según confirmación de la autora.
- [x] Commits pequeños que muestran la evolución y las correcciones.
- [x] Pruebas técnicas completas con cinco imágenes distintas y revisión de sus comparaciones; registro local en `outputs/etapa2/resumen.json`.

**Criterio de cierre:** cinco ejecuciones correctas sobre entradas distintas, con salida y registro por caso. Se verifican dimensiones, salidas no uniformes, hashes y comparación visual. El procesamiento básico acredita la integración del modelo; no se presenta como reducción de ruido demostrada. La generación de ruido, el análisis visual y la comparación triple no son prerrequisitos para cerrar esta etapa.

**Entregable:** aplicación que procesa imágenes mediante `uv run app.py`, ejecución alternativa en Colab y resultados reproducibles de las cinco pruebas mediante `src/validation.py`.

#### Etapa 3 — Análisis visual y honestidad (10–13 de noviembre) — implementada y documentada

Integración completada el 15 de noviembre de 2026: CLIP ViT-B/32 e informe comprensible con afinidades de frases fijas. Se mantiene SD + Tile como decisión provisional; optimizar los resultados queda para después.

- [x] Integrar el análisis de imágenes original y procesada con un modelo de Hugging Face.
- [x] Mostrar un informe en lenguaje natural y comunicar sus límites.
- [x] Documentar ejemplos reales de aciertos y de fallos o alteraciones de estructuras.
- [x] Mantener elementos de honestidad ya disponibles: comparación, control de intensidad y advertencias de reconstrucción.
- [x] Incorporar un mapa de diferencias en `honesty.py`, deslizador en Gradio y advertencias sobre la reconstrucción por IA.

**Cierre implementado:** SD + Tile → comparación → análisis CLIP → informe y descarga. La difusión real del ensayo Colab y el análisis CLIP real sobre sus imágenes están preservados en el [ejemplo versionado](../assets/ejemplos/etapa3_tile/README.md). Las pruebas de integración usan difusión simulada; no se presentan como una nueva ejecución GPU. Los dos barridos y los controles VAE muestran límites: ninguna salida válida supera la entrada ruidosa en PSNR/SSIM. Se documenta el acierto técnico y el fallo de restauración, sin inventar un éxito de limpieza. La prueba interactiva del recorrido completo corresponde a la demo de etapa 4.

**Experimento acotado de ruido:** conservar el TIFF y preparar una referencia común; agregar inicialmente un nivel de ruido gaussiano con NumPy y una semilla propia. Procesar esa versión manteniendo fija la semilla del modelo y comparar **referencia preparada → imagen ruidosa → salida procesada**. Registrar dimensiones, canales, normalización, saturación y parámetros. Cambiar un parámetro por vez al explorar pasos e intensidad. Esto evalúa el modelo preentrenado; no lo entrena. La referencia publicada no es una observación científica perfecta y el ruido sintético no representa todo ruido real.

Para una imagen que ya tiene ruido, sin referencia limpia, mostrar entrada y salida sin inventar una referencia. Si el modelo borra o inventa detalles, registrar el fallo y revisar su adecuación. El mapa de diferencias indica modificaciones, no autenticidad.

**Criterio de cierre:** carga → difusión → análisis visual → resultados, con explicaciones comprensibles y ejemplos documentados. El análisis visual es obligatorio para la entrega final; las métricas y una línea base clásica son opcionales.

- [x] Recordatorio retomado al cerrar la etapa 3: revisar la interfaz pensando en Julia y evaluar un sistema de diseño. Se aborda en etapa 4.

#### Etapa 4 — Documentación y demo (14–16 de noviembre) — en curso

- [x] Incorporar pasos de uso, ayudas de parámetros, progreso, reintento de CLIP y limpieza de resultados al cambiar de entrada. Revisión visual pendiente.
- [x] Organizar el README según el template del docente, conservando modelos, licencias y hardware probado.
- [ ] Completar capturas, video, reflexión de la autora y licencia del código antes de la entrega.
- [ ] Incorporar capturas y ejemplos reales de uso.
- [x] Documentar decisiones desde HAI e identificar decisiones expresadas por la autora y propuestas del agente.
- [ ] Incorporar la captura pendiente a **Qué es real y qué es inventado** y revisar el texto con los resultados finales.
- [x] Instalación bloqueada y arranque desde una copia nueva local, con descarga del ensayo guardado comprobada; sin nueva inferencia. [Registro y alcance](verificacion_etapa4.md). La ejecución completa en Colab sigue pendiente.
- [ ] Grabar y enlazar la demo de cinco minutos: problema, uso completo, resultados y reflexión sobre la reconstrucción.
- [ ] Revisar todos los requisitos técnicos y documentales obligatorios.

**Criterio de cierre:** otra persona puede seguir el README y completar el pipeline, con documentación y video accesibles. Los resultados deben ser observados y registrados, nunca supuestos.

#### Etapa 5 — Contingencia y buffer (17–18 de noviembre) — reservada

Resolver errores finales, completar el formulario de entrega con tiempo y preparar la defensa de las decisiones y conceptos aplicados. No agregar funciones complejas, cambiar los modelos principales ni rehacer el proyecto durante esta etapa.

#### Estrategia de trabajo

**Consigna de referencia:** [Trabajo Integrador 2, notebook original — arquitectura y stack](https://colab.research.google.com/drive/1PjBnThBhDF8x5gYSmbROR_vO7y7AUltV#scrollTo=DRET79IqJzQt). Revisada nuevamente para mantener el alcance: el procesamiento principal debe usar un modelo de difusión de Hugging Face y completar carga → difusión → análisis visual → resultados. Para la sub-tarea B, la guía propone SD/SDXL img2img de baja intensidad y ControlNet Tile como referencias; no exige un modelo específico ni entrenamiento. Los métodos sin difusión solo sirven como comparación y no sustituyen ese requisito. La etapa 3 ya integra el análisis visual y su informe comprensible; los nuevos experimentos de optimización y las líneas base son complementarios y no deben desplazar ese cierre. Los resultados desfavorables del ensayo se conservan como evidencia de límites, sin atribuirles reducción de ruido lograda.

Mantener siempre una versión que funcione. Priorizar difusión y análisis, honestidad sobre las modificaciones, documentación y demo. PSNR, SSIM, LPIPS, filtros clásicos, múltiples modelos, historial, lotes y despliegue público son opcionales. Evitar bloqueos técnicos de más de dos horas: simplificar tamaño o alcance, buscar alternativas y consultar al docente o al grupo cuando corresponda. Antes de ampliar el alcance, revisar: **si se entrega hoy, ¿cumple los requisitos obligatorios?**

[Volver al README principal](../README.md).
