"""Punto de entrada de la interfaz de AstroRestore AI."""
import gradio as gr
import json
import hashlib
import os
from pathlib import Path
from PIL import UnidentifiedImageError
from src.analysis import analyze_images, render_report, render_user_report
from src.diffusion import prepare_image, run_diffusion
from src.diffbir_bridge import get_session
from src.export import export_result
from src.honesty import difference_map, highlight_changes

ROOT = Path(__file__).resolve().parent
THEME = gr.themes.Soft(primary_hue="teal", neutral_hue="slate", font=["Arial", "sans-serif"])
REVIEW_PAIRS = [
    "Limpieza → reconstrucción",
    "Foto cargada → limpieza",
    "Foto cargada → reconstrucción",
]


def compare_stages(state, pair, show_changes=True):
    """Compara el par elegido; las marcas siempre usan esas mismas imágenes."""
    if not state:
        return None, None, ""
    before, after, _, _ = state
    first = first_cleaning(state) if pair != REVIEW_PAIRS[2] else None
    if pair == REVIEW_PAIRS[0] and first is not None:
        left, right = first, after
        explanation = (
            "**Izquierda: 2 · Limpieza. Derecha: 3 · Reconstrucción con IA.** "
            "Observá qué apareció, desapareció o cambió de forma después de la limpieza. "
            "Esta comparación incluye los ajustes de tamaño y color de esa etapa; "
            "no aísla únicamente lo generado por difusión."
        )
    elif pair == REVIEW_PAIRS[1] and first is not None:
        left, right = before, first
        explanation = (
            "**Izquierda: 1 · Foto cargada. Derecha: 2 · Limpieza.** "
            "Revisá si disminuyó el grano y si se perdieron puntos tenues o contornos. "
            "La limpieza también usa IA y puede borrar o modificar detalles."
        )
    else:
        left, right = before, after
        explanation = (
            "**Izquierda: 1 · Foto cargada. Derecha: Reconstrucción con IA.** "
            "Muestra el cambio total del proceso; no separa limpieza y reconstrucción."
        )
        if pair != REVIEW_PAIRS[2]:
            explanation = "**La limpieza intermedia no está disponible.** " + explanation
    explanation += (
        "\n\n**Amarillo:** cambios entre las dos imágenes seleccionadas, sobre la imagen de la derecha. "
        "No significa ‘inventado’. Sin marcas tampoco significa ‘real’."
    )
    return (left, right), highlight_changes(left, right) if show_changes else right.copy(), explanation


def show_review(state, pair, show_changes=True):
    """Actualiza las etapas y oculta resultados al cambiar de archivo o iniciar otra prueba."""
    if not state:
        return None, None, None, None, None, "", gr.update(visible=False)
    comparison, highlighted, explanation = compare_stages(state, pair, show_changes)
    return state[0], first_cleaning(state), state[1], comparison, highlighted, explanation, gr.update(visible=True)


def run_for_review(path, strength, progress=gr.Progress()):
    """Entrega una sola ejecución a la revisión; cambiar de vista no vuelve a inferir."""
    result = run_complete(path, strength, 30, 42, 256, progress=progress)
    return result[7], result[5], result[6]


def selected_engine():
    """El notebook configura DiffBIR; se conserva SD/Tile para CPU local e historial."""
    name = os.environ.get("ASTRORESTORE_ENGINE", "sd_tile")
    if name not in ("sd_tile", "diffbir"):
        raise ValueError("ASTRORESTORE_ENGINE debe ser sd_tile o diffbir.")
    return name


