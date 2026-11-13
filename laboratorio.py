"""Laboratorio Gradio de ruido y difusión, separado de la app de Julia."""

from pathlib import Path
import shutil
from uuid import uuid4

import gradio as gr
from PIL import Image, ImageOps

from src.diffusion import prepare_image
from src.experiment import file_hash, prepare_experiment, restore_experiment
from src.honesty import DISCLAIMER, amplified_difference, difference_map
from src.noise import add_gaussian_noise


NOISE_MAP = "Referencia frente a ruido"
MODEL_MAP = "Entrada ruidosa frente a salida"
TARGET_MAP = "Referencia frente a salida"
LAB_OUTPUTS = Path(__file__).resolve().parent / "outputs" / "laboratorio"


def show_map(state, selection, gain):
    """Cambia mapa o ganancia sin generar ruido ni ejecutar difusión."""
    if not state:
        return None, None, {}
    raw = state["maps"].get(selection)
    if raw is None:
        return None, None, {"aviso": "Este mapa requiere ejecutar difusión primero."}
    enhanced, stats = amplified_difference(raw, float(gain))
    return raw, enhanced, stats


def render_state(state, selection, gain):
    """Mantiene juntas las vistas que pertenecen a una misma entrada y semilla."""
    if not state:
        return (None, None, None, None, None, None, gr.update(choices=[NOISE_MAP], value=NOISE_MAP),
                None, None, {}, {}, None, "Subí una imagen para comenzar.")
    raw, enhanced, stats = show_map(state, selection, gain)
    last = state.get("restored")
    comparison = (state["noisy"], last) if last is not None else (state["reference"], state["noisy"])
    return (
        state, state["original"], state["reference"], state["noisy"], last,
        comparison, gr.update(choices=list(state["maps"]), value=selection),
        raw, enhanced, stats, state["record"], state.get("archive"), state["status"],
    )


def preview_noise(path, sigma, noise_seed, size, gain):
    """Actualiza el ruido al mover su control y descarta cualquier salida anterior."""
    if not path:
        return render_state(None, NOISE_MAP, gain)
    try:
        reference = prepare_image(path, int(size))
        noisy, noise_record = add_gaussian_noise(reference, sigma=float(sigma), seed=int(noise_seed))
        with Image.open(path) as source:
            original = ImageOps.exif_transpose(source).convert("RGB")
        state = {
            "path": str(path), "source_hash": file_hash(Path(path)),
            "sigma": float(sigma), "noise_seed": int(noise_seed), "size": int(size),
            "original": original, "reference": reference, "noisy": noisy,
            "maps": {NOISE_MAP: difference_map(reference, noisy)},
            "record": {"archivo": Path(path).name, "dimensiones_referencia": list(reference.size),
                       "ruido": noise_record, "inferencia_ejecutada": False},
            "status": "Ruido actualizado. No se ejecutó difusión. Una nueva imagen, sigma, semilla o tamaño descarta la salida anterior.",
        }
        return render_state(state, NOISE_MAP, gain)
    except (ValueError, OSError) as error:
        cleared = list(render_state(None, NOISE_MAP, gain))
        cleared[-1] = f"No se pudo preparar la imagen: {error}"
        return tuple(cleared)


def apply_diffusion(state, path, sigma, noise_seed, size, strength, steps, model_seed,
                    device, source_url, credit, license_name, gain):
    """Persiste una instantánea y procesa exactamente el ruido de la vista previa."""
    if not state or not path:
        raise gr.Error("Subí una imagen y revisá su copia con ruido antes de aplicar difusión.")
    try:
        current = (str(path), float(sigma), int(noise_seed), int(size))
        expected = (state["path"], state["sigma"], state["noise_seed"], state["size"])
        if current != expected or file_hash(Path(path)) != state["source_hash"]:
            raise ValueError("La entrada cambió. Esperá a que termine de actualizarse la vista del ruido.")
        folder = LAB_OUTPUTS / uuid4().hex
        provenance = {
            "archivo": Path(path).name, "fuente_declarada": source_url.strip(),
            "credito_declarado": credit.strip(), "licencia_declarada": license_name.strip(),
            "nota": "Procedencia declarada por quien realiza el ensayo; verificar antes de compartir.",
        }
        prepare_experiment(path, folder, sigma=state["sigma"], noise_seed=state["noise_seed"],
                           max_size=state["size"], provenance=provenance)
        with Image.open(folder / "entrada_ruidosa.png") as saved:
            if saved.tobytes() != state["noisy"].tobytes():
                raise ValueError("El ruido guardado no coincide con la vista previa; no se ejecutó difusión.")
        report = restore_experiment(folder, folder / "difusion", strength=float(strength),
                                    steps=int(steps), model_seed=int(model_seed), device=device)
        with Image.open(folder / "difusion/salida.png") as image:
            restored = image.copy()
        updated = dict(state)
        updated["restored"] = restored
        updated["maps"] = {
            NOISE_MAP: state["maps"][NOISE_MAP],
            MODEL_MAP: difference_map(state["noisy"], restored),
            TARGET_MAP: difference_map(state["reference"], restored),
        }
        updated["record"] = report
        updated["archive"] = shutil.make_archive(str(folder / "ensayo"), "zip", folder / "difusion")
        # El ZIP reúne referencia, ruido y salida, además de los registros.
        from zipfile import ZipFile

        with ZipFile(updated["archive"], "a") as archive:
            for name in ("referencia_preparada.png", "entrada_ruidosa.png", "experimento.json",
                         "diferencias_referencia_ruido.png", "comparacion_referencia_ruido.png"):
                archive.write(folder / name, name)
        updated["status"] = (
            f"Difusión ejecutada: intensidad {float(strength):g}, {int(steps)} pasos configurados, "
            f"semilla IA {int(model_seed)}. La evaluación visual sigue pendiente."
        )
        return render_state(updated, MODEL_MAP, gain)
    except (ValueError, OSError, RuntimeError) as error:
        raise gr.Error(str(error)) from error


