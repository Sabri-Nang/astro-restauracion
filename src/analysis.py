"""Afinidades descriptivas CLIP; no miden restauración ni autenticidad."""
from functools import lru_cache
from PIL import Image
from src.diffusion import MODEL_CACHE

MODEL_ID = "openai/clip-vit-base-patch32"
MODEL_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
DESCRIPTIONS = (
    ("campo astronómico", "an astronomical photograph of stars and galaxies"),
    ("textura granulada", "an astronomical photograph with grainy noise"),
    ("fondo uniforme", "an astronomical photograph with a smooth background"),
    ("estructuras definidas", "an astronomical photograph with sharp stars and fine structures"),
    ("estructuras difusas", "an astronomical photograph with blurry diffuse structures"),
    ("textura artificial", "an astronomical photograph with artificial textures"),
)
LIMITS = (
    "CLIP compara afinidades con frases fijas en inglés. No mide ruido eliminado, "
    "calidad ni probabilidad de que la frase sea verdadera. No localiza cambios "
    "ni detecta estrellas inventadas. Su ajuste a 224 píxeles y recorte central "
    "pueden omitir los bordes. Revisá también el deslizador y las diferencias."
)

@lru_cache(maxsize=1)
def load_analyzer():
    """Carga diferida en CPU para conservar la GPU para difusión."""
    from transformers import CLIPImageProcessorPil, CLIPModel, CLIPProcessor, CLIPTokenizer
    options = dict(revision=MODEL_REVISION, cache_dir=str(MODEL_CACHE))
    processor = CLIPProcessor(
        image_processor=CLIPImageProcessorPil.from_pretrained(MODEL_ID, **options),
        tokenizer=CLIPTokenizer.from_pretrained(MODEL_ID, **options),
    )
    model = CLIPModel.from_pretrained(MODEL_ID, **options).to("cpu").eval()
    return processor, model


def analyze_images(before: Image.Image, after: Image.Image) -> dict:
    """Evalúa ambas imágenes con idénticas frases y preprocesamiento."""
    import torch
    import transformers
    if before.mode != "RGB" or after.mode != "RGB" or before.size != after.size:
        raise ValueError("El análisis requiere imágenes RGB de iguales dimensiones.")
    processor, model = load_analyzer()
    inputs = processor(text=[text for _, text in DESCRIPTIONS], images=[before, after],
                       return_tensors="pt", padding=True)
    with torch.inference_mode():
        output = model(**inputs)
        images, texts = output.image_embeds, output.text_embeds
        scores = (images / images.norm(dim=-1, keepdim=True)) @ (texts / texts.norm(dim=-1, keepdim=True)).T
    rows = []
    for index, (label, text) in enumerate(DESCRIPTIONS):
        initial, final = float(scores[0, index]), float(scores[1, index])
        rows.append(dict(descripcion=label, frase=text, entrada=initial,
                         salida=final, diferencia=final - initial))
    return dict(modelo=MODEL_ID, revision=MODEL_REVISION, licencia="MIT",
                dispositivo="cpu", precision="float32", torch=torch.__version__,
                transformers=transformers.__version__,
                preprocesamiento=processor.image_processor.to_dict(),
                afinidades=rows, limites=LIMITS)


def render_report(analysis: dict) -> str:
    """Describe números sin convertirlos en diagnósticos."""
    lines = ["### Lectura orientativa con CLIP", LIMITS]
    for row in analysis["afinidades"]:
        lines.append(f"- **{row['descripcion'].capitalize()}**: entrada {row['entrada']:.4f}; "
                     f"salida {row['salida']:.4f}; cambio {row['diferencia']:+.4f}.")
    lines.append("Un aumento significa mayor semejanza con esa frase, sin demostrar mejor limpieza. "
                 "Conservá el original y verificá fondo, estrellas y contornos en las mismas regiones. "
                 "No uses esta salida para mediciones científicas.")
    return "\n\n".join(lines)


def render_user_report(analysis: dict) -> str:
    """Lectura breve para cualquier persona; los detalles del modelo quedan en el registro."""
    rows = analysis["afinidades"]
    wording = {
        "estructuras difusas": "formas suaves y poco delimitadas",
        "fondo uniforme": "un fondo de aspecto uniforme",
        "textura granulada": "una textura de aspecto granulado",
        "estructuras definidas": "contornos de aspecto definido",
        "textura artificial": "texturas que pueden parecer poco naturales",
        "campo astronómico": "el aspecto de un campo de estrellas y galaxias",
    }

    def describe(labels):
        words = [wording.get(label, label) for label in labels]
        return " y ".join(words)

    lines = ["### Una mirada a tu imagen"]
    if rows:
        before = [row["descripcion"] for row in sorted(rows, key=lambda row: row["entrada"], reverse=True)[:2]]
        after = [row["descripcion"] for row in sorted(rows, key=lambda row: row["salida"], reverse=True)[:2]]
        if set(before) == set(after):
            lines.append(f"La lectura general sugiere {describe(before)} en ambas imágenes. "
                         "Esa impresión se mantiene, aunque puede haber cambios en los detalles.")
        else:
            lines.append(f"**En tu foto**, la lectura sugiere {describe(before)}.")
            lines.append(f"**En el resultado**, sugiere {describe(after)}.")
        if "textura artificial" in before + after:
            lines.append("Que una textura parezca poco natural no confirma que haya sido inventada.")
        lines.append("Es una impresión general de la apariencia: no confirma cuánto ruido se eliminó "
                     "ni qué detalles corresponden al cielo real.")
    else:
        lines.append("**No hay una lectura disponible para esta comparación.** Podés seguir revisando "
                     "las imágenes en el visor.")
    lines.append("**Dónde mirar:** recorré las mismas estrellas, contornos y zonas del fondo en ambas imágenes. "
                 "Si aparece un detalle nuevo, tomalo como **no verificado** hasta contrastarlo con "
                 "otra observación. El amarillo te ayuda a encontrar cambios; no identifica invenciones.")
    return "\n\n".join(lines)
