# Análisis visual implementado

`src/analysis.py` integra CLIP ViT-B/32 de Hugging Face, revisión fija `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`, licencia MIT. Los pesos se cargan solo al pedir el análisis. Se usa CPU float32, procesador PIL explícito, redimensionamiento y recorte central estándar a 224 píxeles. Las versiones de Transformers y Torch y la configuración del procesador quedan registradas.

Se comparan embeddings normalizados de la entrada preparada y la salida con seis frases fijas en inglés. Los resultados son similitudes coseno y sus diferencias, sin softmax. No son porcentajes ni probabilidades calibradas. El informe en español se construye con una plantilla determinista: CLIP no redacta libremente ni determina qué estrella fue inventada. Un resultado favorable a una frase no acredita reducción de ruido.

La interfaz usa SD 1.5 + ControlNet Tile con la misma entrada como condición, fuerza 1, guidance 1 y DDIM. Intensidad inicial 0,10, 30 pasos configurados (3 efectivos), semilla 42 y lado máximo 256. Son condiciones del ensayo, no una recomendación validada de restauración. El filtro de seguridad permanece activo.

Si falla CLIP se mantienen las imágenes y la descarga; «Reintentar informe y descarga» evita otra inferencia de difusión. El ZIP conserva original, entrada preparada, salida, mapa, informe, parámetros, límites y hashes. Sin referencia confiable no se calculan métricas de fidelidad.

## Evidencia y alcance de la comprobación

- Difusión real: ensayo Tile en Colab previamente recibido y revisado, dos salidas válidas y dos bloqueos.
- Visión real: CLIP ejecutado localmente en CPU sobre la entrada gaussiana preservada y la salida Tile 0,10. [Ejemplo versionado](../assets/ejemplos/etapa3_tile/README.md).
- Integración: pruebas de recorrido, ZIP y recuperación usando difusión simulada; no se atribuye una nueva inferencia GPU a estas pruebas.
- La comprobación interactiva del nuevo recorrido completo en Colab corresponde a la preparación de la demo de etapa 4. No se inventa una captura ni una sesión completa de usuario.

La etapa 3 cierra su implementación, informe y ejemplos. La mejora de calidad queda como investigación posterior: la entrada ruidosa sigue superando las salidas SD/Tile en PSNR y SSIM del ensayo conocido. No hay un ejemplo de denoising exitoso validado.

## Presentación para la usuaria

La vista principal utiliza `render_user_report`: presenta las dos frases con mayor afinidad de cada imagen, explica que el orden puede cambiar por diferencias pequeñas y pide comparar estrellas, fondo y contornos. No muestra cifras como puntuación de calidad; los valores exactos permanecen en `parametros.json`. `render_report` conserva el informe técnico para evidencia e investigación. El resaltado amarillo se calcula a partir de píxeles y no depende de CLIP ni localiza autenticidad.
