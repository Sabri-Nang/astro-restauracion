# Comprobaciones de etapa 4 — 15 de noviembre de 2026

## Copia nueva y arranque

Se clonó localmente el commit `13183a8` en una carpeta nueva de `outputs/`, sin copiar el entorno virtual. `uv sync --locked --python 3.12` creó otro entorno con Python 3.12.10 e instaló 75 paquetes desde la caché de dependencias. Es una instalación nueva con caché disponible, no una prueba con caché vacía ni una ejecución Linux/Colab.

La aplicación de esa copia arrancó en un puerto local independiente y respondió HTTP 200. La llamada al endpoint del ensayo guardado devolvió las imágenes reales preservadas, la identificación `ensayo_guardado_sin_nueva_inferencia` y el ZIP con original, entrada preparada, salida IA, diferencias, informe, parámetros y límites. Se comprobó que el modelo de visión registrado es `openai/clip-vit-base-patch32`. El servidor temporal se cerró al terminar.

Esta comprobación no descargó pesos ni ejecutó difusión. La visión real se verificó por separado sobre las imágenes del ensayo; su evidencia está en `assets/ejemplos/etapa3_tile/`. Las pruebas automatizadas del recorrido nuevo usan difusión simulada.

La suite completa pasó **55 pruebas** tanto en el entorno de desarrollo como en la copia nueva. Incluye similitudes conocidas, entradas incompatibles, recuperación de CLIP sin repetir difusión y conservación del original y parámetros en el ZIP. Las advertencias de recursos de Gradio no produjeron fallos; no constituyen una validación visual ni una medición de denoising.

## Pendientes explícitos

El inventario de herramientas de escritorio informó que el host de acceso al navegador no está disponible. Por eso no se da por revisado el diseño en pantalla ni se generaron capturas de interfaz. Quedan por comprobar teclado, modo oscuro, móvil y comprensión con una persona.

La nueva versión integrada todavía debe ejecutarse de principio a fin en Colab con GPU para registrar la demo. El notebook admite el paquete local sin exigir publicación previa; su sintaxis Python fue comprobada al generarlo. No se atribuye esta validación a una sesión de Colab que no ocurrió.
