"""Prueba reproducible de difusión imagen a imagen, sin cargas al importar."""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
from time import perf_counter

from PIL import Image, ImageOps


MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"
MODEL_REVISION = "451f4fe16113bff5a5d2269ed5ad43b0592e9a14"
MODEL_LICENSE = "CreativeML OpenRAIL-M"
MODEL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "huggingface"
DEFAULT_PROMPT = "astronomical photograph, stars and galaxies"
DISCLAIMER = (
    "Prueba técnica de imagen a imagen. No demuestra reducción de ruido ni "
    "autenticidad científica. El modelo puede borrar o inventar estructuras. "
    "La intensidad controla la transformación generativa, no el ruido eliminado."
)


def prepare_image(path: str | Path, max_size: int = 256) -> Image.Image:
    """Lee PNG/TIFF de 8 bits y ajusta a múltiplos de ocho, sin recortar."""
    if max_size not in (256, 512):
        raise ValueError("El tamaño máximo debe ser 256 o 512 píxeles.")
    with Image.open(path) as source:
        if source.format not in ("PNG", "TIFF"):
            raise ValueError("Seleccioná una imagen PNG o TIFF.")
        bits = getattr(source, "tag_v2", {}).get(258, (8,))
        if isinstance(bits, int):
            bits = (bits,)
        if any(bit > 8 for bit in bits) or source.mode in ("I", "F") or source.mode.startswith("I;16"):
            raise ValueError(
                "La prueba admite imágenes de 8 bits por canal. Prepará una "
                "copia RGB de 8 bits y documentá la conversión; conservá el original."
            )
        if source.width < 64 or source.height < 64:
            raise ValueError("La imagen debe medir al menos 64 píxeles por lado.")
        image = ImageOps.exif_transpose(source).convert("RGB")
    scale = min(1.0, max_size / max(image.size))
    width = int(image.width * scale) // 8 * 8
    height = int(image.height * scale) // 8 * 8
    if min(width, height) < 64:
        raise ValueError("La relación de aspecto deja un lado menor a 64 píxeles.")
    return image.resize((width, height), Image.Resampling.LANCZOS)


@lru_cache(maxsize=1)
def load_pipeline(device: str = "auto"):
    """Carga la revisión fijada solo cuando se solicita procesar una imagen."""
    import torch
    from diffusers import DDIMScheduler, StableDiffusionImg2ImgPipeline

    if device not in ("auto", "cpu", "cuda"):
        raise ValueError("El dispositivo debe ser auto, cpu o cuda.")
    selected = "cuda" if device == "auto" and torch.cuda.is_available() else device
    if selected == "auto":
        selected = "cpu"
    if selected == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA no está disponible; utilizá CPU o un entorno GPU de Colab.")
    # La precisión reducida evita duplicar los pesos en float32 en equipos de 16 GB.
    dtype = torch.float16 if selected == "cuda" else torch.bfloat16
    pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        variant="fp16",
        dtype=dtype,
        use_safetensors=True,
        cache_dir=str(MODEL_CACHE),
    )
    pipeline.scheduler = DDIMScheduler.from_config(pipeline.scheduler.config)
    pipeline.vae.enable_slicing()
    pipeline.to(selected)
    return pipeline


def run_diffusion(
    path: str | Path,
    *,
    strength: float = 0.2,
    steps: int = 10,
    seed: int = 42,
    max_size: int = 256,
    device: str = "auto",
) -> tuple[Image.Image, Image.Image, dict]:
    """Ejecuta una prueba generativa y devuelve ambas imágenes y su registro."""
    if not 0 < strength <= 0.5:
        raise ValueError("La intensidad debe ser mayor a cero y como máximo 0,5.")
    if not isinstance(steps, int) or not 2 <= steps <= 50:
        raise ValueError("Los pasos deben ser un entero entre 2 y 50.")
    if int(steps * strength) < 1:
        raise ValueError("Aumentá los pasos o la intensidad para ejecutar al menos un paso efectivo.")
    if not isinstance(seed, int) or not 0 <= seed <= 2**32 - 1:
        raise ValueError("La semilla debe ser un entero entre 0 y 4294967295.")
    image = prepare_image(path, max_size)
    with Path(path).open("rb") as source:
        source_hash = hashlib.file_digest(source, "sha256").hexdigest()
    started = perf_counter()
    pipeline = load_pipeline(device)
    load_seconds = perf_counter() - started

    import torch

    generator = torch.Generator(device=pipeline.device).manual_seed(seed)
    started = perf_counter()
    with torch.inference_mode():
        result = pipeline(
            prompt=DEFAULT_PROMPT,
            image=image,
            strength=strength,
            num_inference_steps=steps,
            guidance_scale=1.0,
            generator=generator,
        )
    inference_seconds = perf_counter() - started
    if result.nsfw_content_detected and any(result.nsfw_content_detected):
        raise RuntimeError("El filtro de seguridad bloqueó la salida; no se guardó como prueba válida.")
    restored = result.images[0]
    metadata = {
        "tipo": "prueba_tecnica_img2img_no_evaluacion_de_denoising",
        "modelo": MODEL_ID,
        "revision": MODEL_REVISION,
        "licencia": MODEL_LICENSE,
        "entrada": Path(path).name,
        "sha256_entrada": source_hash,
        "dimensiones_preparadas": list(image.size),
        "preprocesamiento": "RGB 8 bits, LANCZOS, sin recorte, lados ajustados a múltiplos de 8",
        "ruido_artificial_agregado": False,
        "prompt": DEFAULT_PROMPT,
        "intensidad": strength,
        "pasos_configurados": steps,
        "pasos_efectivos": int(steps * strength),
        "guidance_scale": 1.0,
        "semilla": seed,
        "scheduler": type(pipeline.scheduler).__name__,
        "dispositivo": str(pipeline.device),
        "precision": str(pipeline.unet.dtype),
        "segundos_carga_o_acceso_cache_memoria": round(load_seconds, 3),
        "segundos_inferencia": round(inference_seconds, 3),
        "python": platform.python_version(),
        "sistema": platform.platform(),
        "versiones": {name: version(name) for name in ("torch", "diffusers", "transformers", "pillow")},
        "advertencia": DISCLAIMER,
    }
    return image, restored, metadata


def main() -> None:
    """Guarda una prueba y sus parámetros sin modificar la imagen de origen."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Imagen PNG o TIFF de 8 bits")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/prueba_diffusion"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--strength", type=float, default=0.2)
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size", type=int, choices=(256, 512), default=256)
    args = parser.parse_args()
    print(f"Modelo: {MODEL_ID}\nRevisión: {MODEL_REVISION}", flush=True)
    prepared, processed, metadata = run_diffusion(
        args.input, strength=args.strength, steps=args.steps, seed=args.seed,
        max_size=args.size, device=args.device,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    prepared.save(args.output_dir / "entrada_preparada.png")
    processed.save(args.output_dir / "salida.png")
    (args.output_dir / "parametros.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)
    print(f"Prueba guardada en: {args.output_dir.resolve()}", flush=True)


if __name__ == "__main__":
    main()
