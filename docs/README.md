# Documentación complementaria

El [README principal](../README.md) sigue el template del docente: presentación,
persona, demo, honestidad, instalación, uso y decisiones. Aquí se conserva el
detalle técnico y de seguimiento que no necesita estar en esa primera lectura.

## Proyecto y ejecución

- [Fundamentos y persona](fundamentos_y_persona.md): objetivos, perfil completo de Julia, evolución de la estructura y colaboración con Codex.
- [Arquitectura técnica](arquitectura_tecnica.md): módulos, árbol de archivos, versiones, revisiones de modelos, hardware y comprobaciones sin inferencia.
- [Instalación detallada](instalacion_detallada.md): notebook integrado actual y antecedentes de Colab/VS Code, HTTP 403, subida y tiempos de la prueba inicial.
- [Plan de trabajo](plan_de_trabajo.md): etapas del docente, evidencias de cierre, pendientes y contingencia.

## Interfaz, análisis y entrega

- [Diseño de la interfaz](diseno_interfaz.md): recorrido de Julia, controles, resaltado, descarga y criterios de revisión.
- [Análisis visual](analisis_visual.md): frases y afinidades CLIP, informe, límites y validación.
- [Preparación de entrega](entrega_etapa4.md): comprobación en Colab, capturas y guion de video de cinco minutos.
- [Verificación de etapa 4](verificacion_etapa4.md): pruebas realizadas y su alcance; incluye comprobaciones históricas de 55 pruebas y la revisión posterior de 62, sin atribuir inferencias simuladas a modelos reales.

## Experimentos y datos

- [Experimentos y evaluación](experimentos_y_evaluacion.md): generación gaussiana, barridos SD/Tile, controles VAE, métricas, validación técnica de cinco imágenes y resultados registrados.
- [Procedencia de los ejemplos](../assets/ejemplos/README.md): fuentes, créditos, licencias y modificaciones.
- [Catálogo de ruido gaussiano](../assets/ruido_gaussiano/README.md): seis pares preparados, parámetros y registros de reproducción.
- [Evidencia real de Tile y CLIP](../assets/ejemplos/etapa3_tile/README.md): imágenes públicas, registros e informe del caso versionado.

Los comandos de estos documentos se ejecutan desde la **raíz del repositorio**.
Los enlaces a `outputs/` apuntan a artefactos locales excluidos de Git; no se
descargan al clonar. Las capturas de la interfaz actual, el video, la reflexión
personal y la licencia del código siguen pendientes. La preparación del conjunto
gaussiano no implica haber restaurado ni evaluado sus seis imágenes.
