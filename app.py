"""Punto de entrada de la interfaz de AstroRestore AI."""
import gradio as gr
import json
import hashlib
import os
import html
import queue
import threading
import time
import traceback
import sys
import argparse
from pathlib import Path
from PIL import UnidentifiedImageError
from src.analysis import analyze_images, render_report, render_user_report
from src.diffusion import prepare_image, run_diffusion
from src.diffbir_bridge import PHASES, get_session
from src.export import export_result
from src.honesty import difference_map, highlight_changes

ROOT = Path(__file__).resolve().parent
DEFAULT_ENGINE = "diffbir"
THEME = gr.themes.Soft(primary_hue="blue", neutral_hue="neutral", font=["Arial", "sans-serif"]).set(
    body_text_size="16px", body_background_fill="#f5f5f5", body_background_fill_dark="#f5f5f5",
    body_text_color="#171717", body_text_color_dark="#171717",
    body_text_color_subdued="#525252", color_accent="#1d4ed8", color_accent_soft="#eff6ff",
    link_text_color="#1d4ed8", link_text_color_hover="#1e40af", slider_color="#1d4ed8",
    checkbox_background_color_selected="#1d4ed8", checkbox_border_color_selected="#1d4ed8",
    checkbox_label_background_fill_selected="#eff6ff", checkbox_label_border_color_selected="#1d4ed8",
    checkbox_label_text_color_selected="#1e3a8a", loader_color="#1d4ed8",
    block_background_fill="#ffffff", block_background_fill_dark="#ffffff",
    button_primary_background_fill="#1d4ed8", button_primary_background_fill_dark="#1d4ed8",
    button_primary_background_fill_hover="#1e40af", button_primary_background_fill_hover_dark="#1e40af",
    button_primary_text_color="#ffffff", button_primary_text_color_dark="#ffffff",
)
# Un esquema claro coherente evita mezclar etiquetas oscuras con superficies claras.
_theme_tokens = THEME.to_dict()["theme"]
THEME.set(**{name: _theme_tokens[name.removesuffix("_dark")]
             for name in _theme_tokens if name.endswith("_dark") and name.removesuffix("_dark") in _theme_tokens})
REVIEW_PAIRS = [
    "Limpieza → reconstrucción",
    "Foto cargada → limpieza",
    "Foto cargada → reconstrucción",
]
REGIONS = ["Campo completo", "Centro", "Arriba izquierda", "Arriba derecha", "Abajo izquierda", "Abajo derecha"]
STATUS_STAGES = ["Preparar IA", "Limpiar", "Reconstruir", "Preparar descarga"]


def status_panel(phase="ready", elapsed=0, detail="Elegí una foto para comenzar.", steps=None):
    """Estado accesible y persistente; no convierte hitos arbitrarios en porcentajes."""
    stage = {"prepare": 0, "clean": 1, "prepare_reconstruction": 2, "reconstruct": 2, "finish": 3}.get(phase)
    labels = {"ready": "Lista para empezar", "queue": "En espera de procesamiento",
              "prepare": "Preparando la IA", "clean": "Aplicando limpieza",
              "prepare_reconstruction": "Preparando el modelo de reconstrucción",
              "reconstruct": "Generando reconstrucción", "finish": "Preparando comparación y descarga",
              "done": "Resultado disponible", "partial": "Imágenes disponibles · revisá el aviso", "error": "No se pudo terminar"}
    items = "".join(
        f'<li class="{"actual" if index == stage else ""}">{index + 1}. {label}</li>'
        for index, label in enumerate(STATUS_STAGES)
    )
    measured = ""
    if steps:
        completed, total = steps
        measured = (
            f'<p><strong>Reconstrucción: {completed}/{total} pasos ({completed * 100 // total} %)</strong></p>'
            f'<progress aria-label="Avance de la etapa de reconstrucción" value="{completed}" max="{total}"></progress>'
            '<p class="estado-ayuda">Porcentaje de esta etapa, no de ruido eliminado ni del trabajo completo.</p>'
        )
    timing = f"Tiempo transcurrido: {int(elapsed) // 60:02d}:{int(elapsed) % 60:02d}." if phase not in ("ready", "queue") else ""
    return (
        f'<section class="estado estado-{phase}" aria-label="Estado del procesamiento">'
        f'<div role="status" aria-live="polite" aria-atomic="true"><strong>{labels[phase]}</strong>'
        f'<p>{html.escape(detail)}</p>{measured}</div>'
        f'<p class="estado-tiempo">{timing}</p><ol class="etapas-proceso">{items}</ol></section>'
    )


