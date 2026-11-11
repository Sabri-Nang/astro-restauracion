# Instrucciones para agentes — AstroRestore AI

Estas instrucciones se aplican a todo el repositorio.

- Escribir documentación, comentarios e interfaz en español claro y técnico.
- Mantener Python 3.12 como versión de desarrollo y uv como gestor del entorno.
- Gestionar dependencias en `pyproject.toml` y actualizar `uv.lock` con uv.
- Conservar `uv.lock` en el control de versiones.
- Mantener la aplicación sin empaquetado instalable (`tool.uv.package = false`).
- Ejecutar desde la raíz con `uv run --locked python app.py`.
- Mantener la interfaz en `app.py`, la difusión en `src/diffusion.py`, el análisis
  visual en `src/analysis.py` y diferencias y advertencias en `src/honesty.py`.
- No cargar modelos ni descargar pesos al importar módulos.
- Mantener el código reutilizable desde el notebook de `colab/`.
- Limitar el MVP a reducción de ruido; desenfoque, FITS y superresolución quedan fuera.
- Diferenciar funciones implementadas de planes; no inventar resultados ni métricas.
- No presentar restauración visual ni análisis de IA como verificación científica.
- Calcular PSNR y SSIM únicamente con una referencia confiable.
- Documentar procedencia, licencia y atribución de cada imagen de ejemplo.
- No versionar tokens, credenciales, entornos virtuales ni pesos de modelos.
- Actualizar el README cuando cambien estructura, ejecución o funciones disponibles.
- Verificar los cambios con comprobaciones proporcionales; no descargar modelos
  ni ejecutar inferencias costosas para comprobar cambios de estructura.
- No realizar commits ni push sin autorización explícita del usuario.
