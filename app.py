"""Punto de entrada de la interfaz de AstroRestore AI."""
import gradio as gr
from src.analysis import analyze_images, render_report
from src.diffusion import run_diffusion
from src.export import export_result
from src.honesty import DISCLAIMER, DIFFERENCE_NOTICE, difference_map


def process_image(path, strength, steps, seed, size):
    """Procesa con SD + Tile y conserva la comparación preparada."""
    if not path:
        raise gr.Error("Subí una imagen PNG o TIFF antes de ejecutar la prueba.")
    try:
        prepared, processed, metadata = run_diffusion(
            path, strength=float(strength), steps=int(steps),
            seed=int(seed), max_size=int(size), controlnet_tile=True, controlnet_scale=1.0,
        )
        return prepared, processed, (prepared, processed), difference_map(prepared, processed), metadata
    except (ValueError, OSError, RuntimeError) as error:
        raise gr.Error(str(error)) from error


def complete_analysis(state):
    """Permite reintentar CLIP sin volver a ejecutar difusión."""
    if not state:
        raise gr.Error("Primero procesá una imagen.")
    before, after, metadata, path = state
    metadata = dict(metadata)
    try:
        analysis = analyze_images(before, after)
        metadata["analisis_visual"] = analysis
        report = render_report(analysis)
    except (ImportError, ValueError, OSError, RuntimeError) as error:
        metadata["analisis_visual"] = {"estado": "error", "detalle": str(error)}
        report = ("### Análisis visual no disponible\n\nLa difusión terminó y sus imágenes se conservan. "
                  "Podés descargar el resultado o reintentar solo CLIP. No hay observaciones del modelo "
                  "de visión para esta ejecución.\n\nDetalle: " + str(error))
    try:
        archive = export_result(before, after, metadata, report, path)
    except OSError as error:
        archive = None
        report += "\n\nNo se pudo preparar la descarga: " + str(error)
    return report, metadata, archive


def run_complete(path, strength, steps, seed, size, progress=gr.Progress()):
    """Recorrido completo; no calcula métricas sin referencia conocida."""
    progress(0.05, desc="Preparando SD + Tile; la primera ejecución descarga los modelos")
    result = process_image(path, strength, steps, seed, size)
    state = (result[0], result[1], result[4], path)
    progress(0.8, desc="Comparando ambas imágenes con CLIP en CPU")
    report, metadata, archive = complete_analysis(state)
    progress(1, desc="Resultado disponible")
    return (*result[:4], metadata, report, archive, state)


def create_app() -> gr.Blocks:
    """Construye la interfaz sin descargar modelos al iniciarse."""
    with gr.Blocks(title="AstroRestore AI") as app:
        gr.Markdown("# AstroRestore AI\nExplorá cómo SD 1.5 + ControlNet Tile transforma tu imagen astronómica.")
        gr.Markdown(DISCLAIMER)
        gr.Markdown("Usamos Tile con la propia entrada como condición, sin ampliar resolución. "
                    "La primera prueba descarga varios GB; en CPU la difusión puede demorar mucho. "
                    "Los ensayos actuales no demostraron mejor limpieza que conservar la entrada ruidosa.")
        upload = gr.File(label="Imagen de entrada (PNG o TIFF de 8 bits)", file_types=[".png", ".tif", ".tiff"], type="filepath")
        with gr.Row():
            strength = gr.Slider(0.1, 0.5, value=0.1, step=0.05, label="Intensidad de transformación", info="Más intensidad puede borrar o inventar detalles; no es porcentaje de ruido eliminado.")
            steps = gr.Slider(10, 30, value=30, step=1, label="Pasos configurados", info="Pasos efectivos = parte entera de pasos × intensidad. 30 × 0,10 = 3.")
            seed = gr.Number(value=42, precision=0, label="Semilla del modelo")
            size = gr.Dropdown([256, 512], value=256, label="Lado máximo (píxeles)")
        button = gr.Button("Procesar y comparar", variant="primary")
        with gr.Row():
            prepared = gr.Image(label="Entrada preparada", interactive=False, format="png")
            processed = gr.Image(label="Reconstrucción por IA", interactive=False, format="png")
        comparison = gr.ImageSlider(label="Entrada (izquierda) / reconstrucción (derecha)", interactive=False, format="png")
        gr.Markdown("Mové el deslizador y examiná fondo, puntos luminosos y contornos. "
                    "La comparación usa la entrada convertida a RGB y ajustada de tamaño; se conserva el archivo original.")
        differences = gr.Image(label="Diferencias absolutas · escala fija 0–255", interactive=False, image_mode="L", format="png")
        gr.Markdown(DIFFERENCE_NOTICE)
        report = gr.Markdown("El informe orientativo de CLIP aparecerá después de procesar.")
        retry = gr.Button("Reintentar solo análisis visual")
        archive = gr.File(label="Descargar imágenes, informe y parámetros (ZIP)", interactive=False)
        metadata = gr.JSON(label="Parámetros y registro completo")
        state = gr.State()
        button.click(run_complete, inputs=[upload, strength, steps, seed, size],
                     outputs=[prepared, processed, comparison, differences, metadata, report, archive, state], concurrency_limit=1)
        retry.click(complete_analysis, inputs=[state], outputs=[report, metadata, archive], concurrency_limit=1)
    app.queue(default_concurrency_limit=1)
    return app

if __name__ == "__main__":
    create_app().launch()
