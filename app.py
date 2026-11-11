"""Punto de entrada de la interfaz de AstroRestore AI."""

import gradio as gr

from src.diffusion import DISCLAIMER, run_diffusion


def process_image(path, strength, steps, seed, size):
    """Conecta la prueba de difusión con la interfaz y comunica errores."""
    if not path:
        raise gr.Error("Subí una imagen PNG o TIFF antes de ejecutar la prueba.")
    try:
        return run_diffusion(
            path, strength=float(strength), steps=int(steps),
            seed=int(seed), max_size=int(size),
        )
    except (ValueError, OSError, RuntimeError) as error:
        raise gr.Error(str(error)) from error


def create_app() -> gr.Blocks:
    """Construye la interfaz sin descargar ni cargar modelos al iniciarse."""
    with gr.Blocks(title="AstroRestore AI") as app:
        gr.Markdown("# AstroRestore AI")
        gr.Markdown(
            "Prueba inicial del modelo de difusión. Subí una imagen PNG o TIFF "
            "de 8 bits para comprobar el procesamiento imagen a imagen.\n\n"
            "La primera ejecución descarga los pesos del modelo (varios GB). "
            "En CPU puede demorar. La generación de ruido controlado y el "
            "análisis visual todavía están pendientes."
        )
        gr.Markdown(DISCLAIMER)
        upload = gr.File(label="Imagen de entrada (PNG o TIFF)", file_types=[".png", ".tif", ".tiff"], type="filepath")
        with gr.Row():
            strength = gr.Slider(0.1, 0.5, value=0.2, step=0.05, label="Intensidad de transformación")
            steps = gr.Slider(10, 30, value=10, step=1, label="Pasos de difusión")
            seed = gr.Number(value=42, precision=0, label="Semilla")
            size = gr.Dropdown([256, 512], value=256, label="Lado máximo (píxeles)")
        button = gr.Button("Ejecutar prueba de difusión", variant="primary")
        with gr.Row():
            prepared = gr.Image(label="Entrada preparada para el modelo", interactive=False)
            processed = gr.Image(label="Salida generativa de prueba", interactive=False)
        metadata = gr.JSON(label="Parámetros y registro de la prueba")
        button.click(
            process_image, inputs=[upload, strength, steps, seed, size],
            outputs=[prepared, processed, metadata], concurrency_limit=1,
        )
    app.queue(default_concurrency_limit=1)
    return app


if __name__ == "__main__":
    create_app().launch()
