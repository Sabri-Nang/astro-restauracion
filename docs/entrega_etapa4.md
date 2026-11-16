# Preparación de entrega — etapa 4

La etapa 3 quedó implementada y documentada. Se retoma la revisión centrada en Julia y una base de diseño reutilizable, según lo pedido por la autora. La calidad del denoising sigue sin estar demostrada; mejorarla es trabajo posterior.

## Prueba del recorrido en Colab

1. Ejecutar `uv run --locked python colab/preparar_app.py` desde la raíz. Genera `outputs/astrorestore_app_colab.zip`, sin pesos, entornos ni credenciales.
2. Subir `colab/app_integrada.ipynb` a Colab, elegir GPU T4 y ejecutar las celdas. El origen inicial es el paquete local, para no depender de un push. Tras publicar se puede seleccionar GitHub.
3. Registrar commit, GPU, parámetros, duración y si ocurrió algún error. Subir una foto propia compatible y ejecutar el recorrido real. Los ensayos históricos se consultan en la documentación, sin botones de ejemplo en la interfaz.
4. Descargar el ZIP y conservarlo fuera de Colab. No confundir abrir un resultado previo con ejecutar otra inferencia.

El notebook está generado y sus celdas Python compiladas localmente; su ejecución en Colab todavía requiere una sesión real. Los notebooks anteriores se conservan como evidencia histórica de experimentos.

## Guion propuesto del video de cinco minutos

- 0:00–0:40: problema de Julia, objetivo limitado a ruido y advertencia de reconstrucción.
- 0:40–1:20: subir una imagen con permiso de uso, mostrar su crédito y explicar el control de cuánto puede cambiar la IA la foto. No prometer limpieza.
- 1:20–2:20: iniciar procesamiento real. Si se recorta la espera en edición, indicarlo; no presentar el ensayo guardado como nueva inferencia.
- 2:20–3:20: comparar las mismas regiones y alternar el resaltado amarillo; explicar que indica cambios, sin identificar cuáles son correctos o inventados.
- 3:20–4:10: leer CLIP y sus límites, mostrar parámetros y descargar el ZIP.
- 4:10–5:00: explicar el resultado desfavorable del ensayo y qué se investigaría después. La reflexión debe ser la de la autora.

## Capturas necesarias

Capturar la interfaz real con advertencia, comparación e informe; mantener el crédito de la imagen. Incluir un caso de alteración y, si aparece en la sesión, un error o bloqueo con su mensaje real. Nunca fabricar un bloqueo para la captura. Revisar ancho móvil, modo oscuro y navegación con teclado antes de declararlos validados.

## Pendientes para cerrar la etapa 4

- Validación de la interfaz integrada en Colab y revisión visual de sus estados.
- Capturas o GIF del uso actual, con atribución.
- Grabar, publicar y enlazar el video real.
- La autora debe redactar su reflexión personal y elegir la licencia del código; no se completa en su nombre.
- Revisión final de los requisitos obligatorios, enlaces y accesibilidad de la entrega.

Los modelos y las imágenes tienen licencias documentadas independientes de la licencia que se elija para el código. No atribuir el rendimiento a entrenamiento: se usaron modelos preentrenados.