def inspect_upload(path):
    """Valida antes de cargar modelos y conserva una vista de la copia de trabajo."""
    if not path:
        return None, "Subí una imagen PNG o TIFF RGB de 8 bits.", status_panel(), gr.update(interactive=False), None, "", None
    try:
        prepared = prepare_image(path, max_size=256)
    except (ValueError, OSError) as error:
        message = ("No pudimos abrir esta imagen. Algunos TIFF astronómicos de 32 bits no son compatibles. "
                   "Usá una copia PNG RGB de 8 bits y conservá el original.") if isinstance(error, UnidentifiedImageError) else str(error)
        return None, f"**Archivo no compatible.** {message}", status_panel("error", detail="No se inició la IA. Revisá el formato del archivo."), gr.update(interactive=False), None, "", None
    available = can_process_here()
    detail = ("Foto compatible. Podés iniciar el procesamiento." if available else
              "Foto compatible. Para procesarla con DiffBIR, abrí la aplicación en Colab con GPU. Esta sesión permite revisar la interfaz.")
    return (prepared, f"**Archivo listo.** Copia de trabajo: {prepared.width} × {prepared.height} píxeles. Tu archivo se conserva.",
            status_panel(detail=detail), gr.update(interactive=available), None, "", None)


def stream_processing(path, strength):
    """Publica estados mientras el motor trabaja; el panel no depende del bloque de resultados."""
    events = queue.Queue()
    started = time.monotonic()
    descriptions = {description: name for name, (_, description) in PHASES.items()}

    def progress(value, desc="", **_kwargs):
        if isinstance(value, tuple):
            events.put(("progress", "reconstruct", desc, value))
            return
        name = descriptions.get(desc)
        phase = {"primera_limpieza": "clean", "reconstruyendo": "reconstruct",
                 "ajustando_salida": "finish", "preparando_reconstruccion": "prepare_reconstruction"}.get(name, "prepare")
        if value == 0.8:
            phase = "finish"
        if value != 1:
            events.put(("progress", phase, desc, None))

    def work():
        try:
            events.put(("result", run_complete(path, strength, 30, 42, 256, progress=progress)))
        except Exception as error:
            try:
                log = ROOT / "logs"
                log.mkdir(exist_ok=True)
                with (log / "interfaz.log").open("a", encoding="utf-8") as output:
                    output.write(traceback.format_exc() + "\n")
            except OSError:
                pass  # Un fallo del registro no debe dejar a Julia esperando indefinidamente.
            events.put(("error", str(error) if isinstance(error, gr.Error) else
                        "El procesamiento se interrumpió. Revisá la conexión y el entorno de Colab antes de reintentar."))

    # La primera respuesta llega antes de crear el hilo o cargar modelos.
    phase, detail, steps = "prepare", "La primera vez puede necesitar descargar y cargar modelos. No hay una estimación de duración todavía.", None
    yield status_panel(phase, detail=detail), None, "", None, gr.update(interactive=False), gr.update(interactive=False)
    threading.Thread(target=work, daemon=True).start()
    while True:
        try:
            event = events.get(timeout=1)
        except queue.Empty:
            event = None
        elapsed = time.monotonic() - started
        if event and event[0] == "result":
            result = event[1]
            missing_analysis = result[4].get("analisis_visual", {}).get("estado") == "error"
            incomplete = missing_analysis or not result[6]
            detail = ("La imagen está disponible. La lectura o la descarga no pudieron completarse; podés reintentarlas sin procesar otra vez."
                      if incomplete else "Compará la misma región y revisá los detalles antes de compartir.")
            yield (status_panel("partial" if incomplete else "done", elapsed, detail), result[7], result[5], result[6],
                   gr.update(interactive=True), gr.update(interactive=can_process_here()))
            return
        if event and event[0] == "error":
            yield (status_panel("error", elapsed, event[1] + " Tu archivo original se conserva."), None, "", None,
                   gr.update(interactive=True), gr.update(interactive=can_process_here()))
            return
        if event:
            _, phase, detail, steps = event
        yield (status_panel(phase, elapsed, detail, steps), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip())


