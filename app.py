"""Punto de entrada de la interfaz de AstroRestore AI."""

import gradio as gr


def create_app() -> gr.Blocks:
    """Construye la interfaz inicial sin cargar modelos ni procesar imágenes."""
    with gr.Blocks(title="AstroRestore AI") as app:
        gr.Markdown("# AstroRestore AI")
        gr.Markdown(
            "Aplicación en desarrollo para la reducción de ruido y el análisis "
            "de imágenes astronómicas.\n\n"
            "La restauración, la comparación y el análisis visual todavía "
            "no están implementados."
        )
    return app


if __name__ == "__main__":
    create_app().launch()