def create_lab() -> gr.Blocks:
    """Construye un entorno experimental sin cargar modelos al importar o iniciar."""
    with gr.Blocks(title="AstroRestore · Laboratorio de ruido") as lab:
        gr.Markdown("# Laboratorio de ruido gaussiano y difusión")
        gr.Markdown(
            "Entorno experimental separado de la app de Julia. Cargá tu imagen, mové sigma "
            "para inspeccionar el ruido y pulsá el botón de difusión solo cuando quieras procesarlo. "
            "El modelo se carga únicamente al pulsar ese botón. No se calculan PSNR ni SSIM."
        )
        gr.Markdown(DISCLAIMER)
        state = gr.State()
        upload = gr.File(label="Imagen propia (PNG o TIFF de 8 bits)",
                         file_types=[".png", ".tif", ".tiff"], type="filepath")
        with gr.Row():
            sigma = gr.Slider(0, 0.2, value=0.03, step=0.005, label="Sigma gaussiana (escala 0–1)")
            noise_seed = gr.Number(value=123, precision=0, label="Semilla del ruido")
            size = gr.Dropdown([256, 512], value=256, label="Lado máximo de la referencia (px)")
        with gr.Accordion("Original cargada y procedencia", open=False):
            original = gr.Image(label="Archivo original en RGB, sin reducir", interactive=False, format="png")
            source_url = gr.Textbox(label="Fuente o URL (si es propia, indicarlo)")
            credit = gr.Textbox(label="Crédito o autoría")
            license_name = gr.Textbox(label="Licencia o permiso de uso")
        with gr.Row():
            reference = gr.Image(label="1. Original preparada (referencia del ensayo)", interactive=False, format="png")
            noisy = gr.Image(label="2. Copia con ruido gaussiano", interactive=False, format="png")
            restored = gr.Image(label="3. Última salida de difusión", interactive=False, format="png")
        gr.Markdown("La referencia se convierte a RGB y se ajusta de tamaño antes de agregar ruido; el archivo original se conserva.")
        with gr.Row():
            strength = gr.Slider(0.1, 0.5, value=0.2, step=0.05, label="Intensidad de transformación del modelo")
            steps = gr.Slider(10, 50, value=30, step=1, label="Pasos configurados")
            model_seed = gr.Number(value=42, precision=0, label="Semilla del modelo")
            device = gr.Dropdown(["cuda", "cpu"], value="cuda", label="Dispositivo (CUDA en Colab; CPU puede ser lenta)")
        button = gr.Button("Aplicar difusión a la copia ruidosa", variant="primary")
        status = gr.Markdown("Subí una imagen para comenzar.")
        comparison = gr.ImageSlider(label="Antes de difusión: referencia / ruido. Después: ruido / salida",
                                    interactive=False, format="png")
        with gr.Row():
            selection = gr.Dropdown([NOISE_MAP], value=NOISE_MAP, label="Par de imágenes para el mapa")
            gain = gr.Slider(1, 64, value=16, step=1, label="Ganancia solo visual (multiplicación del mapa)")
        with gr.Row():
            raw = gr.Image(label="Mapa absoluto: escala fija 0–255", interactive=False, image_mode="L", format="png")
            enhanced = gr.Image(label="Mapa amplificado: valor × ganancia, recortado a 255", interactive=False, image_mode="L", format="png")
        gr.Markdown(
            "Un mapa oscuro puede contener diferencias pequeñas. La vista amplificada cambia solo "
            "su presentación y puede saturarse; no modifica las imágenes ni el mapa absoluto. "
            "Estos mapas muestran diferencias de píxeles, no autenticidad ni eficacia de restauración."
        )
        stats = gr.JSON(label="Valores del mapa y ganancia visual")
        record = gr.JSON(label="Parámetros del ruido y de la última ejecución")
        download = gr.File(label="Descargar ensayo completo (disponible después de difusión)", interactive=False)
        outputs = [state, original, reference, noisy, restored, comparison, selection,
                   raw, enhanced, stats, record, download, status]
        gr.on(
            triggers=[upload.change, sigma.input, noise_seed.change, size.change],
            fn=preview_noise, inputs=[upload, sigma, noise_seed, size, gain], outputs=outputs,
            concurrency_id="laboratorio", concurrency_limit=1, trigger_mode="always_last",
        )
        button.click(
            apply_diffusion,
            inputs=[state, upload, sigma, noise_seed, size, strength, steps, model_seed,
                    device, source_url, credit, license_name, gain], outputs=outputs,
            concurrency_id="laboratorio", concurrency_limit=1,
        )
        gr.on(triggers=[selection.input, gain.input], fn=show_map,
              inputs=[state, selection, gain], outputs=[raw, enhanced, stats],
              concurrency_id="laboratorio", concurrency_limit=1, trigger_mode="always_last")
    return lab.queue(default_concurrency_limit=1)


if __name__ == "__main__":
    create_lab().launch()
