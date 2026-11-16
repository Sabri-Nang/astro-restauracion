"""Punto de entrada de la interfaz de AstroRestore AI."""
import gradio as gr
import json
from pathlib import Path
from src.analysis import analyze_images, render_report, render_user_report
from src.diffusion import run_diffusion
from src.export import export_result
from src.honesty import DISCLAIMER, HIGHLIGHT_NOTICE, difference_map, highlight_changes

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
        report = render_user_report(analysis)
    except (ImportError, ValueError, OSError, RuntimeError) as error:
        metadata["analisis_visual"] = {"estado": "error", "detalle": str(error)}
        report = ("### Análisis visual no disponible\n\nLa difusión terminó y sus imágenes se conservan. "
                  "Podés descargar el resultado o reintentar solo CLIP. No hay observaciones del modelo "
                  "de visión para esta ejecución. El detalle técnico queda en el registro descargable.")
    try:
        archive = export_result(before, after, metadata, report, path)
    except OSError as error:
        archive = None
        report += "\n\nNo se pudo preparar la descarga. Probá reintentar el informe y la descarga."
    return report, metadata, archive


def run_complete(path, strength, steps, seed, size, progress=gr.Progress()):
    """Recorrido completo; no calcula métricas sin referencia conocida."""
    progress(0.05, desc="Preparando la reconstrucción; la primera vez puede tardar más")
    result = process_image(path, strength, steps, seed, size)
    state = (result[0], result[1], result[4], path)
    progress(0.8, desc="Comparando las imágenes y preparando tu informe")
    report, metadata, archive = complete_analysis(state)
    state = (result[0], result[1], metadata, path)
    progress(1, desc="Resultado disponible")
    return (*result[:4], metadata, report, archive, state)


def review_image(state, show_changes=True):
    """Alterna la capa de revisión sin ejecutar modelos ni modificar la salida."""
    if not state:
        return None
    before, after, _, _ = state
    return highlight_changes(before, after) if show_changes else after.copy()


def run_for_user(path, strength, show_changes=True, progress=gr.Progress()):
    """Usa valores reproducibles del ensayo sin exponer controles técnicos."""
    result = run_complete(path, strength, 30, 42, 256, progress=progress)
    return result[2], review_image(result[7], show_changes), result[5], result[6], result[7]


def retry_for_user(state):
    """Actualiza el informe y su descarga sin volver a generar la imagen."""
    report, metadata, archive = complete_analysis(state)
    before, after, _, path = state
    return report, archive, (before, after, metadata, path)


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
        gr.Markdown("ASTROFOTOGRAFÍA · EXPLORACIÓN CON IA\n# AstroRestore AI\nCompará los cambios. Conservá tu original.", elem_id="cabecera")
        gr.Markdown("**Versión experimental.** Las pruebas realizadas todavía no demostraron "
                    "una mejor limpieza que conservar la foto de entrada.")
        gr.Markdown(DISCLAIMER, elem_id="aviso-reconstruccion")
        gr.Markdown("## 1 · Subí tu foto del cielo\nElegí una imagen PNG o TIFF. "
                    "Esta versión trabaja sobre una copia pequeña, de hasta 256 píxeles de lado. "
                    "La reconstrucción tendrá ese tamaño; tu archivo original se conserva intacto.")
        upload = gr.File(label="Tu foto astronómica", file_types=[".png", ".tif", ".tiff"], type="filepath")
        with gr.Accordion("¿Mi archivo es compatible?", open=False):
            gr.Markdown("Esta versión admite PNG y TIFF RGB de 8 bits por canal: 256 niveles de color "
                        "por canal. Esto no indica el peso del archivo ni la cantidad de píxeles. "
                        "Algunas herramientas astronómicas guardan TIFF de 16 bits. Si tu archivo "
                        "no es compatible, exportá desde tu editor una **copia RGB de 8 bits** "
                        "y conservá el original de mayor profundidad.")
        strength = gr.Slider(0.1, 0.5, value=0.1, step=0.05,
                             label="Cuánto puede cambiar la IA tu foto",
                             info="Empezá con un cambio pequeño. Aumentarlo permite modificar más detalles; no significa quitar más ruido.")
        button = gr.Button("Procesar y comparar", variant="primary")
        gr.Markdown("La primera vez puede tardar más mientras se prepara la IA. "
                    "Si una salida se bloquea, te avisaremos y tu original seguirá intacto.")
        gr.Markdown("## 2 · Compará y revisá los cambios\nUna imagen convincente puede contener "
                    "detalles generados. Revisá las mismas regiones antes de compartirla.")
        with gr.Row():
            comparison = gr.ImageSlider(label="Tu foto ajustada (izquierda) / reconstrucción IA (derecha)", interactive=False, format="png")
            highlighted = gr.Image(label="Zonas para revisar sobre la reconstrucción", interactive=False, format="png")
        show_changes = gr.Checkbox(label="Resaltar las zonas modificadas en amarillo", value=True)
        gr.Markdown(HIGHLIGHT_NOTICE, elem_id="leyenda-cambios")
        gr.Markdown("Mové el deslizador y compará estrellas, fondo y contornos. "
                    "La foto de entrada también se ajusta al tamaño de trabajo para comparar las mismas regiones.")
        gr.Markdown("## 3 · Leé el informe y guardá tu resultado")
        report = gr.Markdown("Después de procesar verás una lectura orientativa y recomendaciones para revisar tu imagen.")
        retry = gr.Button("Reintentar informe y descarga")
        archive = gr.File(label="Guardar resultado con informe (ZIP)", interactive=False)
        gr.Markdown("La descarga conserva tu original, la reconstrucción sin marcas y una copia "
                    "con las zonas resaltadas. Incluye el aviso de IA y los datos de la prueba, "
                    "por si necesitás revisarlos o compartirlos más adelante.")
        state = gr.State()
        button.click(run_for_user, inputs=[upload, strength, show_changes],
                     outputs=[comparison, highlighted, report, archive, state],
                     concurrency_limit=1, concurrency_id="procesamiento")
        retry.click(retry_for_user, inputs=[state], outputs=[report, archive, state],
                    concurrency_limit=1, concurrency_id="procesamiento")
        show_changes.change(review_image, inputs=[state, show_changes], outputs=[highlighted], queue=False)
        upload.change(lambda: (None, None, "Procesá esta foto para generar su informe.", None, None),
                      outputs=[comparison, highlighted, report, archive, state], queue=False)
    app.queue(default_concurrency_limit=1)
    return app

def launch_app(**kwargs):
    """Comparte el mismo tema local y en Colab con Gradio 6."""
    return create_app().launch(theme=THEME, css_paths=ROOT / "assets/interfaz/tema.css", **kwargs)


if __name__ == "__main__":
    launch_app()