def workspace_pair(state, pair, show_changes=False, region="Campo completo", zoom="Ajustar"):
    """Misma región y ampliación para ambos lados; la capa es solo de revisión."""
    comparison, marked, explanation = compare_stages(state, pair, show_changes)
    if not comparison:
        return None, ""
    left, right = comparison
    if show_changes:
        right = marked
    width, height = left.size
    half_w, half_h = width // 2, height // 2
    boxes = {"Centro": ((width - half_w) // 2, (height - half_h) // 2),
             "Arriba izquierda": (0, 0), "Arriba derecha": (width - half_w, 0),
             "Abajo izquierda": (0, height - half_h), "Abajo derecha": (width - half_w, height - half_h)}
    if region in boxes:
        x, y = boxes[region]
        box = (x, y, x + half_w, y + half_h)
        left, right = left.crop(box), right.crop(box)
    if zoom == "Ampliar píxeles ×2":
        from PIL import Image
        target = (left.width * 2, left.height * 2)
        left, right = left.resize(target, Image.Resampling.NEAREST), right.resize(target, Image.Resampling.NEAREST)
    explanation += f"\n\n**Región: {region}.** {zoom}. Agrandar los píxeles no agrega información ni recupera detalle."
    return (left, right), explanation


def workspace_view(state, pair, show_changes=False, region="Campo completo", zoom="Ajustar"):
    if not state:
        return None, None, None, None, "", gr.update(visible=False)
    comparison, explanation = workspace_pair(state, pair, show_changes, region, zoom)
    return state[0], first_cleaning(state), state[1], comparison, explanation, gr.update(visible=True)


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
    """Mismo valor predeterminado en local y Colab; la variante histórica es explícita."""
    name = os.environ.get("ASTRORESTORE_ENGINE", DEFAULT_ENGINE)
    if name not in ("sd_tile", "diffbir"):
        raise ValueError("ASTRORESTORE_ENGINE debe ser sd_tile o diffbir.")
    return name


def can_process_here():
    """No confunde vista local con inferencia DiffBIR soportada en Windows."""
    return selected_engine() != "diffbir" or sys.platform == "linux"


def runtime_identity():
    """Huellas comparables de código y bloqueos; sin pesos, tokens ni datos personales."""
    files = ("app.py", "src/diffusion.py", "src/diffbir_bridge.py", "src/analysis.py", "src/honesty.py",
             "src/export.py", "assets/interfaz/tema.css", "uv.lock", "colab/diffbir/uv.lock")
    return {"motor": selected_engine(), "normalizacion": "Texto UTF-8 con saltos de línea LF",
            "sha256": {name: hashlib.sha256((ROOT / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest() for name in files}}


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
                  "Podés descargar el resultado o reintentar la lectura sin volver a procesar tu foto.")
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


def retry_workspace(state):
    """Reintenta lectura/exportación y actualiza el estado sin repetir difusión."""
    try:
        report, archive, updated = retry_for_user(state)
        incomplete = updated[2].get("analisis_visual", {}).get("estado") == "error" or not archive
        notice = status_panel("partial" if incomplete else "done", detail=(
            "Las imágenes se conservan. La lectura o la descarga siguen sin estar disponibles."
            if incomplete else "Lectura y descarga disponibles. No se volvió a procesar la imagen."
        ))
        return notice, report, archive, updated
    except Exception:
        return (status_panel("error", detail="No se pudo completar el reintento. Tus imágenes se conservan."),
                gr.skip(), gr.skip(), gr.skip())


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
    """Tres momentos: preparar, esperar con información y revisar antes de compartir."""
    diffbir = selected_engine() == "diffbir"
    with gr.Blocks(title="AstroRestore AI", analytics_enabled=False) as interface:
        gr.Markdown("ASTROFOTOGRAFÍA · COMPARACIÓN CON IA\n# AstroRestore AI\nRevisá tu foto, no solo su apariencia.", elem_id="cabecera")
        gr.Markdown("Restauración: **DiffBIR v2 · limpieza y reconstrucción**. Incluye una lectura visual orientativa." if diffbir else
                    "**Modo histórico: Stable Diffusion 1.5 + ControlNet Tile**. "
                    "Esta variante no ejecuta DiffBIR ni su limpieza intermedia.", elem_classes="texto-ayuda")
        if not can_process_here():
            gr.Markdown("**Vista local de la app.** Podés cargar y validar una foto. Para procesarla con este motor, "
                        "abrí la aplicación en **Colab con GPU**: la integración DiffBIR requiere Linux y CUDA. "
                        "Esta sesión no tiene habilitado el procesamiento.")
        gr.Markdown("**Más nítido no significa más real.** La IA puede agregar detalles o borrar estrellas tenues. "
                    "Compará los cambios antes de compartir; tu archivo original se conserva.", elem_id="aviso-reconstruccion")
        with gr.Row():
            with gr.Column(scale=1, min_width=280):
                gr.Markdown("## 1 · Prepará tu foto\nVamos a intentar reducir el ruido y generar una reconstrucción. "
                            "Después podrás comparar ambas etapas con tu foto." if diffbir else
                            "## 1 · Prepará tu foto\nVamos a generar una reconstrucción para comparar con tu entrada.")
                upload = gr.File(label="Tu foto astronómica", file_types=[".png", ".tif", ".tiff"], type="filepath")
                compatibility = gr.Markdown("Subí una imagen PNG o TIFF RGB de 8 bits.")
                with gr.Accordion("Formatos y tamaño de trabajo", open=False):
                    gr.Markdown("Esta versión admite PNG/TIFF de hasta 8 bits por canal. TIFF de 16 o 32 bits, "
                                "RAW y FITS no se convierten automáticamente. Conservá el original y usá una copia compatible. "
                                "Trabajamos con hasta **256 píxeles de lado**; no se genera una salida de mayor resolución.")
                if diffbir:
                    strength = gr.State(None)
                else:
                    strength = gr.Slider(0.1, 0.5, value=0.1, step=0.05, label="Cuánto puede cambiar la IA tu foto",
                                         info="No es un porcentaje de ruido eliminado.")
                button = gr.Button("Procesar foto", variant="primary", interactive=False)
            with gr.Column(scale=2, min_width=320):
                preview = gr.Image(label="Tu foto · copia de trabajo", interactive=False, format="png", height=260,
                                   elem_id="vista-entrada")
                status = gr.HTML(status_panel(), elem_id="estado-proceso")
        gr.Markdown("Durante la subida, el cargador muestra el estado de transferencia. Después, este panel indica la etapa "
                    "y el tiempo transcurrido. La primera preparación de IA puede tardar varios minutos. "
                    "Dejá abierta la celda de Colab.", elem_classes="texto-ayuda")
        with gr.Group(visible=False, elem_id="revision-resultado") as results:
            gr.Markdown("## 2 · Revisá qué cambió\nEstas imágenes pertenecen a la misma ejecución. "
                        "Cambiar la vista no vuelve a procesar tu foto.")
            with gr.Row():
                initial = gr.Image(label="1 · Foto cargada (copia reducida)", interactive=False, format="png", height=140,
                                   elem_classes="miniatura-etapa")
                first = gr.Image(label="2 · Limpieza (imagen intermedia)", interactive=False, format="png", height=140,
                                 visible=diffbir, elem_classes="miniatura-etapa")
                final = gr.Image(label="3 · Reconstrucción con IA" if diffbir else "Reconstrucción con IA",
                                 interactive=False, format="png", height=140, elem_classes="miniatura-etapa")
            gr.Markdown("**Foto cargada:** punto de partida, sin certificar autenticidad o procesamiento previo. "
                        "**Limpieza:** intenta reducir ruido y también puede suavizar detalles. "
                        "**Reconstrucción:** puede agregar texturas y formas plausibles." if diffbir else
                        "La foto cargada es el punto de partida; la reconstrucción puede agregar o modificar detalles.",
                        elem_classes="texto-ayuda")
            with gr.Row():
                with gr.Column(scale=3, min_width=320):
                    comparison = gr.ImageSlider(label="Comparación del par elegido", interactive=False, format="png",
                                                 height=460, elem_id="visor-principal")
                    explanation = gr.Markdown(elem_id="leyenda-cambios")
                with gr.Column(scale=1, min_width=270):
                    pair = gr.Radio(choices=REVIEW_PAIRS if diffbir else [REVIEW_PAIRS[2]], value=REVIEW_PAIRS[2],
                                    label="¿Qué querés comparar?")
                    focus_generation = gr.Button("Ver qué cambió después de la limpieza", visible=diffbir)
                    region = gr.Dropdown(REGIONS, value=REGIONS[0], label="Misma región en ambos lados", interactive=True)
                    zoom = gr.Radio(["Ajustar", "Ampliar píxeles ×2"], value="Ajustar", label="Ampliación de revisión")
                    show_changes = gr.Checkbox(label="Mostrar cambios en amarillo", value=False)
                    gr.Markdown("El amarillo aparece sobre la imagen de la **derecha**. "
                                "No identifica invenciones. Sin marcas tampoco significa ‘real’.")
                    gr.Markdown("### Tres preguntas para revisar\n"
                                "1. ¿Aparecieron puntos o formas que no distinguías en la entrada?\n"
                                "2. ¿Desaparecieron estrellas tenues o cambiaron contornos?\n"
                                "3. ¿Tenés otra observación independiente para contrastarlos?")
            gr.Markdown("**Detalle nuevo = no verificado.** Que algo aparezca solo en la reconstrucción no permite "
                        "afirmar que sea una estrella real ni demostrar que sea una invención. Necesitás otra observación "
                        "independiente del mismo campo para contrastarlo. Agrandar los píxeles no recupera información.",
                        elem_id="limites-verificacion")
            with gr.Accordion("Lectura general de la imagen · no verifica autenticidad", open=False):
                report = gr.Markdown()
            gr.Markdown("## 3 · Compartí con contexto\nSi compartís el resultado, mostrá la entrada junto a la salida "
                        "identificada como **Reconstruida con IA**. No la uses para mediciones ni como prueba de una estructura nueva.")
            archive = gr.File(label="Descargar imágenes e informe (ZIP)", interactive=False)
            retry = gr.Button("Reintentar lectura y preparar descarga")
            gr.Markdown("El ZIP incluye `para_compartir_con_aviso.png`, el archivo original y las etapas disponibles. "
                        "Su mapa amarillo compara **entrada y resultado final completos**, aunque aquí elijas otra región o par. "
                        "La copia sin marcas también es una reconstrucción de IA.", elem_classes="texto-ayuda")
        state = gr.State()
        upload.change(inspect_upload, inputs=[upload],
                      outputs=[preview, compatibility, status, button, state, report, archive], queue=False,
                      show_progress="hidden", api_name="preparar_foto")
        start = button.click(
            lambda: (None, "", None, status_panel("queue", detail="Solicitud recibida. Esperando un turno del motor."),
                     gr.update(interactive=False), gr.update(interactive=False), REVIEW_PAIRS[2]),
            outputs=[state, report, archive, status, upload, button, pair], queue=False, show_progress="hidden",
            api_name="iniciar_procesamiento",
        )
        start.then(stream_processing, inputs=[upload, strength], outputs=[status, state, report, archive, upload, button],
                   concurrency_limit=1, concurrency_id="procesamiento", show_progress="hidden", stream_every=0.1,
                   api_name="procesar_foto")
        retry_start = retry.click(
            lambda: (status_panel("finish", detail="Reintentando lectura y descarga. Las imágenes no se vuelven a generar."),
                     gr.update(interactive=False), gr.update(interactive=False)), outputs=[status, upload, button],
            queue=False, show_progress="hidden",
        )
        retry_job = retry_start.then(retry_workspace, inputs=[state], outputs=[status, report, archive, state],
                                     concurrency_limit=1, concurrency_id="procesamiento", show_progress="hidden",
                                     api_name="reintentar_lectura")
        retry_job.then(lambda: (gr.update(interactive=True), gr.update(interactive=can_process_here())),
                       outputs=[upload, button], queue=False)
        state.change(workspace_view, inputs=[state, pair, show_changes, region, zoom],
                     outputs=[initial, first, final, comparison, explanation, results], queue=False,
                     show_progress="hidden", api_name="mostrar_revision")
        for control in (pair, show_changes, region, zoom):
            control.change(workspace_pair, inputs=[state, pair, show_changes, region, zoom],
                           outputs=[comparison, explanation], queue=False, show_progress="hidden")
        focus_generation.click(lambda: REVIEW_PAIRS[0], outputs=[pair], queue=False)
    interface.queue(default_concurrency_limit=1)
    return interface


def launch_app(**kwargs):
    """Comparte el mismo tema local y en Colab con Gradio 6."""
    print("Identidad de la aplicación:", json.dumps(runtime_identity(), ensure_ascii=False), flush=True)
    return create_app().launch(theme=THEME, css_paths=ROOT / "assets/interfaz/tema.css", **kwargs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AstroRestore AI: DiffBIR es el motor predeterminado en todos los entornos.")
    parser.add_argument("--engine", choices=("diffbir", "sd_tile"), help="Seleccionar explícitamente el motor; sd_tile es la variante histórica.")
    args = parser.parse_args()
    if args.engine:
        os.environ["ASTRORESTORE_ENGINE"] = args.engine
    launch_app()
