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
    """Interpreta las etiquetas seleccionadas sin convertir su orden en un diagnóstico."""
    rows = analysis["afinidades"]
    lines = [
        "### Lectura general de la imagen",
        "CLIP es el modelo que analiza la apariencia de las imágenes. Elige entre frases "
        "predefinidas; no escribe una descripción libre ni identifica objetos del cielo.",
    ]
    if rows:
        before = [row["descripcion"] for row in sorted(rows, key=lambda row: row["entrada"], reverse=True)[:2]]
        after = [row["descripcion"] for row in sorted(rows, key=lambda row: row["salida"], reverse=True)[:2]]

        def phrases(labels):
            return ", ".join(f"«{label}»" for label in labels)

        if set(before) == set(after):
            lines.append(f"**En esta comparación:** el modelo relacionó ambas imágenes con las mismas "
                         f"descripciones principales: {phrases(before)}.")
            lines.append("**Cómo interpretarlo:** estas etiquetas se mantienen, aunque sus puntuaciones "
                         "puedan variar. Eso no significa que las imágenes sean iguales ni que la limpieza "
                         "haya funcionado o fallado.")
        else:
            lines.append(f"**Foto cargada:** el modelo la relacionó principalmente con {phrases(before)}.")
            lines.append(f"**Reconstrucción con IA:** la relacionó principalmente con {phrases(after)}.")
            lines.append("**Cómo interpretarlo:** cambió la selección de descripciones generales. "
                         "Diferencias pequeñas en las puntuaciones pueden cambiar esa selección; "
                         "esto no demuestra una mejora ni una pérdida de calidad.")
        meanings = {
            "estructuras difusas": "«Estructuras difusas» puede corresponder a nebulosidad extendida; no significa necesariamente desenfoque.",
            "fondo uniforme": "«Fondo uniforme» no garantiza ausencia de ruido.",
            "textura granulada": "«Textura granulada» sugiere parecido con una apariencia de grano; no mide cuánto ruido hay.",
            "estructuras definidas": "«Estructuras definidas» no demuestra que se haya recuperado detalle real.",
            "textura artificial": "«Textura artificial» es una opción de comparación, no una detección de detalles inventados.",
            "campo astronómico": "«Campo astronómico» no identifica estrellas o galaxias concretas.",
        }
        explanations = [meanings[label] for label in dict.fromkeys(before + after) if label in meanings]
        if explanations:
            lines.append("**Qué significan esas palabras:**\n\n" + "\n".join(f"- {text}" for text in explanations))
        lines.append(
            "**Límite de esta lectura:** no permite concluir si disminuyó el ruido ni detectar "
            "invenciones. Puede omitir los bordes de la foto. Los valores técnicos quedan en el ZIP."
        )
    else:
        lines.append("**No hay una lectura disponible para esta comparación.** Esto no permite "
                     "sacar conclusiones sobre las imágenes; podés revisarlas en el visor.")
    lines.extend([
        "**Guía de revisión de la app (no es una conclusión de CLIP):** compará las mismas estrellas, "
        "contornos y zonas del fondo en el visor. Las marcas amarillas muestran cambios, no invenciones. "
        "Un detalle nuevo queda **no verificado** hasta contrastarlo con observaciones independientes.",
        "**Para compartir en clase:** mostrá la entrada junto al resultado e indicá «Reconstruida con IA». "
        "Conservá el original; la reconstrucción no sirve como prueba de un descubrimiento ni para mediciones científicas.",
    ])
    return "\n\n".join(lines)