def process_image(path, strength, steps, seed, size, progress=None):
    """Procesa una foto propia con el motor configurado; no inventa una referencia."""
    if not path:
        raise gr.Error("Subí una imagen PNG o TIFF antes de ejecutar la prueba.")
    try:
        if selected_engine() == "diffbir":
            prepared = prepare_image(path, max_size=256)
            prepared, processed, metadata = get_session().infer(prepared, progress=progress or (lambda *_a, **_k: None))
            metadata["sha256_original"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        else:
            prepared, processed, metadata = run_diffusion(
                path, strength=float(strength), steps=int(steps),
                seed=int(seed), max_size=int(size), controlnet_tile=True, controlnet_scale=1.0,
            )
        return prepared, processed, (prepared, processed), difference_map(prepared, processed), metadata
    except UnidentifiedImageError as error:
        raise gr.Error(
            "No pudimos abrir esta imagen. Puede ser un TIFF con una profundidad o codificación "
            "no compatible, un archivo incompleto o un formato distinto del indicado por su nombre. "
            "Probá con una copia PNG RGB de 8 bits y conservá el original. "
            "El procesamiento con IA no llegó a comenzar."
        ) from error
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
    except (OSError, ValueError) as error:
        archive = None
        report += "\n\nNo se pudo preparar la descarga. Probá reintentar el informe y la descarga."
    return report, metadata, archive


def run_complete(path, strength, steps, seed, size, progress=gr.Progress()):
    """Recorrido completo; no calcula métricas sin referencia conocida."""
    progress(0.05, desc="Preparando la reconstrucción; la primera vez puede tardar más")
    result = process_image(path, strength, steps, seed, size, progress=progress)
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


def first_cleaning(state):
    """Vista opcional de la primera etapa, sin ejecutar modelos ni cambiar el estado."""
    if not state:
        return None
    path = state[2].get("intermedios", {}).get("limpieza_previa.png")
    if not path:
        return None
    from PIL import Image
    try:
        with Image.open(path) as image:
            return image.copy()
    except OSError:
        return None


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
    diffbir = selected_engine() == "diffbir"
    with gr.Blocks(title="AstroRestore AI", analytics_enabled=False) as app:
        gr.Markdown("ASTROFOTOGRAFÍA PARA EXPLORAR Y ENSEÑAR\n# AstroRestore AI\nLimpiá una copia. Revisá lo que cambió.", elem_id="cabecera")
        gr.Markdown(
            "**Versión experimental.** En una imagen de prueba mejoró el parecido global, "
            "pero también cambió formas de galaxias. Revisá los detalles antes de compartirla."
            if diffbir else
            "**Versión experimental.** Las pruebas realizadas todavía no demostraron una mejor limpieza que conservar la foto de entrada."
        )
        gr.Markdown("**Más nítido no significa más real.** La IA puede agregar detalles o borrar estrellas tenues. "
                    "Te ayudamos a comparar; no podemos certificar qué pertenece al cielo. Tu archivo original se conserva.",
                    elem_id="aviso-reconstruccion")
        gr.Markdown("## 1 · Subí tu foto del cielo\nElegí una imagen PNG o TIFF. "
                    "Esta versión trabaja sobre una copia pequeña, de hasta 256 píxeles de lado. "
                    "La reconstrucción tendrá ese tamaño; tu archivo original se conserva intacto.")
        upload = gr.File(label="Tu foto astronómica", file_types=[".png", ".tif", ".tiff"], type="filepath")
        with gr.Accordion("¿Mi archivo es compatible?", open=False):
            gr.Markdown("Esta versión admite PNG y TIFF RGB de 8 bits por canal: 256 niveles de color "
                        "por canal. Esto no indica el peso del archivo ni la cantidad de píxeles. "
                        "Algunas herramientas astronómicas guardan TIFF de 16 o 32 bits. Si tu archivo "
                        "no es compatible, exportá desde tu editor una **copia RGB de 8 bits** "
                        "y conservá el original de mayor profundidad.")
        if diffbir:
            strength = gr.State(None)
            gr.Markdown("**Tu recorrido:** foto cargada → limpieza → reconstrucción con IA → revisión. "
                        "Al terminar vas a ver las tres imágenes juntas. Ambas etapas de procesamiento usan IA; "
                        "la reconstrucción generativa puede agregar estructuras plausibles.")
        else:
            strength = gr.Slider(0.1, 0.5, value=0.1, step=0.05,
                                 label="Cuánto puede cambiar la IA tu foto",
                                 info="Empezá con un cambio pequeño. Aumentarlo permite modificar más detalles; no significa quitar más ruido.")
        button = gr.Button("Procesar y comparar", variant="primary")
        gr.Markdown("La primera vez puede tardar varios minutos mientras se prepara la IA. "
                    "Si no puede terminar, te avisaremos y tu original seguirá intacto.")
        with gr.Group(visible=False, elem_id="revision-resultado") as results:
            gr.Markdown("## 2 · Seguí los cambios, paso a paso\n"
                        "El procesamiento ya terminó. Estas son imágenes guardadas de **la misma ejecución**; "
                        "mirarlas o cambiar de comparación no vuelve a procesar tu foto.")
            with gr.Row():
                with gr.Column(min_width=220):
                    gr.Markdown("### 1 · Foto cargada\nPunto de partida, ajustado al tamaño de trabajo. "
                                "No certificamos su autenticidad ni su procesamiento previo.")
                    initial = gr.Image(label="1 · Foto cargada (copia reducida)", interactive=False, format="png")
                with gr.Column(min_width=220, visible=diffbir):
                    gr.Markdown("### 2 · Limpieza\nIA orientada a reducir ruido, antes de la etapa generativa. "
                                "También puede suavizar o borrar detalles.")
                    first = gr.Image(label="2 · Limpieza (imagen intermedia)", interactive=False, format="png")
                with gr.Column(min_width=220):
                    gr.Markdown("### 3 · Reconstrucción con IA\nResultado final. Puede agregar texturas "
                                "y formas que no estaban registradas en tu foto." if diffbir else
                                "### Reconstrucción con IA\nResultado final. Puede agregar o modificar detalles.")
                    final = gr.Image(label="3 · Reconstrucción con IA" if diffbir else "Reconstrucción con IA",
                                     interactive=False, format="png")
            gr.Markdown("### ¿Qué aportó la reconstrucción?\n"
                        "Empezá por comparar la limpieza con el resultado final." if diffbir else
                        "### ¿Qué cambió respecto de tu foto?")
            pair = gr.Radio(choices=REVIEW_PAIRS if diffbir else [REVIEW_PAIRS[2]],
                            value=REVIEW_PAIRS[0] if diffbir else REVIEW_PAIRS[2],
                            label="Elegí qué imágenes comparar")
            explanation = gr.Markdown(elem_id="leyenda-cambios")
            with gr.Row():
                comparison = gr.ImageSlider(label="Comparación: izquierda / derecha según la leyenda",
                                             interactive=False, format="png")
                highlighted = gr.Image(label="Cambios del par elegido, sobre la imagen de la derecha",
                                       interactive=False, format="png")
            show_changes = gr.Checkbox(label="Mostrar en amarillo dónde cambió el par elegido", value=True)
            gr.Markdown("Mové la línea divisoria sobre **la misma estrella, contorno o zona del fondo**. "
                        "El amarillo es una guía de diferencias de píxeles, no una medida de confianza.")
            gr.Markdown("### ¿Qué puedo decir sobre lo inventado?\n"
                        "**Podés comprobar:** que un punto apareció, desapareció o cambió respecto de la otra imagen.\n\n"
                        "**No podemos confirmar:** si ese punto corresponde a una estrella real o a una estructura generada. "
                        "Un detalle visible solo en la reconstrucción debe tratarse como **no verificado**, no como un descubrimiento.\n\n"
                        "**Para verificarlo:** buscá otra observación independiente del mismo campo. "
                        "Comparar con tu entrada ayuda a revisar cambios, pero no confirma lo que ya no se distingue en ella.",
                        elem_id="limites-verificacion")
            gr.Markdown("**Antes de usarla en clase:** revisá puntos luminosos y sus posiciones, contornos de nebulosas "
                        "y galaxias, y texturas del fondo. Si hay dudas, mostrá la foto cargada junto al resultado "
                        "y explicá la intervención de IA.")
            gr.Markdown("## 3 · Consultá la lectura de IA y guardá la comparación")
            with gr.Accordion("Lectura orientativa de la foto · no detecta invenciones", open=False):
                gr.Markdown("Este modelo de visión describe semejanzas generales. No localiza estrellas "
                            "nuevas ni confirma que una estructura sea real.")
                report = gr.Markdown()
                retry = gr.Button("Reintentar lectura y preparar descarga")
            archive = gr.File(label="Descargar imágenes e informe (ZIP)", interactive=False)
            gr.Markdown("Para compartir, usá **para_compartir_con_aviso.png**, identificada como «Reconstruida con IA», "
                        "junto a tu foto de entrada. El ZIP conserva el original, las etapas disponibles y el informe. "
                        "Su mapa amarillo compara **foto cargada frente a resultado final**, independientemente de la vista elegida aquí. "
                        "No uses la reconstrucción para mediciones ni como prueba de una estructura astronómica.")
        state = gr.State()
        start = button.click(
            lambda: (None, "", None, gr.update(interactive=False), gr.update(interactive=False)),
            outputs=[state, report, archive, upload, button], queue=False,
        )
        processing = start.then(run_for_review, inputs=[upload, strength], outputs=[state, report, archive],
                                concurrency_limit=1, concurrency_id="procesamiento")
        # También se habilitan tras un error; durante el trabajo no se mezcla otra foto.
        processing.then(lambda: (gr.update(interactive=True), gr.update(interactive=True)),
                        outputs=[upload, button], queue=False)
        retry.click(retry_for_user, inputs=[state], outputs=[report, archive, state],
                    concurrency_limit=1, concurrency_id="procesamiento")
        state.change(show_review, inputs=[state, pair, show_changes],
                     outputs=[initial, first, final, comparison, highlighted, explanation, results], queue=False)
        for control in (pair, show_changes):
            control.change(compare_stages, inputs=[state, pair, show_changes],
                           outputs=[comparison, highlighted, explanation], queue=False)
        upload.change(lambda: (None, "", None), outputs=[state, report, archive], queue=False)
    app.queue(default_concurrency_limit=1)
    return app

def launch_app(**kwargs):
    """Comparte el mismo tema local y en Colab con Gradio 6."""
    return create_app().launch(theme=THEME, css_paths=ROOT / "assets/interfaz/tema.css", **kwargs)


if __name__ == "__main__":
    launch_app()
