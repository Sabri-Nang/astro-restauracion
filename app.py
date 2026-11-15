"""Punto de entrada de la interfaz de AstroRestore AI."""
import gradio as gr
import json
from pathlib import Path
from src.analysis import analyze_images, render_report
from src.diffusion import run_diffusion
from src.export import export_result
from src.honesty import DISCLAIMER, DIFFERENCE_NOTICE, difference_map

ROOT = Path(__file__).resolve().parent
THEME = gr.themes.Soft(primary_hue="teal", neutral_hue="slate", font=["Arial", "sans-serif"])


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


def load_recorded_result():
    """Abre evidencia preservada sin simular una nueva inferencia."""
    from PIL import Image

    folder = ROOT / "assets/ejemplos/etapa3_tile"
    before = Image.open(folder / "entrada_ruidosa.png").convert("RGB")
    after = Image.open(folder / "salida_tile.png").convert("RGB")
    analysis = json.loads((folder / "analisis_clip.json").read_text(encoding="utf-8"))
    metadata = dict(
        modo="ensayo_guardado_sin_nueva_inferencia",
        ensayo_original=json.loads((folder / "resultado_tile.json").read_text(encoding="utf-8")),
        analisis_visual=analysis,
        procedencia="NASA, ESA, and J. Comerford (University of Colorado-Boulder); CC BY 4.0; https://esahubble.org/images/potw1803a/",
    )
    report = "**Ensayo guardado: no se ejecutaron modelos al abrir esta vista.**\n\n" + render_report(analysis)
    source = str(folder / "entrada_ruidosa.png")
    archive = export_result(before, after, metadata, report, source)
    return before, after, (before, after), difference_map(before, after), metadata, report, archive, (before, after, metadata, source)


def create_app() -> gr.Blocks:
    """Construye la interfaz sin descargar modelos al iniciarse."""
    with gr.Blocks(title="AstroRestore AI", analytics_enabled=False) as app:
        gr.Markdown("EXPLORACIÓN ASTRONÓMICA · PROTOTIPO\n# AstroRestore AI\nCompará los cambios. Conservá tu original.", elem_id="cabecera")
        gr.Markdown("**Reconstrucción experimental con SD 1.5 + Tile.** Los ensayos actuales "
                    "no demostraron mejor limpieza que conservar la entrada ruidosa.")
        gr.Markdown(DISCLAIMER, elem_id="aviso-reconstruccion")
        gr.Markdown("## 1 · Prepará tu prueba\nPNG o TIFF de 8 bits. Se ajusta el tamaño sin ampliar resolución. "
                    "La primera prueba descarga varios GB; se recomienda GPU en Colab.")
        upload = gr.File(label="Subí tu imagen", file_types=[".png", ".tif", ".tiff"], type="filepath")
        gr.Examples([[str(ROOT / "assets/ruido_gaussiano/potw1803a_sigma0.03_seed123_size256/entrada_ruidosa.png")]],
                    inputs=[upload], label="O probá el ejemplo con ruido gaussiano", cache_examples=False,
                    example_labels=["Galaxias · sigma 0,03"])
        gr.Markdown("Ejemplo: [ESA/Hubble potw1803a](https://esahubble.org/images/potw1803a/). "
                    "NASA, ESA, and J. Comerford (University of Colorado-Boulder). "
                    "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). "
                    "Derivada RGB reducida, con ruido sintético sigma 0,03 y semilla 123.")
        with gr.Accordion("Ajustes de transformación · valores iniciales del ensayo", open=False):
            with gr.Row():
                strength = gr.Slider(0.1, 0.5, value=0.1, step=0.05, label="Intensidad de transformación", info="Más intensidad puede borrar o inventar detalles; no es porcentaje de ruido eliminado.")
                steps = gr.Slider(10, 30, value=30, step=1, label="Pasos configurados", info="Pasos efectivos = parte entera de pasos × intensidad. 30 × 0,10 = 3.")
                seed = gr.Number(value=42, precision=0, label="Semilla del modelo")
                size = gr.Dropdown([256, 512], value=256, label="Lado máximo (píxeles)")
        button = gr.Button("Procesar y comparar", variant="primary")
        recorded = gr.Button("Ver ensayo guardado · sin ejecutar modelos", variant="secondary")
        gr.Markdown("Tile usa la propia entrada como condición, con fuerza 1. "
                    "El filtro de seguridad está activo y puede bloquear una salida. "
                    "El análisis CLIP se ejecuta después de la difusión.")
        gr.Markdown("## 2 · Revisá lo que cambió\nObservá las mismas regiones antes de decidir si conservar la salida.")
        with gr.Row():
            prepared = gr.Image(label="Entrada preparada", interactive=False, format="png")
            processed = gr.Image(label="Reconstrucción por IA", interactive=False, format="png")
        comparison = gr.ImageSlider(label="Entrada (izquierda) / reconstrucción (derecha)", interactive=False, format="png")
        gr.Markdown("Mové el deslizador y examiná fondo, puntos luminosos y contornos. "
                    "La comparación usa la entrada convertida a RGB y ajustada de tamaño; se conserva el archivo original.")
        with gr.Accordion("Inspeccionar el mapa de diferencias", open=False):
            differences = gr.Image(label="Diferencias absolutas · escala fija 0–255", interactive=False, image_mode="L", format="png")
            gr.Markdown(DIFFERENCE_NOTICE)
        gr.Markdown("## 3 · Leé el informe y guardá la prueba")
        report = gr.Markdown("El informe orientativo de CLIP aparecerá después de procesar.")
        retry = gr.Button("Reintentar solo análisis visual")
        archive = gr.File(label="Descargar imágenes, informe y parámetros (ZIP)", interactive=False)
        with gr.Accordion("Ver parámetros y registro completo", open=False):
            metadata = gr.JSON(label="Registro de esta ejecución")
        state = gr.State()
        button.click(run_complete, inputs=[upload, strength, steps, seed, size],
                     outputs=[prepared, processed, comparison, differences, metadata, report, archive, state],
                     concurrency_limit=1, concurrency_id="procesamiento")
        retry.click(complete_analysis, inputs=[state], outputs=[report, metadata, archive],
                    concurrency_limit=1, concurrency_id="procesamiento")
        recorded.click(load_recorded_result,
                       outputs=[prepared, processed, comparison, differences, metadata, report, archive, state],
                       concurrency_limit=1, concurrency_id="procesamiento")
        upload.change(lambda: (None, None, None, None, None, "Procesá esta entrada para generar un informe.", None, None),
                      outputs=[prepared, processed, comparison, differences, metadata, report, archive, state], queue=False)
    app.queue(default_concurrency_limit=1)
    return app

def launch_app(**kwargs):
    """Comparte el mismo tema local y en Colab con Gradio 6."""
    return create_app().launch(theme=THEME, css_paths=ROOT / "assets/interfaz/tema.css", **kwargs)


if __name__ == "__main__":
    launch_app()
